// Creates constraints for files imported into the neo4j instance.
CREATE CONSTRAINT FOR (n:Source) REQUIRE n.id IS UNIQUE;