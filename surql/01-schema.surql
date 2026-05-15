-- =====================================================
-- SCHEMA: Knowledge Graph Tables and Relations
-- =====================================================

-- Articles table with vector embedding
DEFINE TABLE article SCHEMAFULL;
DEFINE FIELD id ON article TYPE string;
DEFINE FIELD title ON article TYPE string;
DEFINE FIELD category ON article TYPE string;
DEFINE FIELD content ON article TYPE string;
DEFINE FIELD embedding ON article TYPE array<float>(512);
DEFINE FIELD created ON article TYPE datetime DEFAULT time::now();

-- Products table
DEFINE TABLE product SCHEMAFULL;
DEFINE FIELD id ON product TYPE string;
DEFINE FIELD name ON product TYPE string;
DEFINE FIELD description ON product TYPE string;
DEFINE FIELD version ON product TYPE string;

-- Customers table
DEFINE TABLE customer SCHEMAFULL;
DEFINE FIELD id ON customer TYPE string;
DEFINE FIELD name ON customer TYPE string;
DEFINE FIELD email ON customer TYPE string;
DEFINE FIELD plan ON customer TYPE string;

-- Support tickets table
DEFINE TABLE ticket SCHEMAFULL;
DEFINE FIELD id ON ticket TYPE string;
DEFINE FIELD subject ON ticket TYPE string;
DEFINE FIELD description ON ticket TYPE string;
DEFINE FIELD status ON ticket TYPE string;
DEFINE FIELD priority ON ticket TYPE string;
DEFINE FIELD created ON ticket TYPE datetime DEFAULT time::now();

-- Solutions table
DEFINE TABLE solution SCHEMAFULL;
DEFINE FIELD id ON solution TYPE string;
DEFINE FIELD title ON solution TYPE string;
DEFINE FIELD steps ON solution TYPE string;
DEFINE FIELD verified ON solution TYPE bool;
DEFINE FIELD weight ON solution TYPE float;
DEFINE FIELD valid_until ON solution TYPE option<datetime>;

-- Graph Relations
DEFINE TABLE references SCHEMAFULL;
DEFINE FIELD in ON references TYPE record(article);
DEFINE FIELD out ON references TYPE record(product);

DEFINE TABLE related_to SCHEMAFULL;
DEFINE FIELD in ON related_to TYPE record(article);
DEFINE FIELD out ON related_to TYPE record(article);

DEFINE TABLE about SCHEMAFULL;
DEFINE FIELD in ON about TYPE record(ticket);
DEFINE FIELD out ON about TYPE record(product);

DEFINE TABLE resolved_by SCHEMAFULL;
DEFINE FIELD in ON resolved_by TYPE record(ticket);
DEFINE FIELD out ON resolved_by TYPE record(solution);
DEFINE FIELD weight ON resolved_by TYPE float DEFAULT 1.0;

DEFINE TABLE authored SCHEMAFULL;
DEFINE FIELD in ON authored TYPE record(ticket);
DEFINE FIELD out ON authored TYPE record(customer);

DEFINE TABLE depends_on SCHEMAFULL;
DEFINE FIELD in ON depends_on TYPE record(product);
DEFINE FIELD out ON depends_on TYPE record(product);

-- Decision + Response Tracing Tables
DEFINE TABLE decision_step SCHEMAFULL;
DEFINE FIELD session ON decision_step TYPE string;
DEFINE FIELD step ON decision_step TYPE int;
DEFINE FIELD action ON decision_step TYPE string;
DEFINE FIELD tool ON decision_step TYPE option<string>;
DEFINE FIELD tool_args ON decision_step TYPE option<string>;
DEFINE FIELD result_summary ON decision_step TYPE option<string>;
DEFINE FIELD created ON decision_step TYPE datetime DEFAULT time::now();

DEFINE TABLE led_to SCHEMAFULL;
DEFINE FIELD in ON led_to TYPE record(decision_step);
DEFINE FIELD out ON led_to TYPE record(decision_step);

DEFINE TABLE retrieval_trace SCHEMAFULL;
DEFINE FIELD session ON retrieval_trace TYPE string;
DEFINE FIELD method ON retrieval_trace TYPE string;
DEFINE FIELD query_text ON retrieval_trace TYPE string;
DEFINE FIELD query_embedding ON retrieval_trace TYPE array<float>(512);
DEFINE FIELD entity_ids ON retrieval_trace TYPE array<string>;
DEFINE FIELD distances ON retrieval_trace TYPE array<float>;
DEFINE FIELD created ON retrieval_trace TYPE datetime DEFAULT time::now();

DEFINE TABLE retrieved SCHEMAFULL;
DEFINE FIELD in ON retrieved TYPE record(decision_step);
DEFINE FIELD out ON retrieved TYPE record(retrieval_trace);

DEFINE TABLE used SCHEMAFULL;
DEFINE FIELD in ON used TYPE record(retrieval_trace);
DEFINE FIELD out ON used TYPE record;

DEFINE TABLE response_trace SCHEMAFULL;
DEFINE FIELD session ON response_trace TYPE string;
DEFINE FIELD query ON response_trace TYPE string;
DEFINE FIELD query_embedding ON response_trace TYPE array<float>(512);
DEFINE FIELD response ON response_trace TYPE string;
DEFINE FIELD model ON response_trace TYPE string;
DEFINE FIELD token_count ON response_trace TYPE option<int>;
DEFINE FIELD created ON response_trace TYPE datetime DEFAULT time::now();

DEFINE TABLE produced SCHEMAFULL;
DEFINE FIELD in ON produced TYPE record(decision_step);
DEFINE FIELD out ON produced TYPE record(response_trace);

-- Vector Indexes
DEFINE ANALYZER article_analyzer TOKENIZERS blank, classics FILTERS ascii, lowercase, portStem;

DEFINE INDEX article_embedding ON article FIELDS embedding MTREE dimensionality 512;

DEFINE INDEX decision_query_embedding ON response_trace FIELDS query_embedding MTREE dimensionality 512;

-- =====================================================
-- EXTENDED SCHEMA: Additional Entity Tables
-- =====================================================

-- User table - End users of the system
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD id ON user TYPE string;
DEFINE FIELD name ON user TYPE string;
DEFINE FIELD email ON user TYPE string;
DEFINE FIELD role ON user TYPE string DEFAULT "user";
DEFINE FIELD preferences ON user TYPE option<object>;
DEFINE FIELD created ON user TYPE datetime DEFAULT time::now();

