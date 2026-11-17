"""neo4j: Neo4j Community server, for the self-install comparison.

This is the DBMS itself (Community, Bolt, file mode), not Neo4j Desktop.
The graph model, Cypher and driver are the same as the relate adapter,
which talks to "the DBMS that Neo4j Desktop (Relate) wraps". They are
kept as two registry names so a self-install attempt that installed
Neo4j server can be compared to a hand-built `neo4j` backend without
pretending it installed Relate.

Connection comes from CTXLAYER_NEO4J_URI / CTXLAYER_NEO4J_USER /
CTXLAYER_NEO4J_PASSWORD (never printed).
"""
from .relate_adapter import Relate


class Neo4j(Relate):
    name = "neo4j"
