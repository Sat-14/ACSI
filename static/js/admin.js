// Admin Panel JavaScript - Extended for Instagram and Twitter
let currentChannels = [];
let instagramHandles = [];
let twitterHandles = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadAllHandles();
    loadApiStats();
    loadRecentContent();
    
    // Auto-refresh stats every minute
    setInterval(() => {
        loadApiStats();
    }, 60000);
});

// Load all platform handles
async function loadAllHandles() {
    await loadChannels();
    await loadInstagramHandles();
    await loadTwitterHandles();
}

// ===== YOUTUBE CHANNEL MANAGEMENT (EXISTING FUNCTIONALITY) =====

async function loadChannels() {
    try {
        const response = await fetch('/api/channels');
        const data = await response.json();
        
        if (data.success) {
            currentChannels = data.channels;
            displayChannels();
        }
    } catch (error) {
        console.error('Error loading YouTube channels:', error);
        document.getElementById('channelsList').innerHTML = 
            '<div class="error-message">Failed to load YouTube channels</div>';
    }
}

function displayChannels() {
    const container = document.getElementById('channelsList');
    
    if (currentChannels.length === 0) {
        container.innerHTML = '<div class="error-message">No YouTube channels tracked yet</div>';
        return;
    }
    
    container.innerHTML = currentChannels.map((channel, index) => `
        <div class="handle-item">
            <span class="handle-name">@${channel}</span>
            <div class="handle-actions">
                <button onclick="processChannel('${channel}')" class="btn btn-secondary btn-small">Process</button>
                <button onclick="removeChannel(${index})" class="btn btn-danger btn-small">Remove</button>
            </div>
        </div>
    `).join('');
}

async function addChannel() {
    const input = document.getElementById('newChannelInput');
    const channelHandle = input.value.trim();
    
    if (!channelHandle) {
        alert('Please enter a channel handle');
        return;
    }
    
    if (!currentChannels.includes(channelHandle)) {
        currentChannels.push(channelHandle);
        
        try {
            const response = await fetch('/api/channels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channels: currentChannels })
            });
            
            const data = await response.json();
            
            if (data.success) {
                input.value = '';
                displayChannels();
                
                if (confirm(`Channel added! Process recent videos from ${channelHandle} now?`)) {
                    await processChannel(channelHandle);
                }
            } else {
                alert('Failed to add channel: ' + (data.error || 'Unknown error'));
                currentChannels.pop();
            }
        } catch (error) {
            console.error('Error adding channel:', error);
            alert('Failed to add channel');
            currentChannels.pop();
        }
    } else {
        alert('Channel already exists');
    }
}

async function removeChannel(index) {
    const channel = currentChannels[index];
    
    if (confirm(`Remove ${channel} from tracking?`)) {
        currentChannels.splice(index, 1);
        
        try {
            const response = await fetch('/api/channels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channels: currentChannels })
            });
            
            if (response.ok) {
                displayChannels();
            } else {
                alert('Failed to remove channel');
                loadChannels();
            }
        } catch (error) {
            console.error('Error removing channel:', error);
            alert('Failed to remove channel');
            loadChannels();
        }
    }
}

async function processChannel(channelHandle) {
    try {
        const response = await fetch('/api/process_channel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel_handle: channelHandle })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Successfully processed ${data.results.processed_videos.length} videos from ${channelHandle}`);
            loadRecentContent();
        } else {
            alert('Failed to process channel: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error processing channel:', error);
        alert('Failed to process channel');
    }
}

// ===== INSTAGRAM HANDLE MANAGEMENT =====

async function loadInstagramHandles() {
    try {
        const response = await fetch('/api/instagram_handles');
        const data = await response.json();
        
        if (data.success) {
            instagramHandles = data.handles;
            displayInstagramHandles();
        }
    } catch (error) {
        console.error('Error loading Instagram handles:', error);
        document.getElementById('instagramHandlesList').innerHTML = 
            '<div class="error-message">Failed to load Instagram handles</div>';
    }
}

function displayInstagramHandles() {
    const container = document.getElementById('instagramHandlesList');
    
    if (instagramHandles.length === 0) {
        container.innerHTML = '<div class="error-message">No Instagram handles tracked yet</div>';
        return;
    }
    
    container.innerHTML = instagramHandles.map((handle, index) => `
        <div class="handle-item">
            <span class="handle-name">@${handle}</span>
            <div class="handle-actions">
                <button onclick="scrapeInstagramHandle('${handle}')" class="btn btn-secondary btn-small">Scrape</button>
                <button onclick="removeInstagramHandle(${index})" class="btn btn-danger btn-small">Remove</button>
            </div>
        </div>
    `).join('');
}

async function addInstagramHandle() {
    const input = document.getElementById('newInstagramInput');
    const handle = input.value.trim().replace('@', '');
    
    if (!handle) {
        alert('Please enter an Instagram handle');
        return;
    }
    
    if (!instagramHandles.includes(handle)) {
        instagramHandles.push(handle);
        
        try {
            const response = await fetch('/api/instagram_handles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ handles: instagramHandles })
            });
            
            const data = await response.json();
            
            if (data.success) {
                input.value = '';
                displayInstagramHandles();
                
                if (confirm(`Instagram handle added! Scrape posts from @${handle} now?`)) {
                    await scrapeInstagramHandle(handle);
                }
            } else {
                alert('Failed to add Instagram handle: ' + (data.error || 'Unknown error'));
                instagramHandles.pop();
            }
        } catch (error) {
            console.error('Error adding Instagram handle:', error);
            alert('Failed to add Instagram handle');
            instagramHandles.pop();
        }
    } else {
        alert('Instagram handle already exists');
    }
}

