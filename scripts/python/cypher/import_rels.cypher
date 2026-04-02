// Loads all elements from the rels array from a batched JKG JSON file
// and creates relationships in Neo4j in batches.
// Assumptions:
// 1. The $file parameter points to a batched JKG file extracted from a
//    JKG JSON file that conforms to the JKG schema --i.e.,
//    {"nodes":[array of nodes objects], "rels:[array of rels objects]}
// 2. The batched JKG JSON file contains a non-empty rels array of
//    relationships between concepts (i.e., with file name in format JGK_Batchrelnnnn.json.
// 3. The batched JKG JSON file validates against the JKG schema.
// 4. Nodes were created in the graph by means of import_nodes.cypher.

// Driver query (CALL apoc.load.json...:
// 1. Reads the JSON file into variable named value
// 2. Explodes the rels array of value so that each array element
//    (corresponding to a relationship) is in a separate row
// 3. Streams the array elements to the action query

// Action query (CALL apoc.cypher.run...:
// For each streamed array element (corresponding to a relationship),
// 1. Finds the start and end nodes of the relationship
// 2. Creates a relationship between the start and end nodes
// Relationships can involve nodes derived from the Semantic Network that do not have
// a Concept label. Identifying a node requires searching both types of nodes.
// To ensure the use of the indexes on the Concept and Node_Label nodes
// (and avoid Out of Memory Errors from table scans), build a dynamic Cypher
// that uses UNION.

CALL apoc.periodic.iterate(
    'CALL apoc.load.json($file) YIELD value
     UNWIND value.rels AS r
     RETURN r',
    'CALL apoc.cypher.run(
        "MATCH (n:Concept    {id: $id}) RETURN n
         UNION
         MATCH (n:Node_Label {id: $id}) RETURN n",
        {id: r.start.properties.id}
     ) YIELD value AS startRow
     CALL apoc.cypher.run(
        "MATCH (n:Concept    {id: $id}) RETURN n
         UNION
         MATCH (n:Node_Label {id: $id}) RETURN n",
        {id: r.end.properties.id}
     ) YIELD value AS endRow
     CALL apoc.create.relationship(startRow.n, r.label, r.properties, endRow.n) YIELD rel
     RETURN rel',
    {batchSize: 1000, parallel: false, params: {file: $file}}
)
YIELD batches, total, committedOperations, failedOperations, errorMessages
RETURN batches, total, committedOperations, failedOperations, errorMessages