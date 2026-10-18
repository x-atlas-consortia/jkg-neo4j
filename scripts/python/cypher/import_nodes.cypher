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

// Parameter values:
// 1. batchSize: controls size of commit chunks. Tradeoff:
//    - small size (<500) : lowers risk of mid-commit failure; lower memory pressure;
//      increased overhead; increased processing time
//    - large size (>1000): increaes risk of OOME; reduced processing time
// 2. parallel: set to false to process sequentially to reduce issues such as lock conflicts
// 3. iterate: important
//    - true (default): fully materializes the
//      (apoc.load.json + UNWIND value.rels result) set in heap before
//      any batching/committing occurs. This has shown to fail once the set
//      of imported files becomes large.
//    - false: forces APOC to stream through the driver query in
//      chunks of batchSize instead of materializing everything up front.
//  4. file: (batch-created) JSON file to import
CALL apoc.periodic.iterate(
    'CALL apoc.load.json($file) YIELD value UNWIND value.nodes AS n RETURN n',
    'CALL apoc.create.node(n.labels, n.properties) YIELD node RETURN node',
    {batchSize: 1000, parallel: false, params: {file: $file}, iterateList: true}
)
YIELD batches, total, committedOperations
RETURN batches, total, committedOperations