async function removeInstagramHandle(index) {
    const handle = instagramHandles[index];
    
    if (confirm(`Remove @${handle} from Instagram tracking?`)) {
        instagramHandles.splice(index, 1);
        
        try {
            const response = await fetch('/api/instagram_handles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ handles: instagramHandles })
            });
            
            if (response.ok) {
                displayInstagramHandles();
            } else {
                alert('Failed to remove Instagram handle');
                loadInstagramHandles();
            }
        } catch (error) {
            console.error('Error removing Instagram handle:', error);
            alert('Failed to remove Instagram handle');
            loadInstagramHandles();
        }
    }
}

async function scrapeInstagramHandle(handle) {
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = 'Scraping...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/scrape_instagram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ handle: handle })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Successfully scraped ${data.results.total_media_downloaded} media files from @${handle}`);
            loadRecentContent();
        } else {
            alert('Failed to scrape Instagram: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error scraping Instagram:', error);
        alert('Failed to scrape Instagram');
    } finally {
        button.textContent = originalText;
        button.disabled = false;
    }
}

async function scrapeAllInstagram() {
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = 'Scraping All...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/scrape_instagram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}) // Empty body scrapes all handles
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Instagram scraping completed: ${data.results.total_media_downloaded} total media files from ${data.results.handles_processed} handles`);
            loadRecentContent();
        } else {
            alert('Failed to scrape Instagram: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error scraping all Instagram:', error);
        alert('Failed to scrape Instagram');
    } finally {
        button.textContent = originalText;
        button.disabled = false;
    }
}

// ===== TWITTER HANDLE MANAGEMENT =====

async function loadTwitterHandles() {
    try {
        const response = await fetch('/api/twitter_handles');
        const data = await response.json();
        
        if (data.success) {
            twitterHandles = data.handles;
            displayTwitterHandles();
        }
    } catch (error) {
        console.error('Error loading Twitter handles:', error);
        document.getElementById('twitterHandlesList').innerHTML = 
            '<div class="error-message">Failed to load Twitter handles</div>';
    }
}

function displayTwitterHandles() {
    const container = document.getElementById('twitterHandlesList');
    
    if (twitterHandles.length === 0) {
        container.innerHTML = '<div class="error-message">No Twitter handles tracked yet</div>';
        return;
    }
    
    container.innerHTML = twitterHandles.map((handle, index) => `
        <div class="handle-item">
            <span class="handle-name">@${handle}</span>
            <div class="handle-actions">
                <button onclick="scrapeTwitterHandle('${handle}')" class="btn btn-secondary btn-small">Scrape</button>
                <button onclick="removeTwitterHandle(${index})" class="btn btn-danger btn-small">Remove</button>
            </div>
        </div>
    `).join('');
}

async function addTwitterHandle() {
    const input = document.getElementById('newTwitterInput');
    const handle = input.value.trim().replace('@', '');
    
    if (!handle) {
        alert('Please enter a Twitter handle');
        return;
    }
    
    if (!twitterHandles.includes(handle)) {
        twitterHandles.push(handle);
        
        try {
            const response = await fetch('/api/twitter_handles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ handles: twitterHandles })
            });
            
            const data = await response.json();
            
            if (data.success) {
                input.value = '';
                displayTwitterHandles();
                
                if (confirm(`Twitter handle added! Scrape posts from @${handle} now?`)) {
                    await scrapeTwitterHandle(handle);
                }
            } else {
                alert('Failed to add Twitter handle: ' + (data.error || 'Unknown error'));
                twitterHandles.pop();
            }
        } catch (error) {
            console.error('Error adding Twitter handle:', error);
            alert('Failed to add Twitter handle');
            twitterHandles.pop();
        }
    } else {
        alert('Twitter handle already exists');
    }
}

async function removeTwitterHandle(index) {
    const handle = twitterHandles[index];
    
    if (confirm(`Remove @${handle} from Twitter tracking?`)) {
        twitterHandles.splice(index, 1);
        
        try {
            const response = await fetch('/api/twitter_handles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ handles: twitterHandles })
            });
            
            if (response.ok) {
                displayTwitterHandles();
            } else {
                alert('Failed to remove Twitter handle');
                loadTwitterHandles();
            }
        } catch (error) {
            console.error('Error removing Twitter handle:', error);
            alert('Failed to remove Twitter handle');
            loadTwitterHandles();
        }
    }
}

async function scrapeTwitterHandle(handle) {
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = 'Scraping...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/scrape_twitter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ handle: handle })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Successfully scraped ${data.results.total_media_downloaded} media files from @${handle}`);
            loadRecentContent();
        } else {
            alert('Failed to scrape Twitter: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error scraping Twitter:', error);
        alert('Failed to scrape Twitter');
    } finally {
        button.textContent = originalText;
        button.disabled = false;
    }
}

