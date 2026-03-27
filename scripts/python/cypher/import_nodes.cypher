// Loads all elements from the nodes array from a batched JKG JSON file
// and creates nodes in Neo4j in batches of 1000.
// Assumptions:
// 1. The $file parameter points to a batched JKG file extracted from a
//    JKG JSON file that conforms to the JKG schema --i.e.,
//    {"nodes":[array of nodes objects], "rels:[array of rels objects]}
// 2. The batched JKG JSON file contains a non-empty nodes array.
// 3. The batched JKG JSON file validates against the JKG schema.

// Driver query (CALL apoc.load.json...:
// 1. Reads the JSON file into variable named value
// 2. Explodes the nodes array of value so that each array element
//    (corresponding to a node) is in a separate row
// 3. Streams the array elements to the action query

// Action query (CALL apoc.create.node...:
// Creates a node in neo4j using the streamed array element.
CALL apoc.periodic.iterate(
    'CALL apoc.load.json($file) YIELD value UNWIND value.nodes AS n RETURN n',
    'CALL apoc.create.node(n.labels, n.properties) YIELD node RETURN node',
    {batchSize: 1000, parallel: false, params: {file: $file}}
)
YIELD batches, total, committedOperations
RETURN batches, total, committedOperations