        if platform.lower() == 'youtube':
            # Get YouTube transcripts (existing functionality)
            content_data = []
            if os.path.exists(TRANSCRIPTS_DIR):
                transcripts = []
                for filename in os.listdir(TRANSCRIPTS_DIR)[:limit]:
                    if filename.endswith('.txt'):
                        filepath = os.path.join(TRANSCRIPTS_DIR, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Parse transcript content (simplified)
                            lines = content.split('\n')
                            title = next((line.split('Video Title:')[1].strip() for line in lines if line.startswith('Video Title:')), 'Unknown')
                            summary = ""
                            topic = ""
                            
                            # Extract summary and topic
                            in_summary = False
                            summary_lines = []
                            for line in lines:
                                if line.strip() == "SUMMARY:":
                                    in_summary = True
                                elif line.strip() == "TOPIC AND SENTIMENT:":
                                    in_summary = False
                                    # Next non-empty line is the topic
                                    topic_idx = lines.index(line) + 1
                                    while topic_idx < len(lines) and not lines[topic_idx].strip():
                                        topic_idx += 1
                                    if topic_idx < len(lines):
                                        topic = lines[topic_idx].strip()
                                elif line.strip().startswith("---"):
                                    in_summary = False
                                elif in_summary and line.strip():
                                    summary_lines.append(line.strip())
                            
                            summary = ' '.join(summary_lines)
                            
                            transcripts.append({
                                'id': filename.replace('.txt', ''),
                                'title': title,
                                'summary': summary,
                                'topic': topic,
                                'platform': 'youtube',
                                'type': 'transcript',
                                'filename': filename
                            })
                        except:
                            continue
            
            content_data = transcripts
            
        elif platform.lower() == 'instagram':
            # Get Instagram posts with AI analysis
            posts = instagram_scraper.get_recent_posts(limit=limit)
            social_transcripts = social_processor.get_social_transcripts(platform='instagram', limit=limit)
            
            content_data = []
            for post in posts:
                # Try to find corresponding AI analysis
                ai_analysis = None
                transcript_filename = None
                
                if post.get('ai_analysis'):
                    ai_analysis = post['ai_analysis']
                elif post.get('transcript_path'):
                    # Extract filename from path
                    transcript_filename = os.path.basename(post['transcript_path'])
                
                # If no AI analysis in post, try to find in social transcripts
                if not ai_analysis:
                    post_id = post.get('post_id', '')
                    for transcript in social_transcripts:
                        if post_id in transcript['filename']:
                            transcript_filename = transcript['filename']
                            # Load the analysis from file
                            try:
                                filepath = os.path.join(social_processor.social_transcripts_dir, transcript_filename)
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                
                                # Extract AI analysis from file
                                lines = content.split('\n')
                                ai_analysis = {
                                    'summary': '',
                                    'topic': '',
                                    'sentiment': 'Neutral',
                                    'content_type': 'Personal',
                                    'engagement_potential': 5
                                }
                                
                                in_summary = False
                                summary_lines = []
                                for line in lines:
                                    if "TOPIC AND THEME:" in line:
                                        topic_idx = lines.index(line) + 1
                                        if topic_idx < len(lines):
                                            ai_analysis['topic'] = lines[topic_idx].strip()
                                    elif "SENTIMENT ANALYSIS:" in line:
                                        sent_idx = lines.index(line) + 1
                                        if sent_idx < len(lines):
                                            ai_analysis['sentiment'] = lines[sent_idx].strip()
                                    elif "AI GENERATED SUMMARY:" in line:
                                        in_summary = True
                                    elif in_summary and line.strip().startswith("---"):
                                        in_summary = False
                                    elif in_summary and line.strip():
                                        summary_lines.append(line.strip())
                                
                                ai_analysis['summary'] = ' '.join(summary_lines)
                                
                            except Exception as e:
                                logger.debug(f"Could not load AI analysis from {transcript_filename}: {e}")
                
                content_item = {
                    'id': post.get('post_id', ''),
                    'title': (ai_analysis.get('topic') if ai_analysis else post.get('metadata', {}).get('caption', ''))[:100] + '...' if ai_analysis or post.get('metadata', {}).get('caption') else 'No caption',
                    'summary': ai_analysis.get('summary', post.get('metadata', {}).get('caption', 'No summary available')) if ai_analysis else post.get('metadata', {}).get('caption', 'No summary available'),
                    'topic': ai_analysis.get('topic', 'Instagram post') if ai_analysis else 'Instagram post',
                    'sentiment': ai_analysis.get('sentiment', 'Neutral') if ai_analysis else 'Neutral',
                    'platform': 'instagram',
                    'type': 'post',
                    'media_count': len(post.get('media', [])),
                    'handle': post.get('handle', ''),
                    'scraped_at': post.get('scraped_at', ''),
                    'engagement_potential': ai_analysis.get('engagement_potential', 5) if ai_analysis else 5,
                    'content_type': ai_analysis.get('content_type', 'Personal') if ai_analysis else 'Personal',
                    'transcript_filename': transcript_filename
                }
                content_data.append(content_item)
            
        elif platform.lower() == 'twitter':
            # Get Twitter posts with AI analysis  
            tweets = twitter_scraper.get_recent_tweets(limit=limit)
            social_transcripts = social_processor.get_social_transcripts(platform='twitter', limit=limit)
            
            content_data = []
            for tweet in tweets:
                # Try to find corresponding AI analysis
                ai_analysis = None
                transcript_filename = None
                
                if tweet.get('ai_analysis'):
                    ai_analysis = tweet['ai_analysis']
                elif tweet.get('transcript_path'):
                    transcript_filename = os.path.basename(tweet['transcript_path'])
                
                # If no AI analysis in tweet, try to find in social transcripts
                if not ai_analysis:
                    tweet_id = tweet.get('tweet_id', '')
                    for transcript in social_transcripts:
                        if tweet_id in transcript['filename']:
                            transcript_filename = transcript['filename']
                            # Load the analysis from file (similar to Instagram logic)
                            try:
                                filepath = os.path.join(social_processor.social_transcripts_dir, transcript_filename)
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                
                                # Extract AI analysis from file
                                lines = content.split('\n')
                                ai_analysis = {
                                    'summary': '',
                                    'topic': '',
                                    'sentiment': 'Neutral',
                                    'content_type': 'Personal',
                                    'engagement_potential': 5
                                }
                                
                                in_summary = False
                                summary_lines = []
                                for line in lines:
                                    if "TOPIC AND THEME:" in line:
                                        topic_idx = lines.index(line) + 1
                                        if topic_idx < len(lines):
                                            ai_analysis['topic'] = lines[topic_idx].strip()
                                    elif "SENTIMENT ANALYSIS:" in line:
                                        sent_idx = lines.index(line) + 1
                                        if sent_idx < len(lines):
                                            ai_analysis['sentiment'] = lines[sent_idx].strip()
                                    elif "AI GENERATED SUMMARY:" in line:
                                        in_summary = True
                                    elif in_summary and line.strip().startswith("---"):
                                        in_summary = False
                                    elif in_summary and line.strip():
                                        summary_lines.append(line.strip())
                                
                                ai_analysis['summary'] = ' '.join(summary_lines)
                                
                            except Exception as e:
                                logger.debug(f"Could not load AI analysis from {transcript_filename}: {e}")
                
                content_item = {
                    'id': tweet.get('tweet_id', ''),
                    'title': (ai_analysis.get('topic') if ai_analysis else tweet.get('text', ''))[:100] + '...' if ai_analysis or tweet.get('text') else 'No text',
                    'summary': ai_analysis.get('summary', tweet.get('text', 'No summary available')) if ai_analysis else tweet.get('text', 'No summary available'),
                    'topic': ai_analysis.get('topic', 'Twitter post') if ai_analysis else 'Twitter post',
                    'sentiment': ai_analysis.get('sentiment', 'Neutral') if ai_analysis else 'Neutral',
                    'platform': 'twitter',
                    'type': 'tweet',
                    'media_count': len(tweet.get('media', [])),
                    'handle': tweet.get('handle', ''),
                    'scraped_at': tweet.get('scraped_at', ''),
                    'engagement': tweet.get('engagement', {}),
                    'engagement_potential': ai_analysis.get('engagement_potential', 5) if ai_analysis else 5,
                    'content_type': ai_analysis.get('content_type', 'Personal') if ai_analysis else 'Personal',
                    'transcript_filename': transcript_filename
                }
                content_data.append(content_item)# app.py - Flask API for YouTube video transcription + Instagram & Twitter scraping

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from video_processor import VideoProcessor
from tracker import ChannelTracker
# NEW IMPORTS for Instagram and Twitter
from instagram_scraper import InstagramScraper
from twitter_scraper import TwitterScraper
import os
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

# NEW: Initialize social media processor
from social_media_processor import SocialMediaProcessor
social_processor = SocialMediaProcessor()

# Initialize components
processor = VideoProcessor()
tracker = ChannelTracker()
# NEW: Initialize Instagram and Twitter scrapers
instagram_scraper = InstagramScraper()
twitter_scraper = TwitterScraper()
logger = logging.getLogger(__name__)

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
            'message': 'Multi-Platform Content Tracker API',
            'version': '1.1',
            'status': 'running',
            'uptime_seconds': round(uptime, 2),
            'platforms': ['youtube', 'instagram', 'twitter'],
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
                'POST /api/scrape_instagram': 'Scrape Instagram posts from specified handles',
                'GET /api/instagram_posts': 'Get recent Instagram posts',
                'GET /api/instagram_handles': 'Get list of Instagram handles',
                'POST /api/instagram_handles': 'Update Instagram handles list',
                
                # Twitter endpoints  
                'POST /api/scrape_twitter': 'Scrape Twitter posts from specified handles',
                'GET /api/twitter_posts': 'Get recent Twitter posts',
                'GET /api/twitter_handles': 'Get list of Twitter handles',
                'POST /api/twitter_handles': 'Update Twitter handles list',
                
                # Multi-platform endpoints
                'GET /api/content/<platform>': 'Get content for specific platform (youtube/instagram/twitter)',
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

# ===== EXISTING YOUTUBE ENDPOINTS (keeping all original functionality) =====

@app.route('/api/process_channel', methods=['POST'])
def process_channel():
    """Process recent videos from a YouTube channel"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        channel_handle = data.get('channel_handle', '').strip()
        
        if not channel_handle:
            logger.warning(f"Channel processing request missing channel_handle")
            log_request('process_channel', False)
            return jsonify({'error': 'Channel handle is required'}), 400
        
        logger.info(f"Processing channel request for: '{channel_handle}'")
        
        results = processor.process_channel(channel_handle)
        
        video_count = len(results['processed_videos'])
        error_count = len(results['errors'])
        
        processing_time = time.time() - start_time
        
        logger.info(f"Channel processing completed for '{channel_handle}': {video_count} videos, {error_count} errors in {processing_time:.1f}s")
        log_request('process_channel', True, processing_time)
        
        return jsonify({
            'success': True,
            'results': results,
            'processing_time': processing_time
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Channel processing failed: {e}")
        log_request('process_channel', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/process_video', methods=['POST'])
def process_video():
    """Process a single video by URL"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        video_url = data.get('video_url', '').strip()
        
        if not video_url:
            logger.warning("Video processing request missing video_url")
            log_request('process_video', False)
            return jsonify({'error': 'Video URL is required'}), 400
        
        logger.info(f"Processing single video request: {video_url}")
        
        results = processor.process_single_video(video_url)
        
        processing_time = time.time() - start_time
        
        if results['success']:
            logger.info(f"Single video processing successful in {processing_time:.1f}s")
            log_request('process_video', True, processing_time)
            return jsonify({
                'success': True,
                'results': results,
                'processing_time': processing_time
            })
        else:
            logger.warning(f"Single video processing failed: {results.get('error', 'Unknown error')}")
            log_request('process_video', False, processing_time)
            return jsonify({
                'success': False,
                'error': results['error']
            }), 400
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Video processing failed: {e}")
        log_request('process_video', False, processing_time)
        return jsonify({'error': str(e)}), 500

# ===== NEW INSTAGRAM ENDPOINTS =====

@app.route('/api/scrape_instagram', methods=['POST'])
def scrape_instagram():
    """Scrape Instagram posts from specified handles"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        handle = data.get('handle', '').strip()
        
        if handle:
            # Scrape specific handle
            logger.info(f"Instagram scraping request for handle: @{handle}")
            results = instagram_scraper.scrape_instagram_handle(handle)
        else:
            # Scrape all handles from file
            logger.info("Instagram scraping request for all handles")
            results = instagram_scraper.scrape_all_handles()
        
        processing_time = time.time() - start_time
        
        logger.info(f"Instagram scraping completed in {processing_time:.1f}s")
        log_request('scrape_instagram', True, processing_time)
        
        return jsonify({
            'success': True,
            'results': results,
            'processing_time': processing_time
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Instagram scraping failed: {e}")
        log_request('scrape_instagram', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/instagram_posts', methods=['GET'])
def get_instagram_posts():
    """Get recent Instagram posts"""
    start_time = time.time()
    
    try:
        handle = request.args.get('handle')
        limit = int(request.args.get('limit', 10))
        
        posts = instagram_scraper.get_recent_posts(handle=handle, limit=limit)
        
        processing_time = time.time() - start_time
        log_request('get_instagram_posts', True, processing_time)
        
        return jsonify({
            'success': True,
            'posts': posts,
            'count': len(posts),
            'processing_time': processing_time
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to get Instagram posts: {e}")
        log_request('get_instagram_posts', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/instagram_handles', methods=['GET', 'POST'])
def manage_instagram_handles():
    """GET: Get list of Instagram handles, POST: Update Instagram handles list"""
    start_time = time.time()
    
    if request.method == 'GET':
        try:
            handles = instagram_scraper.load_handles()
            
            processing_time = time.time() - start_time
            log_request('get_instagram_handles', True, processing_time)
            
            return jsonify({
                'success': True,
                'handles': handles,
                'count': len(handles)
            })
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to get Instagram handles: {e}")
            log_request('get_instagram_handles', False, processing_time)
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        try:
            data = request.get_json()
            handles = data.get('handles', [])
            
            if not isinstance(handles, list):
                logger.warning("Invalid Instagram handles data: expected list")
                log_request('update_instagram_handles', False)
                return jsonify({'error': 'Handles must be a list'}), 400
            
            clean_handles = []
            for handle in handles:
                if isinstance(handle, str) and handle.strip():
                    clean_handles.append(handle.strip().lstrip('@'))
            
            logger.info(f"Updating Instagram handles: {len(clean_handles)} handles")
            
            with open(instagram_scraper.handles_file, 'w', encoding='utf-8') as f:
                f.write("# Instagram Handles to Track\n")
                f.write(f"# Updated via API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for handle in clean_handles:
                    f.write(f"{handle}\n")
            
            processing_time = time.time() - start_time
            logger.info(f"Successfully updated {len(clean_handles)} Instagram handles in {processing_time:.3f}s")
            log_request('update_instagram_handles', True, processing_time)
            
            return jsonify({
                'success': True,
                'message': f'Updated {len(clean_handles)} Instagram handles',
                'handles': clean_handles,
                'processing_time': processing_time
            })
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to update Instagram handles: {e}")
            log_request('update_instagram_handles', False, processing_time)
            return jsonify({'error': str(e)}), 500

# ===== NEW TWITTER ENDPOINTS =====

@app.route('/api/scrape_twitter', methods=['POST'])
def scrape_twitter():
    """Scrape Twitter posts from specified handles"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        handle = data.get('handle', '').strip()
        
        if handle:
            # Scrape specific handle
            logger.info(f"Twitter scraping request for handle: @{handle}")
            results = twitter_scraper.scrape_twitter_handle(handle)
        else:
            # Scrape all handles from file
            logger.info("Twitter scraping request for all handles")
            results = twitter_scraper.scrape_all_handles()
        
        processing_time = time.time() - start_time
        
        logger.info(f"Twitter scraping completed in {processing_time:.1f}s")
        log_request('scrape_twitter', True, processing_time)
        
        return jsonify({
            'success': True,
            'results': results,
            'processing_time': processing_time
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Twitter scraping failed: {e}")
        log_request('scrape_twitter', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/twitter_posts', methods=['GET'])
def get_twitter_posts():
    """Get recent Twitter posts"""
    start_time = time.time()
    
    try:
        handle = request.args.get('handle')
        limit = int(request.args.get('limit', 10))
        
        posts = twitter_scraper.get_recent_tweets(handle=handle, limit=limit)
        
        processing_time = time.time() - start_time
        log_request('get_twitter_posts', True, processing_time)
        
        return jsonify({
            'success': True,
            'posts': posts,
            'count': len(posts),
            'processing_time': processing_time
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to get Twitter posts: {e}")
        log_request('get_twitter_posts', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/twitter_handles', methods=['GET', 'POST'])
def manage_twitter_handles():
    """GET: Get list of Twitter handles, POST: Update Twitter handles list"""
    start_time = time.time()
    
    if request.method == 'GET':
        try:
            handles = twitter_scraper.load_handles()
            
            processing_time = time.time() - start_time
            log_request('get_twitter_handles', True, processing_time)
            
            return jsonify({
                'success': True,
                'handles': handles,
                'count': len(handles)
            })
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to get Twitter handles: {e}")
            log_request('get_twitter_handles', False, processing_time)
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        try:
            data = request.get_json()
            handles = data.get('handles', [])
            
            if not isinstance(handles, list):
                logger.warning("Invalid Twitter handles data: expected list")
                log_request('update_twitter_handles', False)
                return jsonify({'error': 'Handles must be a list'}), 400
            
            clean_handles = []
            for handle in handles:
                if isinstance(handle, str) and handle.strip():
                    clean_handles.append(handle.strip().lstrip('@'))
            
            logger.info(f"Updating Twitter handles: {len(clean_handles)} handles")
            
            with open(twitter_scraper.handles_file, 'w', encoding='utf-8') as f:
                f.write("# Twitter Handles to Track\n")
                f.write(f"# Updated via API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for handle in clean_handles:
                    f.write(f"{handle}\n")
            
            processing_time = time.time() - start_time
            logger.info(f"Successfully updated {len(clean_handles)} Twitter handles in {processing_time:.3f}s")
            log_request('update_twitter_handles', True, processing_time)
            
            return jsonify({
                'success': True,
                'message': f'Updated {len(clean_handles)} Twitter handles',
                'handles': clean_handles,
                'processing_time': processing_time
            })
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to update Twitter handles: {e}")
            log_request('update_twitter_handles', False, processing_time)
            return jsonify({'error': str(e)}), 500

# ===== NEW SOCIAL MEDIA TRANSCRIPTS ENDPOINTS =====

@app.route('/api/social_transcripts', methods=['GET'])
def list_social_transcripts():
    """List all AI-analyzed social media transcripts"""
    start_time = time.time()
    
    try:
        platform = request.args.get('platform')  # Filter by platform if specified
        limit = int(request.args.get('limit', 20))
        
        transcripts = social_processor.get_social_transcripts(platform=platform, limit=limit)
        
        processing_time = time.time() - start_time
        logger.info(f"Listed {len(transcripts)} social media transcripts in {processing_time:.3f}s")
        log_request('list_social_transcripts', True, processing_time)
        
        return jsonify({
            'success': True,
            'transcripts': transcripts,
            'total_count': len(transcripts),
            'platform_filter': platform,
            'processing_time': processing_time
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to list social media transcripts: {e}")
        log_request('list_social_transcripts', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/social_transcript/<filename>', methods=['GET'])
def get_social_transcript(filename):
    """Download or get content of a specific social media transcript"""
    start_time = time.time()
    
    try:
        if not filename.endswith('.txt') or '/' in filename or '\\' in filename:
            logger.warning(f"Invalid social transcript filename requested: {filename}")
            log_request('get_social_transcript', False)
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join(social_processor.social_transcripts_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Social transcript not found: {filename}")
            log_request('get_social_transcript', False)
            return jsonify({'error': 'Social transcript not found'}), 404
        
        format_type = request.args.get('format', 'file')
        file_size = os.path.getsize(filepath)
        
        logger.info(f"Serving social transcript: {filename} ({file_size/1024:.1f} KB) as {format_type}")
        
        if format_type == 'json':
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            processing_time = time.time() - start_time
            log_request('get_social_transcript', True, processing_time)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'content': content,
                'size': file_size
            })
        else:
            processing_time = time.time() - start_time
            log_request('get_social_transcript', True, processing_time)
            return send_file(filepath, as_attachment=True)
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to serve social transcript {filename}: {e}")
        log_request('get_social_transcript', False, processing_time)
        return jsonify({'error': str(e)}), 500

# ===== ENHANCED MULTI-PLATFORM CONTENT ENDPOINT =====

@app.route('/api/content/<platform>', methods=['GET'])
def get_platform_content(platform):
    """Get content for specific platform (youtube/instagram/twitter)"""
    start_time = time.time()
    
    try:
        limit = int(request.args.get('limit', 10))
        
        if platform.lower() == 'youtube':
            # Get YouTube transcripts
            response = jsonify({})
            if os.path.exists(TRANSCRIPTS_DIR):
                transcripts = []
                for filename in os.listdir(TRANSCRIPTS_DIR)[:limit]:
                    if filename.endswith('.txt'):
                        filepath = os.path.join(TRANSCRIPTS_DIR, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Parse transcript content (simplified)
                            lines = content.split('\n')
                            title = next((line.split('Video Title:')[1].strip() for line in lines if line.startswith('Video Title:')), 'Unknown')
                            
                            transcripts.append({
                                'filename': filename,
                                'title': title,
                                'platform': 'youtube',
                                'type': 'transcript'
                            })
                        except:
                            continue
            
            content_data = transcripts
            
        elif platform.lower() == 'instagram':
            posts = instagram_scraper.get_recent_posts(limit=limit)
            content_data = [{
                'id': post.get('post_id', ''),
                'title': post.get('metadata', {}).get('caption', '')[:100] + '...' if post.get('metadata', {}).get('caption') else 'No caption',
                'platform': 'instagram',
                'type': 'post',
                'media_count': len(post.get('media', [])),
                'handle': post.get('handle', ''),
                'scraped_at': post.get('scraped_at', '')
            } for post in posts]
            
        elif platform.lower() == 'twitter':
            tweets = twitter_scraper.get_recent_tweets(limit=limit)
            content_data = [{
                'id': tweet.get('tweet_id', ''),
                'title': tweet.get('text', '')[:100] + '...' if tweet.get('text') else 'No text',
                'platform': 'twitter',
                'type': 'tweet',
                'media_count': len(tweet.get('media', [])),
                'handle': tweet.get('handle', ''),
                'scraped_at': tweet.get('scraped_at', ''),
                'engagement': tweet.get('engagement', {})
            } for tweet in tweets]
            
        else:
            log_request(f'get_content_{platform}', False)
            return jsonify({'error': f'Unsupported platform: {platform}'}), 400
        
        processing_time = time.time() - start_time
        log_request(f'get_content_{platform}', True, processing_time)
        
        return jsonify({
            'success': True,
            'platform': platform,
            'content': content_data,
            'count': len(content_data),
            'processing_time': processing_time
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to get {platform} content: {e}")
        log_request(f'get_content_{platform}', False, processing_time)
        return jsonify({'error': str(e)}), 500

# ===== KEEPING ALL EXISTING ENDPOINTS (transcripts, cleanup, etc.) =====

@app.route('/api/transcripts', methods=['GET'])
def list_transcripts():
    """List all available transcripts"""
    start_time = time.time()
    
    try:
        if not os.path.exists(TRANSCRIPTS_DIR):
            logger.warning(f"Transcripts directory does not exist: {TRANSCRIPTS_DIR}")
            log_request('list_transcripts', True)
            return jsonify({
                'success': True,
                'transcripts': [],
                'message': 'No transcripts directory found'
            })
        
        transcripts = []
        for filename in os.listdir(TRANSCRIPTS_DIR):
            if filename.endswith('.txt'):
                filepath = os.path.join(TRANSCRIPTS_DIR, filename)
                try:
                    stats = os.stat(filepath)
                    transcripts.append({
                        'filename': filename,
                        'size': stats.st_size,
                        'modified': stats.st_mtime,
                        'modified_human': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as file_error:
                    logger.warning(f"Could not get stats for transcript file {filename}: {file_error}")
        
        transcripts.sort(key=lambda x: x['modified'], reverse=True)
        
        processing_time = time.time() - start_time
        logger.info(f"Listed {len(transcripts)} transcripts in {processing_time:.3f}s")
        log_request('list_transcripts', True, processing_time)
        
        return jsonify({
            'success': True,
            'transcripts': transcripts,
            'total_count': len(transcripts),
            'total_size_mb': round(sum(t['size'] for t in transcripts) / (1024 * 1024), 2)
        })
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to list transcripts: {e}")
        log_request('list_transcripts', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/transcript/<filename>', methods=['GET'])
def get_transcript(filename):
    """Download or get content of a specific transcript"""
    start_time = time.time()
    
    try:
        if not filename.endswith('.txt') or '/' in filename or '\\' in filename:
            logger.warning(f"Invalid transcript filename requested: {filename}")
            log_request('get_transcript', False)
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join(TRANSCRIPTS_DIR, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Transcript not found: {filename}")
            log_request('get_transcript', False)
            return jsonify({'error': 'Transcript not found'}), 404
        
        format_type = request.args.get('format', 'file')
        file_size = os.path.getsize(filepath)
        
        logger.info(f"Serving transcript: {filename} ({file_size/1024:.1f} KB) as {format_type}")
        
        if format_type == 'json':
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            processing_time = time.time() - start_time
            log_request('get_transcript', True, processing_time)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'content': content,
                'size': file_size
            })
        else:
            processing_time = time.time() - start_time
            log_request('get_transcript', True, processing_time)
            return send_file(filepath, as_attachment=True)
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to serve transcript {filename}: {e}")
        log_request('get_transcript', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """Clean up temporary files"""
    start_time = time.time()
    
    try:
        logger.info("Manual cleanup requested via API")
        processor.cleanup_temp_audio()
        
        processing_time = time.time() - start_time
        logger.info(f"Manual cleanup completed in {processing_time:.2f}s")
        log_request('cleanup', True, processing_time)
        
        return jsonify({
            'success': True,
            'message': 'Cleanup completed',
            'processing_time': processing_time
        })
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Manual cleanup failed: {e}")
        log_request('cleanup', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_now', methods=['POST'])
def check_now():
    """Manually trigger channel checking"""
    start_time = time.time()
    
    try:
        logger.info("Manual channel check requested via API")
        
        def run_check():
            try:
                results = tracker.check_channels()
                logger.info(f"Manual channel check completed: {results.get('total_videos_processed', 0)} videos processed")
            except Exception as check_error:
                logger.error(f"Manual channel check failed: {check_error}")
        
        check_thread = threading.Thread(target=run_check, name="ManualChannelCheck")
        check_thread.start()
        
        processing_time = time.time() - start_time
        log_request('check_now', True, processing_time)
        
        return jsonify({
            'success': True,
            'message': 'Channel check started in background',
            'processing_time': processing_time
        })
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to start manual channel check: {e}")
        log_request('check_now', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tracking_status', methods=['GET'])
def tracking_status():
    """Get current tracking status"""
    start_time = time.time()
    
    try:
        channels = tracker.load_channels()
        history = tracker.tracking_history
        
        last_check = None
        total_videos_tracked = 0
        
        if history:
            all_checks = []
            for channel_data in history.values():
                total_videos_tracked += len(channel_data)
                for video in channel_data:
                    check_time = video.get('checked_at', 0)
                    if check_time:
                        all_checks.append(check_time)
            
            if all_checks:
                last_check = max(all_checks)
        
        last_check_human = None
        if last_check:
            last_check_human = datetime.fromtimestamp(last_check).strftime('%Y-%m-%d %H:%M:%S')
        
        processing_time = time.time() - start_time
        logger.debug(f"Tracking status retrieved in {processing_time:.3f}s")
        log_request('tracking_status', True, processing_time)
        
        return jsonify({
            'tracking_active': True,
            'last_check': last_check,
            'last_check_human': last_check_human,
            'channels_count': len(channels),
            'channels': channels,
            'total_videos_tracked': total_videos_tracked,
            'tracking_history_size': len(history)
        })
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to get tracking status: {e}")
        log_request('tracking_status', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/channels', methods=['GET', 'POST'])
def manage_channels():
    """GET: Get list of tracked YouTube channels, POST: Update tracked YouTube channels list"""
    start_time = time.time()
    
    if request.method == 'GET':
        try:
            channels = tracker.load_channels()
            
            processing_time = time.time() - start_time
            logger.debug(f"Retrieved {len(channels)} channels in {processing_time:.3f}s")
            log_request('get_channels', True, processing_time)
            
            return jsonify({
                'success': True,
                'channels': channels,
                'count': len(channels)
            })
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to get channels: {e}")
            log_request('get_channels', False, processing_time)
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        try:
            data = request.get_json()
            channels = data.get('channels', [])
            
            if not isinstance(channels, list):
                logger.warning("Invalid channels data: expected list")
                log_request('update_channels', False)
                return jsonify({'error': 'Channels must be a list'}), 400
            
            clean_channels = []
            for channel in channels:
                if isinstance(channel, str) and channel.strip():
                    clean_channels.append(channel.strip())
            
            logger.info(f"Updating tracked YouTube channels: {len(clean_channels)} channels")
            
            with open(tracker.channels_file, 'w', encoding='utf-8') as f:
                f.write("# YouTube Channels to Track\n")
                f.write(f"# Updated via API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for channel in clean_channels:
                    f.write(f"{channel}\n")
            
            processing_time = time.time() - start_time
            logger.info(f"Successfully updated {len(clean_channels)} YouTube channels in {processing_time:.3f}s")
            log_request('update_channels', True, processing_time)
            
            return jsonify({
                'success': True,
                'message': f'Updated {len(clean_channels)} YouTube channels',
                'channels': clean_channels,
                'processing_time': processing_time
            })
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to update channels: {e}")
            log_request('update_channels', False, processing_time)
            return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get detailed API statistics"""
    start_time = time.time()
    
    try:
        uptime = time.time() - api_stats['start_time']
        
        processor_stats = processor.transcriber.get_processing_stats()
        tracker_stats = tracker.get_tracking_stats()
        
        # NEW: Get Instagram and Twitter stats
        instagram_stats = {
            'handles_count': len(instagram_scraper.load_handles()),
            'downloads_dir': instagram_scraper.downloads_dir
        }
        
        twitter_stats = {
            'handles_count': len(twitter_scraper.load_handles()),
            'downloads_dir': twitter_scraper.downloads_dir
        }
        
        processing_time = time.time() - start_time
        log_request('get_stats', True, processing_time)
        
        return jsonify({
            'success': True,
            'api_stats': {
                'uptime_seconds': round(uptime, 2),
                'uptime_human': f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s",
                'total_requests': api_stats['requests_total'],
                'total_errors': api_stats['errors_total'],
                'error_rate_percent': round((api_stats['errors_total'] / max(api_stats['requests_total'], 1)) * 100, 2),
                'requests_by_endpoint': api_stats['requests_by_endpoint']
            },
            'processor_stats': processor_stats,
            'tracker_stats': tracker_stats,
            'instagram_stats': instagram_stats,
            'twitter_stats': twitter_stats
        })
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to get stats: {e}")
        log_request('get_stats', False, processing_time)
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.method} {request.path}")
    log_request('404_error', False)
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {request.method} {request.path} - {error}")
    log_request('500_error', False)
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(400)
def bad_request(error):
    logger.warning(f"400 error: {request.method} {request.path} - {error}")
    log_request('400_error', False)
    return jsonify({'error': 'Bad request'}), 400

if __name__ == '__main__':
    logger.info(f"Starting Multi-Platform Content Tracker API")
    logger.info(f"Server: http://{FLASK_HOST}:{FLASK_PORT}")
    logger.info(f"Debug mode: {FLASK_DEBUG}")
    logger.info(f"Transcripts directory: {TRANSCRIPTS_DIR}")
    logger.info(f"Instagram downloads: {instagram_scraper.downloads_dir}")
    logger.info(f"Twitter downloads: {twitter_scraper.downloads_dir}")
    
    # Start background tracker
    start_background_tracker()
    
    logger.info("API server startup completed - ready to accept requests")
    logger.info("Frontend available at:")
    logger.info(f"  - Dashboard: http://{FLASK_HOST}:{FLASK_PORT}/")
    logger.info(f"  - Admin Panel: http://{FLASK_HOST}:{FLASK_PORT}/admin.html")
    logger.info(f"  - API Docs: http://{FLASK_HOST}:{FLASK_PORT}/api")
    
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False)