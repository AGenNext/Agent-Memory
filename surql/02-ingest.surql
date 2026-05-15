-- =====================================================
-- INGEST: Sample Data and Graph Building
-- =====================================================

-- Create Articles with embeddings (using base64 encoded vectors for demo)
DEFINE article:auth SET 
    id = "article:auth",
    title = "Authentication Setup Guide",
    category = "getting-started",
    content = "This guide covers setting up authentication for the Acme Platform. Start by creating an API key in the dashboard, then configure your OAuth provider. For SSO integration, contact enterprise support.";

DEFINE article:api_keys SET 
    id = "article:api_keys",
    title = "Managing API Keys",
    category = "security",
    content = "API keys provide programmatic access to the Acme Platform. Generate keys with appropriate scopes. Rotate keys regularly and never share them publicly. Use environment variables for key storage.";

DEFINE article:webhooks SET 
    id = "article:webhooks",
    title = "Webhook Configuration",
    category = "integrations",
    content = "Webhooks notify your system of events in real-time. Configure endpoints in dashboard. Supported events include user.created, order.completed, subscription.updated. Set retry policy for failed deliveries.";

-- Create Products
DEFINE product:auth SET 
    id = "product:auth",
    name = "Auth Pro",
    description = "Enterprise authentication service with SSO and MFA support",
    version = "2.1.0";

DEFINE product:api SET 
    id = "product:api",
    name = "API Gateway",
    description = "Unified API management with rate limiting and analytics",
    version = "3.0.0";

DEFINE product:webhooks SET 
    id = "product:webhooks",
    name = "Webhook Handler",
    description = "Event delivery and retry system",
    version = "1.5.0";

-- Create Customers
DEFINE customer:acme SET 
    id = "customer:acme",
    name = "Acme Corp",
    email = "support@acme.com",
    plan = "enterprise";

DEFINE customer:globex SET 
    id = "customer:globex",
    name = "Globex Inc",
    email = "tech@globex.com",
    plan = "business";

-- Create Tickets
DEFINE ticket:101 SET 
    id = "ticket:101",
    subject = "Cannot authenticate via SSO",
    description = "Users report unable to login with SSO after update",
    status = "open",
    priority = "high";

DEFINE ticket:102 SET 
    id = "ticket:102",
    subject = "API rate limit exceeded",
    description = "Getting 429 errors on production API",
    status = "resolved",
    priority = "medium";

-- Create Solutions
DEFINE solution:001 SET 
    id = "solution:001",
    title = "Clear browser cache and cookies",
    steps = "1. Clear browser cache\n2. Delete cookies for domain\n3. Try incognito mode\n4. Contact IT if persists",
    verified = true,
    weight = 0.9;

DEFINE solution:002 SET 
    id = "solution:002",
    title = "Update API client version",
    steps = "1. Check current version\n2. Update to latest client library\n3. Regenerate API key\n4. Test with staging environment",
    verified = true,
    weight = 0.85;

-- Graph Relations
RELATE article:auth -> references -> product:auth;
RELATE article:api_keys -> references -> product:api;
RELATE article:webhooks -> references -> product:webhooks;

RELATE ticket:101 -> about -> product:auth;
RELATE ticket:102 -> about -> product:api;

RELATE customer:acme -> authored -> ticket:101;
RELATE customer:globex -> authored -> ticket:102;

RELATE ticket:101 -> resolved_by -> solution:001 SET weight = 0.7;
RELATE ticket:102 -> resolved_by -> solution:002 SET weight = 0.9;

RELATE product:auth -> depends_on -> product:api;
RELATE product:webhooks -> depends_on -> product:api;