-- Session table - Agent conversation sessions
DEFINE TABLE session SCHEMAFULL;
DEFINE FIELD id ON session TYPE string;
DEFINE FIELD user_id ON session TYPE record(user);
DEFINE FIELD status ON session TYPE string DEFAULT "active";
DEFINE FIELD started ON session TYPE datetime DEFAULT time::now();
DEFINE FIELD ended ON session TYPE option<datetime>;
DEFINE FIELD rating ON session TYPE option<int>;

-- Tool call table - Individual tool executions
DEFINE TABLE tool_call SCHEMAFULL;
DEFINE FIELD id ON tool_call TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD step ON tool_call TYPE int;
DEFINE FIELD tool_name ON tool_call TYPE string;
DEFINE FIELD arguments ON tool_call TYPE object;
DEFINE FIELD result ON tool_call TYPE string;
DEFINE FIELD duration_ms ON tool_call TYPE int;
DEFINE FIELD created ON tool_call TYPE datetime DEFAULT time::now();

-- Feedback table - User ratings/thumbnails
DEFINE TABLE feedback SCHEMAFULL;
DEFINE FIELD id ON feedback TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD response ON response_trace TYPE record(response_trace);
DEFINE FIELD rating ON feedback TYPE int;
DEFINE FIELD comment ON feedback TYPE option<string>;
DEFINE FIELD created ON feedback TYPE datetime DEFAULT time::now();

-- Entity table - Extracted entities from conversations
DEFINE TABLE entity SCHEMAFULL;
DEFINE FIELD id ON entity TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD type ON entity TYPE string;
DEFINE FIELD name ON entity TYPE string;
DEFINE FIELD properties ON entity TYPE object;
DEFINE FIELD confidence ON entity TYPE float DEFAULT 1.0;
DEFINE FIELD created ON entity TYPE datetime DEFAULT time::now();

-- Relationship table - Discovered entity relationships
DEFINE TABLE relationship SCHEMAFULL;
DEFINE FIELD id ON relationship TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD from_entity ON relationship TYPE record(entity);
DEFINE FIELD to_entity ON relationship TYPE record(entity);
DEFINE FIELD relation_type ON relationship TYPE string;
DEFINE FIELD confidence ON relationship TYPE float DEFAULT 1.0;
DEFINE FIELD created ON relationship TYPE datetime DEFAULT time::now();

-- Knowledge table - General knowledge facts
DEFINE TABLE knowledge SCHEMAFULL;
DEFINE FIELD id ON knowledge TYPE string;
DEFINE FIELD fact ON knowledge TYPE string;
DEFINE FIELD category ON knowledge TYPE string;
DEFINE FIELD source ON knowledge TYPE string;
DEFINE FIELD verified ON knowledge TYPE bool DEFAULT false;
DEFINE FIELD embedding ON knowledge TYPE array<float>(512);
DEFINE FIELD created ON knowledge TYPE datetime DEFAULT time::now();

-- Context table - Retrieved context chunks
DEFINE TABLE context_chunk SCHEMAFULL;
DEFINE FIELD id ON context_chunk TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD source_type ON context_chunk TYPE string;
DEFINE FIELD source_id ON context_chunk TYPE string;
DEFINE FIELD content ON context_chunk TYPE string;
DEFINE FIELD embedding ON context_chunk TYPE array<float>(512);
DEFINE FIELD relevance ON context_chunk TYPE float;
DEFINE FIELD created ON context_chunk TYPE datetime DEFAULT time::now();

-- Additional Graph Relations
DEFINE TABLE creates SCHEMAFULL;
DEFINE FIELD in ON creates TYPE record(user);
DEFINE FIELD out ON creates TYPE record(session);

DEFINE TABLE has SCHEMAFULL;
DEFINE FIELD in ON has TYPE record(session);
DEFINE FIELD out ON has TYPE record(decision_step);

DEFINE TABLE executes SCHEMAFULL;
DEFINE FIELD in ON executes TYPE record(decision_step);
DEFINE FIELD out ON executes TYPE record(tool_call);

DEFINE TABLE rates SCHEMAFULL;
DEFINE FIELD in ON rates TYPE record(session);
DEFINE FIELD out ON rates TYPE record(feedback);

DEFINE TABLE responded_by SCHEMAFULL;
DEFINE FIELD in ON responded_by TYPE record(response_trace);
DEFINE FIELD out ON responded_by TYPE record(feedback);

DEFINE TABLE has_entity SCHEMAFULL;
DEFINE FIELD in ON has_entity TYPE record(session);
DEFINE FIELD out ON has_entity TYPE record(entity);

DEFINE TABLE relates_to_entity SCHEMAFULL;
DEFINE FIELD in ON relates_to_entity TYPE record(entity);
DEFINE FIELD out ON relates_to_entity TYPE record(relationship);

DEFINE TABLE has_chunk SCHEMAFULL;
DEFINE FIELD in ON has_chunk TYPE record(session);
DEFINE FIELD out ON has_chunk TYPE record(context_chunk);

DEFINE TABLE references_knowledge SCHEMAFULL;
DEFINE FIELD in ON references_knowledge TYPE record(context_chunk);
DEFINE FIELD out ON references_knowledge TYPE record(knowledge);

-- Vector Indexes for new tables
DEFINE INDEX knowledge_embedding ON knowledge FIELDS embedding MTREE dimensionality 512;
DEFINE INDEX context_embedding ON context_chunk FIELDS embedding MTREE dimensionality 512;
DEFINE INDEX entity_name ON entity FIELDS name;-- =====================================================
-- MORE TABLES: Agent, Messaging, Analytics
-- =====================================================

-- Agent table - Different AI agents with configs
DEFINE TABLE agent SCHEMAFULL;
DEFINE FIELD id ON agent TYPE string;
DEFINE FIELD name ON agent TYPE string;
DEFINE FIELD model ON agent TYPE string;
DEFINE FIELD provider ON agent TYPE string DEFAULT "openai";
DEFINE FIELD config ON agent TYPE object;
DEFINE FIELD system_prompt ON agent TYPE string;
DEFINE FIELD tools ON agent TYPE array<string>;
DEFINE FIELD status ON agent TYPE string DEFAULT "active";
DEFINE FIELD created ON agent TYPE datetime DEFAULT time::now();

-- Message table - Chat messages
DEFINE TABLE message SCHEMAFULL;
DEFINE FIELD id ON message TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD role ON message TYPE string;
DEFINE FIELD content ON message TYPE string;
DEFINE FIELD embedding ON message TYPE array<float>(512);
DEFINE FIELD tokens ON message TYPE option<int>;
DEFINE FIELD created ON message TYPE datetime DEFAULT time::now();

