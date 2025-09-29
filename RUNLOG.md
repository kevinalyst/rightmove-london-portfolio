# Cloudflare Worker 503 Diagnosis Runlog

## Issue
HTTP 503 errors when Cloudflare Worker calls Snowflake Cortex Agent

## Success Criteria
- [x] Create RUNLOG.md to track findings
- [ ] /api/chat returns 200 with valid JSON for mode:"analyst" 
- [ ] /api/chat returns 200 with valid JSON for mode:"search"
- [ ] OPTIONS /api/chat returns 204 with proper CORS headers
- [ ] /api/health returns 200 JSON {ok:true}
- [ ] Frontend chat can send query end-to-end with no 5xx

## Findings

### Step 1: Initial Code Review
**Time:** 2025-09-29 10:00
**Hypothesis:** Need to understand current Worker implementation
**Test:** Read Worker code and wrangler.toml
**Result:** Found issues:
- No /api/health endpoint implemented
- No support for mode:"analyst" vs mode:"search" (only agent endpoint)
- No retry logic or timeout control
- Generic 503 error returned for all Cortex errors
- SNOWFLAKE_PAT_TOKEN not in wrangler.toml (must be secret)

### Step 2: Check Worker Logs & Reproduce
**Time:** 2025-09-29 10:05
**Hypothesis:** Need to see actual error messages from production
**Test:** Query Worker observability logs for recent errors
**Result:** 
- Worker is deployed on different account (axiuluo40@gmail.com)
- Worker URL: https://london-portfolio-backend.axiuluo40.workers.dev
- Pages domain (london-property-analysis.uk) returns 405 - routing issue
- Worker returns 503 "Cortex backend currently unavailable"
- SNOWFLAKE_PAT_TOKEN is configured as secret

### Step 3: Add Debug Logging & Health Check
**Time:** 2025-09-29 10:15
**Hypothesis:** Need better error visibility and health check endpoint
**Test:** Add console.error with full error details, implement /api/health
**Result:** 
- Added /api/health endpoint ✓
- Added retry logic with exponential backoff ✓
- Added mode support (analyst/search) ✓
- Enhanced error logging with correlation IDs ✓
- Worker deployed successfully

### Step 4: Test Updated Worker
**Time:** 2025-09-29 10:20
**Hypothesis:** Worker should now handle requests properly
**Test:** Test health check and chat endpoints
**Result:**
- Health check works: GET /api/health returns 200 with config
- CORS OPTIONS works: returns 204 with proper headers
- Chat endpoint returns 526 error (Invalid SSL certificate)
- Error suggests Snowflake SSL cert validation issue

### Step 5: Diagnose SSL/TLS Issue
**Time:** 2025-09-29 10:25
**Hypothesis:** Cloudflare Worker may have issues with Snowflake's SSL certificate
**Test:** Use MCP to test direct Snowflake connectivity
**Result:** 
- MCP successfully connected to Snowflake Cortex Agent ✓
- Confirms credentials and agent are working correctly
- 526 error is specific to Worker environment

### Step 6: Pages Routing Issue
**Time:** 2025-09-29 10:30
**Hypothesis:** Pages domain not routing /api/* to Worker
**Test:** Compare Pages domain vs Worker domain responses
**Result:**
- Worker URL works: https://london-portfolio-backend.axiuluo40.workers.dev
- Pages domain /api/health returns HTML (not JSON) - routing issue confirmed
- Pages is serving static files instead of routing to Worker

### Step 7: Fix - Update Frontend to Use Worker URL
**Time:** 2025-09-29 10:35
**Hypothesis:** Update frontend to point directly to Worker URL as immediate fix
**Test:** Update index.html backend URL and test
**Result:** Frontend already pointing to Worker URL

### Step 8: Detailed Error Analysis
**Time:** 2025-09-29 10:40
**Hypothesis:** 526 error might be from Snowflake, not Cloudflare
**Test:** Add detailed logging and examine response
**Result:**
- Error IS coming from Snowflake API (status: 526, body: "error code: 526")
- URL: https://KA89655.eu-west2.gcp.snowflakecomputing.com/api/v0/agents/...
- Snowflake is returning HTTP 526 which is unusual
- No request ID returned from Snowflake

### Step 9: Verify Snowflake URL Format
**Time:** 2025-09-29 10:45
**Hypothesis:** Snowflake account URL might be incorrectly formatted
**Test:** Use MCP to verify correct endpoint format
**Result:** 
- Tried both v0 and v2 API endpoints - both return 526
- URL format appears correct: https://KA89655.eu-west2.gcp.snowflakecomputing.com
- Error is definitely coming from Snowflake (not Cloudflare)

### Step 10: Root Cause - 526 Error Investigation
**Time:** 2025-09-29 10:50
**Hypothesis:** Snowflake is returning 526 due to authentication or configuration issue
**Test:** Research and test different authentication methods
**Result:** 
- Tried both "Snowflake" and "Bearer" authorization header prefixes
- Both return same 526 error from Snowflake
- MCP tool successfully connects, so credentials are valid

## Summary of Findings

### What Works
✅ Worker deployed and accessible at https://london-portfolio-backend.axiuluo40.workers.dev
✅ Health check endpoint implemented: GET /api/health returns 200
✅ CORS properly configured: OPTIONS /api/chat returns 204
✅ Mode support added (analyst/search)
✅ Retry logic and timeout control implemented
✅ Enhanced error logging shows Snowflake is returning 526

### Root Cause
❌ Snowflake API is returning HTTP 526 "error code: 526"
❌ This is NOT a Cloudflare SSL error - it's coming from Snowflake itself
❌ The 526 error occurs for both v0 and v2 API endpoints
❌ Both "Snowflake" and "Bearer" auth prefixes fail

### Blocking Issue
The 526 error from Snowflake is preventing the Worker from functioning. This appears to be:
1. An authentication/authorization issue with the PAT token
2. A configuration issue with the Snowflake agent
3. A network/firewall restriction

### Recommended Next Steps
1. Verify the SNOWFLAKE_PAT_TOKEN is valid and has correct permissions
2. Check if the agent RIGHTMOVE_ANALYSIS exists in SNOWFLAKE_INTELLIGENCE.AGENTS
3. Test the exact same request using curl directly (not through Worker)
4. Contact Snowflake support about the 526 error code
5. Consider using the SQL API endpoint instead of Cortex Agents as a fallback

