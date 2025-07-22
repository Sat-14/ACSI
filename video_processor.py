# video_processor.py - Main processing logic that combines downloading and transcription

from youtube_downloader import YouTubeDownloader
from gemini_transcriber import GeminiTranscriber
import os
import logging
import yt_dlp
import sys
import threading
from config import TEMP_AUDIO_DIR
import time

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
def setup_video_processor_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('video_processor.log', encoding='utf-8')
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

class VideoProcessor:
    def __init__(self):
        self.downloader = YouTubeDownloader()
        self.transcriber = GeminiTranscriber()
        self.logger = setup_video_processor_logging()
        self._processing_lock = threading.Lock()  # Prevent duplicate processing
        
        self.logger.info("VideoProcessor initialized - Components loaded successfully")
    
    def process_channel(self, channel_handle):
        """Process all recent videos from a channel"""
        self.logger.info(f"Starting channel processing for: '{channel_handle}'")
        
        results = {
            'channel': channel_handle,
            'processed_videos': [],
            'errors': []
        }
        
        try:
            # Get recent videos
            recent_videos = self.downloader.get_recent_videos_from_channel(channel_handle)
            
            # No recent videos is NOT an error - this is normal behavior
            if not recent_videos:
                self.logger.info(f"No recent videos found for channel: '{channel_handle}' - this is normal")
                return results
            
            self.logger.info(f"Found {len(recent_videos)} recent videos to process")
            
            # Process each video
            for i, video in enumerate(recent_videos, 1):
                # --- CORRECTED FIX: Apply delay *before* processing the 2nd, 3rd, etc., video ---
                if i > 1:  # No delay for the first video, but delay for all others
                    self.logger.info("Applying 60-second delay to respect API rate limits...")
                    time.sleep(60)
                # --------------------------------------------------------------------------------

                self.logger.info(f"Processing video {i}/{len(recent_videos)}: '{video['title']}'")
                self.logger.debug(f"Video details - ID: {video['video_id']}, Upload date: {video['upload_date']}")
                
                try:
                    # Download audio
                    self.logger.debug(f"Starting audio download for video: '{video['title']}'")
                    audio_info = self.downloader.download_audio(video)
                    
                    if audio_info:
                        # Log file size but don't skip large files
                        if 'file_size_mb' in audio_info:
                            self.logger.info(f"Audio file size: {audio_info['file_size_mb']:.1f} MB")
                            if audio_info['file_size_mb'] > 20:
                                self.logger.warning(f"Large audio file ({audio_info['file_size_mb']:.1f} MB) - transcription may take longer")
                        
                        self.logger.debug(f"Audio download successful, starting transcription for: '{video['title']}'")
                        
                        # Transcribe and save
                        result = self.transcriber.process_audio_file(audio_info)
                        
                        if result['success']:
                            self.logger.info(f"[OK] Successfully processed: '{video['title']}'")
                            self.logger.debug(f"Summary saved to: {result['transcript_path']}")
                            
                            processed_video = {
                                'title': video['title'],
                                'video_id': video['video_id'],
                                'transcript_path': result['transcript_path'],
                                'url': video['url'],
                                'summary': result.get('summary', ''),
                                'topic': result.get('topic', '')
                            }
                            
                            results['processed_videos'].append(processed_video)
                            
                            # Log summary/topic if available
                            if result.get('summary'):
                                self.logger.debug(f"Generated summary for '{video['title']}': {result['summary'][:100]}...")
                            if result.get('topic'):
                                self.logger.debug(f"Identified topic for '{video['title']}': {result['topic']}")
                                
                        else:
                            error_msg = f"Failed to transcribe: '{video['title']}'"
                            self.logger.error(error_msg)
                            results['errors'].append(error_msg)
                            
                            # Log specific transcription error if available
                            if 'error' in result:
                                self.logger.error(f"Transcription error details: {result['error']}")
                                
                    else:
                        error_msg = f"Failed to download audio: '{video['title']}'"
                        self.logger.error(error_msg)
                        results['errors'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Unexpected error processing '{video['title']}': {e}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Log final results
            success_count = len(results['processed_videos'])
            error_count = len(results['errors'])
            total_count = len(recent_videos)
            
            self.logger.info(f"Channel processing complete for '{channel_handle}':")
            self.logger.info(f"  [OK] Successfully processed: {success_count}/{total_count} videos")
            
            if error_count > 0:
                self.logger.warning(f"  [FAIL] Failed to process: {error_count}/{total_count} videos")
                self.logger.debug(f"Errors encountered: {results['errors']}")
            
        except Exception as e:
            error_msg = f"Channel processing failed for '{channel_handle}': {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def process_single_video(self, video_url):
        """Process a single video by URL"""
        self.logger.info(f"Starting single video processing for: {video_url}")
        
        results = {
            'video_url': video_url,
            'success': False,
            'error': None
        }
        
        try:
            # Extract video info
            self.logger.debug(f"Extracting video metadata from: {video_url}")
            
            meta_opts = {
                'quiet': True,
                'skip_download': True,
                'no_warnings': True,
            }
            
            try:
                with yt_dlp.YoutubeDL(meta_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    video_info = {
                        'url': video_url,
                        'title': info.get('title', 'Unknown'),
                        'upload_date': info.get('upload_date', ''),
                        'video_id': info.get('id', '')
                    }
            except Exception as e:
                # Handle member-only, private, or unavailable videos gracefully
                error_str = str(e)
                if "members on level" in error_str or "available to this channel's members" in error_str:
                    results['error'] = "Video is member-only content"
                    self.logger.warning(f"Skipping member-only video: {video_url}")
                elif "Private video" in error_str:
                    results['error'] = "Video is private"
                    self.logger.warning(f"Skipping private video: {video_url}")
                elif "Video unavailable" in error_str:
                    results['error'] = "Video is unavailable"
                    self.logger.warning(f"Skipping unavailable video: {video_url}")
                else:
                    results['error'] = f"Failed to extract video info: {e}"
                    self.logger.error(f"Failed to extract video info from {video_url}: {e}")
                return results
            
            self.logger.info(f"Video metadata extracted: '{video_info['title']}' (ID: {video_info['video_id']})")
            
            # Download audio
            self.logger.debug(f"Starting audio download for: '{video_info['title']}'")
            audio_info = self.downloader.download_audio(video_info)
            
            if audio_info:
                self.logger.debug(f"Audio download successful, starting transcription")
                
                # Transcribe and save
                result = self.transcriber.process_audio_file(audio_info)
                
                if result['success']:
                    self.logger.info(f"[OK] Single video processing successful: '{video_info['title']}'")
                    self.logger.debug(f"Summary saved to: {result['transcript_path']}")
                    
                    results['success'] = True
                    results['transcript_path'] = result['transcript_path']
                    results['video_info'] = video_info
                    results['summary'] = result.get('summary', '')
                    results['topic'] = result.get('topic', '')
                    
                else:
                    error_msg = "Failed to transcribe audio"
                    self.logger.error(f"Transcription failed for: '{video_info['title']}'")
                    if 'error' in result:
                        self.logger.error(f"Transcription error details: {result['error']}")
                    results['error'] = error_msg
                    
            else:
                error_msg = "Failed to download audio"
                self.logger.error(f"Audio download failed for: '{video_info['title']}'")
                results['error'] = error_msg
                
        except Exception as e:
            error_msg = f"Unexpected error processing video: {e}"
            self.logger.error(f"Single video processing failed for {video_url}: {e}")
            results['error'] = error_msg
        
        if results['success']:
            self.logger.info(f"Single video processing completed successfully")
        else:
            self.logger.error(f"Single video processing failed: {results['error']}")
        
        return results
    
    def cleanup_temp_audio(self):
        """Clean up any remaining audio files in temp directory"""
        self.logger.info("Starting temporary audio file cleanup")
        
        try:
            if not os.path.exists(TEMP_AUDIO_DIR):
                self.logger.debug(f"Temp audio directory does not exist: {TEMP_AUDIO_DIR}")
                return
            
            audio_files = []
            # Include all possible audio formats
            audio_extensions = ('.mp3', '.m4a', '.wav', '.opus', '.aac', '.webm', '.ogg', '.flac', '.weba')
            
            for file in os.listdir(TEMP_AUDIO_DIR):
                if file.lower().endswith(audio_extensions):
                    audio_files.append(file)
            
            if not audio_files:
                self.logger.debug("No temporary audio files found to clean up")
                return
            
            self.logger.info(f"Found {len(audio_files)} temporary audio files to clean up")
            
            cleaned_count = 0
            failed_count = 0
            total_size_cleaned = 0
            
            for file in audio_files:
                try:
                    file_path = os.path.join(TEMP_AUDIO_DIR, file)
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    
                    total_size_cleaned += file_size
                    self.logger.debug(f"Cleaned up audio file: {file} ({file_size/1024/1024:.1f} MB)")
                    cleaned_count += 1
                    
                except Exception as file_error:
                    self.logger.error(f"Failed to clean up audio file '{file}': {file_error}")
                    failed_count += 1
            
            self.logger.info(f"Cleanup complete: {cleaned_count} files cleaned ({total_size_cleaned/1024/1024:.1f} MB freed), {failed_count} failed")
            
        except Exception as e:
            self.logger.error(f"Error during temp audio cleanup: {e}")
    
    def get_processing_summary(self, results):
        """Generate a summary of processing results"""
        if isinstance(results, dict) and 'processed_videos' in results:
            # Channel processing results
            summary = {
                'channel': results['channel'],
                'total_processed': len(results['processed_videos']),
                'total_errors': len(results['errors']),
                'success_rate': 0
            }
            
            total_videos = summary['total_processed'] + summary['total_errors']
            if total_videos > 0:
                summary['success_rate'] = (summary['total_processed'] / total_videos) * 100
            
            self.logger.info(f"Processing Summary for '{results['channel']}':")
            self.logger.info(f"  - Videos processed: {summary['total_processed']}")
            self.logger.info(f"  - Processing errors: {summary['total_errors']}")
            self.logger.info(f"  - Success rate: {summary['success_rate']:.1f}%")
            
            return summary
            
        else:
            # Single video processing results
            status = "SUCCESS" if results.get('success') else "FAILED"
            self.logger.info(f"Single Video Processing Summary: {status}")
            if not results.get('success') and results.get('error'):
                self.logger.info(f"  - Error: {results['error']}")
            
            return results
