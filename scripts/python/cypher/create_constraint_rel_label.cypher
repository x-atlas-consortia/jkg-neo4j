// Creates constraints for files imported into the neo4j instance.
CREATE CONSTRAINT FOR (n:Rel_Label) REQUIRE n.id IS UNIQUE;