-- Conversation table - Multi-turn conversations
DEFINE TABLE conversation SCHEMAFULL;
DEFINE FIELD id ON conversation TYPE string;
DEFINE FIELD title ON conversation TYPE string;
DEFINE FIELD agent ON conversation TYPE record(agent);
DEFINE FIELD user ON conversation TYPE record(user);
DEFINE FIELD status ON conversation TYPE string DEFAULT "active";
DEFINE FIELD message_count ON conversation TYPE int DEFAULT 0;
DEFINE FIELD created ON conversation TYPE datetime DEFAULT time::now();
DEFINE FIELD updated ON conversation TYPE datetime DEFAULT time::now();

-- Attachment table - File attachments
DEFINE TABLE attachment SCHEMAFULL;
DEFINE FIELD id ON attachment TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD message ON message TYPE record(message);
DEFINE FIELD filename ON attachment TYPE string;
DEFINE FIELD content_type ON attachment TYPE string;
DEFINE FIELD size ON attachment TYPE int;
DEFINE FIELD url ON attachment TYPE string;
DEFINE FIELD created ON attachment TYPE datetime DEFAULT time::now();

-- Tool table - Available tools/function definitions
DEFINE TABLE tool SCHEMAFULL;
DEFINE FIELD id ON tool TYPE string;
DEFINE FIELD name ON tool TYPE string;
DEFINE FIELD description ON tool TYPE string;
DEFINE FIELD schema ON tool TYPE object;
DEFINE FIELD handler ON tool TYPE string;
DEFINE FIELD enabled ON tool TYPE bool DEFAULT true;
DEFINE FIELD created ON tool TYPE datetime DEFAULT time::now();

-- Prompt template table - Prompt templates
DEFINE TABLE prompt_template SCHEMAFULL;
DEFINE FIELD id ON prompt_template TYPE string;
DEFINE FIELD name ON prompt_template TYPE string;
DEFINE FIELD template ON prompt_template TYPE string;
DEFINE FIELD variables ON prompt_template TYPE array<string>;
DEFINE FIELD version ON prompt_template TYPE int DEFAULT 1;
DEFINE FIELD created ON prompt_template TYPE datetime DEFAULT time::now();

-- Cache table - Cached responses
DEFINE TABLE cache SCHEMAFULL;
DEFINE FIELD id ON cache TYPE string;
DEFINE FIELD key ON cache TYPE string;
DEFINE FIELD value ON cache TYPE string;
DEFINE FIELD hash ON cache TYPE string;
DEFINE FIELD ttl ON cache TYPE int;
DEFINE FIELD hit_count ON cache TYPE int DEFAULT 0;
DEFINE FIELD created ON cache TYPE datetime DEFAULT time::now();
DEFINE FIELD expires ON cache TYPE datetime;

-- Workflow table - Agent workflow definitions
DEFINE TABLE workflow SCHEMAFULL;
DEFINE FIELD id ON workflow TYPE string;
DEFINE FIELD name ON workflow TYPE string;
DEFINE FIELD description ON workflow TYPE string;
DEFINE FIELD steps ON workflow TYPE array<object>;
DEFINE FIELD config ON workflow TYPE object;
DEFINE FIELD enabled ON workflow TYPE bool DEFAULT true;
DEFINE FIELD created ON workflow TYPE datetime DEFAULT time::now();

-- State table - Agent state snapshots
DEFINE TABLE state SCHEMAFULL;
DEFINE FIELD id ON state TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD workflow ON workflow TYPE record(workflow);
DEFINE FIELD step ON state TYPE int;
DEFINE FIELD data ON state TYPE object;
DEFINE FIELD created ON state TYPE datetime DEFAULT time::now();

-- Metric table - Analytics metrics
DEFINE TABLE metric SCHEMAFULL;
DEFINE FIELD id ON metric TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD name ON metric TYPE string;
DEFINE FIELD value ON metric TYPE float;
DEFINE FIELD unit ON metric TYPE string;
DEFINE FIELD tags ON metric TYPE object;
DEFINE FIELD created ON metric TYPE datetime DEFAULT time::now();

-- Alert table - Notifications
DEFINE TABLE alert SCHEMAFULL;
DEFINE FIELD id ON alert TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD type ON alert TYPE string;
DEFINE FIELD severity ON alert TYPE string;
DEFINE FIELD title ON alert TYPE string;
DEFINE FIELD message ON alert TYPE string;
DEFINE FIELD data ON alert TYPE object;
DEFINE FIELD read ON alert TYPE bool DEFAULT false;
DEFINE FIELD created ON alert TYPE datetime DEFAULT time::now();

-- API key table - API keys/secrets
DEFINE TABLE api_key SCHEMAFULL;
DEFINE FIELD id ON api_key TYPE string;
DEFINE FIELD name ON api_key TYPE string;
DEFINE FIELD key_hash ON api_key TYPE string;
DEFINE FIELD provider ON api_key TYPE string;
DEFINE FIELD scopes ON api_key TYPE array<string>;
DEFINE FIELD last_used ON api_key TYPE option<datetime>;
DEFINE FIELD expires ON api_key TYPE option<datetime>;
DEFINE FIELD created ON api_key TYPE datetime DEFAULT time::now();

-- Policy table - Access policies
DEFINE TABLE policy SCHEMAFULL;
DEFINE FIELD id ON policy TYPE string;
DEFINE FIELD name ON policy TYPE string;
DEFINE FIELD description ON policy TYPE string;
DEFINE FIELD rules ON policy TYPE object;
DEFINE FIELD enabled ON policy TYPE bool DEFAULT true;
DEFINE FIELD created ON policy TYPE datetime DEFAULT time::now();

-- Log table - System logs
DEFINE TABLE log SCHEMAFULL;
DEFINE FIELD id ON log TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD level ON log TYPE string;
DEFINE FIELD source ON log TYPE string;
DEFINE FIELD message ON log TYPE string;
DEFINE FIELD data ON log TYPE option<object>;
DEFINE FIELD created ON log TYPE datetime DEFAULT time::now();

-- Integration table - External integrations
DEFINE TABLE integration SCHEMAFULL;
DEFINE FIELD id ON integration TYPE string;
DEFINE FIELD name ON integration TYPE string;
DEFINE FIELD type ON integration TYPE string;
DEFINE FIELD config ON integration TYPE object;
DEFINE FIELD status ON integration TYPE string DEFAULT "active";
DEFINE FIELD last_sync ON integration TYPE option<datetime>;
DEFINE FIELD created ON integration TYPE datetime DEFAULT time::now();

