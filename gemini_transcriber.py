# gemini_transcriber.py - Handles audio transcription using Google Gemini with chunking support

import google.generativeai as genai
import os
import time
import logging
import sys
from config import GEMINI_API_KEY, TRANSCRIPTS_DIR, TRANSCRIPT_EXTENSION

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
def setup_gemini_transcriber_logging():
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('gemini_transcriber.log', encoding='utf-8')
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

class GeminiTranscriber:
    def __init__(self):
        self.logger = setup_gemini_transcriber_logging()
        
        # File size limits - increased for larger files
        self.max_file_size_mb = 20  # Gemini's recommended limit
        self.chunk_size_mb = 10     # Size for each chunk if splitting needed
        self.absolutely_max_size_mb = 100  # Increased from 50 MB
        
        # Configure Gemini API
        try:
            if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
                raise ValueError("GEMINI_API_KEY is not set or empty")
            
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.logger.info("GeminiTranscriber initialized successfully with gemini-1.5-flash model")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini API: {e}")
            self.logger.error("Please ensure GEMINI_API_KEY is properly configured")
            raise
        
        # Ensure transcripts directory exists
        try:
            os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
            self.logger.debug(f"Transcripts directory verified: {TRANSCRIPTS_DIR}")
        except Exception as e:
            self.logger.error(f"Failed to create transcripts directory: {e}")
            raise
    
    def split_audio_file(self, audio_path, max_size_mb):
        """Split audio file into chunks based on file size"""
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            return [audio_path]  # No need to split
        
        # For now, we'll handle this by transcribing in parts
        # This is a placeholder - actual audio splitting would require audio processing library
        self.logger.warning(f"Audio file is {file_size_mb:.1f} MB, which exceeds {max_size_mb} MB limit")
        return [audio_path]  # Return original file, we'll handle it differently
    
    def transcribe_audio_chunk(self, audio_path, chunk_info=None):
        """Transcribe a single audio chunk"""
        transcription_start_time = time.time()
        uploaded_file = None
        
        try:
            # Upload the audio file to Gemini
            self.logger.debug(f"Uploading audio file to Gemini: {os.path.basename(audio_path)}")
            uploaded_file = genai.upload_file(path=audio_path)
            
            upload_time = time.time() - transcription_start_time
            self.logger.debug(f"Audio file uploaded successfully in {upload_time:.1f} seconds")
            
            # Wait for file processing - longer wait for larger files
            file_size = os.path.getsize(audio_path) / (1024 * 1024)
            if file_size > 5:  # Files larger than 5MB
                wait_time = min(10, file_size / 3)  # Increased wait time
                self.logger.debug(f"Large file ({file_size:.1f} MB), waiting {wait_time:.1f}s for processing...")
                time.sleep(wait_time)
            
            # Create prompt for transcription
            if chunk_info:
                prompt = f"""Please transcribe this audio file (part {chunk_info['part']} of {chunk_info['total']}).
                Include all spoken words, and format the transcription in a readable way 
                with proper punctuation and paragraph breaks where appropriate.
                
                Important: If the audio is unclear or inaudible in parts, indicate with [UNCLEAR] or [INAUDIBLE]."""
            else:
                prompt = """Please transcribe this audio file completely and accurately. 
                Include all spoken words, and format the transcription in a readable way 
                with proper punctuation and paragraph breaks where appropriate.
                
                Important: If the audio is unclear or inaudible in parts, indicate with [UNCLEAR] or [INAUDIBLE]."""
            
            # Generate transcription
            self.logger.debug("Sending transcription request to Gemini")
            response = self.model.generate_content([prompt, uploaded_file])
            
            # Extract transcription text
            transcription = response.text
            
            if not transcription or transcription.strip() == "":
                self.logger.error("Received empty transcription from Gemini")
                return None
            
            total_time = time.time() - transcription_start_time
            word_count = len(transcription.split()) if transcription else 0
            
            self.logger.info(f"[OK] Transcription chunk completed in {total_time:.1f} seconds ({word_count} words)")
            
            return transcription
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return None
        
        finally:
            # Clean up uploaded file from Gemini
            if uploaded_file:
                try:
                    genai.delete_file(uploaded_file.name)
                    self.logger.debug("Cleaned up uploaded file from Gemini")
                except Exception as cleanup_error:
                    self.logger.debug(f"Could not clean up Gemini file: {cleanup_error}")
    
    def transcribe_audio(self, audio_path):
        """Transcribe audio file using Gemini - with support for large files"""
        if not os.path.exists(audio_path):
            self.logger.error(f"Audio file not found: {audio_path}")
            return None
        
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)
        self.logger.info(f"Starting transcription for: {os.path.basename(audio_path)} ({file_size_mb:.1f} MB)")
        
        # Check absolute size limit
        if file_size_mb > self.absolutely_max_size_mb:
            self.logger.error(f"Audio file is too large ({file_size_mb:.1f} MB). Maximum supported: {self.absolutely_max_size_mb} MB")
            self.logger.error("Consider processing shorter videos or splitting the video into parts")
            return None
        
        # For very large files, we might need to handle them differently
        if file_size_mb > self.max_file_size_mb:
            self.logger.warning(f"Audio file exceeds recommended {self.max_file_size_mb} MB limit.")
            self.logger.info("Attempting to transcribe anyway - this may take longer or fail")
            # For now, we'll try to transcribe anyway and let Gemini handle it
            # In production, you might want to implement actual audio splitting
        
        # Transcribe the audio
        transcription = self.transcribe_audio_chunk(audio_path)
        
        if transcription:
            self.logger.info(f"[OK] Full transcription completed successfully")
        
        return transcription
    
    def generate_summary(self, transcription):
        """Generate summary and topic analysis from transcription"""
        if not transcription or not transcription.strip():
            self.logger.warning("Cannot generate summary: transcription is empty")
            return None
        
        transcription_length = len(transcription.split())
        self.logger.info(f"Generating summary and topic analysis for transcription ({transcription_length} words)")
        
        # Handle very short transcriptions
        if transcription_length < 50:
            self.logger.warning(f"Transcription is very short ({transcription_length} words) - summary may be limited")
        
        summary_start_time = time.time()
        
        try:
            # Adjust summary length based on transcription length
            summary_words = min(200, max(50, transcription_length // 4))
            
            prompt = f"""Based on this video transcription, provide:

1. SUMMARY: A concise summary in EXACTLY {summary_words} words or less
2. TOPIC: In EXACTLY 15 words or less, state what topic this video is about and whether the sentiment is positive or negative

Format your response EXACTLY like this:
SUMMARY:
[Your {summary_words}-word summary here]

TOPIC:
[Topic and sentiment in 15 words or less]

Transcription:
{transcription}"""
            
            self.logger.debug("Sending summary generation request to Gemini")
            response = self.model.generate_content(prompt)
            summary_text = response.text
            
            if not summary_text or summary_text.strip() == "":
                self.logger.error("Received empty response from Gemini for summary generation")
                return None
            
            # Parse the response
            summary = ""
            topic = ""
            
            if "SUMMARY:" in summary_text and "TOPIC:" in summary_text:
                parts = summary_text.split("TOPIC:")
                summary = parts[0].replace("SUMMARY:", "").strip()
                topic = parts[1].strip()
                
                summary_time = time.time() - summary_start_time
                summary_word_count = len(summary.split())
                topic_word_count = len(topic.split())
                
                self.logger.info(f"[OK] Summary and topic generated successfully in {summary_time:.1f} seconds")
                self.logger.debug(f"Summary length: {summary_word_count} words, Topic length: {topic_word_count} words")
                
                # Validate length constraints
                if summary_word_count > summary_words:
                    self.logger.warning(f"Summary exceeds {summary_words} words ({summary_word_count} words)")
                if topic_word_count > 15:
                    self.logger.warning(f"Topic exceeds 15 words ({topic_word_count} words)")
                
            else:
                self.logger.error("Failed to parse summary response - incorrect format")
                self.logger.debug(f"Received response: {summary_text[:200]}...")
                return None
            
            return {
                'summary': summary,
                'topic': topic,
                'full_transcription': transcription
            }
            
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            return None
    
    def save_transcription(self, transcription_data, video_info):
        """Save ONLY summary and topic to a text file (no full transcript)"""
        try:
            # Create safe filename
            title = video_info.get('title', 'Unknown_Title')
            video_id = video_info.get('video_id', 'unknown')
            
            # Remove problematic characters
            safe_title = "".join(c for c in title 
                               if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:100]  # Limit length for filesystem
            
            if not safe_title:
                safe_title = "untitled"
            
            filename = f"{video_id}_{safe_title}{TRANSCRIPT_EXTENSION}"
            filepath = os.path.join(TRANSCRIPTS_DIR, filename)
            
            self.logger.debug(f"Saving summary to: {filepath}")
            
            # Prepare content with metadata (NO FULL TRANSCRIPT)
            content_parts = [
                f"Video Title: {video_info.get('title', 'Unknown')}",
                f"Video URL: {video_info.get('url', 'Unknown')}",
                f"Upload Date: {video_info.get('upload_date', 'Unknown')}",
                f"Video ID: {video_info.get('video_id', 'Unknown')}",
                f"Processing Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "-" * 80,
                "",
                "TOPIC AND SENTIMENT:",
                transcription_data.get('topic', 'No topic generated'),
                "",
                "-" * 80,
                "",
                "SUMMARY:",
                "",
                transcription_data.get('summary', 'No summary generated'),
                "",
                "-" * 80
            ]
            
            # Save summary only (no full transcription)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_parts))
            
            file_size = os.path.getsize(filepath)
            self.logger.info(f"[OK] Summary saved successfully: {filename} ({file_size/1024:.1f} KB)")
            
            # Validate file was written correctly
            if file_size == 0:
                self.logger.error(f"Saved file is empty: {filepath}")
                return None
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save summary for '{video_info.get('title', 'Unknown')}': {e}")
            return None
    
    def cleanup_audio_file(self, audio_path):
        """Clean up audio file after successful processing"""
        if not audio_path:
            self.logger.warning("No audio path provided for cleanup")
            return False
            
        try:
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                os.remove(audio_path)
                self.logger.debug(f"Cleaned up audio file: {os.path.basename(audio_path)} ({file_size/1024/1024:.1f} MB)")
                return True
            else:
                self.logger.warning(f"Audio file not found for cleanup: {audio_path}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to clean up audio file {audio_path}: {e}")
            return False
    
    def process_audio_file(self, audio_info):
        """Process a single audio file: transcribe and save"""
        if not audio_info or 'audio_path' not in audio_info or 'video_info' not in audio_info:
            self.logger.error("Invalid audio_info provided")
            return {
                'success': False,
                'error': 'Invalid audio_info provided'
            }
        
        audio_path = audio_info['audio_path']
        video_info = audio_info['video_info']
        
        self.logger.info(f"Starting audio processing for: '{video_info.get('title', 'Unknown')}'")
        processing_start_time = time.time()
        
        result = {
            'success': False,
            'video_info': video_info,
            'error': None
        }
        
        try:
            # Log audio format info
            if 'format' in audio_info:
                self.logger.debug(f"Audio format: {audio_info['format']}, Size: {audio_info.get('file_size_mb', 'Unknown')} MB")
            
            # Transcribe audio
            transcription = self.transcribe_audio(audio_path)
            
            if not transcription:
                result['error'] = "Transcription failed"
                self.logger.error(f"Audio processing failed at transcription stage for: '{video_info.get('title', 'Unknown')}'")
                return result
            
            # Generate summary and topic analysis
            summary_data = self.generate_summary(transcription)
            
            if not summary_data:
                result['error'] = "Summary generation failed"
                self.logger.error(f"Audio processing failed at summary generation stage for: '{video_info.get('title', 'Unknown')}'")
                return result
            
            # Save transcription and summary
            transcript_path = self.save_transcription(summary_data, video_info)
            
            if not transcript_path:
                result['error'] = "Failed to save transcription"
                self.logger.error(f"Audio processing failed at save stage for: '{video_info.get('title', 'Unknown')}'")
                return result
            
            # Clean up audio file after successful processing
            cleanup_success = self.cleanup_audio_file(audio_path)
            if cleanup_success:
                self.logger.info(f"[OK] Audio file cleaned up successfully")
            else:
                self.logger.warning(f"[WARNING] Could not clean up audio file, but transcription was saved")
            
            # Calculate total processing time
            total_processing_time = time.time() - processing_start_time
            
            self.logger.info(f"[OK] Audio processing completed successfully for: '{video_info.get('title', 'Unknown')}' in {total_processing_time:.1f} seconds")
            
            result.update({
                'success': True,
                'transcript_path': transcript_path,
                'summary': summary_data.get('summary', ''),
                'topic': summary_data.get('topic', ''),
                'processing_time': total_processing_time
            })
            
        except Exception as e:
            error_msg = f"Unexpected error during audio processing: {e}"
            self.logger.error(f"Audio processing failed for '{video_info.get('title', 'Unknown')}': {error_msg}")
            result['error'] = error_msg
        
        return result
    
    def get_processing_stats(self):
        """Get statistics about processed transcriptions"""
        try:
            if not os.path.exists(TRANSCRIPTS_DIR):
                self.logger.debug(f"Transcripts directory does not exist: {TRANSCRIPTS_DIR}")
                return {
                    'total_transcripts': 0, 
                    'total_size_mb': 0,
                    'transcripts_directory': TRANSCRIPTS_DIR,
                    'directory_exists': False
                }
            
            transcript_files = [f for f in os.listdir(TRANSCRIPTS_DIR) 
                              if f.endswith(TRANSCRIPT_EXTENSION)]
            
            total_size = 0
            for f in transcript_files:
                try:
                    file_path = os.path.join(TRANSCRIPTS_DIR, f)
                    total_size += os.path.getsize(file_path)
                except Exception as e:
                    self.logger.warning(f"Could not get size for {f}: {e}")
            
            stats = {
                'total_transcripts': len(transcript_files),
                'total_size_mb': total_size / (1024 * 1024),
                'transcripts_directory': TRANSCRIPTS_DIR,
                'directory_exists': True,
                'average_file_size_kb': (total_size / len(transcript_files) / 1024) if transcript_files else 0
            }
            
            self.logger.debug(f"Processing stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get processing stats: {e}")
            return {'error': str(e)}
    
    def validate_api_key(self):
        """Validate that the Gemini API key is working"""
        try:
            # Try a simple test request
            test_response = self.model.generate_content("Test connection")
            if test_response and test_response.text:
                self.logger.info("Gemini API key validation successful")
                return True
            else:
                self.logger.error("Gemini API key validation failed - no response")
                return False
        except Exception as e:
            self.logger.error(f"Gemini API key validation failed: {e}")
            return False