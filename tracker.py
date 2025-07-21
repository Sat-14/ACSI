# tracker.py - Automatic channel tracker that runs every 6 hours

import os
import time
import json
import threading
import schedule
import logging
import sys
from datetime import datetime
from video_processor import VideoProcessor
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

# Configure safe logging
def setup_tracker_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('tracker.log', encoding='utf-8')
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

class ChannelTracker:
    def __init__(self):
        self.processor = VideoProcessor()
        self.channels_file = os.path.join(BASE_DIR, 'channels.txt')
        self.tracking_log_file = os.path.join(BASE_DIR, 'tracking_log.json')
        self.results_dir = os.path.join(BASE_DIR, 'tracking_results')
        self.logger = setup_tracker_logging()
        
        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)
        self.logger.debug(f"Results directory created/verified: {self.results_dir}")
        
        # Load tracking history
        self.tracking_history = self.load_tracking_history()
        self.logger.info("ChannelTracker initialized successfully")
        self.logger.debug(f"Loaded tracking history for {len(self.tracking_history)} channels")
    
    def load_tracking_history(self):
        """Load tracking history from file"""
        if os.path.exists(self.tracking_log_file):
            try:
                with open(self.tracking_log_file, 'r') as f:
                    history = json.load(f)
                    self.logger.debug(f"Tracking history loaded from: {self.tracking_log_file}")
                    return history
            except Exception as e:
                self.logger.error(f"Failed to load tracking history from {self.tracking_log_file}: {e}")
        else:
            self.logger.debug(f"No existing tracking history found at: {self.tracking_log_file}")
        
        return {}
    
    def save_tracking_history(self):
        """Save tracking history to file"""
        try:
            with open(self.tracking_log_file, 'w') as f:
                json.dump(self.tracking_history, f, indent=2)
            self.logger.debug(f"Tracking history saved to: {self.tracking_log_file}")
        except Exception as e:
            self.logger.error(f"Failed to save tracking history to {self.tracking_log_file}: {e}")
    
    def load_channels(self):
        """Load channels from text file"""
        channels = []
        
        if not os.path.exists(self.channels_file):
            self.logger.warning(f"Channels file not found: {self.channels_file}")
            return channels
        
        try:
            with open(self.channels_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        channels.append(line)
                    elif line.startswith('#'):
                        self.logger.debug(f"Skipped comment line {line_num}: {line}")
            
            self.logger.info(f"Loaded {len(channels)} channels from: {self.channels_file}")
            self.logger.debug(f"Channels to track: {channels}")
            
        except Exception as e:
            self.logger.error(f"Failed to load channels from {self.channels_file}: {e}")
        
        return channels
    
    def save_summary_report(self, timestamp, results):
        """Save a summary report of the tracking run"""
        timestamp_str = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.results_dir, f"summary_{timestamp_str}.txt")
        
        try:
            total_videos = sum(len(r['processed_videos']) for r in results)
            total_errors = sum(len(r['errors']) for r in results)
            
            self.logger.debug(f"Generating summary report: {total_videos} videos, {total_errors} errors")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"YouTube Channel Tracking Report\n")
                f.write(f"Generated: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Channels checked: {len(results)}\n")
                f.write(f"Total new videos found: {total_videos}\n")
                f.write(f"Total processing errors: {total_errors}\n\n")
                
                for result in results:
                    channel = result['channel']
                    f.write(f"\nChannel: {channel}\n")
                    f.write("-" * 40 + "\n")
                    
                    if result['processed_videos']:
                        f.write(f"New videos found: {len(result['processed_videos'])}\n\n")
                        for video in result['processed_videos']:
                            f.write(f"Video: {video.get('title', 'Unknown')}\n")
                            f.write(f"Video ID: {video.get('video_id', 'N/A')}\n")
                            f.write(f"URL: {video.get('url', 'N/A')}\n")
                            f.write(f"Topic: {video.get('topic', 'N/A')}\n")
                            f.write(f"Summary:\n{video.get('summary', 'N/A')}\n")
                            f.write("-" * 40 + "\n")
                    else:
                        f.write("No new videos found.\n")
                    
                    if result['errors']:
                        f.write(f"\nErrors encountered: {len(result['errors'])}\n")
                        for error in result['errors']:
                            f.write(f"  - {error}\n")
                        f.write("\n")
            
            self.logger.info(f"Summary report saved: {report_file}")
            self.logger.debug(f"Report contains {total_videos} videos across {len(results)} channels")
            
        except Exception as e:
            self.logger.error(f"Failed to save summary report to {report_file}: {e}")
            report_file = None
        
        return report_file
    
    def check_channels(self):
        """Check all channels for new videos"""
        check_start_time = time.time()
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.logger.info(f"Starting scheduled channel check at {timestamp_str}")
        
        channels = self.load_channels()
        if not channels:
            self.logger.warning("No channels found to track - check channels.txt file")
            return {
                'timestamp': check_start_time,
                'channels_checked': 0,
                'total_videos_processed': 0,
                'report_file': None,
                'results': []
            }
        
        timestamp = time.time()
        all_results = []
        total_videos_processed = 0
        total_errors = 0
        
        self.logger.info(f"Processing {len(channels)} channels for new content")
        
        for i, channel in enumerate(channels, 1):
            self.logger.info(f"Checking channel {i}/{len(channels)}: '{channel}'")
            
            try:
                # Process channel
                results = self.processor.process_channel(channel)
                
                # Log channel results
                video_count = len(results['processed_videos'])
                error_count = len(results['errors'])
                
                if video_count > 0:
                    self.logger.info(f"[OK] Found {video_count} new videos from '{channel}'")
                    total_videos_processed += video_count
                else:
                    self.logger.debug(f"No new videos found from '{channel}'")
                
                if error_count > 0:
                    self.logger.warning(f"Encountered {error_count} errors processing '{channel}'")
                    total_errors += error_count
                
                all_results.append(results)
                
                # Update tracking history
                if channel not in self.tracking_history:
                    self.tracking_history[channel] = []
                    self.logger.debug(f"Created new tracking history for channel: '{channel}'")
                
                videos_added_to_history = 0
                for video in results['processed_videos']:
                    self.tracking_history[channel].append({
                        'video_id': video['video_id'],
                        'title': video['title'],
                        'checked_at': timestamp,
                        'topic': video.get('topic', 'N/A')
                    })
                    videos_added_to_history += 1
                
                if videos_added_to_history > 0:
                    self.logger.debug(f"Added {videos_added_to_history} videos to tracking history for '{channel}'")
                
                # Rate limiting delay between channels
                if i < len(channels):  # Don't delay after the last channel
                    self.logger.debug(f"Applying rate limit delay (5 seconds) before next channel")
                    time.sleep(5)
                
            except Exception as e:
                error_msg = f"Unexpected error processing channel '{channel}': {e}"
                self.logger.error(error_msg)
                
                all_results.append({
                    'channel': channel,
                    'processed_videos': [],
                    'errors': [str(e)]
                })
                total_errors += 1
        
        # Save tracking history
        self.save_tracking_history()
        
        # Save summary report
        report_file = self.save_summary_report(timestamp, all_results)
        
        # Calculate processing time
        processing_time = time.time() - check_start_time
        
        # Log final summary
        self.logger.info(f"Channel check completed in {processing_time:.1f} seconds:")
        self.logger.info(f"  - Channels checked: {len(channels)}")
        self.logger.info(f"  - New videos processed: {total_videos_processed}")
        self.logger.info(f"  - Total errors: {total_errors}")
        
        if report_file:
            self.logger.info(f"  - Summary report: {report_file}")
        
        # Cleanup temporary files
        self.logger.debug("Starting temporary file cleanup")
        self.processor.cleanup_temp_audio()
        
        # Return results for API endpoint if needed
        return {
            'timestamp': timestamp,
            'channels_checked': len(channels),
            'total_videos_processed': total_videos_processed,
            'total_errors': total_errors,
            'processing_time': processing_time,
            'report_file': report_file,
            'results': all_results
        }
    
    def start_automatic_tracking(self):
        """Start automatic tracking every 6 hours"""
        self.logger.info("Starting automatic channel tracking service")
        self.logger.info("Schedule: Check channels every 6 hours")
        self.logger.info(f"Channels source: {self.channels_file}")
        self.logger.info(f"Results directory: {self.results_dir}")
        
        # Run immediately on start
        self.logger.info("Running initial channel check...")
        try:
            initial_results = self.check_channels()
            self.logger.info(f"Initial check completed - processed {initial_results['total_videos_processed']} videos")
        except Exception as e:
            self.logger.error(f"Initial channel check failed: {e}")
        
        # Schedule to run every 6 hours
        schedule.every(6).hours.do(self._scheduled_check)
        
        self.logger.info("Automatic tracking scheduler started - waiting for next scheduled run")
        
        # Keep the scheduler running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal - stopping automatic tracking")
                break
            except Exception as e:
                self.logger.error(f"Error in tracking scheduler: {e}")
                time.sleep(60)  # Continue after error
    
    def _scheduled_check(self):
        """Wrapper for scheduled channel checks with error handling"""
        try:
            self.logger.info("Executing scheduled channel check")
            results = self.check_channels()
            self.logger.info(f"Scheduled check completed - processed {results['total_videos_processed']} videos")
        except Exception as e:
            self.logger.error(f"Scheduled channel check failed: {e}")
    
    def run_in_background(self):
        """Run the tracker in a background thread"""
        self.logger.info("Starting channel tracker in background thread")
        
        try:
            tracker_thread = threading.Thread(target=self.start_automatic_tracking, name="ChannelTracker")
            tracker_thread.daemon = True
            tracker_thread.start()
            
            self.logger.info("Channel tracker background thread started successfully")
            return tracker_thread
            
        except Exception as e:
            self.logger.error(f"Failed to start background tracker thread: {e}")
            return None
    
    def get_tracking_stats(self):
        """Get statistics about tracking history"""
        stats = {
            'channels_tracked': len(self.tracking_history),
            'total_videos_tracked': sum(len(videos) for videos in self.tracking_history.values()),
            'last_check': None
        }
        
        # Find most recent check time
        latest_timestamp = 0
        for channel_videos in self.tracking_history.values():
            for video in channel_videos:
                if video.get('checked_at', 0) > latest_timestamp:
                    latest_timestamp = video['checked_at']
        
        if latest_timestamp > 0:
            stats['last_check'] = datetime.fromtimestamp(latest_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        self.logger.debug(f"Tracking stats: {stats}")
        return stats

if __name__ == "__main__":
    tracker = ChannelTracker()
    
    # Check if running as standalone or imported
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # Run once for testing
        tracker.logger.info("Running single channel check (test mode)")
        results = tracker.check_channels()
        tracker.logger.info(f"Test run completed: {results['total_videos_processed']} videos processed")
    else:
        # Run continuously
        tracker.logger.info("Starting continuous tracking mode")
        tracker.start_automatic_tracking()