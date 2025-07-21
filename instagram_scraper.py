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

def setup_instagram_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('instagram_scraper.log', encoding='utf-8')
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
        """Extract metadata from Instagram post"""
        metadata = {
            'caption': '',
            'likes': 0,
            'comments': 0,
            'timestamp': '',
            'hashtags': []
        }
        
        try:
            # Try to get caption
            caption_selectors = [
                "article h1",
                "div[data-testid='post-text'] span",
                "div span[style*='word-wrap']",
                "article div span"
            ]
            
            for selector in caption_selectors:
                caption_element = page.query_selector(selector)
                if caption_element:
                    caption_text = caption_element.inner_text().strip()
                    if caption_text and len(caption_text) > 10:  # Avoid empty or very short text
                        metadata['caption'] = caption_text
                        # Extract hashtags
                        words = caption_text.split()
                        metadata['hashtags'] = [word for word in words if word.startswith('#')]
                        break
            
            # Try to get engagement metrics (Instagram often blocks this)
            try:
                likes_element = page.query_selector("section button span")
                if likes_element:
                    likes_text = likes_element.inner_text()
                    # Handle different formats: "1,234 likes", "1.2K likes", etc.
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
        
        results = {
            'handle': handle,
            'posts_scraped': [],
            'errors': [],
            'total_media_downloaded': 0
        }
        
        try:
            with sync_playwright() as p:
                # Launch browser with better settings
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
                
                # Set user agent to avoid detection
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                self.logger.info(f"Navigating to Instagram profile: @{handle}")
                
                # Navigate to Instagram profile
                profile_url = f"https://www.instagram.com/{handle}/"
                page.goto(profile_url, timeout=60000, wait_until="networkidle")
                time.sleep(3)
                
                # Check if profile exists
                if "Page Not Found" in page.content() or "Sorry, this page isn't available" in page.content():
                    error_msg = f"Instagram profile @{handle} not found"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
                    browser.close()
                    return results
                
                # Get recent posts (first 10)
                posts = page.query_selector_all("article a")[:10]
                
                if not posts:
                    self.logger.warning(f"No posts found for @{handle}")
                    browser.close()
                    return results
                
                self.logger.info(f"Found {len(posts)} posts to process")
                
                # Create handle-specific folder
                handle_folder = os.path.join(self.downloads_dir, handle)
                os.makedirs(handle_folder, exist_ok=True)
                
                # Collect post links
                post_links = []
                for post in posts:
                    href = post.get_attribute("href")
                    if href:
                        post_links.append(f"https://www.instagram.com{href}")
                
                # Process each post
                for i, post_link in enumerate(post_links):
                    try:
                        self.logger.info(f"Processing post {i+1}/{len(post_links)}")
                        
                        page.goto(post_link, timeout=60000, wait_until="networkidle")
                        time.sleep(2)
                        
                        # Extract metadata
                        metadata = self.extract_post_metadata(page)
                        
                        # Look for media
                        media_downloaded = []
                        
                        # Check for video
                        video = page.query_selector("video")
                        if video:
                            src = video.get_attribute("src")
                            if src:
                                video_path = os.path.join(handle_folder, f"video_{i+1}.mp4")
                                if self.download_file(src, video_path):
                                    media_downloaded.append({
                                        'type': 'video',
                                        'path': video_path,
                                        'url': src
                                    })
                        
                        # Check for images
                        images = page.query_selector_all("img")
                        img_count = 0
                        for img in images:
                            src = img.get_attribute("src")
                            # Filter out profile images, icons, etc.
                            if src and any(keyword in src for keyword in ['instagram.com/p/', 'instagram.com/reel/', 'scontent']):
                                img_path = os.path.join(handle_folder, f"image_{i+1}_{img_count+1}.jpg")
                                if self.download_file(src, img_path):
                                    media_downloaded.append({
                                        'type': 'image',
                                        'path': img_path,
                                        'url': src
                                    })
                                    img_count += 1
                                    if img_count >= 3:  # Limit images per post
                                        break
                        
                        if media_downloaded:
                            post_data = {
                                'post_id': f"{handle}_post_{i+1}",
                                'url': post_link,
                                'handle': handle,
                                'media': media_downloaded,
                                'metadata': metadata,
                                'scraped_at': datetime.now().isoformat()
                            }
                            
                            # NEW: Process with Gemini AI if there's text content
                            if metadata.get('caption'):
                                try:
                                    # Import here to avoid circular imports
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
                            
                            # Save metadata to JSON
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
        return resultsattribute("src")
                            if src:
                                video_path = os.path.join(handle_folder, f"video_{i+1}.mp4")
                                if self.download_file(src, video_path):
                                    media_downloaded.append({
                                        'type': 'video',
                                        'path': video_path,
                                        'url': src
                                    })
                        
                        # Check for images
                        images = page.query_selector_all("img")
                        img_count = 0
                        for img in images:
                            src = img.get_attribute("src")
                            # Filter out profile images, icons, etc.
                            if src and any(keyword in src for keyword in ['instagram.com/p/', 'instagram.com/reel/', 'scontent']):
                                img_path = os.path.join(handle_folder, f"image_{i+1}_{img_count+1}.jpg")
                                if self.download_file(src, img_path):
                                    media_downloaded.append({
                                        'type': 'image',
                                        'path': img_path,
                                        'url': src
                                    })
                                    img_count += 1
                                    if img_count >= 3:  # Limit images per post
                                        break
                        
                        if media_downloaded:
                            post_data = {
                                'post_id': f"{handle}_post_{i+1}",
                                'url': post_link,
                                'media': media_downloaded,
                                'metadata': metadata,
                                'scraped_at': datetime.now().isoformat()
                            }
                            
                            # Save metadata to JSON
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
        handles = []
        
        if not os.path.exists(self.handles_file):
            self.logger.warning(f"Instagram handles file not found: {self.handles_file}")
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
            
            self.logger.info(f"Loaded {len(handles)} Instagram handles")
            
        except Exception as e:
            self.logger.error(f"Failed to load Instagram handles: {e}")
        
        return handles
    
    def scrape_all_handles(self):
        """Scrape all Instagram handles"""
        handles = self.load_handles()
        
        if not handles:
            self.logger.warning("No Instagram handles to scrape")
            return {
                'handles_processed': 0,
                'total_media_downloaded': 0,
                'results': []
            }
        
        all_results = []
        total_media = 0
        
        for i, handle in enumerate(handles, 1):
            self.logger.info(f"Processing handle {i}/{len(handles)}: @{handle}")
            
            result = self.scrape_instagram_handle(handle)
            all_results.append(result)
            total_media += result['total_media_downloaded']
            
            # Rate limiting between handles
            if i < len(handles):
                self.logger.debug("Applying rate limit delay (10 seconds)")
                time.sleep(10)
        
        summary = {
            'handles_processed': len(handles),
            'total_media_downloaded': total_media,
            'results': all_results
        }
        
        self.logger.info(f"All Instagram handles processed: {total_media} total media files")
        return summary
    
    def get_recent_posts(self, handle=None, limit=10):
        """Get recent posts for dashboard display"""
        posts = []
        
        try:
            if handle:
                # Get posts for specific handle
                handle_folder = os.path.join(self.downloads_dir, handle)
                if os.path.exists(handle_folder):
                    posts.extend(self._load_posts_from_folder(handle_folder, handle, limit))
            else:
                # Get posts from all handles
                for handle_dir in os.listdir(self.downloads_dir):
                    handle_folder = os.path.join(self.downloads_dir, handle_dir)
                    if os.path.isdir(handle_folder):
                        posts.extend(self._load_posts_from_folder(handle_folder, handle_dir, limit))
            
            # Sort by scraped_at timestamp
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
            metadata_files.sort(reverse=True)  # Most recent first
            
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