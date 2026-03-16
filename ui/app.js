/* ========================================
   Configuration & State
   ======================================== */

const CONFIG = {
    apiBaseUrl: 'http://localhost:8000/api',  // API server port
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

    // Snapshot endpoints
    async getSnapshots(limit = 20) {
        return this.request(`/snapshots?limit=${limit}`);
    }

    async getSnapshot(snapshotId) {
        return this.request(`/snapshots/${snapshotId}`);
    }

    async createSnapshot(payload) {
        return this.request('/snapshots', { method: 'POST', body: JSON.stringify(payload) });
    }

    async deleteSnapshot(snapshotId) {
        return this.request(`/snapshots/${snapshotId}`, { method: 'DELETE' });
    }

    async compareSnapshots(id1, id2) {
        return this.request(`/snapshots/${id1}/compare/${id2}`);
    }

    async scoreSnapshots(id1, id2) {
        return this.request(`/snapshots/${id1}/score/${id2}`);
    }

    // Prompt versioning endpoints
    async getPromptNames() {
        return this.request('/prompts');
    }

    async getPromptVersions(name) {
        return this.request(`/prompts/${encodeURIComponent(name)}`);
    }

    async getActivePrompt(name) {
        return this.request(`/prompts/${encodeURIComponent(name)}/active`);
    }

    async savePromptVersion(payload) {
        return this.request('/prompts', { method: 'POST', body: JSON.stringify(payload) });
    }

    async diffPrompts(name, va, vb) {
        return this.request(`/prompts/${encodeURIComponent(name)}/diff/${va}/${vb}`);
    }

    async deletePromptVersion(name, version) {
        return this.request(`/prompts/${encodeURIComponent(name)}/versions/${version}`, { method: 'DELETE' });
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

async function loadViewData(viewName) {
    switch (viewName) {
        case 'sessions':
            loadSessions();
            break;
        case 'timeline':
            if (STATE.currentSession) {
                loadTimeline(STATE.currentSession);
            } else {
                // Auto-select most recent session if none selected
                if (STATE.sessions.length === 0) {
                    await loadSessions();
                }
                if (STATE.sessions.length > 0) {
                    const mostRecentSession = STATE.sessions[0];
                    const sessionId = mostRecentSession.id || mostRecentSession.session_id;
                    STATE.currentSession = sessionId;
                    loadTimeline(sessionId);
                } else {
                    // Show empty state if no sessions
                    const timelineEl = document.getElementById('timeline');
                    if (timelineEl) {
                        timelineEl.innerHTML = `
                            <div class="empty-state">
                                <span class="empty-icon">📊</span>
                                <h3>No Sessions Available</h3>
                                <p>Create a session first to view timeline data</p>
                            </div>
                        `;
                    }
                }
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

    timelineEl.innerHTML = events.map(event => {
        const eventId = event.id || event.event_id;
        return `
        <div class="timeline-event" data-event-id="${eventId}" onclick="showEventDetails('${eventId}')">
            <div class="timeline-event-time">${formatTime(event.timestamp)}</div>
            <div class="timeline-event-content">
                <div class="timeline-event-type">${getEventIcon(event.event_type)} ${event.event_type}</div>
                <div class="timeline-event-details">${getEventSummary(event)}</div>
            </div>
        </div>
    `}).join('');
}

function getEventIcon(eventType) {
    const icons = {
        'retrieval': '🔍',
        'prompt': '📝',
        'generation': '🚀',
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
    const data = event.data || event.event_data || {};
    
    // Handle new event types
    if (event.event_type === 'retrieval') {
        return `Retrieved ${data.chunks?.length || 0} chunks • ${data.duration_ms || 0}ms • $${(data.embedding_cost || 0).toFixed(6)}`;
    }
    
    if (event.event_type === 'prompt') {
        return `${data.token_count || 0} tokens • Template: ${data.template_name || 'default'}`;
    }
    
    if (event.event_type === 'generation') {
        return `${data.input_tokens || 0} → ${data.output_tokens || 0} tokens • ${data.duration_ms || 0}ms • $${(data.cost || 0).toFixed(6)}`;
    }
    
    // Legacy event types
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

function showEventDetails(eventId) {
    // Remove selection from all events
    document.querySelectorAll('.timeline-event').forEach(el => {
        el.classList.remove('selected');
    });

    // Add selection to clicked event
    document.querySelector(`[data-event-id="${eventId}"]`)?.classList.add('selected');

    const detailsEl = document.getElementById('event-details');
    
    // Find event in STATE.currentEvents
    const event = STATE.currentEvents.find(e => (e.id || e.event_id) === eventId);
    
    if (!event) {
        detailsEl.innerHTML = '<h3>Event Details</h3><p class="text-danger">Event not found</p>';
        return;
    }
    
    const eventData = event.data || event.event_data || {};

    detailsEl.innerHTML = `
        <h3>Event Details</h3>
        <div class="event-details-content">
            <div class="detail-group">
                <div class="detail-label">Event ID</div>
                <div class="detail-value">${event.id || event.event_id}</div>
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
                <div class="detail-value">${eventData.duration_ms ? `${eventData.duration_ms}ms` : 'N/A'}</div>
            </div>
            ${eventData.cost ? `
            <div class="detail-group">
                <div class="detail-label">Cost</div>
                <div class="detail-value cost">$${eventData.cost.toFixed(6)}</div>
            </div>
            ` : ''}
            <div class="detail-group">
                <div class="detail-label">Event Data</div>
                <div class="detail-value"><pre>${JSON.stringify(eventData, null, 2)}</pre></div>
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
                data: events.map(e => {
                    const data = e.data || {};
                    return data.duration_ms || 0;
                }),
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
                            const eventData = event.data || {};
                            return [
                                `Duration: ${eventData.duration_ms || 0}ms`,
                                `Cost: $${(eventData.cost || 0).toFixed(6)}`,
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
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading snapshots...</p></div>';

    try {
        const snapshots = await api.getSnapshots(50);

        if (!snapshots || snapshots.length === 0) {
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
            return;
        }

        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0;">${snapshots.length} snapshot${snapshots.length !== 1 ? 's' : ''}</h3>
                <button class="btn-primary" onclick="createSnapshot()">+ New Snapshot</button>
            </div>
            <div class="snapshots-grid">
                ${snapshots.map(snap => `
                    <div class="snapshot-card" id="snap-${snap.id}">
                        <div class="snapshot-card-header">
                            <strong>${snap.name || snap.id.slice(0, 8)}</strong>
                            <span class="snapshot-date">${formatDate(snap.created_at)}</span>
                        </div>
                        ${snap.description ? `<p class="snapshot-desc">${snap.description}</p>` : ''}
                        <div class="snapshot-meta">
                            <span>ID: <code>${snap.id.slice(0, 10)}…</code></span>
                        </div>
                        <div class="snapshot-actions">
                            <button class="btn-secondary btn-sm" onclick="selectForCompare('${snap.id}')">Compare</button>
                            <button class="btn-danger btn-sm" onclick="deleteSnapshot('${snap.id}')">Delete</button>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div id="compare-panel" style="display:none; margin-top: 1.5rem; padding: 1rem; border: 1px solid var(--border-color); border-radius: 0.5rem;">
                <h4 style="margin: 0 0 0.75rem 0;">Regression Comparison</h4>
                <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;">
                    <div>
                        <label style="font-size: 0.85rem; font-weight: 600;">Baseline</label>
                        <select id="compare-base" style="margin-left: 0.5rem; padding: 0.35rem 0.5rem; border: 1px solid var(--border-color); border-radius: 0.4rem;">
                            ${snapshots.map(s => `<option value="${s.id}">${s.name || s.id.slice(0,8)}</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label style="font-size: 0.85rem; font-weight: 600;">Candidate</label>
                        <select id="compare-candidate" style="margin-left: 0.5rem; padding: 0.35rem 0.5rem; border: 1px solid var(--border-color); border-radius: 0.4rem;">
                            ${snapshots.map((s, i) => `<option value="${s.id}" ${i === 1 ? 'selected' : ''}>${s.name || s.id.slice(0,8)}</option>`).join('')}
                        </select>
                    </div>
                    <button class="btn-primary" onclick="runRegression()">Run Regression</button>
                </div>
                <div id="regression-result" style="margin-top: 1rem;"></div>
            </div>
        `;

        // Show compare panel automatically if we have >= 2 snapshots
        if (snapshots.length >= 2) {
            document.getElementById('compare-panel').style.display = 'block';
        }
    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚠️</span>
                <h3>Failed to Load Snapshots</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

function selectForCompare(snapshotId) {
    const panel = document.getElementById('compare-panel');
    if (panel) panel.style.display = 'block';
    const candidateSelect = document.getElementById('compare-candidate');
    if (candidateSelect) candidateSelect.value = snapshotId;
}

async function runRegression() {
    const baseId = document.getElementById('compare-base')?.value;
    const candidateId = document.getElementById('compare-candidate')?.value;
    const resultEl = document.getElementById('regression-result');

    if (!baseId || !candidateId) return;
    if (baseId === candidateId) {
        showToast('Error', 'Please select two different snapshots', 'error');
        return;
    }

    resultEl.innerHTML = '<div class="loading"><div class="spinner"></div><p>Running comparison…</p></div>';

    try {
        const [scoreData, comparison] = await Promise.all([
            api.scoreSnapshots(baseId, candidateId),
            api.compareSnapshots(baseId, candidateId)
        ]);

        const verdictClass = {PASS: 'text-success', WARN: 'text-warning', FAIL: 'text-danger'}[scoreData.verdict] || '';
        resultEl.innerHTML = `
            <div style="display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-start;">
                <div style="flex: 0 0 auto; text-align: center; padding: 1rem; background: var(--card-bg); border-radius: 0.5rem; min-width: 140px;">
                    <div style="font-size: 2rem; font-weight: 700;" class="${verdictClass}">${scoreData.verdict}</div>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">Score: ${(scoreData.score * 100).toFixed(1)}%</div>
                </div>
                <div style="flex: 1; min-width: 260px;">
                    <table style="width:100%; font-size: 0.875rem; border-collapse: collapse;">
                        <tr><td style="padding: 0.3rem 0.6rem; color: var(--text-muted);">Retrieval similarity</td>
                            <td style="padding: 0.3rem 0.6rem; font-weight: 600;">${((comparison.retrieval_diff?.similarity ?? 0) * 100).toFixed(1)}%</td></tr>
                        <tr><td style="padding: 0.3rem 0.6rem; color: var(--text-muted);">Answer similarity</td>
                            <td style="padding: 0.3rem 0.6rem; font-weight: 600;">${((comparison.answer_diff?.similarity ?? 0) * 100).toFixed(1)}%</td></tr>
                        <tr><td style="padding: 0.3rem 0.6rem; color: var(--text-muted);">Cost delta</td>
                            <td style="padding: 0.3rem 0.6rem; font-weight: 600;">$${(comparison.cost_diff?.absolute_delta ?? 0).toFixed(6)}</td></tr>
                    </table>
                    ${comparison.answer_diff?.diff_lines?.length
                        ? `<details style="margin-top:0.5rem;"><summary style="cursor:pointer;font-size:0.8rem;">Show answer diff</summary>
                            <pre style="font-size:0.75rem;overflow:auto;max-height:200px;background:var(--code-bg,#f5f5f5);padding:0.5rem;border-radius:0.4rem;">${comparison.answer_diff.diff_lines.map(l => escapeHtml(l)).join('\n')}</pre></details>`
                        : ''}
                </div>
            </div>`;
    } catch (error) {
        resultEl.innerHTML = `<p class="text-danger">Comparison failed: ${error.message}</p>`;
    }
}

function escapeHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
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
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Session ID (to snapshot)</label>
                <input type="text" id="snapshot-session-id" placeholder="e.g., abc-123…" 
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem;">
            </div>
            <button class="btn-primary" onclick="saveSnapshot()" style="align-self: flex-end;">
                Create Snapshot
            </button>
        </div>
    `);
}

async function saveSnapshot() {
    const name = document.getElementById('snapshot-name').value.trim();
    const description = document.getElementById('snapshot-desc').value.trim();
    const sessionId = document.getElementById('snapshot-session-id').value.trim();

    if (!name) {
        showToast('Error', 'Please enter a snapshot name', 'error');
        return;
    }

    try {
        await api.createSnapshot({ name, description, session_id: sessionId || undefined });
        showToast('Success', 'Snapshot created successfully', 'success');
        closeModal();
        loadSnapshots();
    } catch (error) {
        showToast('Error', `Failed to create snapshot: ${error.message}`, 'error');
    }
}

async function deleteSnapshot(snapshotId) {
    if (!confirm('Delete this snapshot? This action cannot be undone.')) return;
    try {
        await api.deleteSnapshot(snapshotId);
        showToast('Success', 'Snapshot deleted', 'success');
        loadSnapshots();
    } catch (error) {
        showToast('Error', `Failed to delete snapshot: ${error.message}`, 'error');
    }
}

/* ========================================
   Prompts View
   ======================================== */

async function loadPrompts() {
    const container = document.getElementById('prompts-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading prompts…</p></div>';

    try {
        const names = await api.getPromptNames();

        if (!names || names.length === 0) {
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
            return;
        }

        // Fetch all versions in parallel
        const versionsPerName = await Promise.all(names.map(n => api.getPromptVersions(n)));

        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0;">${names.length} prompt${names.length !== 1 ? 's' : ''}</h3>
                <button class="btn-primary" onclick="registerPrompt()">+ New Prompt</button>
            </div>
            ${names.map((name, i) => {
                const versions = versionsPerName[i] || [];
                const active = versions.find(v => v.is_active) || versions[0];
                return `
                <div class="prompt-card" style="border: 1px solid var(--border-color); border-radius: 0.5rem; padding: 1rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <strong style="font-size: 1rem;">${escapeHtml(name)}</strong>
                        <span style="font-size: 0.8rem; color: var(--text-muted);">${versions.length} version${versions.length !== 1 ? 's' : ''}</span>
                    </div>
                    ${active ? `
                    <div style="margin-bottom: 0.75rem;">
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.25rem;">Active template (v${active.version})</div>
                        <pre style="margin: 0; font-size: 0.8rem; background: var(--code-bg, #f5f5f5); padding: 0.5rem; border-radius: 0.4rem; overflow: auto; max-height: 120px;">${escapeHtml(active.template)}</pre>
                    </div>` : ''}
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
                        ${versions.length >= 2 ? `
                        <select id="diff-va-${i}" style="padding: 0.3rem 0.5rem; border: 1px solid var(--border-color); border-radius: 0.4rem; font-size: 0.8rem;">
                            ${versions.map(v => `<option value="${v.version}">v${v.version}</option>`).join('')}
                        </select>
                        <span style="font-size: 0.8rem; color: var(--text-muted);">vs</span>
                        <select id="diff-vb-${i}" style="padding: 0.3rem 0.5rem; border: 1px solid var(--border-color); border-radius: 0.4rem; font-size: 0.8rem;">
                            ${versions.map((v, vi) => `<option value="${v.version}" ${vi === 1 ? 'selected' : ''}>${'v' + v.version}</option>`).join('')}
                        </select>
                        <button class="btn-secondary btn-sm" onclick="showPromptDiff('${escapeHtml(name)}', ${i})">Show Diff</button>
                        ` : ''}
                        <button class="btn-primary btn-sm" onclick="registerPrompt('${escapeHtml(name)}')">+ New Version</button>
                    </div>
                    <div id="prompt-diff-${i}" style="margin-top: 0.5rem;"></div>
                </div>`;
            }).join('')}
        `;
    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚠️</span>
                <h3>Failed to Load Prompts</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

async function showPromptDiff(name, idx) {
    const va = parseInt(document.getElementById(`diff-va-${idx}`)?.value);
    const vb = parseInt(document.getElementById(`diff-vb-${idx}`)?.value);
    const resultEl = document.getElementById(`prompt-diff-${idx}`);

    if (va === vb) {
        showToast('Error', 'Please select two different versions', 'error');
        return;
    }

    resultEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const diff = await api.diffPrompts(name, va, vb);
        const lines = diff.diff_lines || [];
        resultEl.innerHTML = `
            <details open>
                <summary style="cursor:pointer; font-size:0.8rem; margin-bottom:0.4rem;">
                    Diff v${va} → v${vb} &nbsp; <span style="color:var(--text-muted);">similarity ${(diff.similarity_score * 100).toFixed(1)}%</span>
                </summary>
                <pre style="font-size:0.75rem;overflow:auto;max-height:200px;background:var(--code-bg,#f5f5f5);padding:0.5rem;border-radius:0.4rem;">${lines.map(l => {
                    const cls = l.startsWith('+') ? 'color:green' : l.startsWith('-') ? 'color:red' : 'color:var(--text-muted)';
                    return `<span style="${cls}">${escapeHtml(l)}</span>`;
                }).join('\n')}</pre>
            </details>`;
    } catch (error) {
        resultEl.innerHTML = `<p class="text-danger" style="font-size:0.8rem;">Diff failed: ${error.message}</p>`;
    }
}

function registerPrompt(existingName = '') {
    showModal('Register Prompt', `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Prompt Name</label>
                <input type="text" id="prompt-name" placeholder="e.g., qa_prompt" value="${escapeHtml(existingName)}"
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem;"
                    ${existingName ? 'readonly' : ''}>
            </div>
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Template</label>
                <textarea id="prompt-template" placeholder="Enter your prompt template…" rows="6"
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem; font-family: monospace;"></textarea>
            </div>
            <div>
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Description (optional)</label>
                <input type="text" id="prompt-description" placeholder="What changed in this version?"
                    style="width: 100%; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.5rem;">
            </div>
            <button class="btn-primary" onclick="savePrompt()" style="align-self: flex-end;">
                Save Prompt
            </button>
        </div>
    `);
}

async function savePrompt() {
    const name = document.getElementById('prompt-name').value.trim();
    const template = document.getElementById('prompt-template').value;
    const description = document.getElementById('prompt-description').value.trim();

    if (!name || !template) {
        showToast('Error', 'Please fill in name and template', 'error');
        return;
    }

    try {
        await api.savePromptVersion({ name, template, description: description || undefined });
        showToast('Success', 'Prompt version saved', 'success');
        closeModal();
        loadPrompts();
    } catch (error) {
        showToast('Error', `Failed to save prompt: ${error.message}`, 'error');
    }
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
        filtered = filtered.filter(e => {
            const data = e.data || {};
            return (data.duration_ms || 0) >= minDuration;
        });
    }
    
    if (maxCost < Infinity) {
        filtered = filtered.filter(e => {
            const data = e.data || {};
            return (data.cost || 0) <= maxCost;
        });
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
    a.download = `ragtrace-${sessionId.slice(0, 8)}-${Date.now()}.json`;
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
    const rows = STATE.currentEvents.map(e => {
        const eventData = e.data || e.event_data || {};
        return [
            e.id || e.event_id || '',
            e.event_type || '',
            e.timestamp ? new Date(e.timestamp).toISOString() : '',
            eventData.duration_ms || 0,
            (eventData.cost || 0).toFixed(6),
            JSON.stringify(eventData).replace(/"/g, '""')
        ];
    });
    
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
    a.download = `ragtrace-events-${sessionId.slice(0, 8)}-${Date.now()}.csv`;
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

    console.log('RAGTrace UI initialized');
});

/* ========================================
   Expose Functions to Global Scope
   (Required for onclick handlers in module)
   ======================================== */

window.viewSession = viewSession;
window.showEventDetails = showEventDetails;
window.filterEvents = filterEvents;
window.clearFilters = clearFilters;
window.exportSessionJSON = exportSessionJSON;
window.exportSessionCSV = exportSessionCSV;
window.copyToClipboard = copyToClipboard;
