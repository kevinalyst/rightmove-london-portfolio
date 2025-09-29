# Snowflake PAT Token Setup Guide for External API Access

## Overview
Snowflake's Programmatic Access Tokens (PATs) provide a secure, password-free authentication mechanism for REST APIs. This guide covers setting up PAT for external services like Cloudflare Workers.

**Important**: Snowflake is phasing out single-factor password authentication by November 2025, making PATs the recommended approach for programmatic access.

## Prerequisites

### 1. Network Policy Requirements ⚠️
PAT authentication **requires** a network policy with network rules:
- For service users (TYPE=SERVICE): Network policy is mandatory
- For human users (TYPE=PERSON): Can generate token without policy, but need policy to use it

### 2. Authentication Policy Requirements
An authentication policy must be configured to allow PAT usage.

## Step-by-Step Setup

### Step 1: Create Network Policy and Rules
```sql
-- Create a network rule (adjust IP ranges for your use case)
CREATE OR REPLACE NETWORK RULE allow_cloudflare_ips
  TYPE = IPV4
  VALUE_LIST = ('0.0.0.0/0')  -- For testing; restrict to Cloudflare IPs in production
  MODE = INGRESS
  COMMENT = 'Allow Cloudflare Workers';

-- Create network policy
CREATE OR REPLACE NETWORK POLICY cloudflare_api_policy
  ALLOWED_NETWORK_RULE_LIST = ('allow_cloudflare_ips')
  COMMENT = 'Policy for Cloudflare Worker API access';
```

### Step 2: Create Authentication Policy
```sql
-- Create authentication policy that allows PAT
CREATE OR REPLACE AUTHENTICATION POLICY pat_auth_policy
  AUTHENTICATION_METHODS = ('PROGRAMMATIC_ACCESS_TOKEN')
  COMMENT = 'Allow PAT authentication for API access';
```

### Step 3: Create a Service User (Recommended)
```sql
-- Create a service user specifically for your API
CREATE OR REPLACE USER cloudflare_api_user
  TYPE = SERVICE
  COMMENT = 'Service user for Cloudflare Worker API access';

-- Grant necessary roles
GRANT ROLE <your_role> TO USER cloudflare_api_user;

-- Apply policies to the user
ALTER USER cloudflare_api_user 
  SET NETWORK_POLICY = cloudflare_api_policy
  AUTHENTICATION_POLICY = pat_auth_policy;
```

### Step 4: Generate PAT Token
```sql
-- Generate a PAT with specific settings
DECLARE
  pat_secret STRING;
  pat_token STRING;
BEGIN
  CALL SYSTEM$GENERATE_PROGRAMMATIC_ACCESS_TOKEN(
    USER_NAME => 'cloudflare_api_user',
    -- Set validity period (max 90 days)
    VALIDITY_DAYS => 90,
    -- Assign to specific role
    SESSION_ROLE => '<your_role>',
    COMMENT => 'Token for Cloudflare Worker'
  ) INTO :pat_secret, :pat_token;
  
  -- IMPORTANT: Save these values securely!
  SELECT 
    :pat_secret AS token_secret,
    :pat_token AS token_identifier;
END;
```

### Step 5: Configure Worker with PAT

In your Cloudflare Worker:
1. Store the `token_secret` as a Worker secret:
   ```bash
   wrangler secret put SNOWFLAKE_PAT_TOKEN
   # Paste the token_secret value
   ```

2. Update your Worker code to use proper headers:
   ```javascript
   const headers = {
     'Content-Type': 'application/json',
     'Accept': 'application/json',
     'Authorization': `Bearer ${token}`,  // Use Bearer prefix
     'X-Snowflake-Authorization-Token-Type': 'PROGRAMMATIC_ACCESS_TOKEN'
   };
   ```

## Security Best Practices

### 1. IP Restriction
Replace the wide-open IP range with Cloudflare's actual IP ranges:
```sql
-- Get Cloudflare IPv4 ranges from: https://www.cloudflare.com/ips-v4
CREATE OR REPLACE NETWORK RULE allow_cloudflare_ips
  TYPE = IPV4
  VALUE_LIST = (
    '173.245.48.0/20',
    '103.21.244.0/22',
    '103.22.200.0/22',
    -- Add all Cloudflare IP ranges
  )
  MODE = INGRESS;
```

### 2. Role-Based Access
Create a custom role with minimal permissions:
```sql
CREATE OR REPLACE ROLE cortex_api_role;

-- Grant only necessary permissions
GRANT USAGE ON DATABASE SNOWFLAKE_INTELLIGENCE TO ROLE cortex_api_role;
GRANT USAGE ON SCHEMA SNOWFLAKE_INTELLIGENCE.AGENTS TO ROLE cortex_api_role;
GRANT USAGE ON CORTEX AGENT SNOWFLAKE_INTELLIGENCE.AGENTS.RIGHTMOVE_ANALYSIS TO ROLE cortex_api_role;

-- For Cortex Search
GRANT USAGE ON DATABASE RIGHTMOVE_LONDON_SELL TO ROLE cortex_api_role;
GRANT USAGE ON SCHEMA RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF TO ROLE cortex_api_role;
GRANT USAGE ON CORTEX SEARCH SERVICE RIGHTMOVE_LONDON_SELL.CLOUDRUN_DXLVF.UNSTRUCTURED_RAG TO ROLE cortex_api_role;

-- Assign to user
GRANT ROLE cortex_api_role TO USER cloudflare_api_user;
```

### 3. Token Management
- Set expiration dates (max 90 days)
- Rotate tokens regularly
- Monitor token usage
- Revoke tokens when no longer needed:
  ```sql
  CALL SYSTEM$REVOKE_PROGRAMMATIC_ACCESS_TOKEN('<token_identifier>');
  ```

## Troubleshooting

### Common Issues
1. **"PAT_INVALID" error**: Check network policy and user existence
2. **526 error**: Verify token format and headers
3. **403 error**: Check role permissions

### Verify Token
Test the token locally first:
```bash
curl -X POST https://<account>.snowflakecomputing.com/api/v2/databases \
  -H "Authorization: Bearer <token_secret>" \
  -H "X-Snowflake-Authorization-Token-Type: PROGRAMMATIC_ACCESS_TOKEN"
```

### List Active Tokens
```sql
-- View all active tokens for a user
SHOW PROGRAMMATIC ACCESS TOKENS FOR USER cloudflare_api_user;
```

## References
- [Snowflake PAT Documentation](https://docs.snowflake.com/en/user-guide/programmatic-access-tokens)
- [Snowflake REST API Authentication](https://docs.snowflake.com/en/developer-guide/snowflake-rest-api/authentication)
- [Network Policies Guide](https://docs.snowflake.com/en/user-guide/network-policies)
