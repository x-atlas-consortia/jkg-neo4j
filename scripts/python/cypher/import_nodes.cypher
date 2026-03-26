CALL apoc.periodic.iterate(
    'CALL apoc.load.jsonArray($file, ".nodes")
    YIELD value AS n
    RETURN n',
    'CREATE (node:$(n.labels))
    SET node = n.properties',
    {batchSize: 1000, parallel: false, params: {file: $file}}
)
YIELD batches, total, committedOperations
RETURN batches, total, committedOperations