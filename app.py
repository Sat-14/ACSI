# app.py - Flask API for YouTube video transcription + Instagram & Twitter scraping with Gemini AI

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from video_processor import VideoProcessor
from tracker import ChannelTracker
# NEW IMPORTS for Instagram, Twitter, and Social Media AI Processing
from twitter_processor import TwitterScraper
from social_media_processor import SocialMediaProcessor
from instagram_scraper import InstagramScraper
import os
import shutil # Import for directory operations
import threading
import logging
import sys
import time
from datetime import datetime
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, TRANSCRIPTS_DIR

# --- Start of new logging setup ---

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

def setup_flask_logging():
    """Configures the root logger for safe file and console output."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('flask_api.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Safe console handler for Windows
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    root_logger.setLevel(logging.INFO)
    
    # Suppress werkzeug's default logging to reduce noise
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

# --- End of new logging setup ---

# Initialize logging and Flask app
setup_flask_logging()
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize ALL components
processor = VideoProcessor()
tracker = ChannelTracker()
instagram_scraper = InstagramScraper()
twitter_scraper = TwitterScraper()
social_processor = SocialMediaProcessor()
logger = logging.getLogger(__name__)

# --- NEW: FUNCTION TO CLEAR DATA ON STARTUP ---
def clear_data_on_startup():
    """Wipes data from previous runs for a fresh start."""
    logger.info("Server starting up - clearing previous run data...")
    from config import TEMP_AUDIO_DIR

    # Directories to clear and recreate
    dirs_to_clear = [
        TRANSCRIPTS_DIR,
        TEMP_AUDIO_DIR,
        instagram_scraper.downloads_dir,
        twitter_scraper.downloads_dir,
        social_processor.social_transcripts_dir,
        'tracking_results'
    ]

    for dir_path in dirs_to_clear:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                logger.info(f"Successfully removed directory: '{dir_path}'")
            except OSError as e:
                logger.error(f"Error removing directory {dir_path}: {e.strerror}")
        # Recreate the directory to ensure it exists for the application
        os.makedirs(dir_path, exist_ok=True)

    # Specific files to delete
    files_to_delete = ['tracking_log.json']
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Successfully deleted file: '{file_path}'")
            except OSError as e:
                logger.error(f"Error deleting file {file_path}: {e.strerror}")

    logger.info("Previous run data has been cleared successfully.")


# Track API usage statistics
api_stats = {
    'requests_total': 0,
    'requests_by_endpoint': {},
    'errors_total': 0,
    'start_time': time.time()
}

def log_request(endpoint_name, success=True, processing_time=None):
    """Log API request statistics"""
    global api_stats
    
    api_stats['requests_total'] += 1
    
    if endpoint_name not in api_stats['requests_by_endpoint']:
        api_stats['requests_by_endpoint'][endpoint_name] = {'count': 0, 'errors': 0}
    
    api_stats['requests_by_endpoint'][endpoint_name]['count'] += 1
    
    if not success:
        api_stats['errors_total'] += 1
        api_stats['requests_by_endpoint'][endpoint_name]['errors'] += 1
    
    # Log request details
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')[:50]
    
    log_message = f"API Request - {endpoint_name} | IP: {client_ip} | Status: {'SUCCESS' if success else 'ERROR'}"
    if processing_time:
        log_message += f" | Time: {processing_time:.2f}s"
    
    if success:
        logger.info(log_message)
    else:
        logger.warning(log_message)
    
    logger.debug(f"User-Agent: {user_agent}")

def start_background_tracker():
    """Start the background channel tracker"""
    try:
        tracker_thread = tracker.run_in_background()
        if tracker_thread:
            logger.info("Background channel tracker started successfully")
        else:
            logger.error("Failed to start background channel tracker")
    except Exception as e:
        logger.error(f"Error starting background tracker: {e}")

@app.before_request
def before_request():
    """Log incoming requests"""
    request.start_time = time.time()
    
    if request.endpoint and not request.path.startswith('/static'):
        logger.debug(f"Incoming request: {request.method} {request.path}")

@app.after_request
def after_request(response):
    """Log request completion"""
    if hasattr(request, 'start_time') and request.endpoint:
        processing_time = time.time() - request.start_time
        
        if processing_time > 5.0:
            logger.warning(f"Slow request detected: {request.method} {request.path} took {processing_time:.2f}s")
    
    return response

# Frontend Routes
@app.route('/')
def home():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/admin.html')
def admin():
    """Serve the admin panel"""
    return render_template('admin.html')

# API Routes
@app.route('/api')
def api_index():
    """API root endpoint"""
    start_time = time.time()
    
    try:
        uptime = time.time() - api_stats['start_time']
        
        response_data = {
            'message': 'Multi-Platform Content Tracker API with Gemini AI',
            'version': '2.0',
            'status': 'running',
            'uptime_seconds': round(uptime, 2),
            'platforms': ['youtube', 'instagram', 'twitter'],
            'ai_features': ['gemini_analysis', 'smart_summaries', 'sentiment_analysis', 'topic_classification', 'engagement_prediction'],
            'api_stats': {
                'total_requests': api_stats['requests_total'],
                'total_errors': api_stats['errors_total'],
                'error_rate': round((api_stats['errors_total'] / max(api_stats['requests_total'], 1)) * 100, 2)
            },
            'endpoints': {
                # YouTube endpoints
                'POST /api/process_channel': 'Process recent videos from a YouTube channel',
                'POST /api/process_video': 'Process a single video by URL',
                'GET /api/transcripts': 'List all available transcripts',
                'GET /api/transcript/<filename>': 'Download a specific transcript',
                
                # Instagram endpoints
                'POST /api/scrape_instagram': 'Scrape Instagram posts with AI analysis',
                'GET /api/instagram_posts': 'Get recent Instagram posts',
                'GET /api/instagram_handles': 'Get list of Instagram handles',
                'POST /api/instagram_handles': 'Update Instagram handles list',
                
                # Twitter endpoints  
                'POST /api/scrape_twitter': 'Scrape Twitter posts with AI analysis',
                'GET /api/twitter_posts': 'Get recent Twitter posts',
                'GET /api/twitter_handles': 'Get list of Twitter handles',
                'POST /api/twitter_handles': 'Update Twitter handles list',
                
                # Multi-platform endpoints
                'GET /api/content/<platform>': 'Get AI-enhanced content for specific platform',
                'GET /api/social_transcripts': 'Get AI-analyzed social media transcripts',
                'GET /api/social_transcript/<filename>': 'Download specific social media transcript',
                
                # System endpoints
                'POST /api/cleanup': 'Clean up temporary files',
                'POST /api/check_now': 'Manually trigger channel checking',
                'GET /api/tracking_status': 'Get current tracking status',
                'GET /api/channels': 'Get list of tracked YouTube channels',
                'POST /api/channels': 'Update tracked YouTube channels list',
                'GET /api/stats': 'Get detailed API statistics'
            }
        }
        
        processing_time = time.time() - start_time
        log_request('api_index', True, processing_time)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in api index endpoint: {e}")
        log_request('api_index', False)
        return jsonify({'error': 'Internal server error'}), 500

# ===== YOUTUBE ENDPOINTS =====

@app.route('/api/process_channel', methods=['POST'])
def process_channel():
    start_time = time.time()
    try:
        data = request.get_json()
        channel_handle = data.get('channel_handle', '').strip()
        if not channel_handle:
            return jsonify({'error': 'Channel handle is required'}), 400
        
        results = processor.process_channel(channel_handle)
        processing_time = time.time() - start_time
        log_request('process_channel', True, processing_time)
        return jsonify({'success': True, 'results': results, 'processing_time': processing_time})
    except Exception as e:
        log_request('process_channel', False)
        return jsonify({'error': str(e)}), 500

@app.route('/api/process_video', methods=['POST'])
def process_video():
    start_time = time.time()
    try:
        data = request.get_json()
        video_url = data.get('video_url', '').strip()
        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        results = processor.process_single_video(video_url)
        processing_time = time.time() - start_time
        
        if results['success']:
            log_request('process_video', True, processing_time)
            return jsonify({'success': True, 'results': results, 'processing_time': processing_time})
        else:
            log_request('process_video', False, processing_time)
            return jsonify({'success': False, 'error': results['error']}), 400
    except Exception as e:
        log_request('process_video', False)
        return jsonify({'error': str(e)}), 500

# ===== INSTAGRAM ENDPOINTS =====

@app.route('/api/scrape_instagram', methods=['POST'])
def scrape_instagram():
    start_time = time.time()
    try:
        data = request.get_json()
        handle = data.get('handle', '').strip()
        results = instagram_scraper.scrape_instagram_handle(handle) if handle else instagram_scraper.scrape_all_handles()
        processing_time = time.time() - start_time
        log_request('scrape_instagram', True, processing_time)
        return jsonify({'success': True, 'results': results, 'processing_time': processing_time})
    except Exception as e:
        log_request('scrape_instagram', False)
        return jsonify({'error': str(e)}), 500

@app.route('/api/instagram_posts', methods=['GET'])
def get_instagram_posts():
    try:
        handle = request.args.get('handle')
        limit = int(request.args.get('limit', 10))
        posts = instagram_scraper.get_recent_posts(handle=handle, limit=limit)
        return jsonify({'success': True, 'posts': posts, 'count': len(posts)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/instagram_handles', methods=['GET', 'POST'])
def manage_instagram_handles():
    if request.method == 'GET':
        handles = instagram_scraper.load_handles()
        return jsonify({'success': True, 'handles': handles, 'count': len(handles)})
    else: # POST
        data = request.get_json()
        handles = [h.strip().lstrip('@') for h in data.get('handles', []) if isinstance(h, str) and h.strip()]
        with open(instagram_scraper.handles_file, 'w', encoding='utf-8') as f:
            f.write(f"# Instagram Handles - Updated via API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            for handle in handles:
                f.write(f"{handle}\n")
        return jsonify({'success': True, 'message': f'Updated {len(handles)} handles', 'handles': handles})

# ===== TWITTER ENDPOINTS =====

@app.route('/api/scrape_twitter', methods=['POST'])
def scrape_twitter():
    start_time = time.time()
    try:
        data = request.get_json()
        handle = data.get('handle', '').strip()
        results = twitter_scraper.scrape_twitter_handle(handle) if handle else twitter_scraper.scrape_all_handles()
        processing_time = time.time() - start_time
        log_request('scrape_twitter', True, processing_time)
        return jsonify({'success': True, 'results': results, 'processing_time': processing_time})
    except Exception as e:
        log_request('scrape_twitter', False)
        return jsonify({'error': str(e)}), 500

@app.route('/api/twitter_posts', methods=['GET'])
def get_twitter_posts():
    try:
        handle = request.args.get('handle')
        limit = int(request.args.get('limit', 10))
        posts = twitter_scraper.get_recent_tweets(handle=handle, limit=limit)
        return jsonify({'success': True, 'posts': posts, 'count': len(posts)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/twitter_handles', methods=['GET', 'POST'])
def manage_twitter_handles():
    if request.method == 'GET':
        handles = twitter_scraper.load_handles()
        return jsonify({'success': True, 'handles': handles, 'count': len(handles)})
    else: # POST
        data = request.get_json()
        handles = [h.strip().lstrip('@') for h in data.get('handles', []) if isinstance(h, str) and h.strip()]
        with open(twitter_scraper.handles_file, 'w', encoding='utf-8') as f:
            f.write(f"# Twitter Handles - Updated via API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            for handle in handles:
                f.write(f"{handle}\n")
        return jsonify({'success': True, 'message': f'Updated {len(handles)} handles', 'handles': handles})

# ===== SOCIAL MEDIA AI TRANSCRIPTS & CONTENT ENDPOINTS =====

@app.route('/api/social_transcripts', methods=['GET'])
def list_social_transcripts():
    platform = request.args.get('platform')
    limit = int(request.args.get('limit', 20))
    transcripts = social_processor.get_social_transcripts(platform=platform, limit=limit)
    return jsonify({'success': True, 'transcripts': transcripts})

@app.route('/api/social_transcript/<filename>', methods=['GET'])
def get_social_transcript(filename):
    if '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    filepath = os.path.join(social_processor.social_transcripts_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True)

@app.route('/api/content/<platform>', methods=['GET'])
def get_platform_content(platform):
    start_time = time.time()
    try:
        limit = int(request.args.get('limit', 10))
        content_data = []

        if platform.lower() == 'youtube':
            # Simplified logic to grab from pre-processed transcripts
            transcripts = []
            if os.path.exists(TRANSCRIPTS_DIR):
                files = sorted([os.path.join(TRANSCRIPTS_DIR, f) for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.txt')], key=os.path.getmtime, reverse=True)
                for filepath in files[:limit]:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    lines = content.split('\n')
                    title = next((l.split('Video Title:')[1].strip() for l in lines if l.startswith('Video Title:')), 'Unknown')
                    url = next((l.split('Video URL:')[1].strip() for l in lines if l.startswith('Video URL:')), '')
                    summary_lines = []
                    in_summary = False
                    for line in lines:
                        if line.strip() == "SUMMARY:": in_summary = True
                        elif line.strip().startswith("---"): in_summary = False
                        elif in_summary: summary_lines.append(line.strip())
                    transcripts.append({'title': title, 'url': url, 'summary': ' '.join(summary_lines)})
            content_data = transcripts
        elif platform.lower() == 'instagram':
            content_data = instagram_scraper.get_recent_posts(limit=limit)
        elif platform.lower() == 'twitter':
            content_data = twitter_scraper.get_recent_tweets(limit=limit)
        else:
            return jsonify({'error': f'Unsupported platform: {platform}'}), 400
        
        processing_time = time.time() - start_time
        log_request(f'get_content_{platform}', True, processing_time)
        return jsonify({'success': True, 'platform': platform, 'content': content_data, 'count': len(content_data)})
    except Exception as e:
        log_request(f'get_content_{platform}', False)
        return jsonify({'error': str(e)}), 500

# ===== YOUTUBE TRANSCRIPT ENDPOINTS =====

@app.route('/api/transcripts', methods=['GET'])
def list_transcripts():
    if not os.path.exists(TRANSCRIPTS_DIR):
        return jsonify({'success': True, 'transcripts': []})
    
    transcripts = []
    for filename in os.listdir(TRANSCRIPTS_DIR):
        if filename.endswith('.txt'):
            filepath = os.path.join(TRANSCRIPTS_DIR, filename)
            stats = os.stat(filepath)
            transcripts.append({
                'filename': filename, 'size': stats.st_size, 'modified': stats.st_mtime,
                'modified_human': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    transcripts.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'success': True, 'transcripts': transcripts})

@app.route('/api/transcript/<filename>', methods=['GET'])
def get_transcript(filename):
    if '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    filepath = os.path.join(TRANSCRIPTS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Transcript not found'}), 404
    
    if request.args.get('format') == 'json':
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'filename': filename, 'content': content})
    else:
        return send_file(filepath, as_attachment=True)

# ===== SYSTEM ENDPOINTS =====

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    processor.cleanup_temp_audio()
    return jsonify({'success': True, 'message': 'Cleanup completed'})

@app.route('/api/check_now', methods=['POST'])
def check_now():
    threading.Thread(target=tracker.check_channels, name="ManualChannelCheck").start()
    return jsonify({'success': True, 'message': 'Channel check started in background'})

@app.route('/api/tracking_status', methods=['GET'])
def tracking_status():
    return jsonify(tracker.get_tracking_stats())

@app.route('/api/channels', methods=['GET', 'POST'])
def manage_channels():
    if request.method == 'GET':
        return jsonify({'success': True, 'channels': tracker.load_channels()})
    else:
        data = request.get_json()
        channels = [c.strip() for c in data.get('channels', []) if isinstance(c, str) and c.strip()]
        with open(tracker.channels_file, 'w', encoding='utf-8') as f:
            f.write(f"# YouTube Channels - Updated via API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            for channel in channels:
                f.write(f"{channel}\n")
        return jsonify({'success': True, 'message': f'Updated {len(channels)} YouTube channels', 'channels': channels})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get detailed API statistics across all platforms"""
    start_time = time.time()
    
    try:
        uptime = time.time() - api_stats['start_time']
        
        # Get stats from all components
        processor_stats = processor.transcriber.get_processing_stats()
        tracker_stats = tracker.get_tracking_stats()
        
        # Get social media stats
        instagram_stats = {
            'handles_count': len(instagram_scraper.load_handles()),
            'downloads_dir': instagram_scraper.downloads_dir
        }
        
        twitter_stats = {
            'handles_count': len(twitter_scraper.load_handles()),
            'downloads_dir': twitter_scraper.downloads_dir
        }
        
        # Get social media AI analysis stats
        social_transcripts = social_processor.get_social_transcripts(limit=1000)
        social_stats = {
            'total_ai_analyses': len(social_transcripts),
            'instagram_analyses': len([t for t in social_transcripts if t.get('platform') == 'instagram']),
            'twitter_analyses': len([t for t in social_transcripts if t.get('platform') == 'twitter']),
            'transcripts_dir': social_processor.social_transcripts_dir
        }
        
        # Prepare the full api_stats object for the response
        full_api_stats = {
            'uptime_seconds': round(uptime, 2),
            'uptime_human': f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s",
            'total_requests': api_stats['requests_total'],
            'total_errors': api_stats['errors_total'],
            'error_rate_percent': round((api_stats['errors_total'] / max(api_stats['requests_total'], 1)) * 100, 2),
            'requests_by_endpoint': api_stats['requests_by_endpoint']
        }
        
        processing_time = time.time() - start_time
        log_request('get_stats', True, processing_time)
        
        return jsonify({
            'success': True,
            'api_stats': full_api_stats, # Use the fully calculated object
            'processor_stats': processor_stats,
            'tracker_stats': tracker_stats,
            'instagram_stats': instagram_stats,
            'twitter_stats': twitter_stats,
            'social_ai_stats': social_stats
        })
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to get stats: {e}")
        log_request('get_stats', False, processing_time)
        return jsonify({'error': str(e)}), 500

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

