# social_media_processor.py - Processes Instagram/Twitter content with Gemini AI integration

import os
import time
import json
import logging
import sys
from datetime import datetime
from gemini_transcriber import GeminiTranscriber
from config import BASE_DIR, TRANSCRIPTS_DIR

class SocialMediaProcessor:
    def __init__(self):
        self.transcriber = GeminiTranscriber()
        self.logger = self.setup_logging()
        self.social_transcripts_dir = os.path.join(TRANSCRIPTS_DIR, 'social_media')
        
        # Ensure social media transcripts directory exists
        os.makedirs(self.social_transcripts_dir, exist_ok=True)
        
        self.logger.info("Social Media Processor initialized with Gemini integration")
    
    def setup_logging(self):
        logger = logging.getLogger(__name__)
        logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler('social_media_processor.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler  
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        logger.setLevel(logging.INFO)
        logger.propagate = False
        return logger
    
    def generate_social_summary(self, text_content, platform, handle, post_type="post"):
        """Generate summary and topic analysis for social media content using Gemini"""
        
        if not text_content or not text_content.strip():
            self.logger.warning(f"No text content provided for {platform} {post_type}")
            return None
        
        text_length = len(text_content.split())
        self.logger.info(f"Generating Gemini summary for {platform} {post_type} from @{handle} ({text_length} words)")
        
        # Handle very short content
        if text_length < 5:
            self.logger.warning(f"Content too short for meaningful analysis ({text_length} words)")
            return {
                'summary': text_content,
                'topic': f"Short {platform} {post_type}",
                'sentiment': 'Neutral',
                'content_analysis': 'Content too brief for detailed analysis'
            }
        
        summary_start_time = time.time()
        
        try:
            # Adjust analysis depth based on content length
            if text_length < 20:
                summary_words = 30
                analysis_depth = "brief"
            elif text_length < 50:
                summary_words = 50  
                analysis_depth = "moderate"
            else:
                summary_words = 100
                analysis_depth = "detailed"
            
            # Create platform-specific prompt
            prompt = f"""Analyze this {platform} {post_type} from @{handle} and provide:

1. SUMMARY: A concise summary in EXACTLY {summary_words} words or less
2. TOPIC: In EXACTLY 15 words or less, state the main topic/theme
3. SENTIMENT: One word: Positive, Negative, or Neutral  
4. CONTENT_TYPE: Classify as one of: Personal, News, Promotional, Educational, Entertainment, Opinion, Question, Announcement
5. ENGAGEMENT_POTENTIAL: Rate 1-10 how likely this is to get high engagement
6. KEY_THEMES: List 3-5 main themes/topics (comma separated)

Format your response EXACTLY like this:
SUMMARY:
[Your {summary_words}-word summary here]

TOPIC:
[Topic in 15 words or less]

SENTIMENT:
[Positive/Negative/Neutral]

CONTENT_TYPE:
[Classification]

ENGAGEMENT_POTENTIAL:
[1-10 rating]

KEY_THEMES:
[theme1, theme2, theme3]

{platform.upper()} {post_type.upper()} CONTENT:
{text_content}"""
            
            self.logger.debug(f"Sending {analysis_depth} analysis request to Gemini")
            response = self.transcriber.model.generate_content(prompt)
            analysis_text = response.text
            
            if not analysis_text or analysis_text.strip() == "":
                self.logger.error("Received empty response from Gemini for social media analysis")
                return None
            
            # Parse the response
            result = self.parse_gemini_social_response(analysis_text, text_content)
            
            if result:
                analysis_time = time.time() - summary_start_time
                self.logger.info(f"[OK] {platform} analysis completed in {analysis_time:.1f}s")
                self.logger.debug(f"Generated summary: {result.get('summary', '')[:50]}...")
                
                return result
            else:
                self.logger.error("Failed to parse Gemini social media analysis response")
                return None
                
        except Exception as e:
            self.logger.error(f"Social media analysis failed: {e}")
            return None
    
    def parse_gemini_social_response(self, response_text, original_content):
        """Parse Gemini's structured response for social media content"""
        
        try:
            result = {
                'summary': '',
                'topic': '', 
                'sentiment': 'Neutral',
                'content_type': 'Personal',
                'engagement_potential': 5,
                'key_themes': [],
                'full_content': original_content
            }
            
            # Split response into sections
            sections = response_text.split('\n')
            current_section = None
            
            for line in sections:
                line = line.strip()
                
                if line.startswith('SUMMARY:'):
                    current_section = 'summary'
                    # Also capture content on same line
                    content = line.replace('SUMMARY:', '').strip()
                    if content:
                        result['summary'] = content
                elif line.startswith('TOPIC:'):
                    current_section = 'topic'
                    content = line.replace('TOPIC:', '').strip()
                    if content:
                        result['topic'] = content
                elif line.startswith('SENTIMENT:'):
                    current_section = 'sentiment'
                    content = line.replace('SENTIMENT:', '').strip()
                    if content and content in ['Positive', 'Negative', 'Neutral']:
                        result['sentiment'] = content
                elif line.startswith('CONTENT_TYPE:'):
                    current_section = 'content_type'
                    content = line.replace('CONTENT_TYPE:', '').strip()
                    if content:
                        result['content_type'] = content
                elif line.startswith('ENGAGEMENT_POTENTIAL:'):
                    current_section = 'engagement_potential'
                    content = line.replace('ENGAGEMENT_POTENTIAL:', '').strip()
                    try:
                        rating = int(content.split()[0])  # Get first number
                        if 1 <= rating <= 10:
                            result['engagement_potential'] = rating
                    except:
                        pass
                elif line.startswith('KEY_THEMES:'):
                    current_section = 'key_themes'
                    content = line.replace('KEY_THEMES:', '').strip()
                    if content:
                        themes = [theme.strip() for theme in content.split(',')]
                        result['key_themes'] = themes
                elif line and current_section and not line.startswith(('SUMMARY:', 'TOPIC:', 'SENTIMENT:', 'CONTENT_TYPE:', 'ENGAGEMENT_POTENTIAL:', 'KEY_THEMES:')):
                    # Continue previous section
                    if current_section == 'summary':
                        result['summary'] += ' ' + line
                    elif current_section == 'topic':
                        result['topic'] += ' ' + line
            
            # Clean up results
            result['summary'] = result['summary'].strip()
            result['topic'] = result['topic'].strip()
            
            # Validate we have minimum required content
            if not result['summary'] and not result['topic']:
                self.logger.error("No summary or topic extracted from Gemini response")
                return None
            
            # Set defaults if missing
            if not result['summary']:
                result['summary'] = original_content[:100] + ('...' if len(original_content) > 100 else '')
            if not result['topic']:
                result['topic'] = 'Social media post'
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing social media analysis response: {e}")
            self.logger.debug(f"Response text: {response_text[:200]}...")
            return None
    
    def save_social_analysis(self, analysis_data, post_data, platform):
        """Save social media analysis to transcript-like file"""
        
        try:
            # Create safe filename
            handle = post_data.get('handle', 'unknown')
            post_id = post_data.get('post_id', post_data.get('tweet_id', 'unknown_post'))
            
            # Clean up post_id for filename
            safe_post_id = "".join(c for c in post_id if c.isalnum() or c in ('_', '-'))
            filename = f"{platform}_{handle}_{safe_post_id}.txt"
            filepath = os.path.join(self.social_transcripts_dir, filename)
            
            self.logger.debug(f"Saving {platform} analysis to: {filepath}")
            
            # Prepare content similar to YouTube transcript format
            content_parts = [
                f"Platform: {platform.upper()}",
                f"Handle: @{handle}",
                f"Post ID: {post_id}",
                f"URL: {post_data.get('url', 'Unknown')}",
                f"Processing Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Scraped Date: {post_data.get('scraped_at', 'Unknown')}",
                "-" * 80,
                "",
                "CONTENT TYPE:",
                analysis_data.get('content_type', 'Unknown'),
                "",
                "TOPIC AND THEME:",
                analysis_data.get('topic', 'No topic generated'),
                "",
                "SENTIMENT ANALYSIS:",
                analysis_data.get('sentiment', 'Neutral'),
                "",
                "KEY THEMES:",
                ', '.join(analysis_data.get('key_themes', ['None'])),
                "",
                "ENGAGEMENT POTENTIAL:",
                f"{analysis_data.get('engagement_potential', 5)}/10",
                "",
                "-" * 80,
                "",
                "AI GENERATED SUMMARY:",
                "",
                analysis_data.get('summary', 'No summary generated'),
                "",
                "-" * 80,
                "",
                "ORIGINAL CONTENT:",
                "",
                analysis_data.get('full_content', 'No content available'),
                "",
                "-" * 80,
            ]
            
            # Add platform-specific metadata
            if platform == 'instagram':
                if 'metadata' in post_data:
                    metadata = post_data['metadata']
                    content_parts.extend([
                        "",
                        "INSTAGRAM SPECIFIC DATA:",
                        f"Hashtags: {', '.join(metadata.get('hashtags', []))}",
                        f"Media Count: {len(post_data.get('media', []))}",
                        f"Likes: {metadata.get('likes', 'Unknown')}",
                        ""
                    ])
            elif platform == 'twitter':
                if 'engagement' in post_data:
                    engagement = post_data['engagement']
                    content_parts.extend([
                        "",
                        "TWITTER SPECIFIC DATA:",
                        f"Hashtags: {', '.join(post_data.get('hashtags', []))}",
                        f"Mentions: {', '.join(post_data.get('mentions', []))}",
                        f"Media Count: {len(post_data.get('media', []))}",
                        f"Likes: {engagement.get('likes', 0)}",
                        f"Retweets: {engagement.get('retweets', 0)}",
                        f"Replies: {engagement.get('replies', 0)}",
                        ""
                    ])
            
            # Save analysis file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_parts))
            
            file_size = os.path.getsize(filepath)
            self.logger.info(f"[OK] {platform} analysis saved: {filename} ({file_size/1024:.1f} KB)")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save {platform} analysis: {e}")
            return None
    
    def process_instagram_post(self, post_data):
        """Process Instagram post with Gemini analysis"""
        
        self.logger.info(f"Processing Instagram post from @{post_data.get('handle', 'unknown')}")
        
        # Extract text content
        caption = post_data.get('metadata', {}).get('caption', '')
        hashtags = post_data.get('metadata', {}).get('hashtags', [])
        
        # Combine caption and hashtags for analysis
        text_content = caption
        if hashtags:
            text_content += "\n\nHashtags: " + ' '.join(hashtags)
        
        if not text_content.strip():
            self.logger.warning("Instagram post has no text content to analyze")
            return {
                'success': False,
                'error': 'No text content available for analysis'
            }
        
        # Generate AI analysis
        analysis = self.generate_social_summary(
            text_content, 
            'instagram', 
            post_data.get('handle', 'unknown'),
            'post'
        )
        
        if not analysis:
            return {
                'success': False,
                'error': 'Failed to generate analysis'
            }
        
        # Save analysis
        transcript_path = self.save_social_analysis(analysis, post_data, 'instagram')
        
        if transcript_path:
            return {
                'success': True,
                'transcript_path': transcript_path,
                'analysis': analysis
            }
        else:
            return {
                'success': False,
                'error': 'Failed to save analysis'
            }
    
    def process_twitter_post(self, tweet_data):
        """Process Twitter post with Gemini analysis"""
        
        self.logger.info(f"Processing Twitter post from @{tweet_data.get('handle', 'unknown')}")
        
        # Extract text content
        tweet_text = tweet_data.get('text', '')
        hashtags = tweet_data.get('hashtags', [])
        mentions = tweet_data.get('mentions', [])
        
        # Combine tweet text, hashtags, and mentions for analysis
        text_content = tweet_text
        if hashtags:
            text_content += "\n\nHashtags: " + ' '.join(hashtags)
        if mentions:
            text_content += "\nMentions: " + ' '.join(mentions)
        
        if not text_content.strip():
            self.logger.warning("Twitter post has no text content to analyze")
            return {
                'success': False,
                'error': 'No text content available for analysis'  
            }
        
        # Generate AI analysis
        analysis = self.generate_social_summary(
            text_content,
            'twitter', 
            tweet_data.get('handle', 'unknown'),
            'tweet'
        )
        
        if not analysis:
            return {
                'success': False,
                'error': 'Failed to generate analysis'
            }
        
        # Save analysis  
        transcript_path = self.save_social_analysis(analysis, tweet_data, 'twitter')
        
        if transcript_path:
            return {
                'success': True,
                'transcript_path': transcript_path,
                'analysis': analysis
            }
        else:
            return {
                'success': False,
                'error': 'Failed to save analysis'
            }
    
    def process_social_content_batch(self, posts, platform):
        """Process multiple social media posts with AI analysis"""
        
        self.logger.info(f"Starting batch processing: {len(posts)} {platform} posts")
        
        results = {
            'platform': platform,
            'processed_posts': [],
            'errors': [],
            'total_processed': 0,
            'total_errors': 0
        }
        
        for i, post in enumerate(posts, 1):
            try:
                self.logger.info(f"Processing {platform} post {i}/{len(posts)}")
                
                if platform == 'instagram':
                    result = self.process_instagram_post(post)
                elif platform == 'twitter':
                    result = self.process_twitter_post(post)
                else:
                    raise ValueError(f"Unsupported platform: {platform}")
                
                if result['success']:
                    processed_post = {
                        'post_data': post,
                        'analysis': result['analysis'],
                        'transcript_path': result['transcript_path']
                    }
                    results['processed_posts'].append(processed_post)
                    results['total_processed'] += 1
                    
                    self.logger.info(f"[OK] {platform} post {i} processed successfully")
                else:
                    error_msg = f"Failed to process {platform} post {i}: {result['error']}"
                    results['errors'].append(error_msg)
                    results['total_errors'] += 1
                    self.logger.error(error_msg)
                
                # Rate limiting between posts
                if i < len(posts):
                    time.sleep(2)  # 2 second delay between Gemini requests
                    
            except Exception as e:
                error_msg = f"Unexpected error processing {platform} post {i}: {e}"
                results['errors'].append(error_msg)
                results['total_errors'] += 1
                self.logger.error(error_msg)
        
        self.logger.info(f"Batch processing completed: {results['total_processed']} successful, {results['total_errors']} errors")
        return results
    
    def get_social_transcripts(self, platform=None, limit=10):
        """Get social media transcripts (similar to YouTube transcripts)"""
        
        try:
            transcripts = []
            
            if not os.path.exists(self.social_transcripts_dir):
                return transcripts
            
            for filename in os.listdir(self.social_transcripts_dir):
                if filename.endswith('.txt'):
                    # Filter by platform if specified
                    if platform and not filename.startswith(f"{platform}_"):
                        continue
                    
                    filepath = os.path.join(self.social_transcripts_dir, filename)
                    try:
                        stats = os.stat(filepath)
                        transcripts.append({
                            'filename': filename,
                            'platform': filename.split('_')[0] if '_' in filename else 'unknown',
                            'size': stats.st_size,
                            'modified': stats.st_mtime,
                            'modified_human': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
                    except Exception as e:
                        self.logger.warning(f"Could not get stats for {filename}: {e}")
            
            # Sort by modification time (newest first)
            transcripts.sort(key=lambda x: x['modified'], reverse=True)
            
            return transcripts[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting social transcripts: {e}")
            return []
