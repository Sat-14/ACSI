// Global variables
let currentPlatform = 'youtube';
let contentData = {
    youtube: [],
    instagram: [],
    twitter: []
};
let trackingStatus = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadContent();
    loadTrackingStatus();
    // Auto-refresh every 5 minutes
    setInterval(() => {
        loadContent();
        loadTrackingStatus();
    }, 300000);
});

// API Functions
async function loadContent() {
    try {
        // Load content based on current platform
        if (currentPlatform === 'youtube') {
            await loadYouTubeContent();
        } else if (currentPlatform === 'instagram') {
            await loadInstagramContent();
        } else if (currentPlatform === 'twitter') {
            await loadTwitterContent();
        }
        
        displayContent();
        updateLastRefreshTime();
    } catch (error) {
        console.error('Error loading content:', error);
        showError('Failed to load content. Please try again later.');
    }
}

async function loadYouTubeContent() {
    try {
        const response = await fetch('/api/transcripts');
        if (!response.ok) throw new Error('Failed to fetch transcripts');
        
        const data = await response.json();
        if (data.success && data.transcripts) {
            // Load content of recent transcripts
            contentData.youtube = await loadTranscriptContents(data.transcripts.slice(0, 10));
        }
    } catch (error) {
        console.error('Error loading YouTube content:', error);
        contentData.youtube = [];
    }
}

async function loadInstagramContent() {
    try {
        const response = await fetch('/api/content/instagram?limit=10');
        if (!response.ok) throw new Error('Failed to fetch Instagram content');
        
        const data = await response.json();
        if (data.success && data.content) {
            contentData.instagram = data.content.map(post => ({
                platform: 'instagram',
                title: post.title || 'No caption available',
                summary: post.summary || 'Instagram post',
                topic: post.topic || 'Instagram post',
                sentiment: post.sentiment || 'Neutral',
                url: post.url || '#',
                upload_date: post.scraped_at,
                processing_date: post.scraped_at,
                handle: post.handle,
                media_count: post.media_count || 0,
                engagement_potential: post.engagement_potential || 5,
                content_type: post.content_type || 'Personal',
                transcript_filename: post.transcript_filename,
                ai_enhanced: !!post.transcript_filename // Has AI analysis
            }));
        }
    } catch (error) {
        console.error('Error loading Instagram content:', error);
        contentData.instagram = [];
    }
}

async function loadTwitterContent() {
    try {
        const response = await fetch('/api/content/twitter?limit=10');
        if (!response.ok) throw new Error('Failed to fetch Twitter content');
        
        const data = await response.json();
        if (data.success && data.content) {
            contentData.twitter = data.content.map(tweet => ({
                platform: 'twitter',
                title: tweet.title || 'No text available',
                summary: tweet.summary || 'Twitter post',
                topic: tweet.topic || 'Twitter post',
                sentiment: tweet.sentiment || 'Neutral',
                url: tweet.url || '#',
                upload_date: tweet.scraped_at,
                processing_date: tweet.scraped_at,
                handle: tweet.handle,
                media_count: tweet.media_count || 0,
                engagement: tweet.engagement || {},
                engagement_potential: tweet.engagement_potential || 5,
                content_type: tweet.content_type || 'Personal',
                transcript_filename: tweet.transcript_filename,
                ai_enhanced: !!tweet.transcript_filename // Has AI analysis
            }));
        }
    } catch (error) {
        console.error('Error loading Twitter content:', error);
        contentData.twitter = [];
    }
}

async function loadTranscriptContents(transcripts) {
    const contents = [];
    
    for (const transcript of transcripts) {
        try {
            const response = await fetch(`/api/transcript/${transcript.filename}?format=json`);
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.content) {
                    // Parse the transcript content
                    const parsed = parseTranscriptContent(data.content, transcript);
                    if (parsed) contents.push(parsed);
                }
            }
        } catch (error) {
            console.error(`Error loading transcript ${transcript.filename}:`, error);
        }
    }
    
    return contents;
}

async function loadTrackingStatus() {
    try {
        const response = await fetch('/api/tracking_status');
        if (response.ok) {
            const data = await response.json();
            trackingStatus = data;
            updateTrackingInfo();
        }
    } catch (error) {
        console.error('Error loading tracking status:', error);
    }
}

