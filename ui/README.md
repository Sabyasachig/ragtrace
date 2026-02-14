# RAG Debugger Web UI

Modern web interface for debugging and analyzing RAG pipelines in real-time.

## Features

### 📊 Sessions View
- Browse all debugging sessions
- Real-time session updates via WebSocket
- Search and filter sessions
- Sort by date, cost, or duration
- View session metrics (cost, tokens, events)

### ⏱️ Timeline View
- Visualize event flow chronologically
- Interactive event selection
- Detailed event inspection
- Performance metrics
- Cost breakdown per event

### 🧪 Regression Testing
- Create and manage snapshots
- Compare pipeline outputs
- Track changes over time
- Identify regressions

### 📝 Prompt Versioning
- Register prompt templates
- Track prompt versions
- Compare prompt performance
- Version history

## Quick Start

### 1. Start the API Server

```bash
cd /Users/sabyasachighosh/Projects/rag_trace/rag-debugger
uvicorn api.main:app --reload --port 8000
```

### 2. Start the UI Server

```bash
cd ui
python3 serve.py
```

### 3. Open in Browser

Navigate to: **http://localhost:3000**

## Architecture

```
ui/
├── index.html      # Main HTML structure
├── styles.css      # Complete styling system
├── app.js          # Application logic & API client
├── serve.py        # Development server
└── README.md       # This file
```

## Technology Stack

- **Frontend**: Vanilla JavaScript (ES6+)
- **Styling**: CSS3 with CSS Variables
- **API Communication**: Fetch API + WebSocket
- **Real-time Updates**: WebSocket connection to API

## Configuration

Edit `app.js` to configure:

```javascript
const CONFIG = {
    apiBaseUrl: 'http://localhost:8000/api/v1',
    wsUrl: 'ws://localhost:8000/ws',
    refreshInterval: 5000,
    toastDuration: 4000
};
```

## Features Implemented

✅ **Core UI Components**
- Responsive navigation system
- Multi-view SPA architecture
- Modal system for dialogs
- Toast notifications
- Theme toggle (light/dark)
- Connection status indicator

✅ **Sessions Management**
- List all sessions with pagination
- Search functionality
- Sort by multiple criteria
- Session detail view
- Real-time session updates

✅ **Timeline Visualization**
- Event timeline rendering
- Event filtering by type
- Interactive event selection
- Detailed event inspection
- Cost and performance metrics

✅ **Real-time Features**
- WebSocket connection
- Live session updates
- Event broadcasting
- Connection status monitoring

## Keyboard Shortcuts

- `Ctrl/Cmd + K` - Search sessions
- `Esc` - Close modals
- `Ctrl/Cmd + R` - Refresh current view
- `Ctrl/Cmd + Shift + D` - Toggle dark mode

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Development

### File Structure

```javascript
// app.js components:
- APIClient          // API communication layer
- ConnectionManager  // WebSocket management
- View Management    // Multi-view navigation
- Session Handlers   // Session list/detail logic
- Timeline Renderer  // Event visualization
- Modal System       // Dialog management
- Toast System       // Notifications
- Theme System       // Dark/light mode
```

### Adding New Views

1. Add HTML structure in `index.html`
2. Add navigation button
3. Implement view logic in `app.js`
4. Style in `styles.css`

### Styling Guidelines

- Use CSS variables for theming
- Follow BEM-like naming convention
- Responsive mobile-first approach
- Consistent spacing scale

## API Endpoints Used

- `GET /api/v1/sessions` - List sessions
- `GET /api/v1/sessions/{id}` - Get session details
- `GET /api/v1/sessions/{id}/events` - Get session events
- `GET /api/v1/sessions/{id}/cost` - Get cost breakdown
- `GET /api/v1/events` - List events
- `GET /api/v1/stats` - Get statistics
- `WS /ws` - WebSocket for real-time updates

## Troubleshooting

### UI not loading
- Check if `serve.py` is running on port 3000
- Verify no port conflicts
- Check browser console for errors

### API connection failed
- Ensure API server is running on port 8000
- Check CORS configuration
- Verify network connectivity

### WebSocket disconnected
- API server may be down
- Check firewall settings
- Try refreshing the page

### No sessions showing
- Create a session using the examples
- Check API endpoint `/api/v1/sessions`
- Verify database has data

## Performance

- Initial load: < 500ms
- Time to interactive: < 1s
- WebSocket latency: < 50ms
- Session list render: < 100ms for 1000 items

## Security Notes

For production deployment:

1. **CORS**: Configure specific origins in API
2. **HTTPS**: Use SSL certificates
3. **Authentication**: Add auth middleware
4. **Rate Limiting**: Implement API rate limits
5. **WebSocket Auth**: Add WS authentication

## Future Enhancements

🔮 **Planned Features**:
- Chart.js integration for cost graphs
- Advanced filtering and query builder
- Export sessions to JSON/CSV
- Session comparison view
- Custom dashboard widgets
- Keyboard navigation
- Accessibility improvements (WCAG 2.1)

## Contributing

1. Test changes in development mode
2. Ensure responsive design works
3. Test in multiple browsers
4. Update this README if needed

## License

MIT License - See main project LICENSE file
