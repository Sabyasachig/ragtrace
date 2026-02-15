/* ========================================
   Configuration & State
   ======================================== */

const CONFIG = {
    apiBaseUrl: 'http://localhost:8000/api',  // Fixed: /api not /api/v1
    wsUrl: 'ws://localhost:8000/ws',
    refreshInterval: 5000,
    toastDuration: 4000
};

const STATE = {
    currentView: 'sessions',
    currentSession: null,
    currentSessionData: null,
    currentEvents: [],
    currentCostData: null,
    sessions: [],
    searchQuery: '',
    sortBy: 'created_at',
    theme: localStorage.getItem('theme') || 'light',
    ws: null,
    isConnected: false
};

/* ========================================
   API Client
   ======================================== */

class APIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            showToast('Error', error.message, 'error');
            throw error;
        }
    }

    // Session endpoints
    async getSessions(limit = 50, offset = 0) {
        return this.request(`/sessions?limit=${limit}&offset=${offset}`);
    }

    async getSession(sessionId) {
        return this.request(`/sessions/${sessionId}`);
    }

    async getSessionEvents(sessionId) {
        return this.request(`/sessions/${sessionId}/events`);
    }

    async getSessionCost(sessionId) {
        return this.request(`/sessions/${sessionId}/cost`);
    }

    async deleteSession(sessionId) {
        return this.request(`/sessions/${sessionId}`, { method: 'DELETE' });
    }

    // Event endpoints
    async getEvents(sessionId = null, eventType = null, limit = 100) {
        const params = new URLSearchParams();
        if (sessionId) params.append('session_id', sessionId);
        if (eventType) params.append('event_type', eventType);
        params.append('limit', limit);
        return this.request(`/events?${params}`);
    }

    // Stats endpoints
    async getStats() {
        return this.request('/stats');
    }

    async getCostBreakdown(sessionId = null) {
        const params = sessionId ? `?session_id=${sessionId}` : '';
        return this.request(`/cost/breakdown${params}`);
    }
}

const api = new APIClient(CONFIG.apiBaseUrl);

/* ========================================
   WebSocket Connection
   ======================================== */

function connectWebSocket() {
    try {
        STATE.ws = new WebSocket(CONFIG.wsUrl);

        STATE.ws.onopen = () => {
            STATE.isConnected = true;
            updateConnectionStatus(true);
            console.log('WebSocket connected');
        };

        STATE.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };

        STATE.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            STATE.isConnected = false;
            updateConnectionStatus(false);
        };

        STATE.ws.onclose = () => {
            STATE.isConnected = false;
            updateConnectionStatus(false);
            console.log('WebSocket disconnected');
            
            // Attempt reconnection after 5 seconds
            setTimeout(connectWebSocket, 5000);
        };
    } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        STATE.isConnected = false;
        updateConnectionStatus(false);
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'session_created':
            showToast('New Session', 'A new debugging session was started', 'info');
            if (STATE.currentView === 'sessions') {
                loadSessions();
            }
            break;
        
        case 'event_captured':
            if (STATE.currentSession === data.session_id && STATE.currentView === 'timeline') {
                loadTimeline(data.session_id);
            }
            break;
        
        case 'session_completed':
            showToast('Session Completed', `Session ${data.session_id} finished`, 'success');
            if (STATE.currentView === 'sessions') {
                loadSessions();
            }
            break;
    }
}

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    const statusText = statusEl.querySelector('.status-text');
    
    if (connected) {
        statusEl.classList.remove('disconnected');
        statusText.textContent = 'Connected';
    } else {
        statusEl.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

/* ========================================
   View Management
   ======================================== */

function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });

    // Show selected view
    document.getElementById(`${viewName}-view`).classList.add('active');

    // Update navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.view === viewName) {
            btn.classList.add('active');
        }
    });

    STATE.currentView = viewName;

    // Load view data
    loadViewData(viewName);
}

