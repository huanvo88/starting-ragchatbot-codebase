// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    
    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // New chat button
    newChatButton.addEventListener('click', startNewChat);
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        // Use streaming endpoint for better user experience
        await handleStreamingResponse(query, loadingMessage);
    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        // Format sources as clickable links when available
        const formattedSources = sources.map(source => {
            if (typeof source === 'object' && source.text) {
                if (source.link) {
                    return `<a href="${source.link}" target="_blank" rel="noopener noreferrer">${source.text}</a>`;
                } else {
                    return source.text;
                }
            } else {
                // Handle legacy string format
                return typeof source === 'string' ? source : String(source);
            }
        });
        
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${formattedSources.join(', ')}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function handleStreamingResponse(query, loadingMessage) {
    const response = await fetch(`${API_URL}/query/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: query,
            session_id: currentSessionId
        })
    });

    if (!response.ok) throw new Error('Query failed');

    // Remove loading message and create streaming message container
    loadingMessage.remove();
    
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = `message-${messageId}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Process streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    let sources = [];

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') {
                        // Finalize message with sources if available
                        if (sources.length > 0) {
                            // Format sources as clickable links when available
                            const formattedSources = sources.map(source => {
                                if (typeof source === 'object' && source.text) {
                                    if (source.link) {
                                        return `<a href="${source.link}" target="_blank" rel="noopener noreferrer">${source.text}</a>`;
                                    } else {
                                        return source.text;
                                    }
                                } else {
                                    // Handle legacy string format
                                    return typeof source === 'string' ? source : String(source);
                                }
                            });
                            
                            const sourcesHtml = `
                                <details class="sources-collapsible">
                                    <summary class="sources-header">Sources</summary>
                                    <div class="sources-content">${formattedSources.join(', ')}</div>
                                </details>
                            `;
                            messageDiv.innerHTML = contentDiv.outerHTML + sourcesHtml;
                        }
                        return;
                    }

                    try {
                        const chunk = JSON.parse(data);
                        
                        if (chunk.type === 'session_id' && !currentSessionId) {
                            currentSessionId = chunk.session_id;
                        } else if (chunk.type === 'content') {
                            fullContent += chunk.content;
                            // Convert markdown and update display
                            contentDiv.innerHTML = marked.parse(fullContent);
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        } else if (chunk.type === 'sources') {
                            sources = chunk.sources;
                        } else if (chunk.error) {
                            throw new Error(chunk.error);
                        }
                    } catch (parseError) {
                        console.warn('Failed to parse chunk:', data);
                    }
                }
            }
        }
    } finally {
        reader.releaseLock();
    }
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

function startNewChat() {
    // Clear the current conversation
    currentSessionId = null;
    chatMessages.innerHTML = '';
    
    // Add welcome message
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
    
    // Focus the chat input for user convenience
    chatInput.focus();
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}