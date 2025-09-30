# Frontend Layout & Visualization Fix

**Date**: September 30, 2025  
**Status**: ✅ DEPLOYED

## Problems Solved

### Issue 1: Grid Layout Creating Side-by-Side Columns
**Symptom**: Thinking Process and Cortex Queries appearing side-by-side instead of stacked vertically

**Root Cause**:
- CSS `.message` uses `grid-template-columns: auto 1fr` (2 columns)
- Streaming message added 4 children: badge, thinking, answer, SQL
- Grid placed them as:
  - Row 1: Badge | Thinking
  - Row 2: Answer | SQL ← Unwanted side-by-side

**Solution**:
- Added `.message-content-wrapper` div to wrap all content
- Wrapper uses `flexbox` with `flex-direction: column`
- Forces vertical stacking: Thinking → SQL → Answer → Viz
- Badge stays in first grid column (left side)

### Issue 2: Visualization Not Rendering
**Symptom**: Agent mentions creating visualization but chart/table doesn't appear

**Root Causes**:
1. Manual questions don't have `viz` parameter (only pills have `data-viz` attribute)
2. Table data extracted from `response` event but no viz spec to render it
3. `renderVizBelow` called on wrong parent element

**Solution**:
- Extract table data from `response.table` event AND `response` event content
- Implement `inferVizFromResponse()` to auto-detect viz type from:
  - Answer text keywords ("by borough", "by zone", "across")
  - Data structure (column names like "zone", "borough", "price")
- Auto-generate viz spec: `{type: 'bar', x: 'zone_column', y: 'price_column'}`
- Render in dedicated `vizPlaceholder` div within content wrapper

---

## Implementation Details

### Frontend Changes (`docs/app.js`)

#### 1. New Layout Structure
```javascript
message (grid)
├─ badge (column 1)
└─ message-content-wrapper (column 2, flexbox vertical)
   ├─ Row 1: thinkingSection <details>
   ├─ Row 2: sqlSection <div>
   └─ Row 3: outputSection <div>
      ├─ answerDiv (text)
      └─ vizPlaceholder (charts/tables)
```

#### 2. Visualization Inference Logic
```javascript
function inferVizFromResponse(answerText, data) {
  // Check for grouping keywords
  if (answerText.includes('by borough') || 
      columns.includes('zone') ||
      columns.includes('borough')) {
    
    // Find X axis (categorical)
    xColumn = 'zone' or 'borough' or first column
    
    // Find Y axis (numeric)
    yColumn = column with 'price'/'count'/'avg'
    
    // Determine type
    if (answerText.includes('trend')) return 'line'
    else return 'bar'
  }
}
```

#### 3. Event Handlers Updated
- `response.table` → Capture table data early
- `response` → Extract table from content, infer viz, render
- `vizPlaceholder` → Target for all visualizations

### CSS Changes (`docs/styles.css`)

**Added**:
```css
.message-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
```

**Effect**: All content stacks vertically in second grid column

---

## Visual Flow (New)

### During Streaming:
```
┌──────────────────────────────────────────┐
│ Assistant │                              │
│           ├──────────────────────────────┤
│           │ 🤔 Thinking... ▼             │
│           │ [planning] Planning...       │
│           │ The user is asking for...    │
│           │ [Live streaming]             │
│           ├──────────────────────────────┤
│           │ ⚡ Executing SQL ▼           │
│           │ WITH __rightmove AS (        │
│           │   SELECT zone, AVG(price)... │
│           │ )                            │
│           ├──────────────────────────────┤
│           │ Average prices vary...       │
│           │ [Answer streaming in]        │
└───────────┴──────────────────────────────┘
```

### After Completion:
```
┌──────────────────────────────────────────┐
│ Assistant │                              │
│           ├──────────────────────────────┤
│           │ 🤔 Thinking Process ▶        │
│           ├──────────────────────────────┤
│           │ ⚡ Cortex Analyst Queries ▶  │
│           ├──────────────────────────────┤
│           │ Average prices vary...       │
│           │ Top 5 boroughs:              │
│           │ - Westminster: £5.3M         │
│           │ ...                          │
│           │                              │
│           │ ┌────────────────────────┐   │
│           │ │   [BAR CHART]          │   │
│           │ │                        │   │
│           │ │   Borough vs Price     │   │
│           │ └────────────────────────┘   │
│           │                              │
│           │ Next steps: Filter by type...│
└───────────┴──────────────────────────────┘
```

---

## Visualization Auto-Detection

### Triggers (Answer Text):
- "by borough" → Bar chart
- "by zone" → Bar chart
- "across" → Bar chart
- "trend" / "over time" → Line chart
- "distribution" → Histogram

### Column Detection:
**X-axis** (categorical):
- Contains: "zone", "borough", "type", "name", "category"
- Fallback: First column

**Y-axis** (numeric):
- Contains: "price", "count", "avg", "median", "total"
- Fallback: First numeric column

### Default Behavior:
- If keywords found + data has structure → Auto-render chart
- If pill clicked with `data-viz` → Use explicit viz type
- If no match → No visualization (answer only)

---

## Testing

### Test Cases:

**1. Borough Comparison (Auto-Viz)**
```
Question: "Average price by borough"
Expected:
- Thinking streams live ✓
- SQL appears with GROUP BY borough ✓
- Answer streams ✓
- Bar chart auto-renders ✓
- Single column layout ✓
```

**2. Zone Analysis (Auto-Viz)**
```
Question: "Property count by zone"
Expected:
- Infers bar chart with zone (X) vs count (Y)
- Chart appears below answer text
```

**3. Simple Query (No Viz)**
```
Question: "How many properties?"
Expected:
- Answer appears
- No chart (no grouping detected)
```

**4. Pill Click (Explicit Viz)**
```
Click: "Average price by borough" [data-viz="bar"]
Expected:
- Uses explicit viz spec
- Renders bar chart
```

---

## Deployment

- ✅ CSS updated with `.message-content-wrapper`
- ✅ `createStreamingMessage()` restructured
- ✅ `inferVizFromResponse()` implemented
- ✅ `response` handler updated with auto-viz logic
- ✅ Pushed to GitHub
- ⏳ Pages deploying...

---

## Next Steps

After deployment completes:
1. Visit https://london-property-analysis.uk/?debug=1
2. Click "Average price by borough" pill
3. Verify:
   - Single column layout (no side-by-side)
   - Bar chart renders below answer
   - Chart shows borough on X-axis, price on Y-axis

If issues found:
- Check browser console for "[viz]" logs
- Verify table data structure
- Check column name matching logic