# ===== APPLICATION STARTUP =====

if __name__ == '__main__':
    # ===== NEW: CLEAR PREVIOUS DATA ON STARTUP =====
    clear_data_on_startup()
    # ===============================================

    logger.info("=" * 80)
    logger.info("STARTING MULTI-PLATFORM CONTENT TRACKER WITH GEMINI AI")
    logger.info("=" * 80)
    logger.info(f"Version: 2.0 - Full AI Integration")
    logger.info(f"Server: http://{FLASK_HOST}:{FLASK_PORT}")
    logger.info(f"Debug mode: {FLASK_DEBUG}")
    logger.info("")
    logger.info("DIRECTORY CONFIGURATION:")
    logger.info(f"  YouTube Transcripts: {TRANSCRIPTS_DIR}")
    logger.info(f"  Social AI Transcripts: {social_processor.social_transcripts_dir}")
    logger.info(f"  Instagram Downloads: {instagram_scraper.downloads_dir}")
    logger.info(f"  Twitter Downloads: {twitter_scraper.downloads_dir}")
    logger.info("")
    logger.info("PLATFORMS SUPPORTED:")
    logger.info("  ✅ YouTube - Video transcription & AI analysis")
    logger.info("  ✅ Instagram - Post scraping & AI analysis") 
    logger.info("  ✅ Twitter - Tweet scraping & AI analysis")
    logger.info("")
    logger.info("AI FEATURES:")
    logger.info("  🤖 Gemini AI Integration")
    logger.info("  📊 Smart Summaries")
    logger.info("  🎯 Topic Classification")
    logger.info("  😊 Sentiment Analysis")
    logger.info("  🔥 Engagement Prediction")
    logger.info("  📈 Content Categorization")
    
    # Start background tracker for YouTube
    start_background_tracker()
    
    logger.info("")
    logger.info("FRONTEND INTERFACES:")
    logger.info(f"  📱 Dashboard: http://{FLASK_HOST}:{FLASK_PORT}/")
    logger.info(f"  ⚙️  Admin Panel: http://{FLASK_HOST}:{FLASK_PORT}/admin.html")
    logger.info(f"  🔌 API Docs: http://{FLASK_HOST}:{FLASK_PORT}/api")
    logger.info("")
    logger.info("🚀 MULTI-PLATFORM CONTENT TRACKER IS READY!")
    logger.info("=" * 80)
    
    # Run the Flask application
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False)
