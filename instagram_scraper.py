# instagram_scraper.py - Instagram content scraper integrated with the existing system

import os
import time
import urllib.request
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
                '✓': '[OK]', '✗': '[FAIL]', '→': '->', '←': '<-',
                '✔': '[OK]', '✖': '[FAIL]', '•': '*', '…': '...'
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

def setup_instagram_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('instagram_scraper.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Safe console handler
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

class InstagramScraper:
    def __init__(self):
        self.logger = setup_instagram_logging()
        self.downloads_dir = os.path.join(BASE_DIR, 'downloads', 'instagram')
        self.handles_file = os.path.join(BASE_DIR, 'handleinsta.txt')
        
        # Ensure directories exist
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        self.logger.info("Instagram scraper initialized")
    
    def download_file(self, url, path):
        """Download a file from URL"""
        try:
            urllib.request.urlretrieve(url, path)
            file_size = os.path.getsize(path) / (1024 * 1024)  # Size in MB
            self.logger.info(f"[OK] Downloaded: {os.path.basename(path)} ({file_size:.1f} MB)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return False
    
    def extract_post_metadata(self, page):
        """Extract metadata from Instagram post (more robust version)"""
        metadata = {
            'caption': '',
            'likes': 0,
            'comments': 0,
            'timestamp': '',
            'hashtags': []
        }
        
        try:
            # A more robust list of selectors for finding the caption
            caption_selectors = [
                "article h1",                            # For the main post title/caption
                "div[data-testid='post-text']",          # Test ID used by Instagram
                "div[class*='_a9zs']",                   # A common class for caption wrapper
                "div.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x193iq5w.xeuugli.x1fj9vlw.x13faqbe.x1vvkbs.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1i0v60h.x1rkvf73.x1q0g3np.x87ps6o.x1a2a7pz.xjbqb8w.x1l7klfx.x1iyjqo2.xs83m0k.x2lwn1j.xeuugli", # A very specific, but sometimes used, class
                "article div[role='presentation'] div[dir='auto']" # General structure
            ]
            
            for selector in caption_selectors:
                caption_element = page.query_selector(selector)
                if caption_element:
                    # Extract text from all child spans to build the full caption
                    spans = caption_element.query_selector_all("span")
                    full_caption_text = " ".join([span.inner_text() for span in spans]).strip()

                    # Fallback to the element's main text if no spans are found
                    if not full_caption_text:
                        full_caption_text = caption_element.inner_text().strip()
                    
                    # Relaxed length check to capture shorter captions
                    if full_caption_text and len(full_caption_text) > 2:
                        metadata['caption'] = full_caption_text
                        words = full_caption_text.split()
                        metadata['hashtags'] = [word for word in words if word.startswith('#')]
                        self.logger.debug(f"Found caption using selector '{selector}': {full_caption_text[:50]}...")
                        break # Stop once a caption is found
            
            if not metadata['caption']:
                self.logger.warning("Could not find caption for post.")

            # Try to get engagement metrics
            try:
                likes_element = page.query_selector("section button span, a[href*='liked_by'] span")
                if likes_element:
                    likes_text = likes_element.inner_text()
                    if 'K' in likes_text:
                        metadata['likes'] = int(float(likes_text.replace('K', '').replace(',', '')) * 1000)
                    elif ',' in likes_text:
                        metadata['likes'] = int(likes_text.replace(',', '').replace(' likes', ''))
            except:
                pass
                
        except Exception as e:
            self.logger.debug(f"Could not extract full metadata: {e}")
        
        return metadata
    
    def scrape_instagram_handle(self, handle):
        """Scrape Instagram posts from a specific handle"""
        self.logger.info(f"Starting Instagram scrape for: @{handle}")
        results = {'handle': handle, 'posts_scraped': [], 'errors': [], 'total_media_downloaded': 0}
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
                )
                page = browser.new_page()
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                self.logger.info(f"Navigating to Instagram profile: @{handle}")
                profile_url = f"https://www.instagram.com/{handle}/"
                page.goto(profile_url, timeout=60000, wait_until="networkidle")
                time.sleep(3)
                
                if "Page Not Found" in page.content() or "Sorry, this page isn't available" in page.content():
                    error_msg = f"Instagram profile @{handle} not found"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
                    browser.close()
                    return results
                
                posts = page.query_selector_all("article a")[:10]
                if not posts:
                    self.logger.warning(f"No posts found for @{handle}")
                    browser.close()
                    return results
                
                self.logger.info(f"Found {len(posts)} posts to process")
                handle_folder = os.path.join(self.downloads_dir, handle)
                os.makedirs(handle_folder, exist_ok=True)
                
                post_links = [f"https://www.instagram.com{post.get_attribute('href')}" for post in posts if post.get_attribute("href")]
                
                for i, post_link in enumerate(post_links):
                    try:
                        self.logger.info(f"Processing post {i+1}/{len(post_links)}")
                        page.goto(post_link, timeout=60000, wait_until="networkidle")
                        time.sleep(2)
                        
                        metadata = self.extract_post_metadata(page)
                        media_downloaded = []
                        
                        # Process video
                        video = page.query_selector("video")
                        if video and video.get_attribute("src"):
                            src = video.get_attribute("src")
                            video_path = os.path.join(handle_folder, f"video_{i+1}.mp4")
                            if self.download_file(src, video_path):
                                media_downloaded.append({'type': 'video', 'path': video_path, 'url': src})
                        
                        # Process images
                        images = page.query_selector_all("img")
                        img_count = 0
                        for img in images:
                            src = img.get_attribute("src")
                            if src and any(k in src for k in ['instagram.com/p/', 'instagram.com/reel/', 'scontent']):
                                img_path = os.path.join(handle_folder, f"image_{i+1}_{img_count+1}.jpg")
                                if self.download_file(src, img_path):
                                    media_downloaded.append({'type': 'image', 'path': img_path, 'url': src})
                                    img_count += 1
                                    if img_count >= 3: break
                        
                        if media_downloaded:
                            post_data = {
                                'post_id': f"{handle}_post_{i+1}", 'url': post_link, 'handle': handle,
                                'media': media_downloaded, 'metadata': metadata, 'scraped_at': datetime.now().isoformat()
                            }
                            
                            if metadata.get('caption'):
                                try:
                                    from social_media_processor import SocialMediaProcessor
                                    processor = SocialMediaProcessor()
                                    ai_result = processor.process_instagram_post(post_data)
                                    if ai_result['success']:
                                        post_data['ai_analysis'] = ai_result['analysis']
                                        post_data['transcript_path'] = ai_result['transcript_path']
                                        self.logger.info(f"[OK] AI analysis completed for post {i+1}")
                                    else:
                                        self.logger.warning(f"AI analysis failed for post {i+1}: {ai_result['error']}")
                                except Exception as ai_error:
                                    self.logger.error(f"AI analysis error for post {i+1}: {ai_error}")
                            
                            metadata_path = os.path.join(handle_folder, f"post_{i+1}_metadata.json")
                            with open(metadata_path, 'w', encoding='utf-8') as f:
                                json.dump(post_data, f, indent=2, ensure_ascii=False)
                            
                            results['posts_scraped'].append(post_data)
                            results['total_media_downloaded'] += len(media_downloaded)
                            self.logger.info(f"[OK] Post {i+1} processed: {len(media_downloaded)} media files")
                        else:
                            self.logger.warning(f"No media found in post {i+1}")
                            
                    except Exception as e:
                        error_msg = f"Error processing post {i+1}: {e}"
                        self.logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                browser.close()
        except Exception as e:
            error_msg = f"Failed to scrape Instagram handle @{handle}: {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
        
        self.logger.info(f"Instagram scraping completed for @{handle}: {results['total_media_downloaded']} media files, {len(results['errors'])} errors")
        return results
    
    def load_handles(self):
        """Load Instagram handles from file"""
        if not os.path.exists(self.handles_file):
            self.logger.warning(f"Instagram handles file not found: {self.handles_file}")
            return []
        
        handles = []
        try:
            with open(self.handles_file, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith('#'):
                        handles.append(stripped_line.lstrip('@'))
            self.logger.info(f"Loaded {len(handles)} Instagram handles")
        except Exception as e:
            self.logger.error(f"Failed to load Instagram handles: {e}")
        return handles
    
    def scrape_all_handles(self):
        """Scrape all Instagram handles"""
        handles = self.load_handles()
        if not handles:
            self.logger.warning("No Instagram handles to scrape")
            return {'handles_processed': 0, 'total_media_downloaded': 0, 'results': []}
        
        all_results = []
        total_media = 0
        for i, handle in enumerate(handles, 1):
            self.logger.info(f"Processing handle {i}/{len(handles)}: @{handle}")
            result = self.scrape_instagram_handle(handle)
            all_results.append(result)
            total_media += result['total_media_downloaded']
            if i < len(handles):
                self.logger.debug("Applying rate limit delay (10 seconds)")
                time.sleep(10)
        
        summary = {'handles_processed': len(handles), 'total_media_downloaded': total_media, 'results': all_results}
        self.logger.info(f"All Instagram handles processed: {total_media} total media files")
        return summary
    
    def get_recent_posts(self, handle=None, limit=10):
        """Get recent posts for dashboard display"""
        posts = []
        try:
            target_dirs = [os.path.join(self.downloads_dir, handle)] if handle else [os.path.join(self.downloads_dir, d) for d in os.listdir(self.downloads_dir)]
            
            for handle_folder in target_dirs:
                if os.path.isdir(handle_folder):
                    folder_name = os.path.basename(handle_folder)
                    posts.extend(self._load_posts_from_folder(handle_folder, folder_name, limit))

            posts.sort(key=lambda x: x.get('scraped_at', ''), reverse=True)
            return posts[:limit]
        except Exception as e:
            self.logger.error(f"Error getting recent posts: {e}")
            return []
    
    def _load_posts_from_folder(self, folder_path, handle, limit):
        """Load posts from a handle folder"""
        posts = []
        try:
            metadata_files = [f for f in os.listdir(folder_path) if f.endswith('_metadata.json')]
            metadata_files.sort(key=lambda f: os.path.getmtime(os.path.join(folder_path, f)), reverse=True)
            
            for metadata_file in metadata_files[:limit]:
                metadata_path = os.path.join(folder_path, metadata_file)
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        post_data = json.load(f)
                        post_data['handle'] = handle
                        posts.append(post_data)
                except Exception as e:
                    self.logger.error(f"Error loading metadata from {metadata_file}: {e}")
        except Exception as e:
            self.logger.error(f"Error loading posts from {folder_path}: {e}")
        return posts