-- Additional Relations
DEFINE TABLE uses SCHEMAFULL;
DEFINE FIELD in ON uses TYPE record(tool);
DEFINE FIELD out ON uses TYPE record(tool);

DEFINE TABLE has_message SCHEMAFULL;
DEFINE FIELD in ON has_message TYPE record(session);
DEFINE FIELD out ON has_message TYPE record(message);

DEFINE TABLE belongs_to_conversation SCHEMAFULL;
DEFINE FIELD in ON belongs_to_conversation TYPE record(conversation);
DEFINE FIELD out ON belongs_to_conversation TYPE record(session);

DEFINE TABLE uses_template SCHEMAFULL;
DEFINE FIELD in ON uses_template TYPE record(agent);
DEFINE FIELD out ON uses_template TYPE record(prompt_template);

DEFINE TABLE implements_workflow SCHEMAFULL;
DEFINE FIELD in ON implements_workflow TYPE record(agent);
DEFINE FIELD out ON implements_workflow TYPE record(workflow);

DEFINE TABLE enforces SCHEMAFULL;
DEFINE FIELD in ON enforces TYPE record(policy);
DEFINE FIELD out ON enforces TYPE record(session);

-- Indexes
DEFINE INDEX cache_key ON cache FIELDS key;
DEFINE INDEX metric_name ON metric FIELDS name;
DEFINE INDEX log_level ON log FIELDS level;
DEFINE INDEX message_embedding ON message FIELDS embedding MTREE dimensionality 512;
-- =====================================================
-- ENTERPRISE TABLES: RAG, Evaluation, Multi-agent
-- =====================================================

-- Document table - Source documents for RAG
DEFINE TABLE document SCHEMAFULL;
DEFINE FIELD id ON document TYPE string;
DEFINE FIELD title ON document TYPE string;
DEFINE FIELD content ON document TYPE string;
DEFINE FIELD url ON document TYPE option<string>;
DEFINE FIELD source ON document TYPE string;
DEFINE FIELD doc_type ON document TYPE string;
DEFINE FIELD metadata ON document TYPE object;
DEFINE FIELD embedding ON document TYPE array<float>(512);
DEFINE FIELD created ON document TYPE datetime DEFAULT time::now();

-- Chunk table - Document chunks for RAG
DEFINE TABLE chunk SCHEMAFULL;
DEFINE FIELD id ON chunk TYPE string;
DEFINE FIELD document ON document TYPE record(document);
DEFINE FIELD index ON chunk TYPE int;
DEFINE FIELD content ON chunk TYPE string;
DEFINE FIELD embedding ON chunk TYPE array<float>(512);
DEFINE FIELD token_count ON chunk TYPE int;
DEFINE FIELD created ON chunk TYPE datetime DEFAULT time::now();

-- Collection table - Document collections
DEFINE TABLE collection SCHEMAFULL;
DEFINE FIELD id ON collection TYPE string;
DEFINE FIELD name ON collection TYPE string;
DEFINE FIELD description ON collection TYPE string;
DEFINE FIELD config ON collection TYPE object;
DEFINE FIELD document_count ON collection TYPE int DEFAULT 0;
DEFINE FIELD created ON collection TYPE datetime DEFAULT time::now();

-- Embedding model table - Embedding model configs
DEFINE TABLE embedding_model SCHEMAFULL;
DEFINE FIELD id ON embedding_model TYPE string;
DEFINE FIELD name ON embedding_model TYPE string;
DEFINE FIELD provider ON embedding_model TYPE string;
DEFINE FIELD model ON embedding_model TYPE string;
DEFINE FIELD dimensions ON embedding_model TYPE int DEFAULT 1536;
DEFINE FIELD cost_per_1k ON embedding_model TYPE float;
DEFINE FIELD created ON embedding_model TYPE datetime DEFAULT time::now();

-- Vector store table - Vector store configs
DEFINE TABLE vector_store SCHEMAFULL;
DEFINE FIELD id ON vector_store TYPE string;
DEFINE FIELD name ON vector_store TYPE string;
DEFINE FIELD provider ON vector_store TYPE string;
DEFINE FIELD config ON vector_store TYPE object;
DEFINE FIELD status ON vector_store TYPE string DEFAULT "active";
DEFINE FIELD created ON vector_store TYPE datetime DEFAULT time::now();

-- Retrieval result table - RAG retrieval results
DEFINE TABLE retrieval_result SCHEMAFULL;
DEFINE FIELD id ON retrieval_result TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD query ON retrieval_result TYPE string;
DEFINE FIELD chunks ON retrieval_result TYPE array<object>;
DEFINE FIELD context ON retrieval_result TYPE string;
DEFINE FIELD latency_ms ON retrieval_result TYPE int;
DEFINE FIELD created ON retrieval_result TYPE datetime DEFAULT time::now();

-- LLM config table - LLM configurations
DEFINE TABLE llm_config SCHEMAFULL;
DEFINE FIELD id ON llm_config TYPE string;
DEFINE FIELD name ON llm_config TYPE string;
DEFINE FIELD provider ON llm_config TYPE string;
DEFINE FIELD model ON llm_config TYPE string;
DEFINE FIELD config ON llm_config TYPE object;
DEFINE FIELD cost_per_1k_input ON llm_config TYPE float;
DEFINE FIELD cost_per_1k_output ON llm_config TYPE float;
DEFINE FIELD created ON llm_config TYPE datetime DEFAULT time::now();

-- Evaluation run table - Evaluation executions
DEFINE TABLE evaluation_run SCHEMAFULL;
DEFINE FIELD id ON evaluation_run TYPE string;
DEFINE FIELD name ON evaluation_run TYPE string;
DEFINE FIELD dataset ON evaluation_run TYPE string;
DEFINE FIELD metrics ON evaluation_run TYPE array<string>;
DEFINE FIELD config ON evaluation_run TYPE object;
DEFINE FIELD status ON evaluation_run TYPE string DEFAULT "pending";
DEFINE FIELD results ON evaluation_run TYPE object;
DEFINE FIELD created ON evaluation_run TYPE datetime DEFAULT time::now();

-- Test case table - Evaluation test cases
DEFINE TABLE test_case SCHEMAFULL;
DEFINE FIELD id ON test_case TYPE string;
DEFINE FIELD name ON test_case TYPE string;
DEFINE FIELD input ON test_case TYPE string;
DEFINE FIELD expected_output ON test_case TYPE option<string>;
DEFINE FIELD metadata ON test_case TYPE object;
DEFINE FIELD created ON test_case TYPE datetime DEFAULT time::now();

