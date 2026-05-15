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