async function scrapeAllTwitter() {
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = 'Scraping All...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/scrape_twitter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}) // Empty body scrapes all handles
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Twitter scraping completed: ${data.results.total_media_downloaded} total media files from ${data.results.handles_processed} handles`);
            loadRecentContent();
        } else {
            alert('Failed to scrape Twitter: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error scraping all Twitter:', error);
        alert('Failed to scrape Twitter');
    } finally {
        button.textContent = originalText;
        button.disabled = false;
    }
}

// ===== VIDEO PROCESSING (EXISTING FUNCTIONALITY) =====

async function processVideo() {
    const input = document.getElementById('videoUrlInput');
    const videoUrl = input.value.trim();
    const resultDiv = document.getElementById('videoProcessingResult');
    
    if (!videoUrl) {
        alert('Please enter a video URL');
        return;
    }
    
    resultDiv.className = 'processing-result loading';
    resultDiv.innerHTML = '<div class="loading-spinner"></div> Processing video...';
    resultDiv.style.display = 'block';
    
    try {
        const response = await fetch('/api/process_video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_url: videoUrl })
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.className = 'processing-result success';
            resultDiv.innerHTML = `
                <strong>Success!</strong><br>
                Processed: ${data.results.video_title || 'Unknown Title'}<br>
                Processing time: ${data.processing_time.toFixed(1)}s
            `;
            input.value = '';
            loadRecentContent();
        } else {
            resultDiv.className = 'processing-result error';
            resultDiv.innerHTML = `<strong>Error:</strong> ${data.error || 'Failed to process video'}`;
        }
    } catch (error) {
        console.error('Error processing video:', error);
        resultDiv.className = 'processing-result error';
        resultDiv.innerHTML = '<strong>Error:</strong> Failed to process video';
    }
}

// ===== STATISTICS FUNCTIONS =====

async function loadApiStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            displayApiStats(data);
        }
    } catch (error) {
        console.error('Error loading API stats:', error);
        document.getElementById('apiStats').innerHTML = 
            '<div class="error-message">Failed to load statistics</div>';
    }
}

function displayApiStats(data) {
    const container = document.getElementById('apiStats');
    const stats = data.api_stats;
    const instagram_stats = data.instagram_stats || {};
    const twitter_stats = data.twitter_stats || {};
    
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.uptime_human}</div>
            <div class="stat-label">Uptime</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.total_requests}</div>
            <div class="stat-label">Total Requests</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.error_rate_percent}%</div>
            <div class="stat-label">Error Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.tracker_stats?.total_channels || 0}</div>
            <div class="stat-label">YouTube Channels</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${instagram_stats.handles_count || 0}</div>
            <div class="stat-label">Instagram Handles</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${twitter_stats.handles_count || 0}</div>
            <div class="stat-label">Twitter Handles</div>
        </div>
    `;
}

// ===== RECENT CONTENT FUNCTIONS =====

