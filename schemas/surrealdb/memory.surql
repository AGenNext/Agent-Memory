DEFINE TABLE memory SCHEMAFULL;

DEFINE FIELD type ON TABLE memory TYPE string;
DEFINE FIELD content ON TABLE memory TYPE object;
DEFINE FIELD embedding ON TABLE memory FLEXIBLE TYPE array;
DEFINE FIELD created_at ON TABLE memory TYPE datetime VALUE time::now();

DEFINE INDEX memory_embedding_idx
ON TABLE memory
FIELDS embedding
HNSW DIMENSION 1536;
