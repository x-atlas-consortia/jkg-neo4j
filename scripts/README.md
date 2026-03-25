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

## Components
* **validate_jkg_json.sh**: Bash script
* **validate_jkg_json.py**: Python script

## Inputs
* JSON files
  * If the JKG JSON has been batched, schema validation will work with the batched files that were created in the _/batch_ subdirectory.
  * If the JKG JSON has not been batched, schema validation will work with the entire JKG JSON file.
  * If spot-validation has been specified in the **container.cfg** file (_schema_validation_spot_=true and _num_spot_checks_= a number), then schema validation will work with a random selection of files from the batch file directory.
*  **JKG Schema** - the JKG schema
  
Input file names and locations are specified in the common configuration file.

## Types of validation
**validate_jkg_json** can perform two types of validation:
1. **Schema validation** against the [JKG Schema](https://github.com/x-atlas-consortia/json-knowledge-graph/blob/main/JKG_Schema.json), using the [jsonschema](https://python-jsonschema.readthedocs.io/en/latest/) package.
2. **Structural validation**:
   * checks for duplicate nodes
   * checks for "referential integrity"--e.g., that node identifiers in the **rels** array have corresponding elements in the **nodes** array; etc.

# Configurable scope for schema validation
The scope of schema validation can be controlled by values in the **container.cfg** configuration file.
Limiting the scope of schema validation can speed debugging.

## Structural validation
Structural validation requires the entire JKG JSON file; however, it is possible to specify the types of checks with boolean flags:
   * **check_uniqueness**
   * **check_referential**
## Schema validation
Schema validation scope can be finely controlled via configuration.
### Parallelized schema validation
  * _schema_validation_parallel_ is a boolean flag.
    * If _true_, then schema validation will employ parallel processing, and work on batch files.
    * If not _true_, then schema validation will work with the entire JKG JSON.
  * _jkg_validate_chunk_ is an integer that specifies the number of nodes in each parallel processing chunk. _jkg_validate_chunk_ should be at least 100, to prevent timeout errors in parallel processes.
### Spot checking
Spot checking allows for validation of a random sample of batch files.
  * _schema_validation_spot_ is a boolean flag; if true, then schema validation will work with a random subset of batch files. 
  * _num_spot_checks_ is an integer that specifies the number of batch files to select for spot checking
### Individual batch file validation
It is possible to evaluate a specific set of individual batch files.
* _batch_files_ is a list of file names to evaluate. 

Specific batch file validation overrides all other forms of schema validation.

## Schema validation by parallel processing
A JKG JSON file is likely to be extremely large: for example, the JKG JSON produced from the 2025AB release of the UMLS is 4.4 GB.
Validation of an entire JKG JSON against the entire JKG schema will likely require a considerable amount of time.

To speed validation, the validation script allows for schema validation by parallel processing. 
The validation script distributes "chunks" of an input JSON file among a set of
"worker" processes that work in parallel.

The size of the chunk for parallel schema validation should be large enough to allow worker processes to finish before timeout.
The script will warn if the chunk size is below 100.

Schema validation using parallel processing is only available for batched JKG JSON files.

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

Validation will show progress bars when:
* parsing JSON files
* validating JSON files against the schema in parallel

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

