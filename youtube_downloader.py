# youtube_downloader.py - Handles YouTube video downloading functionality WITHOUT ffmpeg

import yt_dlp
from datetime import datetime, timezone
import re
import os
import logging
import sys
import time
import shutil
from config import RECENT_HOURS, MAX_VIDEOS_TO_CHECK, TEMP_AUDIO_DIR

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

# Configure safe logging
def setup_youtube_downloader_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('youtube_downloader.log', encoding='utf-8')
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
    logger.propagate = False  # Prevent duplicate logging
    return logger

class YouTubeDownloader:
    def __init__(self):
        self.recent_hours = RECENT_HOURS
        self.max_videos = MAX_VIDEOS_TO_CHECK
        self.logger = setup_youtube_downloader_logging()
        
        # Ensure temp directory exists
        os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
        
        self.logger.info(f"YouTubeDownloader initialized - Recent hours: {self.recent_hours}, Max videos: {self.max_videos}")
        
    def is_recent(self, upload_date_str):
        """Check if a video was uploaded within the recent time window"""
        try:
            upload_date = datetime.strptime(upload_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            time_diff = now - upload_date
            hours_old = time_diff.total_seconds() / 3600
            
            is_recent = time_diff.total_seconds() < (self.recent_hours * 3600)
            
            self.logger.debug(f"Video age check - Upload date: {upload_date}, Hours old: {hours_old:.1f}, Is recent: {is_recent}")
            
            return is_recent
        except Exception as e:
            self.logger.error(f"Failed to parse upload date '{upload_date_str}': {e}")
            return False
    
    def normalize_channel_handle(self, channel_handle):
        """Normalize channel handle to proper format"""
        original_handle = channel_handle
        
        if not re.match(r'^(@|UC|channel/)', channel_handle):
            channel_handle = f"@{channel_handle.lstrip('@')}"
            
        self.logger.debug(f"Channel handle normalized: '{original_handle}' -> '{channel_handle}'")
        return channel_handle
    
    def get_channel_videos(self, channel_handle):
        """Fetch video list from YouTube channel"""
        url = f"https://www.youtube.com/{channel_handle}/videos"
        self.logger.info(f"Fetching channel videos from: {url}")
        
        flat_opts = {
            'quiet': True,
            'extract_flat': True,
            'playlist_items': f'1-{self.max_videos}',
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(flat_opts) as ydl:
                flat_result = ydl.extract_info(url, download=False)
                
            if not flat_result or 'entries' not in flat_result:
                self.logger.warning(f"No videos found for channel: {channel_handle}")
                return []
            
            video_count = len([v for v in flat_result['entries'] if v])
            video_urls = [f"https://www.youtube.com/watch?v={v['id']}" 
                         for v in flat_result['entries'] if v]
            
            self.logger.info(f"Successfully retrieved {video_count} videos from channel: {channel_handle}")
            self.logger.debug(f"Video URLs: {video_urls[:3]}{'...' if len(video_urls) > 3 else ''}")
            
            return video_urls
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve videos from channel '{channel_handle}': {e}")
            return []
    
    def filter_recent_videos(self, video_urls):
        """Filter videos to only include recent ones"""
        self.logger.info(f"Filtering {len(video_urls)} videos for recent uploads (within {self.recent_hours} hours)")
        
        recent_videos = []
        meta_opts = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(meta_opts) as ydl:
            for i, v_url in enumerate(video_urls, 1):
                try:
                    self.logger.debug(f"Processing video {i}/{len(video_urls)}: {v_url}")
                    
                    info = ydl.extract_info(v_url, download=False)
                    title = info.get('title', 'Unknown')
                    upload_date = info.get('upload_date')
                    video_id = info.get('id', '')
                    duration = info.get('duration', 0)  # Duration in seconds
                    
                    self.logger.debug(f"Video info - Title: '{title}', Upload date: {upload_date}, ID: {video_id}, Duration: {duration}s")
                    
                    # Skip long videos if configured
                    if hasattr(self, 'skip_large_videos'):
                        from config import SKIP_LARGE_VIDEOS, MAX_VIDEO_DURATION_MINUTES
                        if SKIP_LARGE_VIDEOS and duration > (MAX_VIDEO_DURATION_MINUTES * 60):
                            self.logger.info(f"[SKIP] Video too long: '{title}' ({duration//60} minutes)")
                            continue
                    
                    self.logger.debug(f"Video info - Title: '{title}', Upload date: {upload_date}, ID: {video_id}")
                    
                    if not upload_date:
                        self.logger.warning(f"No upload date available for video: '{title}' - Skipping")
                        continue
                    
                    if self.is_recent(upload_date):
                        self.logger.info(f"[OK] Recent video found: '{title}' (uploaded: {upload_date})")
                        recent_videos.append({
                            'url': v_url,
                            'title': title,
                            'upload_date': upload_date,
                            'video_id': video_id
                        })
                    else:
                        self.logger.debug(f"[SKIP] Video too old: '{title}' (uploaded: {upload_date})")
                        
                except Exception as e:
                    # Handle member-only and private videos
                    error_str = str(e)
                    if "members on level" in error_str or "available to this channel's members" in error_str:
                        self.logger.debug(f"Skipping member-only video: {v_url}")
                    elif "Private video" in error_str:
                        self.logger.debug(f"Skipping private video: {v_url}")
                    elif "Video unavailable" in error_str:
                        self.logger.debug(f"Skipping unavailable video: {v_url}")
                    else:
                        self.logger.error(f"Failed to get metadata for video {v_url}: {e}")
        
        self.logger.info(f"Filtering complete: {len(recent_videos)} recent videos found out of {len(video_urls)} checked")
        return recent_videos
    
    def download_audio(self, video_info):
        """Download audio from a video WITHOUT ffmpeg - Direct M4A/WebM download"""
        self.logger.info(f"Starting audio download for: '{video_info['title']}'")
        
        try:
            # Clean filename - make it even safer
            safe_title = "".join(c for c in video_info['title'] 
                               if c.isalnum() or c in (' ', '-', '_')).rstrip()[:40]  # Shorter length
            safe_title = safe_title.replace(' ', '_')  # Replace spaces with underscores
            filename = f"{video_info['video_id']}_{safe_title}"
            
            output_path = os.path.join(TEMP_AUDIO_DIR, filename)
            
            self.logger.debug(f"Output path template: {output_path}")
            
            # Download options - Windows-friendly settings
            download_opts = {
                'outtmpl': output_path + '.%(ext)s',
                # Download audio directly without conversion
                'format': 'm4a/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                # NO postprocessors - we want the raw audio file
                'postprocessors': [],
                # Windows-specific fixes
                'retries': 10,
                'fragment_retries': 10,
                'file_access_retries': 10,
                'concurrent_fragment_downloads': 1,  # Avoid parallel downloads
                # Disable features that might cause locks
                'writedescription': False,
                'writeinfojson': False,
                'writeannotations': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'writethumbnail': False,
            }
            
            # Download the audio
            actual_filepath = None
            try:
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    download_info = ydl.extract_info(video_info['url'], download=True)
                    
                    # Get the expected filename from download info
                    if download_info and 'requested_downloads' in download_info:
                        requested_downloads = download_info.get('requested_downloads', [])
                        if requested_downloads:
                            actual_filepath = requested_downloads[0].get('filepath')
            except Exception as download_error:
                # Check if it's the Windows file locking error
                if "[WinError 32]" in str(download_error) and ".part" in str(download_error):
                    self.logger.warning("Windows file locking error detected, attempting recovery...")
                    
                    # Wait for Windows to release the file
                    time.sleep(2)
                    
                    # Try to find and rename the .part file manually
                    for ext in ['m4a', 'webm', 'opus', 'mp3']:
                        part_file = output_path + f'.{ext}.part'
                        target_file = output_path + f'.{ext}'
                        
                        if os.path.exists(part_file):
                            self.logger.info(f"Found partial file: {os.path.basename(part_file)}")
                            
                            # Multiple attempts to rename with delays
                            for attempt in range(5):
                                try:
                                    # Check if target already exists (from previous attempt)
                                    if os.path.exists(target_file):
                                        actual_filepath = target_file
                                        self.logger.info("Target file already exists, using it")
                                        break
                                    
                                    # Try to rename
                                    os.rename(part_file, target_file)
                                    actual_filepath = target_file
                                    self.logger.info(f"Successfully renamed partial file on attempt {attempt + 1}")
                                    break
                                except Exception as e:
                                    if attempt < 4:
                                        self.logger.warning(f"Rename attempt {attempt + 1} failed, waiting...")
                                        time.sleep(2)
                                    else:
                                        # Last resort: copy instead of rename
                                        try:
                                            shutil.copy2(part_file, target_file)
                                            actual_filepath = target_file
                                            self.logger.info("Successfully copied partial file as fallback")
                                            # Try to delete the .part file
                                            try:
                                                os.remove(part_file)
                                            except:
                                                pass
                                        except Exception as copy_error:
                                            self.logger.error(f"Could not copy partial file: {copy_error}")
                            
                            if actual_filepath:
                                break
                    
                    if not actual_filepath:
                        self.logger.error("Could not recover from Windows file locking error")
                        raise download_error
                else:
                    # Not a file locking error, re-raise
                    raise download_error
            
            # If we still don't have a filepath, try to find the downloaded file
            if not actual_filepath:
                time.sleep(1)  # Give Windows a moment
                
                for ext in ['m4a', 'webm', 'opus', 'mp3']:
                    potential_file = output_path + f'.{ext}'
                    if os.path.exists(potential_file):
                        actual_filepath = potential_file
                        break
            
            if actual_filepath and os.path.exists(actual_filepath):
                file_size = os.path.getsize(actual_filepath)
                file_ext = os.path.splitext(actual_filepath)[1]
                self.logger.info(f"[OK] Audio download successful: '{video_info['title']}' ({file_size/1024/1024:.1f} MB, format: {file_ext})")
                self.logger.debug(f"Audio file path: {actual_filepath}")
                
                return {
                    'audio_path': actual_filepath,
                    'video_info': video_info,
                    'file_size_mb': file_size / (1024 * 1024),
                    'format': file_ext.lstrip('.')
                }
            else:
                self.logger.error(f"Audio file not found after download")
                return None
                
        except Exception as e:
            self.logger.error(f"Audio download failed for '{video_info['title']}': {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            
            # Check if it's a network or access issue
            if "HTTP Error 403" in str(e):
                self.logger.error("Access forbidden - video might be age-restricted or region-locked")
            elif "Video unavailable" in str(e):
                self.logger.error("Video is unavailable")
            elif "[WinError 32]" in str(e):
                self.logger.error("Windows file locking issue - file is being used by another process")
            
            return None
        """Download audio from a video WITHOUT ffmpeg - Direct M4A/WebM download"""
        self.logger.info(f"Starting audio download for: '{video_info['title']}'")
        
        # Clean filename
        safe_title = "".join(c for c in video_info['title'] 
                           if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]  # Limit length
        filename = f"{video_info['video_id']}_{safe_title}"
        
        # Output path - we'll let yt-dlp decide the extension
        output_path = os.path.join(TEMP_AUDIO_DIR, filename)
        
        self.logger.debug(f"Output path template: {output_path}")
        
        # Download options - Windows-friendly settings
        download_opts = {
            'outtmpl': output_path + '.%(ext)s',
            # Download audio directly without conversion
            'format': 'm4a/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            # NO postprocessors - we want the raw audio file
            'postprocessors': [],
            # Windows-specific fixes
            'retries': 10,
            'fragment_retries': 10,
            'file_access_retries': 10,
            'concurrent_fragment_downloads': 1,  # Avoid parallel downloads
            # Disable features that might cause locks
            'writedescription': False,
            'writeinfojson': False,
            'writeannotations': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
        }
        
        try:
            # First, check what formats are available
            info_opts = {
                'quiet': True,
                'skip_download': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(video_info['url'], download=False)
                
                # Log available formats for debugging
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                
                self.logger.debug(f"Available audio formats: {[f['ext'] for f in audio_formats[:5]]}")
            
            # Download the audio
            actual_filepath = None
            try:
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    download_info = ydl.extract_info(video_info['url'], download=True)
                    
                    # Get the expected filename from download info
                    if download_info and 'requested_downloads' in download_info:
                        requested_downloads = download_info.get('requested_downloads', [])
                        if requested_downloads:
                            actual_filepath = requested_downloads[0].get('filepath')
            except Exception as download_error:
                # Check if it's the Windows file locking error
                if "[WinError 32]" in str(download_error) and ".part" in str(download_error):
                    self.logger.warning("Windows file locking error detected, attempting recovery...")
                    
                    # Wait for Windows to release the file
                    time.sleep(2)
                    
                    # Try to find and rename the .part file manually
                    for ext in ['m4a', 'webm', 'opus', 'mp3']:
                        part_file = output_path + f'.{ext}.part'
                        target_file = output_path + f'.{ext}'
                        
                        if os.path.exists(part_file):
                            self.logger.info(f"Found partial file: {os.path.basename(part_file)}")
                            
                            # Multiple attempts to rename with delays
                            for attempt in range(5):
                                try:
                                    # Check if target already exists (from previous attempt)
                                    if os.path.exists(target_file):
                                        actual_filepath = target_file
                                        self.logger.info("Target file already exists, using it")
                                        break
                                    
                                    # Try to rename
                                    os.rename(part_file, target_file)
                                    actual_filepath = target_file
                                    self.logger.info(f"Successfully renamed partial file on attempt {attempt + 1}")
                                    break
                                except Exception as e:
                                    if attempt < 4:
                                        self.logger.warning(f"Rename attempt {attempt + 1} failed, waiting...")
                                        time.sleep(2)
                                    else:
                                        # Last resort: copy instead of rename
                                        try:
                                            import shutil
                                            shutil.copy2(part_file, target_file)
                                            actual_filepath = target_file
                                            self.logger.info("Successfully copied partial file as fallback")
                                            # Try to delete the .part file
                                            try:
                                                os.remove(part_file)
                                            except:
                                                pass
                                        except Exception as copy_error:
                                            self.logger.error(f"Could not copy partial file: {copy_error}")
                            
                            if actual_filepath:
                                break
                    
                    if not actual_filepath:
                        self.logger.error("Could not recover from Windows file locking error")
                        raise download_error
                else:
                    # Not a file locking error, re-raise
                    raise download_error
            
            # If we still don't have a filepath, try to find the downloaded file
            if not actual_filepath:
                time.sleep(1)  # Give Windows a moment
                
                for ext in ['m4a', 'webm', 'opus', 'mp3']:
                    potential_file = output_path + f'.{ext}'
                    if os.path.exists(potential_file):
                        actual_filepath = potential_file
                        break
            
            if actual_filepath and os.path.exists(actual_filepath):
                file_size = os.path.getsize(actual_filepath)
                file_ext = os.path.splitext(actual_filepath)[1]
                self.logger.info(f"[OK] Audio download successful: '{video_info['title']}' ({file_size/1024/1024:.1f} MB, format: {file_ext})")
                self.logger.debug(f"Audio file path: {actual_filepath}")
                
                return {
                    'audio_path': actual_filepath,
                    'video_info': video_info,
                    'file_size_mb': file_size / (1024 * 1024),
                    'format': file_ext.lstrip('.')
                }
            else:
                self.logger.error(f"Audio file not found after download")
                return None
                
        except Exception as e:
            self.logger.error(f"Audio download failed for '{video_info['title']}': {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            
            # Check if it's a network or access issue
            if "HTTP Error 403" in str(e):
                self.logger.error("Access forbidden - video might be age-restricted or region-locked")
            elif "Video unavailable" in str(e):
                self.logger.error("Video is unavailable")
            elif "[WinError 32]" in str(e):
                self.logger.error("Windows file locking issue - file is being used by another process")
            
            return None
    
    def get_recent_videos_from_channel(self, channel_handle):
        """Main method to get recent videos from a channel"""
        self.logger.info(f"Starting recent video search for channel: '{channel_handle}'")
        
        # Normalize channel handle
        channel_handle = self.normalize_channel_handle(channel_handle)
        
        # Get video list
        video_urls = self.get_channel_videos(channel_handle)
        if not video_urls:
            self.logger.warning(f"No videos retrieved from channel: {channel_handle}")
            return []
        
        # Filter recent videos
        recent_videos = self.filter_recent_videos(video_urls)
        
        if recent_videos:
            self.logger.info(f"Search complete: Found {len(recent_videos)} recent videos from '{channel_handle}'")
        else:
            self.logger.info(f"Search complete: No recent videos found from '{channel_handle}' within {self.recent_hours} hours")
        
        return recent_videos
