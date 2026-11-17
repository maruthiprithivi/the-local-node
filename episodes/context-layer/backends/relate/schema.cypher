// Run on every setup: start from an empty graph, then add the uniqueness constraints (Community edition).
MATCH (n) DETACH DELETE n;
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT fact_key IF NOT EXISTS FOR (f:Fact) REQUIRE (f.entity_id, f.text) IS UNIQUE;
