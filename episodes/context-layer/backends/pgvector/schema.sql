CREATE EXTENSION IF NOT EXISTS vector;
DROP TABLE IF EXISTS memory;
CREATE TABLE memory (
  id        bigserial PRIMARY KEY,
  entity_id text NOT NULL,
  fact      text NOT NULL,
  embedding vector(64) NOT NULL,
  UNIQUE (entity_id, fact)
);
CREATE INDEX memory_entity ON memory (entity_id);