-- Evaluation result table - Individual test results
DEFINE TABLE evaluation_result SCHEMAFULL;
DEFINE FIELD id ON evaluation_result TYPE string;
DEFINE FIELD test_case ON test_case TYPE record(test_case);
DEFINE FIELD evaluation_run ON evaluation_run TYPE record(evaluation_run);
DEFINE FIELD output ON evaluation_result TYPE string;
DEFINE FIELD metrics ON evaluation_result TYPE object;
DEFINE FIELD passed ON evaluation_result TYPE bool;
DEFINE FIELD created ON evaluation_result TYPE datetime DEFAULT time::now();

-- Experiment table - A/B experiments
DEFINE TABLE experiment SCHEMAFULL;
DEFINE FIELD id ON experiment TYPE string;
DEFINE FIELD name ON experiment TYPE string;
DEFINE FIELD description ON experiment TYPE string;
DEFINE FIELD variants ON experiment TYPE array<object>;
DEFINE FIELD traffic ON experiment TYPE float DEFAULT 100.0;
DEFINE FIELD status ON experiment TYPE string DEFAULT "draft";
DEFINE FIELD started ON experiment TYPE option<datetime>;
DEFINE FIELD ended ON experiment TYPE option<datetime>;
DEFINE FIELD created ON experiment TYPE datetime DEFAULT time::now();

-- Variant assignment table - Experiment assignments
DEFINE TABLE variant_assignment SCHEMAFULL;
DEFINE FIELD id ON variant_assignment TYPE string;
DEFINE FIELD experiment ON experiment TYPE record(experiment);
DEFINE FIELD user ON variant_assignment TYPE record(user);
DEFINE FIELD variant ON variant_assignment TYPE string;
DEFINE FIELD created ON variant_assignment TYPE datetime DEFAULT time::now();

-- Variant result table - Experiment results
DEFINE TABLE variant_result SCHEMAFULL;
DEFINE FIELD id ON variant_result TYPE string;
DEFINE FIELD experiment ON experiment TYPE record(experiment);
DEFINE FIELD variant ON variant_result TYPE string;
DEFINE FIELD metric_name ON variant_result TYPE string;
DEFINE FIELD value ON variant_result TYPE float;
DEFINE FIELD sample_size ON variant_result TYPE int;
DEFINE FIELD created ON variant_result TYPE datetime DEFAULT time::now();

-- Agent config table - Saved agent configurations
DEFINE TABLE agent_config SCHEMAFULL;
DEFINE FIELD id ON agent_config TYPE string;
DEFINE FIELD name ON agent_config TYPE string;
DEFINE FIELD agent ON agent_config TYPE record(agent);
DEFINE FIELD llm ON agent_config TYPE record(llm_config);
DEFINE FIELD embedding_model ON agent_config TYPE record(embedding_model);
DEFINE FIELD tools ON agent_config TYPE array<string>;
DEFINE FIELD system_prompt ON agent_config TYPE string;
DEFINE FIELD config ON agent_config TYPE object;
DEFINE FIELD version ON agent_config TYPE int DEFAULT 1;
DEFINE FIELD created ON agent_config TYPE datetime DEFAULT time::now();

-- Guardrail table - Safety guardrails
DEFINE TABLE guardrail SCHEMAFULL;
DEFINE FIELD id ON guardrail TYPE string;
DEFINE FIELD name ON guardrail TYPE string;
DEFINE FIELD type ON guardrail TYPE string;
DEFINE FIELD config ON guardrail TYPE object;
DEFINE FIELD enabled ON guardrail TYPE bool DEFAULT true;
DEFINE FIELD created ON guardrail TYPE datetime DEFAULT time::now();

-- Guardrail check table - Guardrail check results
DEFINE TABLE guardrail_check SCHEMAFULL;
DEFINE FIELD id ON guardrail_check TYPE string;
DEFINE FIELD guardrail ON guardrail_check TYPE record(guardrail);
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD input ON guardrail_check TYPE string;
DEFINE FIELD output ON guardrail_check TYPE string;
DEFINE FIELD passed ON guardrail_check TYPE bool;
DEFINE FIELD violations ON guardrail_check TYPE array<string>;
DEFINE FIELD created ON guardrail_check TYPE datetime DEFAULT time::now();

-- Rate limit table - Rate limiting rules
DEFINE TABLE rate_limit SCHEMAFULL;
DEFINE FIELD id ON rate_limit TYPE string;
DEFINE FIELD name ON rate_limit TYPE string;
DEFINE FIELD user ON rate_limit TYPE record(user);
DEFINE FIELD endpoint ON rate_limit TYPE string;
DEFINE FIELD limit ON rate_limit TYPE int;
DEFINE FIELD window_sec ON rate_limit TYPE int;
DEFINE FIELD created ON rate_limit TYPE datetime DEFAULT time::now();

-- Rate limit usage table - Usage tracking
DEFINE TABLE rate_limit_usage SCHEMAFULL;
DEFINE FIELD id ON rate_limit_usage TYPE string;
DEFINE FIELD rate_limit ON rate_limit_usage TYPE record(rate_limit);
DEFINE FIELD user ON rate_limit_usage TYPE record(user);
DEFINE FIELD count ON rate_limit_usage TYPE int DEFAULT 0;
DEFINE FIELD window_start ON rate_limit_usage TYPE datetime DEFAULT time::now();

-- Audit log table - Audit trail
DEFINE TABLE audit_log SCHEMAFULL;
DEFINE FIELD id ON audit_log TYPE string;
DEFINE FIELD user ON audit_log TYPE record(user);
DEFINE FIELD action ON audit_log TYPE string;
DEFINE FIELD resource_type ON audit_log TYPE string;
DEFINE FIELD resource_id ON audit_log TYPE string;
DEFINE FIELD details ON audit_log TYPE object;
DEFINE FIELD ip ON audit_log TYPE option<string>;
DEFINE FIELD created ON audit_log TYPE datetime DEFAULT time::now();

-- Webhook table - Webhook configurations
DEFINE TABLE webhook SCHEMAFULL;
DEFINE FIELD id ON webhook TYPE string;
DEFINE FIELD name ON webhook TYPE string;
DEFINE FIELD url ON webhook TYPE string;
DEFINE FIELD events ON webhook TYPE array<string>;
DEFINE FIELD secret ON webhook TYPE string;
DEFINE FIELD status ON webhook TYPE string DEFAULT "active";
DEFINE FIELD created ON webhook TYPE datetime DEFAULT time::now();

