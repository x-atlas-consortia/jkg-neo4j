# jkg-neo4j
## Tools 

For an explanation of tool patterns, including file structure of source files, 
consult the main README.md.

All tools work with a common configuation file named **container.cfg**. 
The file **container.cfg.example** in this repo serves as a template for **container.cfg**.

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

# validate_jkg_json

## Purpose
Validates a JSON file in JSON Knowledge Graph (JKG) format.

## Forms of validation
**validate_jkg_json** performs two types of validation:
1. Schema validation against the [JKG Schema](https://github.com/x-atlas-consortia/json-knowledge-graph/blob/main/JKG_Schema.json), using the [jsonschema](https://python-jsonschema.readthedocs.io/en/latest/) package.
2. Structural validation:
   * checks for duplicate nodes
   * checks for "referential integrity"--e.g., that node identifiers in the **rels** array have corresponding elements in the **nodes** array; etc.

## Components
* **validate_jkg_json.sh**: Bash script
* **validate_jkg_json.py**: Python script

## Validation by parallel processing
A JKG JSON file is likely to be extremely large: for example, the JKG JSON produced from the 2025AB release of the UMLS is 4.4 GB.
Validation of an entire JKG JSON against the entire JKG schema will likely require a considerable amount of time.

To speed validation, the validation script allows for validation by parallel processing. 
The validation script distributes "chunks" of an input JSON file among a set of
"worker" processes that work in parallel.

The size of the chunk for parallel schema validation should be large enough to allow worker processes to finish before timeout.
The script will warn if the chunk size is below 100.

## Inputs
* **JKG JSON** - a JSON file in JKG format that represents a knowledge graph. If the JKG JSON has been batched, schema validation will work with the batched files.
* **JKG Schema** - the JKG schema
Input file names and locations are specified in the common configuration file.

## Outputs
### in the /log directory:
* **validate_jkg_json.log**- application log
### in the input directory that contains the JKG JSON file:
* **validation_errors.tsv**
    
    TSV of validation errors. 
  * Errors are sorted by: 
    * array type (nodes first, then rels)
    * item - the JSON object in which the error was found
    * error message
  * When validation by sampling is performed, errors are returned in random order, so errors are sorted by item.

* **missing_X_.csv** - CSVs of missing **X** elements, including:
  * SABs not in the sources array
  * SABs in the properties of elements of the rels array but not in the sources array
  * concept labels not in node_labels
  * relationship labels not in rel_labels
  * start or end ids in rels without corresponding nodes
  
* **duplicate_*_.csv** - CSVs of duplicate elements, including:
  * duplicate node ids in the nodes array
  * duplicate SABs in the sources array
  * duplicate labels in the node_labels array
  * duplicate labels in the rel_labels array

### file rotation
* **validate_jkg_json.py** will append to **validate_jkg_json.log**. The developer will need to "rotate" the log manually by deleting it.
* **validate_jkg_json.py** will delete prior validation CSV files as part of execution.

### Interpreting schema validation error messages
The error messages from jsonschema can be cryptic. 
One way to interpret a schema validation error is to load both the item and the JKG JSON schema 
into a prompt to GitHub Copilot and asking for an explanation. Copilot can often describe the
validation error in greater detail.



# import_jkg_json
## Purpose
Imports a JKG JSON file into the neo4j instance hosted by the jkg-neo4j Docker container.

The script:
* reads each file in the set of distributed JKG JSON batch files
* iteratively imports the batch files into neo4j
* creates indexes and constraints in the neo4j database

## Components
* **import_jkg_json.sh**: Bash script
* **import_jkg_json.py**: Python script
## Input
A JKG JSON file

## Outputs
* **import_jkg_json.log**: application log

## Assumption
The JKG JSON source has been both
* validated against the JKG Schema
* batch distributed

# build_container
## Purpose
Builds a Docker container that hosts a neo4j instance. The script can
build a container either with an external volume mount or without. 

In the workflow to build a neo4j distribution, **build_container** executes numerous times:
* initially to build an empty "primer" neo4j instance without an external volume
* after export of the primer neo4j database to an external volume
* after import of JKG source
* to build a container from a distribution

## Components
* **build_container.sh**: Bash script

# export_bind_mount
## Purpose
Exports the database of the containerized neo4j instance to an external volume.
## Component
* **export_bind_mounth.sh**: Bash script

# shutdown_neo4j
## Purpose
Shuts down the containerized neo4j instance gracefully within the Docker container. 
Controlled, explicit shutdown allows the neo4j instance to clean up and close files and prevents 
"code 137" process errors in Docker.
## Component
* **shutdown_neo4j.sh**: Bash script

# build_distribution_zip
## Purpose
Builds a Zip archive that contains the minimal set of files necessary to start a local Docker container.
## Component
* **build_distribution_zip.sh*: Bash script

