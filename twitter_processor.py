# twitter_processor.py - Twitter content scraper integrated with the existing system

import os
import time
import requests
import logging
import json
import sys
import re  # Moved import to the top
from datetime import datetime
from playwright.sync_api import sync_playwright
from config import BASE_DIR

# Safe logging setup for Windows compatibility
class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that safely handles Unicode characters on Windows"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            replacements = {
                '✓': '[OK]', '✗': '[FAIL]', '→': '->', '←': '<-',
                '✔': '[OK]', '✖': '[FAIL]', '•': '*', '…': '...'
            }
            for unicode_char, replacement in replacements.items():
                msg = msg.replace(unicode_char, replacement)
            
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
                stream.flush()
            except UnicodeEncodeError:
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                stream.write(safe_msg + self.terminator)
                stream.flush()
        except Exception:
            self.handleError(record)

def setup_twitter_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    file_handler = logging.FileHandler('twitter_scraper.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)
    
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

class TwitterScraper:
    def __init__(self):
        self.logger = setup_twitter_logging()
        self.downloads_dir = os.path.join(BASE_DIR, 'downloads', 'twitter')
        self.handles_file = os.path.join(BASE_DIR, 'handletwitter.txt')
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.logger.info("Twitter scraper initialized")
    
    def download_file(self, url, path):
        """Download a file from URL with proper headers"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://twitter.com"
            }
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            if response.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                file_size = os.path.getsize(path) / (1024 * 1024)
                self.logger.info(f"[OK] Downloaded: {os.path.basename(path)} ({file_size:.1f} MB)")
                return True
            else:
                self.logger.error(f"Failed to download {url}: HTTP {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return False
    
    def extract_tweet_metadata(self, tweet_element):
        """Extract metadata from a tweet element"""
        metadata = {'text': '', 'hashtags': [], 'mentions': [], 'likes': 0, 'retweets': 0, 'replies': 0, 'timestamp': ''}
        
        try:
            text_selectors = ["div[lang] span", "div[data-testid='tweetText'] span", "div[dir='ltr'] span"]
            tweet_text = ""
            for selector in text_selectors:
                text_elements = tweet_element.query_selector_all(selector)
                full_text = " ".join([el.inner_text().strip() for el in text_elements])
                if len(full_text) > len(tweet_text):
                    tweet_text = full_text
            metadata['text'] = tweet_text
            
            if tweet_text:
                words = tweet_text.split()
                metadata['hashtags'] = list(set([word for word in words if word.startswith('#')]))
                metadata['mentions'] = list(set([word for word in words if word.startswith('@')]))
            
            # Extract engagement from aria-label
            buttons = tweet_element.query_selector_all("button[data-testid]")
            for button in buttons:
                label = button.get_attribute("aria-label") or ""
                numbers = re.findall(r'[\d,]+', label)
                if not numbers: continue
                count = int(numbers[0].replace(',', ''))
                
                if "like" in label.lower(): metadata['likes'] = count
                elif "retweet" in label.lower(): metadata['retweets'] = count
                elif "reply" in label.lower(): metadata['replies'] = count
            
            time_element = tweet_element.query_selector("time")
            if time_element:
                metadata['timestamp'] = time_element.get_attribute("datetime")
        except Exception as e:
            self.logger.debug(f"Could not extract full tweet metadata: {e}")
        return metadata
    
    def scrape_twitter_handle(self, handle):
        """Scrape Twitter posts from a specific handle (more robust version)"""
        self.logger.info(f"Starting Twitter scrape for: @{handle}")
        results = {'handle': handle, 'tweets_scraped': [], 'errors': [], 'total_media_downloaded': 0}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
                page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                page.set_default_timeout(60000)

                self.logger.info(f"Navigating to Twitter profile: @{handle}")
                page.goto(f"https://twitter.com/{handle}", wait_until="domcontentloaded")
                time.sleep(5) # Allow time for dynamic content to load

                page_content = page.content().lower()
                if "this account doesn" in page_content or "page doesn't exist" in page_content:
                    results['errors'].append(f"Twitter profile @{handle} not found")
                    browser.close()
                    return results

                handle_folder = os.path.join(self.downloads_dir, handle)
                os.makedirs(handle_folder, exist_ok=True)

                processed_tweet_ids = set()
                tweet_count = 0
                max_tweets_to_process = 10
                
                for _ in range(5): # Scroll up to 5 times to load content
                    if tweet_count >= max_tweets_to_process:
                        break
                    
                    # --- FIX 1: Using a more stable selector to find tweets ---
                    articles = page.query_selector_all('article[role="article"]')
                    
                    if not articles:
                        self.logger.warning("No tweet articles found on this scroll. The page structure may have changed.")
                    
                    for article in articles:
                        if tweet_count >= max_tweets_to_process:
                            break

                        link_element = article.query_selector("a[href*='/status/']")
                        if not link_element:
                            continue
                        
                        tweet_id_path = link_element.get_attribute('href')
                        if tweet_id_path in processed_tweet_ids:
                            continue

                        metadata = self.extract_tweet_metadata(article)
                        media_elements = article.query_selector_all("img[src*='pbs.twimg.com/media'], video")
                        
                        # --- FIX 2: Process a tweet if it has text OR media ---
                        if not metadata.get('text') and not media_elements:
                            continue # Skip tweets that are empty (e.g., deleted quote tweets)
                        
                        processed_tweet_ids.add(tweet_id_path)
                        downloaded_media = []

                        if media_elements:
                            for media_element in media_elements:
                                src = media_element.get_attribute('src')
                                if not src: continue
                                
                                ext = 'mp4' if media_element.tag_name == 'video' else 'jpg'
                                if "pbs.twimg.com/media" in src:
                                    src = src.split("?")[0] + "?format=jpg&name=large"

                                media_filename = os.path.join(handle_folder, f"{tweet_id_path.split('/')[-1]}_{len(downloaded_media)}.{ext}")
                                if self.download_file(src, media_filename):
                                    downloaded_media.append({
                                        'type': 'video' if ext == 'mp4' else 'image',
                                        'path': media_filename,
                                        'url': src
                                    })

                        tweet_count += 1
                        tweet_data = {
                            'tweet_id': tweet_id_path.split('/')[-1], 'handle': handle, 'text': metadata['text'],
                            'hashtags': metadata['hashtags'], 'mentions': metadata['mentions'], 'media': downloaded_media,
                            'engagement': {'likes': metadata['likes'], 'retweets': metadata['retweets'], 'replies': metadata['replies']},
                            'timestamp': metadata['timestamp'], 'scraped_at': datetime.now().isoformat()
                        }
                        
                        if tweet_data.get('text'):
                            try:
                                from social_media_processor import SocialMediaProcessor
                                processor = SocialMediaProcessor()
                                ai_result = processor.process_twitter_post(tweet_data)
                                if ai_result['success']:
                                    tweet_data['ai_analysis'] = ai_result['analysis']
                                    tweet_data['transcript_path'] = ai_result['transcript_path']
                                    self.logger.info(f"[OK] AI analysis completed for tweet {tweet_count}")
                            except Exception as ai_error:
                                self.logger.error(f"AI analysis error for tweet {tweet_count}: {ai_error}")
                        
                        metadata_path = os.path.join(handle_folder, f"{tweet_data['tweet_id']}_metadata.json")
                        with open(metadata_path, 'w', encoding='utf-8') as f:
                            json.dump(tweet_data, f, indent=2, ensure_ascii=False)
                        
                        results['tweets_scraped'].append(tweet_data)
                        results['total_media_downloaded'] += len(downloaded_media)
                        self.logger.info(f"[OK] Tweet {tweet_count} processed ({tweet_data['tweet_id']})")

                    page.keyboard.press("PageDown")
                    time.sleep(3) # Wait for new content to load
                
                browser.close()
        except Exception as e:
            self.logger.error(f"Failed to scrape Twitter handle @{handle}: {e}", exc_info=True)
            results['errors'].append(str(e))
        
        self.logger.info(f"Twitter scraping completed for @{handle}: {results['total_media_downloaded']} media files, {len(results['errors'])} errors")
        return results
    def load_handles(self):
        """Load Twitter handles from file"""
        if not os.path.exists(self.handles_file):
            self.logger.warning(f"Twitter handles file not found: {self.handles_file}")
            return []
        handles = []
        try:
            with open(self.handles_file, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith('#'):
                        handles.append(stripped_line.lstrip('@'))
            self.logger.info(f"Loaded {len(handles)} Twitter handles")
        except Exception as e:
            self.logger.error(f"Failed to load Twitter handles: {e}")
        return handles
    
    def scrape_all_handles(self):
        """Scrape all Twitter handles"""
        handles = self.load_handles()
        if not handles:
            self.logger.warning("No Twitter handles to scrape")
            return {'handles_processed': 0, 'total_media_downloaded': 0, 'results': []}
        
        all_results, total_media = [], 0
        for i, handle in enumerate(handles, 1):
            self.logger.info(f"Processing handle {i}/{len(handles)}: @{handle}")
            result = self.scrape_twitter_handle(handle)
            all_results.append(result)
            total_media += result['total_media_downloaded']
            if i < len(handles):
                self.logger.debug("Applying rate limit delay (15 seconds)")
                time.sleep(15)
        
        summary = {'handles_processed': len(handles), 'total_media_downloaded': total_media, 'results': all_results}
        self.logger.info(f"All Twitter handles processed: {total_media} total media files")
        return summary
    
    def get_recent_tweets(self, handle=None, limit=10):
        """Get recent tweets for dashboard display"""
        tweets = []
        try:
            target_dirs = [os.path.join(self.downloads_dir, handle)] if handle else [os.path.join(self.downloads_dir, d) for d in os.listdir(self.downloads_dir)]
            all_files = []
            for handle_folder in target_dirs:
                if os.path.isdir(handle_folder):
                    for f in os.listdir(handle_folder):
                        if f.endswith('_metadata.json'):
                            all_files.append(os.path.join(handle_folder, f))

            all_files.sort(key=os.path.getmtime, reverse=True)
            
            for f_path in all_files[:limit]:
                try:
                    with open(f_path, 'r', encoding='utf-8') as f:
                        tweets.append(json.load(f))
                except Exception as e:
                    self.logger.error(f"Error loading metadata from {f_path}: {e}")
            return tweets
        except Exception as e:
            self.logger.error(f"Error getting recent tweets: {e}")
            return []
    
    def _load_tweets_from_folder(self, folder_path, handle, limit):
        # This function is kept for compatibility but get_recent_tweets is now more robust
        self.logger.debug("Using legacy _load_tweets_from_folder. Consider updating.")
        return []