-- Webhook delivery table - Webhook deliveries
DEFINE TABLE webhook_delivery SCHEMAFULL;
DEFINE FIELD id ON webhook_delivery TYPE string;
DEFINE FIELD webhook ON webhook_delivery TYPE record(webhook);
DEFINE FIELD event ON webhook_delivery TYPE string;
DEFINE FIELD payload ON webhook_delivery TYPE string;
DEFINE FIELD status ON webhook_delivery TYPE string;
DEFINE FIELD response ON webhook_delivery TYPE option<string>;
DEFINE FIELD attempts ON webhook_delivery TYPE int DEFAULT 0;
DEFINE FIELD created ON webhook_delivery TYPE datetime DEFAULT time::now();

-- Additional Relations
DEFINE TABLE contains SCHEMAFULL;
DEFINE FIELD in ON contains TYPE record(document);
DEFINE FIELD out ON contains TYPE record(chunk);

DEFINE TABLE belongs_to_collection SCHEMAFULL;
DEFINE FIELD in ON belongs_to_collection TYPE record(collection);
DEFINE FIELD out ON belongs_to_collection TYPE record(document);

DEFINE TABLE uses_embedding SCHEMAFULL;
DEFINE FIELD in ON uses_embedding TYPE record(collection);
DEFINE FIELD out ON uses_embedding TYPE record(embedding_model);

DEFINE TABLE uses_vector_store SCHEMAFULL;
DEFINE FIELD in ON uses_vector_store TYPE record(collection);
DEFINE FIELD out ON uses_vector_store TYPE record(vector_store);

DEFINE TABLE runs SCHEMAFULL;
DEFINE FIELD in ON runs TYPE record(agent);
DEFINE FIELD out ON runs TYPE record(evaluation_run);

DEFINE TABLE tests SCHEMAFULL;
DEFINE FIELD in ON tests TYPE record(evaluation_run);
DEFINE FIELD out ON tests TYPE record(test_case);

DEFINE TABLE assigned_to SCHEMAFULL;
DEFINE FIELD in ON assigned_to TYPE record(experiment);
DEFINE FIELD out ON assigned_to TYPE record(variant_assignment);

DEFINE TABLE has_guardrail SCHEMAFULL;
DEFINE FIELD in ON has_guardrail TYPE record(agent);
DEFINE FIELD out ON has_guardrail TYPE record(guardrail);

DEFINE TABLE triggers SCHEMAFULL;
DEFINE FIELD in ON triggers TYPE record(event);
DEFINE FIELD out ON triggers TYPE record(webhook);

-- Indexes
DEFINE INDEX document_source ON document FIELDS source;
DEFINE INDEX chunk_embedding ON chunk FIELDS embedding MTREE dimensionality 512;
DEFINE INDEX collection_name ON collection FIELDS name;
DEFINE INDEX test_case_name ON test_case FIELDS name;
DEFINE INDEX experiment_name ON experiment FIELDS name;
DEFINE INDEX audit_action ON audit_log FIELDS action;
-- =====================================================
-- REAL-WORLD TABLES: Multi-tenancy, Billing, Jobs
-- =====================================================

-- Tenant table - Multi-tenant organizations
DEFINE TABLE tenant SCHEMAFULL;
DEFINE FIELD id ON tenant TYPE string;
DEFINE FIELD name ON tenant TYPE string;
DEFINE FIELD slug ON tenant TYPE string;
DEFINE FIELD domain ON tenant TYPE option<string>;
DEFINE FIELD plan ON tenant TYPE string DEFAULT "free";
DEFINE FIELD config ON tenant TYPE object;
DEFINE FIELD status ON tenant TYPE string DEFAULT "active";
DEFINE FIELD created ON tenant TYPE datetime DEFAULT time::now();

-- Subscription table - Billing subscriptions
DEFINE TABLE subscription SCHEMAFULL;
DEFINE FIELD id ON subscription TYPE string;
DEFINE FIELD tenant ON subscription TYPE record(tenant);
DEFINE FIELD plan ON subscription TYPE string;
DEFINE FIELD status ON subscription TYPE string DEFAULT "active";
DEFINE FIELD billing_email ON subscription TYPE string;
DEFINE FIELD stripe_id ON subscription TYPE option<string>;
DEFINE FIELD current_period_start ON subscription TYPE datetime;
DEFINE FIELD current_period_end ON subscription TYPE datetime;
DEFINE FIELD created ON subscription TYPE datetime DEFAULT time::now();

-- Invoice table - Billing invoices
DEFINE TABLE invoice SCHEMAFULL;
DEFINE FIELD id ON invoice TYPE string;
DEFINE FIELD subscription ON subscription TYPE record(subscription);
DEFINE FIELD amount ON invoice TYPE int;
DEFINE FIELD currency ON invoice TYPE string DEFAULT "usd";
DEFINE FIELD status ON invoice TYPE string;
DEFINE FIELD paid_at ON invoice TYPE option<datetime>;
DEFINE FIELD due_date ON invoice TYPE datetime;
DEFINE FIELD items ON invoice TYPE array<object>;
DEFINE FIELD created ON invoice TYPE datetime DEFAULT time::now();

-- Usage record table - API usage tracking
DEFINE TABLE usage_record SCHEMAFULL;
DEFINE FIELD id ON usage_record TYPE string;
DEFINE FIELD tenant ON usage_record TYPE record(tenant);
DEFINE FIELD metric ON usage_record TYPE string;
DEFINE FIELD count ON usage_record TYPE int DEFAULT 0;
DEFINE FIELD cost ON usage_record TYPE float DEFAULT 0.0;
DEFINE FIELD period_start ON usage_record TYPE datetime;
DEFINE FIELD period_end ON usage_record TYPE datetime;
DEFINE FIELD created ON usage_record TYPE datetime DEFAULT time::now();

-- Team member table - Team collaboration
DEFINE TABLE team_member SCHEMAFULL;
DEFINE FIELD id ON team_member TYPE string;
DEFINE FIELD tenant ON team_member TYPE record(tenant);
DEFINE FIELD user ON team_member TYPE record(user);
DEFINE FIELD role ON team_member TYPE string DEFAULT "member";
DEFINE FIELD invited_by ON team_member TYPE record(user);
DEFINE FIELD status ON team_member TYPE string DEFAULT "pending";
DEFINE FIELD created ON team_member TYPE datetime DEFAULT time::now();

-- Invite table - Team invites
DEFINE TABLE invite SCHEMAFULL;
DEFINE FIELD id ON invite TYPE string;
DEFINE FIELD tenant ON invite TYPE record(tenant);
DEFINE FIELD email ON invite TYPE string;
DEFINE FIELD role ON invite TYPE string DEFAULT "member";
DEFINE FIELD token ON invite TYPE string;
DEFINE FIELD expires ON invite TYPE datetime;
DEFINE FIELD created ON invite TYPE datetime DEFAULT time::now();

