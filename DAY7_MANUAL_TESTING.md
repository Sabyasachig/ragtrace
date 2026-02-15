# Day 7 Manual Testing Guide
## RAG Debugger v0.2.0 - Timeline Visualizations Testing

**Date:** February 16, 2026  
**Branch:** `feature/v0.2.0-day7-timeline-charts`  
**Status:** Ready for Manual Testing

---

## Pre-Testing Setup ✅

### Environment Status
- ✅ **API Server:** Running on port 8765
- ✅ **UI Server:** Running on port 3000  
- ✅ **Database:** `~/.ragdebug/ragdebug.db` with 5 test sessions
- ✅ **Browser:** Simple Browser opened at http://localhost:3000
- ✅ **Git:** All changes committed

### Recent Fixes
1. ✅ Updated UI config to use port 8765 (API actual port)
2. ✅ Added GET `/api/sessions/{id}/events` endpoint
3. ✅ Added GET `/api/sessions/{id}/cost` endpoint
4. ✅ API endpoints tested and responding correctly

---

## Quick Test Checklist

### Phase 1: Basic Functionality (5 min)
```
□ 1. Open http://localhost:3000 in browser
□ 2. Verify sessions list loads
□ 3. Click on first session
□ 4. Verify Timeline view loads
□ 5. Check browser console for errors (F12)
```

### Phase 2: Chart Visualization (10 min)
```
□ 6. Verify "Performance Waterfall" chart visible
□ 7. Verify chart has horizontal bars
□ 8. Hover over bars to see tooltips
□ 9. Verify "Cost Breakdown" chart visible
□ 10. Verify doughnut chart renders
□ 11. Check if charts are responsive (resize window)
```

### Phase 3: Filtering (10 min)
```
□ 12. Select event type from dropdown
□ 13. Verify timeline filters
□ 14. Verify chart updates
□ 15. Enter min duration (e.g., 100)
□ 16. Verify filters apply
□ 17. Click "Clear Filters"
□ 18. Verify all events return
```

### Phase 4: Export Functionality (10 min)
```
□ 19. Click "Export JSON" button
□ 20. Verify file downloads
□ 21. Click "Export CSV" button
□ 22. Verify CSV downloads
□ 23. Click "Copy to Clipboard"
□ 24. Paste in text editor (Cmd+V)
□ 25. Verify JSON data copied
```

### Phase 5: Error Handling (5 min)
```
□ 26. Navigate back to Sessions view
□ 27. Return to Timeline
□ 28. Verify state preserved
□ 29. Test with different sessions
□ 30. Check console for any errors
```

---

## Manual Testing Instructions

### Step-by-Step Guide

#### 1. Open Application
```
✓ Browser is already open at http://localhost:3000
✓ You should see "RAG Debugger v0.2.0" header
✓ Sessions view should be active
```

#### 2. Test Sessions List
**What to Check:**
- Sessions are displayed in cards
- Each card shows: Query, Date, Cost, Duration, Model
- Sessions are sorted by most recent first
- "View Details" button visible on each card

**Expected Count:** 5 test sessions

#### 3. Load Timeline View
**Action:** Click "View Details" on first session

**What to Check:**
- URL changes to include session ID
- View switches to Timeline
- Session info displays at top
- Timeline events list appears below
- Two chart areas visible below timeline

#### 4. Verify Performance Waterfall Chart
**Location:** Left side of charts section

**What to Check:**
- ✅ Chart title: "Performance Waterfall"
- ✅ Horizontal bar chart visible
- ✅ Each bar has a label (e.g., "1. retrieval")
- ✅ Bars are colored (different colors for different event types)
- ✅ X-axis shows "Duration (ms)"
- ✅ Hover shows tooltip with: Duration, Cost, Type

**Troubleshooting:**
- If you see "No events to display": Events might be empty, try another session
- If chart doesn't render: Check browser console (F12) for errors
- If colors are all the same: Check `getEventColor()` function

#### 5. Verify Cost Breakdown Chart
**Location:** Right side of charts section

