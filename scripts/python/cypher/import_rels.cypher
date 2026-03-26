CALL apoc.periodic.iterate(
    'CALL apoc.load.jsonArray($file, ".rels")
    YIELD value AS r
    RETURN r',
    'MATCH (start:Concept|Node_Label{id:r.start.properties.id})
    MATCH (end:Concept|Node_Label{id:r.end.properties.id})
    CREATE (start)-[rel:$(r.label)]->(end)
    SET rel = r.properties',
    {batchSize: 1000, parallel: false, params: {file: $file}}
)
YIELD batches, total, committedOperations
RETURN batches, total, committedOperations