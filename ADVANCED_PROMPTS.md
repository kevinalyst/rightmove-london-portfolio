# Advanced Pill Button Prompts - Implementation

**Date**: September 30, 2025  
**Status**: ✅ DEPLOYED

## Challenge
Replace simple pill buttons with complex analytical prompts that are too long for button display.

## Solution: Hidden Full Prompts

### Implementation Strategy
1. **Short labels** on buttons (fit visually)
2. **Full prompts** in `data-prompt` attribute  
3. **Click populates** textarea for editing
4. **User controls** when to send

---

## New Pill Buttons

### 1. Best Space Value Properties
**Button Label**: "Best space value properties"  
**Full Prompt**:
```
Use Cortex Analyst. Produce a dataset for a table: columns RIGHTMOVE_ID, URL, AREA, PROPERTY_TYPE, BEDROOMS, SIZE_SQM, PRICE_VALUE, PRICE_PER_SQM. Exclude rows with null area, exclude land in property_type; winsorize outliers at the 1st/99th percentile for price_per_sqm. Then return a ranking of the top 20 best space value (lowest price_per_sqm) with bedrooms shown. Round prices with £ formatting and £/sqm to 0 decimals.
```

**Analysis Type**: Analyst (table)  
**Purpose**: Find best value properties by price per square meter

### 2. Median £/sqm by Area & Type  
**Button Label**: "Median £/sqm by area & type"  
**Full Prompt**:
```
Use Cortex Analyst, compute the median price_per_sqm by area and property_type. Return a tidy table with columns: area, property_type, listings_count, median_ppsqm. Exclude groups with listings_count < 50 and rows missing area. Also append a second table: the top 10 lowest median_ppsqm combinations (best value). Round £/sqm to 0 decimals. Creates: grouped bar charts
```

**Analysis Type**: Analyst (bar chart)  
**Purpose**: Market analysis by location and property type

### 3. Investment Opportunity Properties
**Button Label**: "Investment opportunity properties"  
**Full Prompt**:
```
Use Cortex Search, search descriptions/features/history for phrases like up-and-coming, emerging hotspot, regeneration, investment potential, Crossrail/Elizabeth line, new transport links, planned development, rental yield. Return up to 20 candidate rightmove_id, then filter out land in property type and rank by lowest price_per_sqm. Output the top 20 with columns: RIGHTMOVE_ID, URL, AREA, property_type, bedrooms, price_value, price_per_sqm, matched_snippet (a short snippet highlighting the signal).
```

**Analysis Type**: Search (table)  
**Purpose**: Find properties with investment signals

### 4. Renovation Projects & Risks
**Button Label**: "Renovation projects & risks"  
**Full Prompt**:
```
Use Cortex Search, Find listings mentioning transformation/renovation potential using phrases like modernisation required, refurbishment, fixer-upper, extension/loft potential, STPP, redevelopment, project, auction, cash buyers. Also flag risk cues like short lease, non-standard construction, EWS1, ex-local authority, structural issues. Return up to 20 candidates rightmove_id, filter out land in property type, and output the top 10 by lowest price_per_sqm with columns: RIGHTMOVE_ID, URL, property_type, bedrooms, size_sqm, price_value, price_per_sqm, opportunity_terms, risk_terms, matched_snippet. List any matched opportunity/risk terms in those two columns.
```

**Analysis Type**: Search (table)  
**Purpose**: Find renovation opportunities with risk assessment

---

## Technical Implementation

### HTML Structure
```html
<button class="pill" 
        data-mode="analyst" 
        data-viz="table"
        data-prompt="[FULL COMPLEX PROMPT HERE]">
  Short Button Label
</button>
```

### JavaScript Handler
```javascript
function handlePrepopClick(e){
  const btn = e.target.closest('.pill');
  const fullPrompt = btn.getAttribute('data-prompt') || btn.textContent.trim();
  const mode = btn.getAttribute('data-mode');
  const viz = btn.getAttribute('data-viz');
  
  // Populate textarea with full prompt
  els.input.value = fullPrompt;
  els.input.focus(); // Ready for editing
  
  // Don't auto-send - let user review/edit
  console.log('[pill] Populated prompt:', fullPrompt.substring(0, 100) + '...');
}
```

### Behavior Changes
**Before**: Click → Auto-send query  
**After**: Click → Populate textarea → User edits → User clicks Ask

---

## User Experience Flow

### Step 1: Click Pill Button
```
User clicks: "Best space value properties"
```

### Step 2: Textarea Population
```
Textarea fills with:
"Use Cortex Analyst. Produce a dataset for a table: columns RIGHTMOVE_ID, URL, AREA, PROPERTY_TYPE, BEDROOMS, SIZE_SQM, PRICE_VALUE, PRICE_PER_SQM. Exclude rows with null area, exclude land in property_type; winsorize outliers at the 1st/99th percentile for price_per_sqm..."

Cursor focuses in textarea for immediate editing
```

### Step 3: User Control
```
User can:
- Edit the prompt (modify parameters, add filters)
- Send as-is (click Ask)
- Clear and write new prompt
```

### Step 4: Execution
```
Click Ask → Streaming begins
Full complex analysis executes
Tables/charts render with responsive sizing
```

---

## Prompt Categories

### Analyst Mode (SQL Analysis):
1. **Value Analysis**: Best space value (price_per_sqm ranking)
2. **Market Analysis**: Median prices by area/type with charts

### Search Mode (Semantic Search):
3. **Investment Signals**: Up-and-coming areas, transport links
4. **Renovation Opportunities**: Fixer-uppers with risk assessment

**Coverage**: Comprehensive property investment analysis workflow

---

## Advanced Features

### Data Quality:
- Winsorization (1st/99th percentiles)
- Null handling (exclude missing data)
- Filtering (exclude land, minimum group sizes)

### Output Formatting:
- £ formatting for prices
- 0 decimal places for £/sqm
- Proper column naming
- Risk/opportunity categorization

### Hybrid Analysis:
- Search → Candidate IDs → Analyst filtering
- Semantic matching + SQL ranking
- Multiple output tables

---

## Deployment

**Changes Made**:
- 4 new pill buttons with complex prompts
- Updated click handler (populate, don't auto-send)
- Added textarea focus for editing
- Maintained all visualization specs

**Files Modified**:
- `docs/index.html` - New button definitions
- `docs/app.js` - Updated click handler logic

**Compatibility**: All existing features preserved

---

## Testing

**Live Site**: https://london-property-analysis.uk/?debug=1

**Test Steps**:
1. Click "Best space value properties"
2. See full complex prompt in textarea
3. Edit if desired (e.g., change "top 20" to "top 10")
4. Click Ask to execute
5. Watch streaming analysis with tables/charts

**Expected**: Professional-grade property analysis with editable advanced prompts!

**The pill buttons now provide sophisticated analytical capabilities while maintaining clean UI design.** 🎯✨