// Parsing Functions
function parseTranscriptContent(content, metadata) {
    try {
        // Extract video information from the transcript format
        const lines = content.split('\n');
        let videoData = {
            platform: 'youtube',
            title: '',
            url: '',
            upload_date: '',
            video_id: '',
            processing_date: metadata.modified_human,
            topic: '',
            sentiment: '',
            summary: '',
            filename: metadata.filename
        };
        
        let currentSection = '';
        let summaryLines = [];
        
        for (const line of lines) {
            const trimmedLine = line.trim();
            
            // Extract video metadata
            if (trimmedLine.startsWith('Video Title:')) {
                videoData.title = trimmedLine.substring('Video Title:'.length).trim();
            } else if (trimmedLine.startsWith('Video URL:')) {
                videoData.url = trimmedLine.substring('Video URL:'.length).trim();
            } else if (trimmedLine.startsWith('Upload Date:')) {
                videoData.upload_date = trimmedLine.substring('Upload Date:'.length).trim();
            } else if (trimmedLine.startsWith('Video ID:')) {
                videoData.video_id = trimmedLine.substring('Video ID:'.length).trim();
            }
            
            // Track sections
            if (trimmedLine === 'TOPIC AND SENTIMENT:') {
                currentSection = 'sentiment';
            } else if (trimmedLine === 'SUMMARY:') {
                currentSection = 'summary';
            } else if (trimmedLine.startsWith('---')) {
                if (currentSection === 'summary' && summaryLines.length > 0) {
                    break; // End of summary section
                }
            }
            
            // Collect section content
            if (currentSection === 'sentiment' && trimmedLine && !trimmedLine.includes('TOPIC AND SENTIMENT')) {
                videoData.sentiment = trimmedLine;
            } else if (currentSection === 'summary' && trimmedLine && !trimmedLine.includes('SUMMARY:')) {
                summaryLines.push(trimmedLine);
            }
        }
        
        videoData.summary = summaryLines.join(' ').trim();
        
        // Only return if we have essential data
        if (videoData.title && videoData.summary) {
            return videoData;
        }
        
        return null;
    } catch (error) {
        console.error('Error parsing transcript:', error);
        return null;
    }
}

// Tracking Info Functions
function updateTrackingInfo() {
    if (!trackingStatus) return;
    
    const container = document.getElementById('lastUpdate');
    if (container && trackingStatus.last_check_human) {
        container.innerHTML = `
            Last checked: ${trackingStatus.last_check_human} | 
            Tracking ${trackingStatus.channels_count} YouTube channels | 
            ${trackingStatus.total_videos_tracked} videos processed
        `;
    }
}

function displayContent() {
    const container = document.getElementById('contentContainer');
    const content = contentData[currentPlatform];

    if (!content || content.length === 0) {
        container.innerHTML = `
            <div class="no-content-message">
                <h3>No ${currentPlatform} content available yet</h3>
                <p>Content will appear here once scraping is complete.</p>
                ${currentPlatform !== 'youtube' ? 
                    `<button onclick="triggerScraping('${currentPlatform}')" class="btn btn-primary">Start ${currentPlatform} Scraping</button>` : 
                    ''
                }
            </div>
        `;
        return;
    }

    container.innerHTML = content.map(item => createContentCard(item)).join('');
}

function createContentCard(item) {
    const sentiment = item.sentiment || extractSentiment(item.summary);
    const sentimentClass = getSentimentClass(sentiment);
    
    // Platform-specific content
    let platformSpecific = '';
    let platformBadgeClass = `${item.platform}-badge`;
    
    if (item.platform === 'instagram') {
        platformSpecific = `
            <div class="platform-details">
                ${item.media_count ? `<span class="media-count">${item.media_count} media files</span>` : ''}
                ${item.content_type ? `<span class="content-type">${item.content_type}</span>` : ''}
                ${item.engagement_potential ? `<span class="engagement-potential">🔥 ${item.engagement_potential}/10</span>` : ''}
                ${item.ai_enhanced ? '<span class="ai-badge">🤖 AI Analyzed</span>' : ''}
            </div>
        `;
    } else if (item.platform === 'twitter') {
        platformSpecific = `
            <div class="platform-details">
                ${item.media_count ? `<span class="media-count">${item.media_count} media files</span>` : ''}
                ${item.engagement?.likes ? `<span class="engagement">❤️ ${item.engagement.likes}</span>` : ''}
                ${item.engagement?.retweets ? `<span class="engagement">🔄 ${item.engagement.retweets}</span>` : ''}
                ${item.content_type ? `<span class="content-type">${item.content_type}</span>` : ''}
                ${item.engagement_potential ? `<span class="engagement-potential">🔥 ${item.engagement_potential}/10</span>` : ''}
                ${item.ai_enhanced ? '<span class="ai-badge">🤖 AI Analyzed</span>' : ''}
            </div>
        `;
    } else if (item.platform === 'youtube') {
        platformSpecific = `
            <div class="platform-details">
                <span class="video-indicator">📹 Video Transcript</span>
                <span class="ai-badge">🤖 AI Analyzed</span>
            </div>
        `;
    }
    
    return `
        <div class="content-card ${item.ai_enhanced ? 'ai-enhanced' : ''}">
            <div class="card-header">
                <span class="platform-badge ${platformBadgeClass}">${item.platform}</span>
                ${item.handle ? `<span class="handle-badge">@${item.handle}</span>` : ''}
            </div>
            <h3 class="content-title">${truncateText(item.title || 'Untitled', 80)}</h3>
            <div class="content-meta">
                ${item.upload_date ? formatDate(item.upload_date) : 'Date unknown'}
                ${item.topic ? `• ${truncateText(item.topic, 50)}` : ''}
            </div>
            <span class="sentiment-tag sentiment-${sentimentClass}">${sentiment}</span>
            <p class="summary-text">${truncateText(item.summary || 'No summary available', 200)}</p>
            ${platformSpecific}
            <div class="card-actions">
                ${item.url ? `<a href="${item.url}" target="_blank" class="view-link">View ${item.platform === 'youtube' ? 'video' : 'post'} →</a>` : ''}
                ${item.transcript_filename ? `<button onclick="viewTranscript('${item.transcript_filename}', '${item.platform}')" class="view-transcript-btn">View AI Analysis</button>` : ''}
            </div>
        </div>
    `;
}