**What to Check:**
- ✅ Chart title: "Cost Breakdown"
- ✅ Doughnut/pie chart visible
- ✅ Three segments: Input Tokens, Output Tokens, Embeddings
- ✅ Colors: Blue, Green, Purple
- ✅ Hover shows tooltip with cost and percentage

**Troubleshooting:**
- If you see "No cost data": Cost might be zero, expected for some sessions
- Check if `renderCostChart()` is being called

#### 6. Test Event Type Filter
**Location:** Below charts section

**Action:**
1. Find "Event Type" dropdown
2. Select "retrieval"
3. Observe changes

**Expected Results:**
- Timeline shows only retrieval events
- Waterfall chart updates with fewer bars
- Toast notification appears: "Filters Applied: Showing X of Y events"
- Other event types hidden

#### 7. Test Duration Filter
**Action:**
1. Enter "100" in "Min duration (ms)" field
2. Press Enter or click outside

**Expected Results:**
- Events with duration < 100ms hidden
- Charts update
- Toast shows filtered count
- Fast events not visible

#### 8. Test Cost Filter
**Action:**
1. Enter "0.001" in "Max cost ($)" field
2. Apply filter

**Expected Results:**
- Events with cost > $0.001 hidden
- Charts update accordingly
- Toast notification appears

#### 9. Test Combined Filters
**Action:**
1. Select event type: "generation"
2. Set min duration: 50
3. Set max cost: 0.005

**Expected Results:**
- Only events matching ALL criteria shown
- AND logic applied (not OR)
- Correct count in toast

#### 10. Test Clear Filters
**Action:** Click "Clear Filters" button

**Expected Results:**
- All filter inputs reset to empty
- Timeline shows all events again
- Charts show all events
- Toast: "Filters Cleared"

#### 11. Test Export JSON
**Action:** Click "📥 Export JSON" button

**Expected Results:**
- File downloads immediately
- Filename format: `ragdebug-{sessionId}-{timestamp}.json`
- File contains:
  ```json
  {
    "session": { /* session data */ },
    "events": [ /* all events */ ],
    "exported_at": "2026-02-16T...",
    "version": "0.2.0"
  }
  ```
- Toast: "Session exported as JSON"

#### 12. Test Export CSV
**Action:** Click "📊 Export CSV" button

**Expected Results:**
- CSV file downloads
- Filename: `ragdebug-events-{sessionId}-{timestamp}.csv`
- Headers: Event ID, Type, Timestamp, Duration (ms), Cost ($), Data
- All events included as rows
- Toast: "Events exported as CSV"

#### 13. Test Copy to Clipboard
**Action:** 
1. Click "📋 Copy to Clipboard" button
2. Open text editor (TextEdit, VS Code, etc.)
3. Paste (Cmd+V)

**Expected Results:**
- No file download
- Events array copied as JSON
- Properly formatted with indentation
- Toast: "Copied X events to clipboard"
- Can paste into any application

#### 14. Test Responsive Design
**Action:** Resize browser window

**Desktop (> 1024px):**
- Charts side-by-side (waterfall wider)
- Filters in horizontal row
- Full width layout

**Tablet (768px - 1024px):**
- Charts stacked vertically
- Filters still horizontal or wrapping
- Readable layout

**Mobile (< 768px):**
- Charts stacked
- Filters stacked
- Touch-friendly buttons

#### 15. Test State Management
**Action:**
1. Apply some filters
2. Navigate to Sessions view (click "Sessions" in header)
3. Go back to Timeline (click same session)

**Expected Results:**
- Filters should be cleared on return
- Fresh data loaded
- Charts re-render
- No stale state from previous view

#### 16. Test Session Switching
**Action:**
1. View Session A
2. Apply filters
3. Return to Sessions
4. View Session B

**Expected Results:**
- Session B loads fresh
- No filters from Session A
- Charts show Session B data
- No data contamination

---

## Known Issues to Document

