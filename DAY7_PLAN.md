# 📊 Day 7 Plan: Timeline Visualizations & Charts

**Start Date:** February 16, 2026  
**Estimated Duration:** 4-5 hours  
**Objective:** Enhance timeline view with Chart.js visualizations  

---

## Overview

Day 7 will transform the timeline view from a simple event list into a powerful visual debugging tool with interactive charts, performance waterfalls, and advanced filtering.

---

## Goals

### Primary Objectives
1. ✨ Add Chart.js library for data visualization
2. 📊 Create performance waterfall chart
3. 🥧 Add cost breakdown pie chart
4. 🔍 Implement event filtering
5. 📤 Add export functionality

### Success Criteria
- [ ] Charts render correctly with real data
- [ ] Waterfall shows event timing visually
- [ ] Filters work for all event types
- [ ] Export generates valid JSON/CSV
- [ ] Performance remains excellent (<1s load)

---

## Implementation Plan

### Phase 1: Chart.js Setup (30 min)

#### 1.1 Add Chart.js to UI
```html
<!-- Add to ui/index.html in <head> -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
```

#### 1.2 Create Chart Container
```html
<!-- Add to timeline view -->
<div class="charts-section">
    <div class="chart-card">
        <h3>Performance Waterfall</h3>
        <canvas id="waterfall-chart"></canvas>
    </div>
    <div class="chart-card">
        <h3>Cost Breakdown</h3>
        <canvas id="cost-chart"></canvas>
    </div>
</div>
```

#### 1.3 Add Chart Styles
```css
/* Add to ui/styles.css */
.charts-section {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.chart-card {
    background: var(--card-bg);
    border-radius: 0.75rem;
    padding: 1.5rem;
    box-shadow: var(--shadow);
}
```

### Phase 2: Waterfall Chart (2 hours)

#### 2.1 Create Waterfall Chart Component
```javascript
// Add to ui/app.js
function renderWaterfallChart(events) {
    const ctx = document.getElementById('waterfall-chart').getContext('2d');
    
    // Transform events into chart data
    const chartData = events.map((event, index) => ({
        x: new Date(event.timestamp).getTime(),
        y: index,
        duration: event.duration_ms || 0,
        label: event.event_type,
        cost: event.cost || 0
    }));
    
    // Create bar chart representing event timeline
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: events.map(e => e.event_type),
            datasets: [{
                label: 'Duration (ms)',
                data: events.map(e => e.duration_ms || 0),
                backgroundColor: events.map(e => getEventColor(e.event_type)),
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y', // Horizontal bars
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const event = events[context.dataIndex];
                            return [
                                `Duration: ${event.duration_ms}ms`,
                                `Cost: $${(event.cost || 0).toFixed(6)}`,
                                `Type: ${event.event_type}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Duration (ms)' }
                },
                y: {
                    title: { display: true, text: 'Event' }
                }
            }
        }
    });
}