async function loadRecentContent() {
    try {
        // Load recent transcripts (YouTube)
        const transcriptResponse = await fetch('/api/transcripts');
        const transcriptData = await transcriptResponse.json();
        
        // Load recent Instagram posts
        const instagramResponse = await fetch('/api/instagram_posts?limit=5');
        const instagramData = await instagramResponse.json();
        
        // Load recent Twitter posts
        const twitterResponse = await fetch('/api/twitter_posts?limit=5');
        const twitterData = await twitterResponse.json();
        
        displayRecentContent({
            transcripts: transcriptData.success ? transcriptData.transcripts.slice(0, 5) : [],
            instagram: instagramData.success ? instagramData.posts : [],
            twitter: twitterData.success ? twitterData.posts : []
        });
        
    } catch (error) {
        console.error('Error loading recent content:', error);
        document.getElementById('recentContent').innerHTML = 
            '<div class="error-message">Failed to load recent content</div>';
    }
}

function displayRecentContent(content) {
    const container = document.getElementById('recentContent');
    
    let html = '<div class="recent-content-tabs">';
    html += '<button class="tab-btn active" onclick="switchContentTab(event, \'youtube\')">YouTube</button>';
    html += '<button class="tab-btn" onclick="switchContentTab(event, \'instagram\')">Instagram</button>';
    html += '<button class="tab-btn" onclick="switchContentTab(event, \'twitter\')">Twitter</button>';
    html += '</div>';
    
    // YouTube transcripts
    html += '<div id="youtube-content" class="content-tab active">';
    if (content.transcripts.length > 0) {
        content.transcripts.forEach(transcript => {
            html += `
                <div class="content-item">
                    <div class="content-info">
                        <div class="content-filename">${transcript.filename}</div>
                        <div class="content-meta">
                            ${formatFileSize(transcript.size)} | ${transcript.modified_human}
                        </div>
                    </div>
                    <div class="content-actions">
                        <a href="/api/transcript/${transcript.filename}" class="btn btn-secondary btn-small">Download</a>
                        <button onclick="viewTranscript('${transcript.filename}')" class="btn btn-primary btn-small">View</button>
                    </div>
                </div>
            `;
        });
    } else {
        html += '<div class="no-content">No YouTube transcripts available</div>';
    }
    html += '</div>';
    
    // Instagram content
    html += '<div id="instagram-content" class="content-tab">';
    if (content.instagram.length > 0) {
        content.instagram.forEach(post => {
            html += `
                <div class="content-item">
                    <div class="content-info">
                        <div class="content-title">@${post.handle} - ${post.metadata?.caption?.substring(0, 50) || 'No caption'}...</div>
                        <div class="content-meta">
                            ${post.media?.length || 0} media files | ${new Date(post.scraped_at).toLocaleDateString()}
                        </div>
                    </div>
                    <div class="content-actions">
                        <a href="${post.url}" target="_blank" class="btn btn-primary btn-small">View Post</a>
                    </div>
                </div>
            `;
        });
    } else {
        html += '<div class="no-content">No Instagram posts available</div>';
    }
    html += '</div>';
    
    // Twitter content
    html += '<div id="twitter-content" class="content-tab">';
    if (content.twitter.length > 0) {
        content.twitter.forEach(tweet => {
            html += `
                <div class="content-item">
                    <div class="content-info">
                        <div class="content-title">@${tweet.handle} - ${tweet.text?.substring(0, 50) || 'No text'}...</div>
                        <div class="content-meta">
                            ${tweet.media?.length || 0} media files | ${tweet.engagement?.likes || 0} likes | ${new Date(tweet.scraped_at).toLocaleDateString()}
                        </div>
                    </div>
                    <div class="content-actions">
                        <a href="https://twitter.com/${tweet.handle}" target="_blank" class="btn btn-primary btn-small">View Profile</a>
                    </div>
                </div>
            `;
        });
    } else {
        html += '<div class="no-content">No Twitter posts available</div>';
    }
    html += '</div>';
    
    container.innerHTML = html;
}

function switchContentTab(event, platform) {
    // Remove active class from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.content-tab').forEach(tab => tab.classList.remove('active'));
    
    // Add active class to clicked tab
    event.target.classList.add('active');
    document.getElementById(`${platform}-content`).classList.add('active');
}

async function viewTranscript(filename) {
    try {
        const response = await fetch(`/api/transcript/${filename}?format=json`);
        const data = await response.json();
        
        if (data.success) {
            const content = data.content;
            const newWindow = window.open('', '_blank', 'width=800,height=600');
            newWindow.document.write(`
                <html>
                <head>
                    <title>${filename}</title>
                    <style>
                        body { 
                            font-family: monospace; 
                            padding: 20px; 
                            background: #0a0a0a; 
                            color: #ccc;
                            white-space: pre-wrap;
                        }
                    </style>
                </head>
                <body>${escapeHtml(content)}</body>
                </html>
            `);
        }
    } catch (error) {
        console.error('Error viewing transcript:', error);
        alert('Failed to load transcript');
    }
}

