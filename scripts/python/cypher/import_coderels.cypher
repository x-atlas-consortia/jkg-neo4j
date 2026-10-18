// Loads all elements from the rels array from a batched JKG JSON file
// and creates relationships in Neo4j in batches of 1000.
// Assumptions:
// 1. The $file parameter points to a batched JKG file extracted from a
//    JKG JSON file that conforms to the JKG schema --i.e.,
//    {"nodes":[array of nodes objects], "rels:[array of rels objects]}
// 2. The batched JKG JSON file contains a non-empty rels array of
//    relationships between concepts and codes (i.e., with file name
//    in format JGK_Batchcoderelnnnn.json.
// 3. The batched JKG JSON file validates against the JKG schema.
// 4. Nodes have been created in the graph by means of import_nodes.cypher.

// Driver query (CALL apoc.load.json...:
// 1. Reads the JSON file into variable named value
// 2. Explodes the rels array of value so that each array element
//    (corresponding to a relationship) is in a separate row
// 3. Streams the array elements to the action query

// Action query (MATCH...:
// For each streamed array element (corresponding to a relationship),
// 1. Finds the start node (a Concept node) and end node (a Term node)
//    of the relationship
// 2. Creates a relationship between the start and end nodes

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
    'CALL apoc.load.json($file) YIELD value
     UNWIND value.rels AS r
     RETURN r',
    'MATCH (start:Concept {id: r.start.properties.id})
     MATCH (end:Term      {id: r.end.properties.id})
     CALL apoc.create.relationship(start, r.label, r.properties, end) YIELD rel
     RETURN rel',
    {batchSize: 1000, parallel: false, params: {file: $file}, iterateList: false}
)
YIELD batches, total, committedOperations, failedOperations, errorMessages
RETURN batches, total, committedOperations, failedOperations, errorMessages