-- Tag table - Tagging taxonomy
DEFINE TABLE tag SCHEMAFULL;
DEFINE FIELD id ON tag TYPE string;
DEFINE FIELD name ON tag TYPE string;
DEFINE FIELD color ON tag TYPE string;
DEFINE FIELD tenant ON tag TYPE record(tenant);
DEFINE FIELD created ON tag TYPE datetime DEFAULT time::now();

-- Tagged table - Tag assignments
DEFINE TABLE tagged SCHEMAFULL;
DEFINE FIELD in ON tagged TYPE record;
DEFINE FIELD out ON tagged TYPE record(tag);
DEFINE FIELD tagged_at ON tagged TYPE datetime DEFAULT time::now();

-- Bookmark table - User bookmarks
DEFINE TABLE bookmark SCHEMAFULL;
DEFINE FIELD id ON bookmark TYPE string;
DEFINE FIELD user ON bookmark TYPE record(user);
DEFINE FIELD resource_type ON bookmark TYPE string;
DEFINE FIELD resource_id ON bookmark TYPE string;
DEFINE FIELD notes ON bookmark TYPE option<string>;
DEFINE FIELD created ON bookmark TYPE datetime DEFAULT time::now();

-- Search index table - Search configuration
DEFINE TABLE search_index SCHEMAFULL;
DEFINE FIELD id ON search_index TYPE string;
DEFINE FIELD name ON search_index TYPE string;
DEFINE FIELD resource_types ON search_index TYPE array<string>;
DEFINE FIELD fields ON search_index TYPE array<string>;
DEFINE FIELD weights ON search_index TYPE object;
DEFINE FIELD config ON search_index TYPE object;
DEFINE FIELD created ON search_index TYPE datetime DEFAULT time::now();

-- API route table - API endpoints
DEFINE TABLE api_route SCHEMAFULL;
DEFINE FIELD id ON api_route TYPE string;
DEFINE FIELD path ON api_route TYPE string;
DEFINE FIELD method ON api_route TYPE string;
DEFINE FIELD handler ON api_route TYPE string;
DEFINE FIELD auth_required ON api_route TYPE bool DEFAULT true;
DEFINE FIELD rate_limit ON api_route TYPE int;
DEFINE FIELD created ON api_route TYPE datetime DEFAULT time::now();

-- Job table - Background jobs queue
DEFINE TABLE job SCHEMAFULL;
DEFINE FIELD id ON job TYPE string;
DEFINE FIELD name ON job TYPE string;
DEFINE FIELD payload ON job TYPE object;
DEFINE FIELD status ON job TYPE string DEFAULT "queued";
DEFINE FIELD progress ON job TYPE int DEFAULT 0;
DEFINE FIELD result ON job TYPE option<object>;
DEFINE FIELD error ON job TYPE option<string>;
DEFINE FIELD attempts ON job TYPE int DEFAULT 0;
DEFINE FIELD max_attempts ON job TYPE int DEFAULT 3;
DEFINE FIELD scheduled_at ON job TYPE option<datetime>;
DEFINE FIELD started_at ON job TYPE option<datetime>;
DEFINE FIELD completed_at ON job TYPE option<datetime>;
DEFINE FIELD created ON job TYPE datetime DEFAULT time::now();

-- Scheduled job table - Cron jobs
DEFINE TABLE scheduled_job SCHEMAFULL;
DEFINE FIELD id ON scheduled_job TYPE string;
DEFINE FIELD name ON scheduled_job TYPE string;
DEFINE FIELD cron_expression ON scheduled_job TYPE string;
DEFINE FIELD handler ON scheduled_job TYPE string;
DEFINE FIELD payload ON scheduled_job TYPE object;
DEFINE FIELD enabled ON scheduled_job TYPE bool DEFAULT true;
DEFINE FIELD last_run ON scheduled_job TYPE option<datetime>;
DEFINE FIELD next_run ON scheduled_job TYPE option<datetime>;
DEFINE FIELD created ON scheduled_job TYPE datetime DEFAULT time::now();

-- Storage bucket table - File storage
DEFINE TABLE storage_bucket SCHEMAFULL;
DEFINE FIELD id ON storage_bucket TYPE string;
DEFINE FIELD name ON storage_bucket TYPE string;
DEFINE FIELD tenant ON storage_bucket TYPE record(tenant);
DEFINE FIELD region ON storage_bucket TYPE string;
DEFINE FIELD public ON storage_bucket TYPE bool DEFAULT false;
DEFINE FIELD created ON storage_bucket TYPE datetime DEFAULT time::now();

-- Storage object table - File metadata
DEFINE TABLE storage_object SCHEMAFULL;
DEFINE FIELD id ON storage_object TYPE string;
DEFINE FIELD bucket ON storage_object TYPE record(storage_bucket);
DEFINE FIELD key ON storage_object TYPE string;
DEFINE FIELD content_type ON storage_object TYPE string;
DEFINE FIELD size ON storage_object TYPE int;
DEFINE FIELD etag ON storage_object TYPE string;
DEFINE FIELD url ON storage_object TYPE option<string>;
DEFINE FIELD created ON storage_object TYPE datetime DEFAULT time::now();

-- Notification table - User notifications
DEFINE TABLE notification SCHEMAFULL;
DEFINE FIELD id ON notification TYPE string;
DEFINE FIELD user ON notification TYPE record(user);
DEFINE FIELD type ON notification TYPE string;
DEFINE FIELD title ON notification TYPE string;
DEFINE FIELD body ON notification TYPE string;
DEFINE FIELD data ON notification TYPE object;
DEFINE FIELD read ON notification TYPE bool DEFAULT false;
DEFINE FIELD read_at ON notification TYPE option<datetime>;
DEFINE FIELD created ON notification TYPE datetime DEFAULT time::now();

-- Custom field table - Extensible metadata
DEFINE TABLE custom_field SCHEMAFULL;
DEFINE FIELD id ON custom_field TYPE string;
DEFINE FIELD name ON custom_field TYPE string;
DEFINE FIELD field_type ON custom_field TYPE string;
DEFINE FIELD resource_type ON custom_field TYPE string;
DEFINE FIELD options ON custom_field TYPE array<string>;
DEFINE FIELD required ON custom_field TYPE bool DEFAULT false;
DEFINE FIELD created ON custom_field TYPE datetime DEFAULT time::now();