// ===== UTILITY FUNCTIONS =====

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== EVENT LISTENERS =====

document.addEventListener('DOMContentLoaded', () => {
    // YouTube channel input
    const channelInput = document.getElementById('newChannelInput');
    if (channelInput) {
        channelInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addChannel();
            }
        });
    }
    
    // Instagram handle input
    const instagramInput = document.getElementById('newInstagramInput');
    if (instagramInput) {
        instagramInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addInstagramHandle();
            }
        });
    }
    
    // Twitter handle input
    const twitterInput = document.getElementById('newTwitterInput');
    if (twitterInput) {
        twitterInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addTwitterHandle();
            }
        });
    }
    
    // Video URL input
    const videoInput = document.getElementById('videoUrlInput');
    if (videoInput) {
        videoInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                processVideo();
            }
        });
    }
});

// ===== BULK OPERATIONS =====

async function bulkScrapeAll() {
    if (!confirm('This will scrape all Instagram and Twitter handles. This may take a while. Continue?')) {
        return;
    }
    
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = 'Scraping All Platforms...';
    button.disabled = true;
    
    try {
        let results = {
            instagram: { success: false, message: '' },
            twitter: { success: false, message: '' }
        };
        
        // Scrape Instagram
        try {
            const instagramResponse = await fetch('/api/scrape_instagram', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            const instagramData = await instagramResponse.json();
            results.instagram.success = instagramData.success;
            results.instagram.message = instagramData.success 
                ? `${instagramData.results.total_media_downloaded} media files from ${instagramData.results.handles_processed} handles`
                : instagramData.error;
        } catch (error) {
            results.instagram.message = 'Failed to scrape Instagram';
        }
        
        // Scrape Twitter
        try {
            const twitterResponse = await fetch('/api/scrape_twitter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            const twitterData = await twitterResponse.json();
            results.twitter.success = twitterData.success;
            results.twitter.message = twitterData.success 
                ? `${twitterData.results.total_media_downloaded} media files from ${twitterData.results.handles_processed} handles`
                : twitterData.error;
        } catch (error) {
            results.twitter.message = 'Failed to scrape Twitter';
        }
        
        // Show results
        let message = 'Bulk scraping completed:\n\n';
        message += `Instagram: ${results.instagram.success ? '✓' : '✗'} ${results.instagram.message}\n`;
        message += `Twitter: ${results.twitter.success ? '✓' : '✗'} ${results.twitter.message}`;
        
        alert(message);
        
        if (results.instagram.success || results.twitter.success) {
            loadRecentContent();
            loadApiStats();
        }
        
    } catch (error) {
        console.error('Error in bulk scraping:', error);
        alert('Bulk scraping failed');
    } finally {
        button.textContent = originalText;
        button.disabled = false;
    }
}

// ===== EXPORT FUNCTIONS =====

async function exportHandles() {
    try {
        const data = {
            youtube_channels: currentChannels,
            instagram_handles: instagramHandles,
            twitter_handles: twitterHandles,
            exported_at: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `handles_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
        
        alert('Handles exported successfully!');
    } catch (error) {
        console.error('Error exporting handles:', error);
        alert('Failed to export handles');
    }
}

function importHandles() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        try {
            const text = await file.text();
            const data = JSON.parse(text);
            
            let message = 'Import preview:\n\n';
            message += `YouTube channels: ${data.youtube_channels?.length || 0}\n`;
            message += `Instagram handles: ${data.instagram_handles?.length || 0}\n`;
            message += `Twitter handles: ${data.twitter_handles?.length || 0}\n\n`;
            message += 'This will replace your current handles. Continue?';
            
            if (confirm(message)) {
                // Update YouTube channels
                if (data.youtube_channels) {
                    await fetch('/api/channels', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ channels: data.youtube_channels })
                    });
                }
                
                // Update Instagram handles
                if (data.instagram_handles) {
                    await fetch('/api/instagram_handles', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ handles: data.instagram_handles })
                    });
                }
                
                // Update Twitter handles
                if (data.twitter_handles) {
                    await fetch('/api/twitter_handles', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ handles: data.twitter_handles })
                    });
                }
                
                // Reload all handles
                await loadAllHandles();
                alert('Handles imported successfully!');
            }
            
        } catch (error) {
            console.error('Error importing handles:', error);
            alert('Failed to import handles. Please check the file format.');
        }
    };
    
    input.click();
}
