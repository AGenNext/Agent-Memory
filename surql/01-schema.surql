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
DEFINE INDEX entity_name ON entity FIELDS name;