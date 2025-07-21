# twitter_scraper.py - Twitter content scraper integrated with the existing system

import os
import time
import requests
import logging
import json
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright
from config import BASE_DIR

# Safe logging setup for Windows compatibility
class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that safely handles Unicode characters on Windows"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            
            # Replace problematic Unicode characters
            replacements = {
                '✓': '[OK]',
                '✗': '[FAIL]', 
                '→': '->',
                '←': '<-',
                '✔': '[OK]',
                '✖': '[FAIL]',
                '•': '*',
                '…': '...'
            }
            
            for unicode_char, replacement in replacements.items():
                msg = msg.replace(unicode_char, replacement)
            
            # Write safely
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
                stream.flush()
            except UnicodeEncodeError:
                # Fallback: encode with error handling
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                stream.write(safe_msg + self.terminator)
                stream.flush()
                
        except Exception:
            self.handleError(record)

def setup_twitter_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('twitter_scraper.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Safe console handler
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

class TwitterScraper:
    def __init__(self):
        self.logger = setup_twitter_logging()
        self.downloads_dir = os.path.join(BASE_DIR, 'downloads', 'twitter')
        self.handles_file = os.path.join(BASE_DIR, 'handletwitter.txt')
        
        # Ensure directories exist
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
                
                file_size = os.path.getsize(path) / (1024 * 1024)  # Size in MB
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
        metadata = {
            'text': '',
            'hashtags': [],
            'mentions': [],
            'likes': 0,
            'retweets': 0,
            'replies': 0,
            'timestamp': ''
        }
        
        try:
            # Extract tweet text
            text_selectors = [
                "div[lang] span",
                "div[data-testid='tweetText'] span",
                "div[dir='ltr'] span"
            ]
            
            tweet_text = ""
            for selector in text_selectors:
                text_elements = tweet_element.query_selector_all(selector)
                for element in text_elements:
                    text = element.inner_text().strip()
                    if text and len(text) > tweet_text:
                        tweet_text = text
            
            metadata['text'] = tweet_text
            
            # Extract hashtags and mentions
            if tweet_text:
                words = tweet_text.split()
                metadata['hashtags'] = [word for word in words if word.startswith('#')]
                metadata['mentions'] = [word for word in words if word.startswith('@')]
            
            # Try to extract engagement metrics (often blocked by Twitter)
            try:
                # Look for like/retweet/reply counts
                buttons = tweet_element.query_selector_all("button[data-testid*='like'], button[data-testid*='retweet'], button[data-testid*='reply']")
                for button in buttons:
                    aria_label = button.get_attribute("aria-label") or ""
                    if "like" in aria_label.lower():
                        # Extract number from "X likes"
                        import re
                        numbers = re.findall(r'\d+', aria_label)
                        if numbers:
                            metadata['likes'] = int(numbers[0])
                    elif "retweet" in aria_label.lower():
                        numbers = re.findall(r'\d+', aria_label)
                        if numbers:
                            metadata['retweets'] = int(numbers[0])
                    elif "repl" in aria_label.lower():
                        numbers = re.findall(r'\d+', aria_label)
                        if numbers:
                            metadata['replies'] = int(numbers[0])
            except:
                pass
            
            # Try to get timestamp
            try:
                time_element = tweet_element.query_selector("time")
                if time_element:
                    datetime_attr = time_element.get_attribute("datetime")
                    if datetime_attr:
                        metadata['timestamp'] = datetime_attr
            except:
                pass
                
        except Exception as e:
            self.logger.debug(f"Could not extract full tweet metadata: {e}")
        
        return metadata
    
    def scrape_twitter_handle(self, handle):
        """Scrape Twitter posts from a specific handle"""
        self.logger.info(f"Starting Twitter scrape for: @{handle}")
        
        results = {
            'handle': handle,
            'tweets_scraped': [],
            'errors': [],
            'total_media_downloaded': 0
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,  # Set to True for production
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu'
                    ]
                )
                
                page = browser.new_page()
                page.set_default_timeout(90000)
                
                # Set user agent to avoid detection
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                self.logger.info(f"Navigating to Twitter profile: @{handle}")
                
                # Navigate to Twitter profile
                profile_url = f"https://twitter.com/{handle}"
                
                success = False
                for attempt in range(3):  # Try up to 3 times
                    try:
                        page.goto(profile_url, timeout=90000, wait_until="networkidle")
                        time.sleep(3)
                        success = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            self.logger.warning(f"Attempt {attempt + 1} failed for @{handle}, retrying...")
                            time.sleep(10)
                        else:
                            self.logger.error(f"Failed to load Twitter profile @{handle} after 3 attempts: {e}")
                
                if not success:
                    results['errors'].append(f"Could not load Twitter profile @{handle}")
                    browser.close()
                    return results
                
                # Check if profile exists
                page_content = page.content().lower()
                if "this account doesn't exist" in page_content or "user not found" in page_content:
                    error_msg = f"Twitter profile @{handle} not found"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
                    browser.close()
                    return results
                
                # Create handle-specific folder
                handle_folder = os.path.join(self.downloads_dir, handle)
                os.makedirs(handle_folder, exist_ok=True)
                
                # Scrape tweets with media
                media_count = 0
                tweet_count = 0
                scrolls = 0
                max_tweets = 10
                max_scrolls = 6
                
                while media_count < max_tweets and scrolls < max_scrolls:
                    tweets = page.query_selector_all("article")
                    
                    for tweet in tweets:
                        if media_count >= max_tweets:
                            break
                        
                        try:
                            # Extract metadata
                            metadata = self.extract_tweet_metadata(tweet)
                            
                            # Look for media in the tweet
                            media_urls = []
                            
                            # Check for images
                            imgs = tweet.query_selector_all("img")
                            for img in imgs:
                                src = img.get_attribute("src")
                                if src and "pbs.twimg.com/media" in src and "profile_images" not in src and "emoji" not in src:
                                    # Get high quality version
                                    if "?name=" in src:
                                        src = src.split("?name=")[0] + "?name=large"
                                    media_urls.append((src, "jpg"))
                            
                            # Check for videos
                            videos = tweet.query_selector_all("video")
                            for video in videos:
                                src = video.get_attribute("src")
                                if src:
                                    media_urls.append((src, "mp4"))
                            
                            if media_urls:
                                tweet_count += 1
                                tweet_folder = os.path.join(handle_folder, f"tweet_{tweet_count}")
                                os.makedirs(tweet_folder, exist_ok=True)
                                
                                downloaded_media = []
                                
                                for idx, (media_url, ext) in enumerate(media_urls):
                                    if media_count >= max_tweets:
                                        break
                                    
                                    media_filename = os.path.join(tweet_folder, f"media_{idx + 1}.{ext}")
                                    
                                    if self.download_file(media_url, media_filename):
                                        downloaded_media.append({
                                            'type': 'image' if ext == 'jpg' else 'video',
                                            'path': media_filename,
                                            'url': media_url
                                        })
                                        media_count += 1
                                
                                if downloaded_media:
                                    # Save tweet metadata
                                    tweet_data = {
                                        'tweet_id': f"{handle}_tweet_{tweet_count}",
                                        'handle': handle,
                                        'text': metadata['text'],
                                        'hashtags': metadata['hashtags'],
                                        'mentions': metadata['mentions'],
                                        'media': downloaded_media,
                                        'engagement': {
                                            'likes': metadata['likes'],
                                            'retweets': metadata['retweets'],
                                            'replies': metadata['replies']
                                        },
                                        'timestamp': metadata['timestamp'],
                                        'scraped_at': datetime.now().isoformat()
                                    }
                                    
                                    # Save metadata to JSON
                                    metadata_path = os.path.join(tweet_folder, 'tweet_metadata.json')
                                    with open(metadata_path, 'w', encoding='utf-8') as f:
                                        json.dump(tweet_data, f, indent=2, ensure_ascii=False)
                                    
                                    # Save text to separate file for easy reading
                                    if metadata['text']:
                                        text_path = os.path.join(tweet_folder, 'tweet_text.txt')
                                        with open(text_path, 'w', encoding='utf-8') as f:
                                            f.write(metadata['text'])
                                    
                                    results['tweets_scraped'].append(tweet_data)
                                    results['total_media_downloaded'] += len(downloaded_media)
                                    
                                    self.logger.info(f"[OK] Tweet {tweet_count} processed: {len(downloaded_media)} media files")
                        
                        except Exception as e:
                            error_msg = f"Error processing tweet: {e}"
                            self.logger.error(error_msg)
                            results['errors'].append(error_msg)
                    
                    # Scroll down to load more tweets
                    page.keyboard.press("PageDown")
                    time.sleep(2)
                    scrolls += 1
                
                browser.close()
                
        except Exception as e:
            error_msg = f"Failed to scrape Twitter handle @{handle}: {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
        
        self.logger.info(f"Twitter scraping completed for @{handle}: {results['total_media_downloaded']} media files, {len(results['errors'])} errors")
        return results
    
    def load_handles(self):
        """Load Twitter handles from file"""
        handles = []
        
        if not os.path.exists(self.handles_file):
            self.logger.warning(f"Twitter handles file not found: {self.handles_file}")
            return handles
        
        try:
            with open(self.handles_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Remove @ if present
                        handle = line.lstrip('@')
                        handles.append(handle)
                    elif line.startswith('#'):
                        self.logger.debug(f"Skipped comment line {line_num}: {line}")
            
            self.logger.info(f"Loaded {len(handles)} Twitter handles")
            
        except Exception as e:
            self.logger.error(f"Failed to load Twitter handles: {e}")
        
        return handles
    
    def scrape_all_handles(self):
        """Scrape all Twitter handles"""
        handles = self.load_handles()
        
        if not handles:
            self.logger.warning("No Twitter handles to scrape")
            return {
                'handles_processed': 0,
                'total_media_downloaded': 0,
                'results': []
            }
        
        all_results = []
        total_media = 0
        
        for i, handle in enumerate(handles, 1):
            self.logger.info(f"Processing handle {i}/{len(handles)}: @{handle}")
            
            result = self.scrape_twitter_handle(handle)
            all_results.append(result)
            total_media += result['total_media_downloaded']
            
            # Rate limiting between handles
            if i < len(handles):
                self.logger.debug("Applying rate limit delay (15 seconds)")
                time.sleep(15)  # Longer delay for Twitter
        
        summary = {
            'handles_processed': len(handles),
            'total_media_downloaded': total_media,
            'results': all_results
        }
        
        self.logger.info(f"All Twitter handles processed: {total_media} total media files")
        return summary
    
    def get_recent_tweets(self, handle=None, limit=10):
        """Get recent tweets for dashboard display"""
        tweets = []
        
        try:
            if handle:
                # Get tweets for specific handle
                handle_folder = os.path.join(self.downloads_dir, handle)
                if os.path.exists(handle_folder):
                    tweets.extend(self._load_tweets_from_folder(handle_folder, handle, limit))
            else:
                # Get tweets from all handles
                for handle_dir in os.listdir(self.downloads_dir):
                    handle_folder = os.path.join(self.downloads_dir, handle_dir)
                    if os.path.isdir(handle_folder):
                        tweets.extend(self._load_tweets_from_folder(handle_folder, handle_dir, limit))
            
            # Sort by scraped_at timestamp
            tweets.sort(key=lambda x: x.get('scraped_at', ''), reverse=True)
            return tweets[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting recent tweets: {e}")
            return []
    
    def _load_tweets_from_folder(self, folder_path, handle, limit):
        """Load tweets from a handle folder"""
        tweets = []
        
        try:
            # Get all tweet folders
            tweet_folders = [f for f in os.listdir(folder_path) if f.startswith('tweet_') and os.path.isdir(os.path.join(folder_path, f))]
            tweet_folders.sort(reverse=True)  # Most recent first
            
            for tweet_folder in tweet_folders[:limit]:
                tweet_path = os.path.join(folder_path, tweet_folder)
                metadata_file = os.path.join(tweet_path, 'tweet_metadata.json')
                
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            tweet_data = json.load(f)
                            tweet_data['handle'] = handle
                            tweets.append(tweet_data)
                    except Exception as e:
                        self.logger.error(f"Error loading metadata from {metadata_file}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error loading tweets from {folder_path}: {e}")
        
        return tweets