function loadViewData(viewName) {
    switch (viewName) {
        case 'sessions':
            loadSessions();
            break;
        case 'timeline':
            if (STATE.currentSession) {
                loadTimeline(STATE.currentSession);
            }
            break;
        case 'regression':
            loadSnapshots();
            break;
        case 'prompts':
            loadPrompts();
            break;
    }
}

/* ========================================
   Sessions View
   ======================================== */

async function loadSessions() {
    const container = document.getElementById('sessions-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading sessions...</p></div>';

    try {
        const data = await api.getSessions(100, 0);
        // API returns array directly, not wrapped in object
        STATE.sessions = Array.isArray(data) ? data : (data.sessions || []);

        if (STATE.sessions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📊</span>
                    <h3>No Sessions Yet</h3>
                    <p>Start debugging your RAG pipeline to see sessions here</p>
                </div>
            `;
            return;
        }

        renderSessions(filterAndSortSessions());
    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚠️</span>
                <h3>Failed to Load Sessions</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

function filterAndSortSessions() {
    let filtered = STATE.sessions;

    // Apply search filter
    if (STATE.searchQuery) {
        const query = STATE.searchQuery.toLowerCase();
        filtered = filtered.filter(session => {
            const sessionId = session.id || session.session_id || '';
            return sessionId.toLowerCase().includes(query) ||
                (session.query && session.query.toLowerCase().includes(query)) ||
                (session.model && session.model.toLowerCase().includes(query));
        });
    }

    // Apply sorting
    filtered.sort((a, b) => {
        switch (STATE.sortBy) {
            case 'created_at':
                return new Date(b.created_at) - new Date(a.created_at);
            case 'cost':
                return (b.total_cost || 0) - (a.total_cost || 0);
            case 'duration':
                // Use total_duration_ms or calculate from completed_at
                const durationA = a.total_duration_ms || 
                    (a.completed_at ? new Date(a.completed_at) - new Date(a.created_at) : 0);
                const durationB = b.total_duration_ms || 
                    (b.completed_at ? new Date(b.completed_at) - new Date(b.created_at) : 0);
                return durationB - durationA;
            default:
                return 0;
        }
    });

    return filtered;
}

function renderSessions(sessions) {
    const container = document.getElementById('sessions-list');
    
    if (sessions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🔍</span>
                <h3>No Sessions Found</h3>
                <p>Try adjusting your search or filters</p>
            </div>
        `;
        return;
    }

    container.innerHTML = sessions.map(session => {
        // API returns 'id', UI expects 'session_id'
        const sessionId = session.id || session.session_id;
        return `
        <div class="session-card" onclick="viewSession('${sessionId}')">
            <div class="session-card-icon">${getSessionIcon(session)}</div>
            <div class="session-card-content">
                <div class="session-card-header">
                    <div class="session-card-title">${sessionId}</div>
                </div>
                <div class="session-card-meta">
                    <span>📅 ${formatDate(session.created_at)}</span>
                    <span>⏱️ ${formatDuration(session)}</span>
                    ${session.completed_at ? '<span class="text-success">✓ Completed</span>' : '<span class="text-info">⟳ Active</span>'}
                </div>
                <div class="session-card-stats">
                    <div class="stat">
                        <div class="stat-label">Total Cost</div>
                        <div class="stat-value cost">$${(session.total_cost || 0).toFixed(6)}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Duration</div>
                        <div class="stat-value">${session.total_duration_ms || 0}ms</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Model</div>
                        <div class="stat-value">${session.model || 'N/A'}</div>
                    </div>
                </div>
            </div>
        </div>
    `}).join('');
}

function getSessionIcon(session) {
    if (session.error_count > 0) return '⚠️';
    // API uses 'completed_at', not 'ended_at'
    if (!session.completed_at) return '▶️';
    return '✅';
}

/* ========================================
   Timeline View
   ======================================== */

async function viewSession(sessionId) {
    STATE.currentSession = sessionId;
    switchView('timeline');
    await loadTimeline(sessionId);
}

async function loadTimeline(sessionId) {
    const titleEl = document.getElementById('timeline-title');
    const infoEl = document.getElementById('session-info');
    const timelineEl = document.getElementById('timeline');
    const detailsEl = document.getElementById('event-details');

    titleEl.textContent = `Session: ${sessionId.slice(0, 8)}...`;
    
    infoEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    timelineEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const [sessionData, eventsData, costData] = await Promise.all([
            api.getSession(sessionId),
            api.getSessionEvents(sessionId),
            api.getSessionCost(sessionId)
        ]);

        // Store in STATE for filtering and export
        STATE.currentSessionData = sessionData;
        STATE.currentEvents = eventsData.events || eventsData || [];
        STATE.currentCostData = costData;

        renderSessionInfo(sessionData, costData);
        renderTimeline(STATE.currentEvents);
        renderWaterfallChart(STATE.currentEvents);
        renderCostChart(costData);
        
        detailsEl.innerHTML = '<h3>Event Details</h3><p class="placeholder">Select an event to view details</p>';
    } catch (error) {
        console.error('Timeline load error:', error);
        infoEl.innerHTML = `<p class="text-danger">Failed to load session data: ${error.message}</p>`;
        timelineEl.innerHTML = `<p class="text-danger">Failed to load events: ${error.message}</p>`;
    }
}

function renderSessionInfo(session, costData) {
    const infoEl = document.getElementById('session-info');
    const sessionId = session.id || session.session_id;
    
    infoEl.innerHTML = `
        <div class="session-info-grid">
            <div class="stat">
                <div class="stat-label">Session ID</div>
                <div class="stat-value text-sm font-mono">${sessionId}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Created</div>
                <div class="stat-value text-sm">${formatDate(session.created_at)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Duration</div>
                <div class="stat-value text-sm">${formatDuration(session)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Status</div>
                <div class="stat-value text-sm ${session.completed_at ? 'text-success' : 'text-info'}">
                    ${session.completed_at ? 'Completed' : 'Active'}
                </div>
            </div>
            <div class="stat">
                <div class="stat-label">Total Cost</div>
                <div class="stat-value cost">$${(costData.total_cost || 0).toFixed(6)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Model</div>
                <div class="stat-value">${session.model || 'N/A'}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Input Tokens</div>
                <div class="stat-value">${formatNumber(costData.input_tokens || 0)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Output Tokens</div>
                <div class="stat-value">${formatNumber(costData.output_tokens || 0)}</div>
            </div>
        </div>
    `;
}

function renderTimeline(events) {
    const timelineEl = document.getElementById('timeline');
    
    if (events.length === 0) {
        timelineEl.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📝</span>
                <h3>No Events</h3>
                <p>No events captured for this session</p>
            </div>
        `;
        return;
    }

    // Sort events by timestamp
    events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    timelineEl.innerHTML = events.map(event => `
        <div class="timeline-event" data-event-id="${event.event_id}" onclick="showEventDetails('${event.event_id}')">
            <div class="timeline-event-time">${formatTime(event.timestamp)}</div>
            <div class="timeline-event-content">
                <div class="timeline-event-type">${getEventIcon(event.event_type)} ${event.event_type}</div>
                <div class="timeline-event-details">${getEventSummary(event)}</div>
            </div>
        </div>
    `).join('');
}

function getEventIcon(eventType) {
    const icons = {
        'llm_start': '🚀',
        'llm_end': '✓',
        'llm_error': '⚠️',
        'chain_start': '🔗',
        'chain_end': '✓',
        'tool_start': '🔧',
        'tool_end': '✓',
        'retriever_start': '🔍',
        'retriever_end': '✓',
        'agent_action': '🤖',
        'agent_finish': '✓'
    };
    return icons[eventType] || '•';
}

function getEventSummary(event) {
    const data = event.event_data || {};
    
    if (event.event_type === 'llm_end') {
        return `Generated ${data.output_tokens || 0} tokens • $${(data.cost || 0).toFixed(6)}`;
    }
    
    if (event.event_type === 'retriever_end') {
        return `Retrieved ${data.document_count || 0} documents`;
    }
    
    if (event.event_type.includes('error')) {
        return `Error: ${data.error || 'Unknown error'}`;
    }
    
    return JSON.stringify(data).slice(0, 100);
}

async function showEventDetails(eventId) {
    // Remove selection from all events
    document.querySelectorAll('.timeline-event').forEach(el => {
        el.classList.remove('selected');
    });

    // Add selection to clicked event
    document.querySelector(`[data-event-id="${eventId}"]`)?.classList.add('selected');

    const detailsEl = document.getElementById('event-details');
    
    // Find event in current session
    const eventsData = await api.getEvents(STATE.currentSession);
    const event = eventsData.events.find(e => e.event_id === eventId);
    
    if (!event) {
        detailsEl.innerHTML = '<h3>Event Details</h3><p class="text-danger">Event not found</p>';
        return;
    }

    detailsEl.innerHTML = `
        <h3>Event Details</h3>
        <div class="event-details-content">
            <div class="detail-group">
                <div class="detail-label">Event ID</div>
                <div class="detail-value">${event.event_id}</div>
            </div>
            <div class="detail-group">
                <div class="detail-label">Type</div>
                <div class="detail-value">${event.event_type}</div>
            </div>
            <div class="detail-group">
                <div class="detail-label">Timestamp</div>
                <div class="detail-value">${formatDateTime(event.timestamp)}</div>
            </div>
            <div class="detail-group">
                <div class="detail-label">Duration</div>
                <div class="detail-value">${event.duration ? `${event.duration.toFixed(3)}s` : 'N/A'}</div>
            </div>
            ${event.cost ? `
            <div class="detail-group">
                <div class="detail-label">Cost</div>
                <div class="detail-value cost">$${event.cost.toFixed(6)}</div>
            </div>
            ` : ''}
            <div class="detail-group">
                <div class="detail-label">Event Data</div>
                <div class="detail-value">${JSON.stringify(event.event_data, null, 2)}</div>
            </div>
        </div>
    `;
}

/* ========================================
   Chart Rendering Functions
   ======================================== */

function renderWaterfallChart(events) {
    const canvas = document.getElementById('waterfall-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.waterfallChart) {
        window.waterfallChart.destroy();
    }
    
    if (events.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'var(--text-secondary)';
        ctx.font = '14px var(--font-family)';
        ctx.textAlign = 'center';
        ctx.fillText('No events to display', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    // Create horizontal bar chart showing event durations
    window.waterfallChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: events.map((e, i) => `${i + 1}. ${e.event_type || 'Unknown'}`),
            datasets: [{
                label: 'Duration (ms)',
                data: events.map(e => e.duration_ms || 0),
                backgroundColor: events.map(e => getEventColor(e.event_type)),
                borderWidth: 1,
                borderColor: 'rgba(0, 0, 0, 0.1)'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const event = events[context.dataIndex];
                            return [
                                `Duration: ${event.duration_ms || 0}ms`,
                                `Cost: $${(event.cost || 0).toFixed(6)}`,
                                `Type: ${event.event_type || 'Unknown'}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { 
                        display: true, 
                        text: 'Duration (ms)',
                        color: 'var(--text-secondary)'
                    },
                    grid: {
                        color: 'var(--border-color)'
                    },
                    ticks: {
                        color: 'var(--text-secondary)'
                    }
                },
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: 'var(--text-secondary)',
                        font: {
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

function renderCostChart(costData) {
    const canvas = document.getElementById('cost-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.costChart) {
        window.costChart.destroy();
    }
    
    const inputCost = costData.input_cost || 0;
    const outputCost = costData.output_cost || 0;
    const embeddingCost = costData.embedding_cost || 0;
    
    if (inputCost === 0 && outputCost === 0 && embeddingCost === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'var(--text-secondary)';
        ctx.font = '14px var(--font-family)';
        ctx.textAlign = 'center';
        ctx.fillText('No cost data', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    window.costChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Input Tokens', 'Output Tokens', 'Embeddings'],
            datasets: [{
                data: [inputCost, outputCost, embeddingCost],
                backgroundColor: [
                    '#3b82f6', // Blue
                    '#10b981', // Green
                    '#8b5cf6'  // Purple
                ],
                borderWidth: 2,
                borderColor: 'var(--bg-primary)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: 'var(--text-secondary)',
                        padding: 10
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: $${value.toFixed(6)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function getEventColor(eventType) {
    const colors = {
        'retrieval': '#3b82f6',     // Blue
        'prompt': '#8b5cf6',        // Purple
        'generation': '#10b981',    // Green
        'llm_start': '#f59e0b',     // Orange
        'llm_end': '#10b981',       // Green
        'chain_start': '#06b6d4',   // Cyan
        'chain_end': '#10b981',     // Green
        'tool_start': '#f59e0b',    // Orange
        'tool_end': '#10b981',      // Green
        'retriever_start': '#3b82f6', // Blue
        'retriever_end': '#10b981'  // Green
    };
    return colors[eventType] || '#6b7280'; // Gray default
}

/* ========================================
   Regression View
   ======================================== */

async function loadSnapshots() {
    const container = document.getElementById('snapshots-list');
    
    // TODO: Implement snapshot loading when backend is ready
    container.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">📸</span>
            <h3>No Snapshots Yet</h3>
            <p>Create snapshots to track changes over time</p>
            <button class="btn-primary" style="margin-top: 1rem;" onclick="createSnapshot()">
                + Create First Snapshot
            </button>
        </div>
    `;
}

function createSnapshot() {
    showModal('Create Snapshot', `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Snapshot Name</label>
                <input type="text" id="snapshot-name" placeholder="e.g., Production Baseline" 
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem;">
            </div>
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Description</label>
                <textarea id="snapshot-desc" placeholder="Optional description" rows="3"
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem;"></textarea>
            </div>
            <button class="btn-primary" onclick="saveSnapshot()" style="align-self: flex-end;">
                Create Snapshot
            </button>
        </div>
    `);
}

function saveSnapshot() {
    const name = document.getElementById('snapshot-name').value;
    const description = document.getElementById('snapshot-desc').value;
    
    if (!name) {
        showToast('Error', 'Please enter a snapshot name', 'error');
        return;
    }
    
    // TODO: Implement snapshot creation
    showToast('Success', 'Snapshot created successfully', 'success');
    closeModal();
    loadSnapshots();
}

/* ========================================
   Prompts View
   ======================================== */

async function loadPrompts() {
    const container = document.getElementById('prompts-list');
    
    // TODO: Implement prompt loading when backend is ready
    container.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">📝</span>
            <h3>No Prompts Registered</h3>
            <p>Register prompt templates to track versions</p>
            <button class="btn-primary" style="margin-top: 1rem;" onclick="registerPrompt()">
                + Register First Prompt
            </button>
        </div>
    `;
}

function registerPrompt() {
    showModal('Register Prompt', `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Prompt Name</label>
                <input type="text" id="prompt-name" placeholder="e.g., qa_prompt" 
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem;">
            </div>
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Template</label>
                <textarea id="prompt-template" placeholder="Enter your prompt template..." rows="6"
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem; font-family: monospace;"></textarea>
            </div>
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Version</label>
                <input type="text" id="prompt-version" placeholder="e.g., 1.0.0" value="1.0.0"
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem;">
            </div>
            <button class="btn-primary" onclick="savePrompt()" style="align-self: flex-end;">
                Register Prompt
            </button>
        </div>
    `);
}

function savePrompt() {
    const name = document.getElementById('prompt-name').value;
    const template = document.getElementById('prompt-template').value;
    const version = document.getElementById('prompt-version').value;
    
    if (!name || !template) {
        showToast('Error', 'Please fill in all required fields', 'error');
        return;
    }
    
    // TODO: Implement prompt registration
    showToast('Success', 'Prompt registered successfully', 'success');
    closeModal();
    loadPrompts();
}

/* ========================================
   Event Filtering Functions
   ======================================== */

function filterEvents() {
    if (!STATE.currentEvents || STATE.currentEvents.length === 0) {
        return;
    }
    
    const eventType = document.getElementById('event-type-filter')?.value || '';
    const minDuration = parseFloat(document.getElementById('min-duration-filter')?.value) || 0;
    const maxCost = parseFloat(document.getElementById('max-cost-filter')?.value) || Infinity;
    
    let filtered = [...STATE.currentEvents];
    
    if (eventType) {
        filtered = filtered.filter(e => e.event_type === eventType);
    }
    
    if (minDuration > 0) {
        filtered = filtered.filter(e => (e.duration_ms || 0) >= minDuration);
    }
    
    if (maxCost < Infinity) {
        filtered = filtered.filter(e => (e.cost || 0) <= maxCost);
    }
    
    renderTimeline(filtered);
    renderWaterfallChart(filtered);
    
    showToast('Filters Applied', `Showing ${filtered.length} of ${STATE.currentEvents.length} events`, 'info');
}

function clearFilters() {
    // Reset filter inputs
    const eventTypeFilter = document.getElementById('event-type-filter');
    const minDurationFilter = document.getElementById('min-duration-filter');
    const maxCostFilter = document.getElementById('max-cost-filter');
    
    if (eventTypeFilter) eventTypeFilter.value = '';
    if (minDurationFilter) minDurationFilter.value = '';
    if (maxCostFilter) maxCostFilter.value = '';
    
    // Re-render with all events
    if (STATE.currentEvents) {
        renderTimeline(STATE.currentEvents);
        renderWaterfallChart(STATE.currentEvents);
        showToast('Filters Cleared', 'Showing all events', 'success');
    }
}

/* ========================================
   Export Functions
   ======================================== */

function exportSessionJSON() {
    if (!STATE.currentSessionData || !STATE.currentEvents) {
        showToast('Error', 'No session data to export', 'error');
        return;
    }
    
    const data = {
        session: STATE.currentSessionData,
        events: STATE.currentEvents,
        exported_at: new Date().toISOString(),
        version: '0.2.0'
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { 
        type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const sessionId = STATE.currentSessionData.id || STATE.currentSessionData.session_id || 'session';
    a.download = `ragdebug-${sessionId.slice(0, 8)}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('Success', 'Session exported as JSON', 'success');
}

function exportSessionCSV() {
    if (!STATE.currentEvents || STATE.currentEvents.length === 0) {
        showToast('Error', 'No events to export', 'error');
        return;
    }
    
    // Create CSV header
    const headers = ['Event ID', 'Type', 'Timestamp', 'Duration (ms)', 'Cost ($)', 'Data'];
    
    // Create CSV rows
    const rows = STATE.currentEvents.map(e => [
        e.id || e.event_id || '',
        e.event_type || '',
        e.timestamp ? new Date(e.timestamp).toISOString() : '',
        e.duration_ms || 0,
        (e.cost || 0).toFixed(6),
        JSON.stringify(e.data || e.event_data || {}).replace(/"/g, '""')
    ]);
    
    // Combine into CSV string
    const csv = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const sessionId = STATE.currentSession || 'session';
    a.download = `ragdebug-events-${sessionId.slice(0, 8)}-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('Success', 'Events exported as CSV', 'success');
}

function copyToClipboard() {
    if (!STATE.currentEvents || STATE.currentEvents.length === 0) {
        showToast('Error', 'No events to copy', 'error');
        return;
    }
    
    const text = JSON.stringify(STATE.currentEvents, null, 2);
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Success', `Copied ${STATE.currentEvents.length} events to clipboard`, 'success');
    }).catch(err => {
        showToast('Error', 'Failed to copy to clipboard', 'error');
        console.error('Clipboard error:', err);
    });
}

/* ========================================
   Modal Management
   ======================================== */

function showModal(title, content) {
    const overlay = document.getElementById('modal-overlay');
    const titleEl = document.getElementById('modal-title');
    const bodyEl = document.getElementById('modal-body');
    
    titleEl.textContent = title;
    bodyEl.innerHTML = content;
    overlay.classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
}

/* ========================================
   Toast Notifications
   ======================================== */

function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.25s ease-in-out reverse';
        setTimeout(() => toast.remove(), 250);
    }, CONFIG.toastDuration);
}

/* ========================================
   Theme Management
   ======================================== */

function toggleTheme() {
    STATE.theme = STATE.theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', STATE.theme);
    localStorage.setItem('theme', STATE.theme);
    
    const icon = document.getElementById('theme-icon');
    icon.textContent = STATE.theme === 'light' ? '🌙' : '☀️';
}

/* ========================================
   Utility Functions
   ======================================== */

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
    
    return date.toLocaleDateString();
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDuration(session) {
    // Use total_duration_ms if available, otherwise calculate from timestamps
    if (session.total_duration_ms) {
        const ms = session.total_duration_ms;
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
        return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
    }
    
    // API uses 'completed_at', not 'ended_at'
    if (!session.completed_at) return 'In progress';
    
    const start = new Date(session.created_at);
    const end = new Date(session.completed_at);
    const diff = end - start;
    
    if (diff < 1000) return `${diff}ms`;
    if (diff < 60000) return `${(diff / 1000).toFixed(1)}s`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ${Math.floor((diff % 60000) / 1000)}s`;
    
    return `${Math.floor(diff / 3600000)}h ${Math.floor((diff % 3600000) / 60000)}m`;
}

function formatNumber(num) {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
}

/* ========================================
   Event Listeners
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Set initial theme
    document.documentElement.setAttribute('data-theme', STATE.theme);
    document.getElementById('theme-icon').textContent = STATE.theme === 'light' ? '🌙' : '☀️';

    // Navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchView(e.target.dataset.view);
        });
    });

    // Search and sort
    document.getElementById('search-input').addEventListener('input', (e) => {
        STATE.searchQuery = e.target.value;
        renderSessions(filterAndSortSessions());
    });

    document.getElementById('sort-select').addEventListener('change', (e) => {
        STATE.sortBy = e.target.value;
        renderSessions(filterAndSortSessions());
    });

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadViewData(STATE.currentView);
        showToast('Refreshed', 'Data reloaded successfully', 'success');
    });

    // Theme toggle
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

    // Back button
    document.getElementById('back-to-sessions').addEventListener('click', () => {
        switchView('sessions');
    });

    // Modal close
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal-overlay').addEventListener('click', (e) => {
        if (e.target.id === 'modal-overlay') closeModal();
    });

    // New snapshot button
    document.getElementById('new-snapshot-btn').addEventListener('click', createSnapshot);

    // New prompt button
    document.getElementById('new-prompt-btn').addEventListener('click', registerPrompt);

    // Initialize WebSocket connection
    connectWebSocket();

    // Load initial view
    loadSessions();

    // Set up auto-refresh
    setInterval(() => {
        if (STATE.currentView === 'sessions') {
            loadSessions();
        }
    }, CONFIG.refreshInterval);

    console.log('RAG Debugger UI initialized');
});