// Utility Functions
function extractSentiment(text) {
    if (!text) return 'Neutral';
    const lowerText = text.toLowerCase();
    if (lowerText.includes('positive') || lowerText.includes('happy') || lowerText.includes('exciting') || lowerText.includes('great') || lowerText.includes('amazing')) {
        return 'Positive';
    } else if (lowerText.includes('negative') || lowerText.includes('sad') || lowerText.includes('angry') || lowerText.includes('bad') || lowerText.includes('terrible')) {
        return 'Negative';
    }
    return 'Neutral';
}

function extractSentimentFromText(text) {
    // Simple sentiment analysis for Instagram/Twitter posts
    if (!text) return 'Neutral';
    
    const positiveWords = ['love', 'amazing', 'great', 'awesome', 'fantastic', 'wonderful', 'excellent', 'perfect', '❤️', '😍', '🎉', '✨'];
    const negativeWords = ['hate', 'terrible', 'awful', 'bad', 'worst', 'horrible', 'disappointed', '😢', '😡', '😔'];
    
    const lowerText = text.toLowerCase();
    const positiveScore = positiveWords.reduce((score, word) => score + (lowerText.includes(word) ? 1 : 0), 0);
    const negativeScore = negativeWords.reduce((score, word) => score + (lowerText.includes(word) ? 1 : 0), 0);
    
    if (positiveScore > negativeScore) return 'Positive';
    if (negativeScore > positiveScore) return 'Negative';
    return 'Neutral';
}

function getSentimentClass(sentiment) {
    switch(sentiment.toLowerCase()) {
        case 'positive': return 'positive';
        case 'negative': return 'negative';
        default: return 'neutral';
    }
}

function formatDate(dateStr) {
    if (!dateStr) return 'Date unknown';
    
    // Handle ISO timestamp
    if (dateStr.includes('T')) {
        dateStr = dateStr.split('T')[0];
    }
    
    // Handle YYYYMMDD format
    if (dateStr.length === 8 && /^\d{8}$/.test(dateStr)) {
        const year = dateStr.substring(0, 4);
        const month = dateStr.substring(4, 6);
        const day = dateStr.substring(6, 8);
        dateStr = `${year}-${month}-${day}`;
    }
    
    const date = new Date(dateStr);
    if (isNaN(date)) return dateStr;
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text || '';
    return text.substring(0, maxLength) + '...';
}

