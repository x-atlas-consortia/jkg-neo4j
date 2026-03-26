// Creates constraints for files imported into the neo4j instance.
CREATE CONSTRAINT FOR (n:Term) REQUIRE n.id IS UNIQUE;