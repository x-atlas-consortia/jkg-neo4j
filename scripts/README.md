# jkg-neo4j
## Tools 

For an explanation of tool patterns, including file structure of source files, 
consult the main [README.md.](https://github.com/x-atlas-consortia/jkg-neo4j)

All tools work with a common configuation file named **container.cfg**. 
The file **container.cfg.example** in this repo serves as a template for **container.cfg**.

---

# batch_jkg_json
## Purpose
Divides a JKG JSON file into a set of smaller "batch" JSON files. 
Each batch file has the same structure as its parent, with **nodes** and **rels** arrays.  
However, a batch file of a given type populates only the array of nodes of a type. 
The types of batch files are:
* **node** files, containing nodes
* **rel** files containing rels corresponding to relationships between concepts
* **coderels** files containing rels corresponding to relationships between concepts and codes

A batch file will contain up to a specified number of nodes in its corresponding array.

## Components
* **batch_jkg_json.sh**: Bash script
* **batch_jkg_json.py**: Python script

## Inputs
* a JKG JSON file

## Outputs
Sets of **node**, **rel**, and **coderel** JSON files in the _/batch_ subdirectory 
of the directory that contains the JKG JSON.

## Batch file naming convention

Each batch file's name will be in the format
**JKG_Batch_**_ _type_ _ _batch_ **.JSON**

where 
* _type_ is in the set {"node","rel","coderel"} 
* _batch_ corresponds to the ordinal number of the batch

For example, the file `JKG_Batch_node_0009.JSON` identifies the 
9th array of nodes objects extracted from the JKG JSON. 

The number of objects in an array of a batch file will be up to the batch size specified in the common
**container.cfg** file.

---

# validate_jkg_json

## Purpose
Validates a JSON file in JSON Knowledge Graph (JKG) format.

## Components
* **validate_jkg_json.sh**: Bash script
* **validate_jkg_json.py**: Python script

## Types of validation
**validate_jkg_json** can perform two types of validation:
1. **Schema validation** against the [JKG Schema](https://github.com/x-atlas-consortia/json-knowledge-graph/blob/main/JKG_Schema.json), using the [jsonschema](https://python-jsonschema.readthedocs.io/en/latest/) package.
2. **Structural validation**:
   * gross structural validation that confirms existence of:
      * nodes and rels arrays
      * nodes for all types (Source, Node_Label, Rel_Label, Term, Concept)
   * fine structural validation:
      * checks for duplicate nodes
      * checks for "referential integrity"--e.g., that node identifiers in the **rels** array have corresponding elements in the **nodes** array; etc.

## Validation options
Both the types and scope of validation can be controlled by setting 
values in the **container.cfg** file.

### Fast/small processing options

1. To validate a single batch file, use [specific batch file processing](#specific-batch-file-validation).
2. To sample schema validation, use [spot-checking](#spot-checking).
3. To validate the entire JKG JSON schema, validate using [batch files](#processing-scope-entire-file-vs-batch-file-) and [parallel processing](#processing-type-single-processing-vs-parallel-processing).

### Structural validation
Structural validation requires the entire JKG JSON file; however, it is possible to specify the types of checks with boolean flags:
   * **check_uniqueness**
   * **check_referential**

### Schema validation
Schema validation scope can be finely controlled via configuration.

#### Processing type: single processing vs. parallel processing.
A JKG JSON file is likely to be extremely large: for example, the JKG JSON produced from the 2025AB release of the UMLS is 4.4 GB.
Validation of an entire JKG JSON against the entire JKG schema will likely require a considerable amount of time.

To speed validation, the script can validate the schema using parallel processing. 
The validation script distributes "chunks" of an input JSON file among a set of
"worker" processes that work in parallel.

To enable parallel processing, set _schema_validation_parallel_=true in **container.cfg**.

The size of the chunk (corresponding to the number of nodes in an array) for parallel schema validation 
should be large enough to allow worker processes to finish before timeout.
The script will warn if the chunk size is below 100.

Set the processing chunk size with _parallel_chunk_ in **container.cfg**.

#### Processing Scope: entire file vs. batch file 
There are no real benefits in validating entire arrays of the same type (node, rel) against the JKG schema.
If the JKG JSON has been batched, schema validation is faster against the batched files.

To enable batch file validation, set __schema_validation_batch__=true in **container.cfg**.

The flags for processing type and processing scope are independent. 
Processing times vary greatly. Following are the combined modes of processing (type and scope),
in increasing order of processing time:

1. with parallel processing on batch files 
2. with parallel processing on the entire JKG JSON 
3. with single processing on batch files 
4. with single processing on the entire JKG JSON file

#### Spot checking (sampling)
Spot checking allows for validation of a random sample of batch files. Spot-checking
is a form of batch file processing, using parallel processing.

To enable spot-checking, set _schema_validation_spot_=true in **container.cfg**.
Set _num_spot_checks_ to an integer to specify the number of batch files to select for spot checking.

#### Specific batch file validation (targeted)
It is possible to evaluate a specific set of individual batch files.
Specific batch file validation is a form of batch processing, using parallel processing.

To enable specific batch file validation, set  _batch_files_ to a comma-delimited list of file names to evaluate 

Specific batch file validation overrides all other forms of schema validation.

### Order of precedence of schema validation
1. Specific batch file validation
2. Spot check validation
3. Full schema validation (batch or entire)

## Inputs
* JSON files
  * For batch file validation, schema validation will work with the batch files that were created in the _/batch_ subdirectory.
  * For entire validation, JKG JSON has not been batched, either the JKG JSON or the batch files
  * For spot-validation or specific batch file validation, the batch files
*  **JKG Schema** - the JKG schema
  
Input file names and locations are specified in **container.cfg**.

## Outputs
### in the /log directory:
* **validate_jkg_json.log**- the application log

### in the input directory that contains the JKG JSON file:
* **validation_errors.tsv**
    
    Tab-separated variables (TSV) file of validation errors. 
  * Errors are sorted by: 
    * array type (nodes first, then rels)
    * item - the JSON object in which the error was found
    * error message
  * When parallel schema validation is performed, errors are returned in random order, so errors are sorted by item.

#### Structural validation error files
* **missing_X_.csv** - CSVs of missing elements of type **X** elements, such as:
  * SABs not in the sources array
  * SABs in the properties of elements of the rels array but not in the sources array
  * concept labels not in node_labels
  * relationship labels not in rel_labels
  * start or end ids in rels without corresponding nodes
  
* **duplicate_X_.csv** - CSVs of duplicate elements of type **X**, such as:
  * duplicate node ids in the nodes array
  * duplicate SABs in the sources array
  * duplicate labels in the node_labels array
  * duplicate labels in the rel_labels array

### Output file rotation
* **validate_jkg_json.py** will append to **validate_jkg_json.log**. The developer will need to "rotate" the log manually by deleting it.
* **validate_jkg_json.py** will delete prior validation CSV files as part of execution.

### Interpreting schema validation error messages
The error messages from jsonschema can be cryptic. 
One way to interpret a schema validation error is to load both the item and the JKG JSON schema 
into a prompt to GitHub Copilot and asking for an explanation. Copilot can often describe the
validation error in greater detail.

### Progress monitoring

#### Progress bars
Validation will show progress bars when:
* loading and parsing JSON files
* validating JSON files against the schema in parallel

#### Timers 
When validating JSON files with single processing, the script
will display a timer that updates every 5 seconds.

#### Estimates
For long-running processes, the script will display an estimate of the time
that the process will require, based on working with similar files in the past.

---

# import_jkg_json
## Purpose
Imports the set of batched JKG JSON files into the neo4j instance hosted by the jkg-neo4j Docker container.

The script:
* reads each file in the set of distributed JKG JSON batch files
* iteratively imports the batch files into neo4j
* creates indexes and constraints in the neo4j database

## Components
* **import_jkg_json.sh**: Bash script
* **import_jkg_json.py**: Python script

## Input
A set of batched JKG JSON logs created by the **batch_jkg_json.sh** script.

## Output
* **import_jkg_json.log**: application log

## Configuration
The import script executes the neo4j **apoc.loadjson**  command, which 
accepts a url pointing to a JSON file to load. 

When the Docker neo4j host is prepared properly
by executing the **export_bind_mount.sh** and **build_container.sh** _external_ scripts, the 
docker will have an external bind mount named _import_, to which the import script copies the 
JKG JSON batch files. 

The _import_url_base_ key should be set to the location of batched JKG JSON files _in the Docker container's file system_. 
Because the docker host mounts an external volume, the file location for neo4j is in the path to the internal neo4j import.
For example, if the external volume is in a _json/batch_ directory, the value of 
_import_url_base_ in **container.cfg** should be _file:///usr/src/app/neo4j/import/json/batch/_.

## Assumptions
1. The JKG JSON source has been both
   * validated against the JKG Schema
   * batch distributed
2. The **build_container** and **export_bind_mount** scripts have been run to build a Docker neo4j host with external volumes.

---

# build_container
## Purpose
Builds a Docker container that hosts a neo4j instance. The script can
build a container either with an external volume mount or without. 

In the workflow to build a neo4j distribution, **build_container** executes numerous times:
* initially to build an empty "primer" neo4j instance without an external volume
* after export of the primer neo4j database to an external volume
* after import of JKG JSON source
* to build a container from a distribution

## Components
* **build_container.sh**: Bash script

# export_bind_mount
## Purpose
Exports the database of the containerized neo4j instance to an external volume.
## Component
* **export_bind_mounth.sh**: Bash script

---

# shutdown_neo4j
## Purpose
Shuts down the containerized neo4j instance gracefully within the Docker container. 
Controlled, explicit shutdown allows the neo4j instance to clean up and close files and prevents 
"code 137" process errors in Docker.
## Component
* **shutdown_neo4j.sh**: Bash script

---

# build_distribution_zip
## Purpose
Builds a Zip archive that contains the minimal set of files necessary to start a local Docker container.
## Component
* **build_distribution_zip.sh*: Bash script