-- Custom value table - Field values
DEFINE TABLE custom_value SCHEMAFULL;
DEFINE FIELD id ON custom_value TYPE string;
DEFINE FIELD field ON custom_field TYPE record(custom_field);
DEFINE FIELD resource_type ON custom_value TYPE string;
DEFINE FIELD resource_id ON custom_value TYPE string;
DEFINE FIELD value ON custom_value TYPE string;
DEFINE FIELD created ON custom_value TYPE datetime DEFAULT time::now();

-- Report table - Saved reports
DEFINE TABLE report SCHEMAFULL;
DEFINE FIELD id ON report TYPE string;
DEFINE FIELD name ON report TYPE string;
DEFINE FIELD tenant ON report TYPE record(tenant);
DEFINE FIELD config ON report TYPE object;
DEFINE FIELD schedule ON report TYPE option<string>;
DEFINE FIELD last_run ON report TYPE option<datetime>;
DEFINE FIELD created ON report TYPE datetime DEFAULT time::now();

-- Dashboard table - Analytics dashboards
DEFINE TABLE dashboard SCHEMAFULL;
DEFINE FIELD id ON dashboard TYPE string;
DEFINE FIELD name ON dashboard TYPE string;
DEFINE FIELD tenant ON dashboard TYPE record(tenant);
DEFINE FIELD config ON dashboard TYPE object;
DEFINE FIELD widgets ON dashboard TYPE array<object>;
DEFINE FIELD created ON dashboard TYPE datetime DEFAULT time::now();

-- Shortcut table - Keyboard shortcuts
DEFINE TABLE shortcut SCHEMAFULL;
DEFINE FIELD id ON shortcut TYPE string;
DEFINE FIELD user ON shortcut TYPE record(user);
DEFINE FIELD key ON shortcut TYPE string;
DEFINE FIELD action ON shortcut TYPE string;
DEFINE FIELD created ON shortcut TYPE datetime DEFAULT time::now();

-- API usage by endpoint table - Per-endpoint tracking
DEFINE TABLE api_usage SCHEMAFULL;
DEFINE FIELD id ON api_usage TYPE string;
DEFINE FIELD tenant ON api_usage TYPE record(tenant);
DEFINE FIELD endpoint ON api_usage TYPE string;
DEFINE FIELD method ON api_usage TYPE string;
DEFINE FIELD count ON api_usage TYPE int DEFAULT 0;
DEFINE FIELD latency_p50 ON api_usage TYPE int;
DEFINE FIELD latency_p95 ON api_usage TYPE int;
DEFINE FIELD latency_p99 ON api_usage TYPE int;
DEFINE FIELD errors ON api_usage TYPE int DEFAULT 0;
DEFINE FIELD period_start ON api_usage TYPE datetime;
DEFINE FIELD period_end ON api_usage TYPE datetime;
DEFINE FIELD created ON api_usage TYPE datetime DEFAULT time::now();

-- Sentiment record table - Feedback sentiment
DEFINE TABLE sentiment SCHEMAFULL;
DEFINE FIELD id ON sentiment TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD response ON response_trace TYPE record(response_trace);
DEFINE FIELD score ON sentiment TYPE float;
DEFINE FIELD label ON sentiment TYPE string;
DEFINE FIELD created ON sentiment TYPE datetime DEFAULT time::now();

-- Token usage table - Token tracking per model
DEFINE TABLE token_usage SCHEMAFULL;
DEFINE FIELD id ON token_usage TYPE string;
DEFINE FIELD session ON session TYPE record(session);
DEFINE FIELD model ON token_usage TYPE string;
DEFINE FIELD prompt_tokens ON token_usage TYPE int DEFAULT 0;
DEFINE FIELD completion_tokens ON token_usage TYPE int DEFAULT 0;
DEFINE FIELD total_tokens ON token_usage TYPE int DEFAULT 0;
DEFINE FIELD cost ON token_usage TYPE float DEFAULT 0.0;
DEFINE FIELD created ON token_usage TYPE datetime DEFAULT time::now();

-- Feature flag table - Feature toggles
DEFINE TABLE feature_flag SCHEMAFULL;
DEFINE FIELD id ON feature_flag TYPE string;
DEFINE FIELD name ON feature_flag TYPE string;
DEFINE FIELD description ON feature_flag TYPE string;
DEFINE FIELD enabled_for ON feature_flag TYPE array<string>;
DEFINE FIELD disabled_for ON feature_flag TYPE array<string>;
DEFINE FIELD rollout_percentage ON feature_flag TYPE float DEFAULT 0.0;
DEFINE FIELD created ON feature_flag TYPE datetime DEFAULT time::now();

-- Feature flag override table - Per-tenant flags
DEFINE TABLE feature_flag_override SCHEMAFULL;
DEFINE FIELD id ON feature_flag_override TYPE string;
DEFINE FIELD feature_flag ON feature_flag_override TYPE record(feature_flag);
DEFINE FIELD tenant ON feature_flag_override TYPE record(tenant);
DEFINE FIELD enabled ON feature_flag_override TYPE bool;
DEFINE FIELD created ON feature_flag_override TYPE datetime DEFAULT time::now();

-- Additional Relations
DEFINE TABLE belongs_to_tenant SCHEMAFULL;
DEFINE FIELD in ON belongs_to_tenant TYPE record(tenant);
DEFINE FIELD out ON belongs_to_tenant TYPE record(user);

DEFINE TABLE has_subscription SCHEMAFULL;
DEFINE FIELD in ON has_subscription TYPE record(tenant);
DEFINE FIELD out ON has_subscription TYPE record(subscription);

DEFINE TABLE uses_job SCHEMAFULL;
DEFINE FIELD in ON uses_job TYPE record(job);
DEFINE FIELD out ON uses_job TYPE record(scheduled_job);

DEFINE TABLE saved_to SCHEMAFULL;
DEFINE FIELD in ON saved_to TYPE record(dashboard);
DEFINE FIELD out ON saved_to TYPE record(report);

DEFINE TABLE triggered_by SCHEMAFULL;
DEFINE FIELD in ON triggered_by TYPE record(scheduled_job);
DEFINE FIELD out ON triggered_by TYPE record(job);

-- Indexes
DEFINE INDEX tenant_slug ON tenant FIELDS slug UNIQUE;
DEFINE INDEX subscription_tenant ON subscription FIELDS tenant;
DEFINE INDEX usage_period ON usage_record FIELDS period_start;
DEFINE INDEX job_status ON job FIELDS status;
DEFINE INDEX notification_user ON notification FIELDS user, read;
