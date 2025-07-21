# Multi-Platform Content Intelligence System

A comprehensive content monitoring and analysis platform that automatically tracks, transcribes, and analyzes content across YouTube, Instagram, and Twitter using Google Gemini AI.

## Features

### Multi-Platform Support
- **YouTube**: Video transcription with audio extraction and AI analysis
- **Instagram**: Post scraping with image/video download and caption analysis
- **Twitter**: Tweet extraction with media download and text analysis

### AI-Powered Analysis
- Automatic transcription using Google Gemini AI
- Intelligent content summarization
- Sentiment analysis (Positive/Negative/Neutral)
- Topic and theme identification
- Content categorization (Personal, News, Educational, Promotional)
- Engagement potential prediction (1-10 scale)
- Key hashtag and mention extraction

### Web Interface
- Real-time dashboard for monitoring all platforms
- Admin panel for handle management and bulk operations
- Content cards with AI-enhanced summaries
- Platform-specific statistics and analytics
- Export/import functionality for configuration backup

## Architecture

```
┌─────────────────┬─────────────────┬─────────────────┐
│   YouTube       │   Instagram     │   Twitter       │
│   Processor     │   Scraper       │   Scraper       │
└─────────┬───────┴─────────┬───────┴─────────┬───────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                           │
          ┌─────────────────▼─────────────────┐
          │     Social Media Processor       │
          │     (Gemini AI Integration)      │
          └─────────────────┬─────────────────┘
                           │
          ┌─────────────────▼─────────────────┐
          │         Flask API Server         │
          └─────────────────┬─────────────────┘
                           │
          ┌─────────────────▼─────────────────┐
          │      Frontend Dashboard          │
          └─────────────────┬─────────────────┘
                           │
          ┌─────────────────▼─────────────────┐
          │       Admin Interface            │
          └─────────────────┬─────────────────┘
```

## Installation

### Prerequisites
- Python 3.8+
- Google Gemini API key
- Playwright browser dependencies

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/content-intelligence-system.git
cd content-intelligence-system
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. Configure environment:
```bash
cp config.example.py config.py
# Edit config.py with your Gemini API key
```

5. Create handle files:
```bash
echo "channelname" > channels.txt
echo "instagramhandle" > handleinsta.txt  
echo "twitterhandle" > handletwitter.txt
```

6. Start the application:
```bash
python app.py
```

## Configuration

### API Keys
Set your Google Gemini API key in `config.py`:
```python
GEMINI_API_KEY = "your_gemini_api_key_here"
```

### Platform Handles
- **YouTube**: Add channel handles to `channels.txt` (format: `@channelname`)
- **Instagram**: Add usernames to `handleinsta.txt` (format: `username`)
- **Twitter**: Add handles to `handletwitter.txt` (format: `username`)

### Application Settings
```python
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
RECENT_HOURS = 24  # Time window for new content
MAX_VIDEOS_TO_CHECK = 20  # Limit per platform
```

## Usage

### Web Interface
- **Dashboard**: `http://localhost:5000`
- **Admin Panel**: `http://localhost:5000/admin.html`
- **API Documentation**: `http://localhost:5000/api`

### API Endpoints

#### Content Retrieval
```http
GET /api/content/youtube          # Get YouTube content
GET /api/content/instagram        # Get Instagram content  
GET /api/content/twitter          # Get Twitter content
```

#### Platform Management
```http
POST /api/scrape_instagram        # Trigger Instagram scraping
POST /api/scrape_twitter          # Trigger Twitter scraping
POST /api/process_channel         # Process YouTube channel
```

#### Handle Management
```http
GET /api/instagram_handles        # List Instagram handles
POST /api/instagram_handles       # Update Instagram handles
GET /api/twitter_handles          # List Twitter handles
POST /api/twitter_handles         # Update Twitter handles
```

#### AI Analysis
```http
GET /api/social_transcripts       # List AI-analyzed content
GET /api/social_transcript/<file> # Get specific analysis
```

## File Structure

```
project/
├── app.py                    # Main Flask application
├── social_media_processor.py # AI analysis engine
├── instagram_scraper.py      # Instagram content scraper
├── twitter_scraper.py        # Twitter content scraper
├── video_processor.py        # YouTube video processor
├── gemini_transcriber.py     # AI transcription service
├── config.py                 # Configuration settings
├── channels.txt              # YouTube channel handles
├── handleinsta.txt           # Instagram handles
├── handletwitter.txt         # Twitter handles
├── templates/
│   ├── index.html           # Main dashboard
│   └── admin.html           # Admin interface
├── static/js/
│   ├── app.js               # Dashboard JavaScript
│   └── admin.js             # Admin panel JavaScript
├── transcripts/             # YouTube AI transcripts
│   └── social_media/        # Instagram/Twitter AI analysis
└── downloads/               # Downloaded media files
    ├── instagram/
    └── twitter/
```

## AI Analysis Output

Each piece of content receives comprehensive AI analysis:

### YouTube Videos
- Complete audio transcription
- Content summarization (50-200 words)
- Topic and sentiment identification
- Key themes extraction

### Instagram Posts
- Caption analysis and summarization
- Hashtag extraction and categorization
- Visual content description
- Engagement potential scoring

### Twitter Posts  
- Tweet text analysis and summarization
- Hashtag and mention extraction
- Thread context understanding
- Viral potential assessment

## Technical Details

### Content Processing Pipeline
1. **Content Discovery**: Platform scrapers identify new content
2. **Media Extraction**: Download videos, images, and text content
3. **AI Processing**: Send content to Gemini AI for analysis
4. **Data Storage**: Save structured analysis as transcript files
5. **Frontend Display**: Present enhanced content in dashboard

### Error Handling
- Comprehensive logging across all components
- Graceful handling of rate limits and platform blocks
- Automatic retry mechanisms for failed requests
- Windows-compatible file operations and Unicode support

### Performance Optimizations
- Background processing for non-blocking operations
- Rate limiting to avoid platform restrictions
- Efficient file cleanup and storage management
- Optimized database queries for large datasets

## Development

### Running in Development Mode
```bash
export FLASK_DEBUG=1
python app.py
```

### Adding New Platforms
1. Create platform-specific scraper (follow existing patterns)
2. Add AI processing integration in `social_media_processor.py`
3. Update API endpoints in `app.py`
4. Extend frontend interface for new platform

### Testing
```bash
# Test individual components
python -m pytest tests/

# Test specific platform
python instagram_scraper.py
python twitter_scraper.py
```

## Deployment

### Production Setup
1. Set `FLASK_DEBUG = False` in config
2. Use production WSGI server (gunicorn recommended)
3. Configure reverse proxy (nginx recommended)
4. Set up SSL certificates for HTTPS
5. Configure automated backups for transcript data

### Docker Deployment
```bash
docker build -t content-intelligence .
docker run -p 5000:5000 -v $(pwd)/config.py:/app/config.py content-intelligence
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature-name`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature-name`)
5. Create a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for all public functions
- Include comprehensive error handling

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google Gemini AI for natural language processing
- Playwright for robust web automation
- yt-dlp for YouTube video extraction
- Flask for the web framework
- All contributors and testers
