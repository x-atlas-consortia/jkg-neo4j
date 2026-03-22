# jkg-neo4j
## Tools 

For an explanation of tool patterns, consult the main README.md.

# validate_jkg_json

## Purpose
Validates a JSON file in JSON Knowledge Graph (JKG) format against the [JKG Schema](https://github.com/x-atlas-consortia/json-knowledge-graph/blob/main/JKG_Schema.json).
## Components
* **validate_jkg_json.sh**: Bash script
* **validate_jkg_json.py**: Python script
## Inputs
* **JKG JSON** - a JSON file in JKG format that represents a knowledge graph. 
* **JKG Schema** - the JKG schema
Input file names and locations are specified in the common configuration file.

## Outputs
* **validate_jkg_json.log** - application log
* **validation_errors.csv** - CSV of samples of validation errors

### Configurable validation sampling
A JKG JSON file is likely to be large: for example, the JKG JSON produced from the 2025AB release of the UMLS is 4.4 GB.
Validation of the entire JKG JSON will likely require a considerable amount of time.

Validation of the entire file is often unnecessary; because there are only a few types of nodes in the specification that are generated via script, an error in one node is likely to be common to all nodes of the same type.

To facilitate the use of validation, the validation script allows for validation by sampling. 
The validation script can "chunk" through the JKG JSON, evaluating subsets of nodes and returning only one validation error per chunk. 
Reducing the size of the chunk increases the validation resolution.

# import_jkg_json
## Purpose
Imports a JKG JSON file into the neo4j instance hosted by the jkg-neo4j Docker container.

The script:
* distributes the JKG JSON file into a set of smaller files
* iteratively imports the smaller files into neo4j
* creates indexes and constraints in the neo4j database
## Components
* **import_jkg_json.sh**: Bash script
* **import_jkg_json.py**: Python script
## Input
A JKG JSON file

## Outputs
* **import_jkg_json.log**: application log

## Assumption
The JKG JSON source has been validated against the JKG Schema.