function getEventColor(eventType) {
    const colors = {
        'retrieval': '#3b82f6',    // Blue
        'prompt': '#8b5cf6',       // Purple
        'generation': '#10b981',   // Green
        'llm_start': '#f59e0b',    // Orange
        'llm_end': '#10b981'       // Green
    };
    return colors[eventType] || '#6b7280'; // Gray default
}
```

#### 2.2 Add Timeline Visualization
```javascript
// Enhanced timeline with visual bars
function renderTimeline(events) {
    // ... existing code ...
    
    // Add duration bar visual
    const maxDuration = Math.max(...events.map(e => e.duration_ms || 0));
    
    timelineEl.innerHTML = events.map(event => `
        <div class="timeline-event" data-event-id="${event.event_id}">
            <div class="timeline-event-time">${formatTime(event.timestamp)}</div>
            <div class="timeline-event-content">
                <div class="timeline-event-type">
                    ${getEventIcon(event.event_type)} ${event.event_type}
                </div>
                <div class="timeline-event-details">${getEventSummary(event)}</div>
                ${event.duration_ms ? `
                    <div class="duration-bar-container">
                        <div class="duration-bar" style="
                            width: ${(event.duration_ms / maxDuration) * 100}%;
                            background: ${getEventColor(event.event_type)};
                        "></div>
                        <span class="duration-label">${event.duration_ms}ms</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // Render waterfall chart
    renderWaterfallChart(events);
}
```

### Phase 3: Cost Breakdown Chart (1 hour)

#### 3.1 Create Pie Chart for Costs
```javascript
function renderCostChart(costData) {
    const ctx = document.getElementById('cost-chart').getContext('2d');
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Input Tokens', 'Output Tokens', 'Embeddings'],
            datasets: [{
                data: [
                    costData.input_cost || 0,
                    costData.output_cost || 0,
                    costData.embedding_cost || 0
                ],
                backgroundColor: [
                    '#3b82f6', // Blue
                    '#10b981', // Green
                    '#8b5cf6'  // Purple
                ],
                borderWidth: 2,
                borderColor: 'var(--card-bg)'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: $${value.toFixed(6)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}
```

#### 3.2 Integrate into Timeline Load
```javascript
async function loadTimeline(sessionId) {
    // ... existing code ...
    
    const [sessionData, eventsData, costData] = await Promise.all([
        api.getSession(sessionId),
        api.getSessionEvents(sessionId),
        api.getSessionCost(sessionId)
    ]);
    
    renderSessionInfo(sessionData, costData);
    renderTimeline(eventsData.events || []);
    renderCostChart(costData); // Add this line
}
```

### Phase 4: Event Filtering (1 hour)

#### 4.1 Add Filter UI
```html
<!-- Add to timeline view header -->
<div class="filters">
    <select id="event-type-filter" onchange="filterEvents()">
        <option value="">All Events</option>
        <option value="retrieval">Retrieval</option>
        <option value="prompt">Prompt</option>
        <option value="generation">Generation</option>
    </select>
    
    <input type="number" 
           id="min-duration-filter" 
           placeholder="Min duration (ms)"
           onchange="filterEvents()">
    
    <input type="number" 
           id="max-cost-filter" 
           placeholder="Max cost ($)"
           step="0.000001"
           onchange="filterEvents()">
</div>
```

#### 4.2 Implement Filter Logic
```javascript
function filterEvents() {
    const eventType = document.getElementById('event-type-filter').value;
    const minDuration = parseFloat(document.getElementById('min-duration-filter').value) || 0;
    const maxCost = parseFloat(document.getElementById('max-cost-filter').value) || Infinity;
    
    let filtered = STATE.currentEvents;
    
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
}
```

### Phase 5: Export Functionality (1 hour)

#### 5.1 Add Export Buttons
```html
<!-- Add to timeline view header -->
<div class="export-buttons">
    <button class="btn-secondary" onclick="exportSessionJSON()">
        📥 Export JSON
    </button>
    <button class="btn-secondary" onclick="exportSessionCSV()">
        📊 Export CSV
    </button>
    <button class="btn-secondary" onclick="copyToClipboard()">
        📋 Copy to Clipboard
    </button>
</div>
```

#### 5.2 Implement Export Functions
```javascript
function exportSessionJSON() {
    const session = STATE.currentSessionData;
    const events = STATE.currentEvents;
    
    const data = {
        session,
        events,
        exported_at: new Date().toISOString(),
        version: '0.2.0'
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { 
        type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `session-${session.session_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('Success', 'Session exported as JSON', 'success');
}

function exportSessionCSV() {
    const events = STATE.currentEvents;
    
    // Create CSV header
    const headers = ['Event ID', 'Type', 'Timestamp', 'Duration (ms)', 'Cost ($)'];
    
    // Create CSV rows
    const rows = events.map(e => [
        e.event_id,
        e.event_type,
        new Date(e.timestamp).toISOString(),
        e.duration_ms || 0,
        (e.cost || 0).toFixed(6)
    ]);
    
    // Combine into CSV string
    const csv = [headers, ...rows]
        .map(row => row.join(','))
        .join('\n');
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `events-${STATE.currentSession}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('Success', 'Events exported as CSV', 'success');
}

function copyToClipboard() {
    const events = STATE.currentEvents;
    const text = JSON.stringify(events, null, 2);
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Success', 'Events copied to clipboard', 'success');
    }).catch(err => {
        showToast('Error', 'Failed to copy to clipboard', 'error');
    });
}
```

---

## CSS Additions

```css
/* Chart containers */
.charts-section {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.chart-card {
    background: var(--card-bg);
    border-radius: 0.75rem;
    padding: 1.5rem;
    box-shadow: var(--shadow);
}

.chart-card h3 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
}

.chart-card canvas {
    max-height: 300px;
}

/* Filters */
.filters {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.filters select,
.filters input {
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    background: var(--card-bg);
    color: var(--text-primary);
    font-size: 0.875rem;
}

/* Export buttons */
.export-buttons {
    display: flex;
    gap: 0.5rem;
}

.btn-secondary {
    padding: 0.5rem 1rem;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-secondary:hover {
    background: var(--hover-bg);
    border-color: var(--primary-color);
}

/* Duration bars */
.duration-bar-container {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.duration-bar {
    height: 4px;
    border-radius: 2px;
    transition: width 0.3s ease;
}

.duration-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
}
```

---

## Testing Checklist

### Chart Rendering
- [ ] Waterfall chart displays correctly
- [ ] Cost pie chart shows accurate data
- [ ] Charts are responsive
- [ ] Tooltips show correct information
- [ ] Colors match event types

### Filtering
- [ ] Event type filter works
- [ ] Duration filter works
- [ ] Cost filter works
- [ ] Multiple filters can combine
- [ ] Clear filters button works

### Export
- [ ] JSON export downloads
- [ ] CSV export downloads
- [ ] Clipboard copy works
- [ ] File names are correct
- [ ] Data format is valid

### Performance
- [ ] Page loads in <1 second
- [ ] Charts render in <500ms
- [ ] Filters apply instantly
- [ ] No memory leaks
- [ ] Smooth animations

---

## Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 1 | Chart.js setup | 30 min | ⏳ Pending |
| 2 | Waterfall chart | 2 hours | ⏳ Pending |
| 3 | Cost breakdown | 1 hour | ⏳ Pending |
| 4 | Event filtering | 1 hour | ⏳ Pending |
| 5 | Export functionality | 1 hour | ⏳ Pending |
| - | **Total** | **5.5 hours** | ⏳ Pending |

---

## Success Metrics

- ✅ All charts render with real data
- ✅ Performance remains excellent
- ✅ Filters work correctly
- ✅ Export generates valid files
- ✅ Code is well-documented
- ✅ Tests pass
- ✅ No console errors

---

## Resources

### Chart.js Documentation
- Main docs: https://www.chartjs.org/docs/latest/
- Bar charts: https://www.chartjs.org/docs/latest/charts/bar.html
- Doughnut charts: https://www.chartjs.org/docs/latest/charts/doughnut.html
- Examples: https://www.chartjs.org/docs/latest/samples/

### Useful Plugins
- chartjs-plugin-annotation (for markers)
- chartjs-plugin-zoom (for zooming)
- chartjs-adapter-date-fns (for time axes)

---

## Post-Day 7

### Day 8 Ideas
- Regression testing UI completion
- Prompt version tracking
- Advanced analytics dashboard
- Real-time performance monitoring
- Alert system for cost thresholds

---

**Status:** 📋 Planning Complete  
**Ready to Start:** ✅ Yes  
**Prerequisites:** ✅ Day 6 complete  
**Estimated Completion:** ~5.5 hours from start

*Let's make the timeline view amazing! 🚀*