// UI Interaction Functions
function switchPlatform(platform) {
    currentPlatform = platform;
    
    // Update active tab
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Display content for selected platform
    if (contentData[platform].length > 0) {
        displayContent();
    } else {
        // Show loading state
        const container = document.getElementById('contentContainer');
        container.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <p>Loading ${platform} content...</p>
            </div>
        `;
        loadContent();
    }
}

async function refreshContent() {
    const button = document.querySelector('.refresh-button');
    button.classList.add('spinning');
    
    try {
        if (currentPlatform === 'youtube') {
            // Trigger manual check for YouTube
            await fetch('/api/check_now', { method: 'POST' });
            
            // Wait a moment then reload content
            setTimeout(() => {
                loadContent().finally(() => {
                    button.classList.remove('spinning');
                });
            }, 2000);
        } else {
            // For Instagram/Twitter, just reload the content
            await loadContent();
            button.classList.remove('spinning');
        }
    } catch (error) {
        console.error('Error triggering refresh:', error);
        button.classList.remove('spinning');
    }
}

async function triggerScraping(platform) {
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = 'Scraping...';
    button.disabled = true;
    
    try {
        let endpoint = '';
        if (platform === 'instagram') {
            endpoint = '/api/scrape_instagram';
        } else if (platform === 'twitter') {
            endpoint = '/api/scrape_twitter';
        }
        
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            // Reload content after scraping
            await loadContent();
            showSuccessMessage(`${platform} scraping completed successfully!`);
        } else {
            showError(`${platform} scraping failed: ${data.error}`);
        }
    } catch (error) {
        console.error(`Error triggering ${platform} scraping:`, error);
        showError(`Failed to trigger ${platform} scraping`);
    } finally {
        button.textContent = originalText;
        button.disabled = false;
    }
}

function updateLastRefreshTime() {
    const now = new Date();
    const timeStr = now.toLocaleString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    // Update only if we don't have tracking status
    if (!trackingStatus) {
        document.getElementById('lastUpdate').textContent = `Last updated: ${timeStr}`;
    }
}

function showError(message) {
    const container = document.getElementById('contentContainer');
    container.innerHTML = `<div class="error-message">${message}</div>`;
}

function showSuccessMessage(message) {
    // Create and show a temporary success notification
    const notification = document.createElement('div');
    notification.className = 'success-notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Admin Functions
async function processChannel(channelHandle) {
    try {
        const response = await fetch('/api/process_channel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ channel_handle: channelHandle })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error processing channel:', error);
        throw error;
    }
}

async function scrapeInstagramHandle(handle) {
    try {
        const response = await fetch('/api/scrape_instagram', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ handle: handle })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error scraping Instagram handle:', error);
        throw error;
    }
}

async function scrapeTwitterHandle(handle) {
    try {
        const response = await fetch('/api/scrape_twitter', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ handle: handle })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error scraping Twitter handle:', error);
        throw error;
    }
}

async function getApiStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error getting API stats:', error);
        return null;
    }
}

async function getInstagramHandles() {
    try {
        const response = await fetch('/api/instagram_handles');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error getting Instagram handles:', error);
        return null;
    }
}

async function getTwitterHandles() {
    try {
        const response = await fetch('/api/twitter_handles');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error getting Twitter handles:', error);
        return null;
    }
}

async function updateInstagramHandles(handles) {
    try {
        const response = await fetch('/api/instagram_handles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ handles: handles })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error updating Instagram handles:', error);
        throw error;
    }
}

async function updateTwitterHandles(handles) {
    try {
        const response = await fetch('/api/twitter_handles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ handles: handles })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error updating Twitter handles:', error);
        throw error;
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Press '1' for YouTube, '2' for Instagram, '3' for Twitter
    if (e.key === '1') {
        document.querySelector('.tab-button[onclick*="youtube"]')?.click();
    } else if (e.key === '2') {
        document.querySelector('.tab-button[onclick*="instagram"]')?.click();
    } else if (e.key === '3') {
        document.querySelector('.tab-button[onclick*="twitter"]')?.click();
    } else if (e.key === 'r' || e.key === 'R') {
        // Press 'R' to refresh
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            refreshContent();
        }
    }
});

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .no-content-message {
        text-align: center;
        padding: 40px 20px;
        color: #666;
    }
    
    .no-content-message h3 {
        margin-bottom: 10px;
        color: #333;
    }
    
    .no-content-message p {
        margin-bottom: 20px;
    }
    
    .no-content-message .btn {
        background: #007bff;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
    }
    
    .no-content-message .btn:hover {
        background: #0056b3;
    }
    
    .platform-details {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 10px 0;
    }
    
    .media-count, .engagement {
        background: rgba(0,123,255,0.1);
        color: #007bff;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85em;
    }
    
    .hashtags {
        color: #1da1f2;
        font-size: 0.9em;
        font-weight: 500;
    }
    
    .handle-badge {
        background: rgba(255,255,255,0.2);
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        color: white;
    }
    
    .youtube-badge {
        background: #ff0000;
    }
    
    .instagram-badge {
        background: linear-gradient(45deg, #f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%);
    }
    
    .twitter-badge {
        background: #1da1f2;
    }
    
    .content-type, .engagement-potential {
        background: rgba(156, 39, 176, 0.2);
        color: #9c27b0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85em;
    }
    
    .ai-badge {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    .ai-enhanced {
        border: 1px solid rgba(76, 175, 80, 0.3);
        box-shadow: 0 0 15px rgba(76, 175, 80, 0.1);
    }
    
    .card-actions {
        display: flex;
        gap: 10px;
        margin-top: 15px;
        align-items: center;
    }
    
    .view-transcript-btn {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 15px;
        font-size: 0.85em;
        cursor: pointer;
        transition: all 0.3s;
        text-decoration: none;
        display: inline-block;
    }
    
    .view-transcript-btn:hover {
        background: linear-gradient(45deg, #45a049, #4CAF50);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
    }
`;
document.head.appendChild(style);
