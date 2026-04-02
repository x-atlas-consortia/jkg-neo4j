// Obtains an ordered set of relationship types for relevant
// relationships in the JKG.
// Excludes relationship types that have special characters or that start with numbers.
CALL db.relationshipTypes()
YIELD relationshipType
WHERE NOT (relationshipType CONTAINS '-' OR relationshipType CONTAINS '(' OR relationshipType CONTAINS ':' OR relationshipType =~ '^\\d.*')
WITH collect(relationshipType) AS relationshipTypes
WITH apoc.text.join(relationshipTypes, '|') AS relTypeExpr
CALL apoc.cypher.runSchema(
  'CREATE FULLTEXT INDEX r_sab IF NOT EXISTS FOR ()-[r:' + relTypeExpr + ']-() ON EACH [r.sab]',
  {}
) YIELD value
RETURN value;