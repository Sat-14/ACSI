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
    // Set the initial active tab based on a URL hash or default
    const platform = window.location.hash.substring(1) || 'youtube';
    switchPlatform(platform);

    loadTrackingStatus();
    // Auto-refresh every 5 minutes
    setInterval(() => {
        loadContent(false); // Don't show loader on auto-refresh
        loadTrackingStatus();
    }, 300000);
});

// API Functions
async function loadContent(showLoader = true) {
    const container = document.getElementById('contentContainer');
    if (showLoader) {
        container.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <p>Loading ${currentPlatform} content...</p>
            </div>
        `;
    }

    try {
        if (currentPlatform === 'youtube') {
            await loadYouTubeContent();
        } else {
            // Generic loader for Instagram and Twitter
            const response = await fetch(`/api/content/${currentPlatform}?limit=10`);
            if (!response.ok) throw new Error(`Failed to fetch ${currentPlatform} content`);
            
            const data = await response.json();
            if (data.success && data.content) {
                contentData[currentPlatform] = data.content;
            } else {
                contentData[currentPlatform] = [];
            }
        }
        
        displayContent();
        updateLastRefreshTime();
    } catch (error) {
        console.error('Error loading content:', error);
        showError(`Failed to load content for ${currentPlatform}. Please try again later.`);
    }
}

async function loadYouTubeContent() {
    try {
        const response = await fetch('/api/transcripts');
        if (!response.ok) throw new Error('Failed to fetch transcripts');
        
        const data = await response.json();
        if (data.success && data.transcripts) {
            contentData.youtube = await loadTranscriptContents(data.transcripts.slice(0, 10));
        } else {
             contentData.youtube = [];
        }
    } catch (error) {
        console.error('Error loading YouTube content:', error);
        contentData.youtube = [];
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
                    const parsed = parseYouTubeTranscript(data.content, transcript);
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
            trackingStatus = await response.json();
            updateTrackingInfo();
        }
    } catch (error) {
        console.error('Error loading tracking status:', error);
    }
}

// Parsing Functions
function parseYouTubeTranscript(content, metadata) {
    try {
        const lines = content.split('\n');
        let videoData = {
            platform: 'youtube',
            title: 'Unknown Title',
            url: '',
            upload_date: '',
            video_id: '',
            processing_date: metadata.modified_human,
            topic: 'No Topic',
            summary: 'No Summary',
            filename: metadata.filename,
            ai_enhanced: true
        };
        
        let inSummary = false;
        let summaryLines = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.startsWith('Video Title:')) videoData.title = line.split(':')[1].trim();
            if (line.startsWith('Video URL:')) videoData.url = line.split('Video URL:')[1].trim();
            if (line.startsWith('Upload Date:')) videoData.upload_date = line.split(':')[1].trim();
            if (line.startsWith('Video ID:')) videoData.video_id = line.split(':')[1].trim();
            
            if (line.startsWith('SUMMARY:')) {
                inSummary = true;
            } else if (line.startsWith('TOPIC AND SENTIMENT:')) {
                inSummary = false;
                // Next non-empty line is the topic
                let nextLine = lines[i + 1];
                if (nextLine && nextLine.trim()) {
                    videoData.topic = nextLine.trim();
                }
            } else if (inSummary && line.trim()) {
                summaryLines.push(line.trim());
            }
        }
        
        videoData.summary = summaryLines.join(' ');
        return videoData.title !== 'Unknown Title' ? videoData : null;
    } catch (error) {
        console.error('Error parsing transcript:', error);
        return null;
    }
}

// UI Rendering Functions
function updateTrackingInfo() {
    const container = document.getElementById('lastUpdate');
    if (container && trackingStatus?.last_check_human) {
        container.innerHTML = `
            Last checked: ${new Date(trackingStatus.last_check).toLocaleString()} | 
            Tracking ${trackingStatus.channels_count} YouTube channels | 
            ${trackingStatus.total_videos_tracked} videos processed
        `;
    }
}

function displayContent() {
    const container = document.getElementById('contentContainer');
    const data = contentData[currentPlatform];

    if (!data || data.length === 0) {
        container.innerHTML = `
            <div class="no-content-message">
                <h3>No ${currentPlatform} content available yet</h3>
                <p>Content will appear here once it has been scraped from the Admin Panel.</p>
                ${currentPlatform !== 'youtube' ? 
                    `<button onclick="triggerScraping('${currentPlatform}')" class="btn btn-primary">Start ${currentPlatform} Scraping Now</button>` : 
                    '<p>YouTube content is updated automatically in the background.</p>'
                }
            </div>
        `;
        return;
    }

    container.innerHTML = data.map(item => createContentCard(item)).join('');
}

function createContentCard(item) {
    const sentimentClass = (item.sentiment || 'neutral').toLowerCase();
    const platformBadgeClass = `${item.platform}-badge`;
    
    return `
        <div class="content-card ${item.ai_enhanced ? 'ai-enhanced' : ''}">
            <div class="card-header">
                <span class="platform-badge ${platformBadgeClass}">${item.platform}</span>
                ${item.handle ? `<span class="handle-badge">@${item.handle}</span>` : ''}
            </div>
            <h3 class="video-title">${truncateText(item.title || 'Untitled', 80)}</h3>
            <div class="video-meta">
                ${formatDate(item.upload_date || item.scraped_at)}
                ${item.topic ? `• ${truncateText(item.topic, 50)}` : ''}
            </div>
            ${item.sentiment ? `<span class="sentiment-tag sentiment-${sentimentClass}">${item.sentiment}</span>` : ''}
            <p class="summary-text">${truncateText(item.summary || 'No summary available', 200)}</p>
            <div class="card-actions">
                ${item.url ? `<a href="${item.url}" target="_blank" class="view-link">View Original →</a>` : ''}
            </div>
        </div>
    `;
}

// Utility Functions
function formatDate(dateStr) {
    if (!dateStr) return 'Date unknown';
    const date = new Date(dateStr);
    return isNaN(date) ? dateStr : date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text || '';
    return text.substring(0, maxLength) + '...';
}

// UI Interaction Functions
function switchPlatform(platform) {
    currentPlatform = platform;
    window.location.hash = platform;
    
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase() === platform);
    });
    
    loadContent();
}

async function refreshContent() {
    const button = document.querySelector('.refresh-button');
    button.classList.add('spinning');
    
    try {
        if (currentPlatform === 'youtube') {
            await fetch('/api/check_now', { method: 'POST' });
            setTimeout(() => loadContent(), 2000); // Wait for processing
        } else {
            await triggerScraping(currentPlatform);
        }
    } catch (error) {
        console.error('Error triggering refresh:', error);
    } finally {
        setTimeout(() => button.classList.remove('spinning'), 1000);
    }
}

async function triggerScraping(platform) {
    showLoadingState(true, `Scraping ${platform}...`);
    
    try {
        const endpoint = `/api/scrape_${platform}`;
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({}) // Send empty body for "scrape all"
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccessMessage(`${platform} scraping completed!`);
        } else {
            showError(`${platform} scraping failed: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error(`Error triggering ${platform} scraping:`, error);
        showError(`Failed to trigger ${platform} scraping.`);
    } finally {
        await loadContent(false); // Reload content without showing loader again
    }
}

function updateLastRefreshTime() {
    if (!trackingStatus) {
        const now = new Date();
        const timeStr = now.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        document.getElementById('lastUpdate').textContent = `Last updated: ${timeStr}`;
    }
}

function showLoadingState(isLoading, message = 'Loading content...') {
    const container = document.getElementById('contentContainer');
    if (isLoading) {
        container.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <p>${message}</p>
            </div>
        `;
    }
}

function showError(message) {
    const container = document.getElementById('contentContainer');
    container.innerHTML = `<div class="error-message">${message}</div>`;
}

function showSuccessMessage(message) {
    const notification = document.createElement('div');
    notification.className = 'success-notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    if (e.key === '1') document.querySelector('.tab-button[onclick*="youtube"]')?.click();
    if (e.key === '2') document.querySelector('.tab-button[onclick*="instagram"]')?.click();
    if (e.key === '3') document.querySelector('.tab-button[onclick*="twitter"]')?.click();
    if (e.key.toLowerCase() === 'r') {
        e.preventDefault();
        refreshContent();
    }
});