### Issue Template
```markdown
**Issue:** [Brief description]
**Severity:** Critical / Major / Minor
**Steps to Reproduce:**
1. 
2. 
3. 

**Expected:** [What should happen]
**Actual:** [What actually happens]
**Browser Console Error:** [Copy error from console]
**Screenshot:** [If applicable]
**Workaround:** [If any]
```

---

## Browser Console Checks

### Open Developer Tools
- **Chrome/Edge:** F12 or Cmd+Option+I
- **Firefox:** F12 or Cmd+Option+K
- **Safari:** Cmd+Option+I (after enabling Developer menu)

### What to Look For

#### ✅ No Errors
```
✓ Chart.js loaded successfully
✓ API calls returning 200 OK
✓ No CORS errors
✓ No undefined variables
✓ No failed promises
```

#### ⚠️ Warnings (Acceptable)
```
~ Deprecation warnings (FastAPI)
~ Source map warnings (Chart.js from CDN)
```

#### ❌ Errors (Need to Fix)
```
✗ "Chart is not defined"
✗ "Failed to fetch"
✗ "Uncaught TypeError"
✗ "Cannot read property X of undefined"
✗ CORS policy errors
```

---

## Performance Checks

### Chart Rendering Time
**Test:** Open Timeline with many events

**Measure:**
1. Open Console
2. Type: `console.time('render')`
3. Load timeline
4. Type: `console.timeEnd('render')`

**Expected:** < 200ms for initial render

### Filter Update Time
**Test:** Apply filter and measure update

**Expected:** < 100ms for filter update

### Export Performance
**Test:** Export 100+ events as JSON/CSV

**Expected:** < 500ms, no UI freezing

---

## Success Criteria

### Must Pass (Critical)
- [ ] All 5 test sessions load
- [ ] Timeline view displays without errors
- [ ] Both charts render correctly
- [ ] At least one export format works
- [ ] No critical JavaScript errors

### Should Pass (Important)
- [ ] Filters work correctly
- [ ] Clear filters works
- [ ] All 3 export formats work
- [ ] Responsive design works
- [ ] State management works
- [ ] Toast notifications appear

### Nice to Have (Optional)
- [ ] Performance under 200ms
- [ ] All browsers tested
- [ ] Mobile tested on real device
- [ ] Clipboard works in all browsers

---

## Testing Complete Checklist

```
□ Sessions list loads (5 sessions visible)
□ Timeline view loads for at least 1 session
□ Performance Waterfall chart renders
□ Cost Breakdown chart renders
□ Chart tooltips work on hover
□ Event type filter works
□ Duration filter works
□ Cost filter works
□ Combined filters work (AND logic)
□ Clear filters works
□ Export JSON downloads file
□ Export CSV downloads file
□ Copy to Clipboard works
□ Responsive design verified (3 breakpoints)
□ Session switching works
□ State management works
□ No critical console errors
□ Performance acceptable
□ All features documented
□ Screenshots taken (if needed)
```

---

## Next Steps After Testing

### If All Tests Pass ✅
1. Update `DAY7_TESTING.md` with results
2. Mark all tests as complete
3. Take screenshots for documentation
4. Create final summary document
5. Merge to main branch
6. Push to GitHub
7. Plan Day 8 enhancements

### If Tests Fail ❌
1. Document all issues found
2. Prioritize by severity (Critical → Major → Minor)
3. Fix critical issues first
4. Re-test after fixes
5. Update code and documentation
6. Commit fixes
7. Re-run full test suite

---

## Contact & Support

**Testing Support:**
- Check browser console for errors
- Review API logs: `/tmp/api.log`
- Review UI logs: `/tmp/ui.log`
- Check database: `~/.ragdebug/ragdebug.db`

**Documentation:**
- `DAY7_COMPLETE.md` - Implementation details
- `DAY7_TESTING.md` - Full test plan
- `DAY7_PLAN.md` - Original requirements

---

**Testing Started:** February 16, 2026  
**Current Status:** Ready for Manual Testing  
**Browser:** http://localhost:3000 (already open)  
**Action Required:** Follow Step-by-Step Guide above
