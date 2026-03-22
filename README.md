# jkg-neo4j
**jkg-neo4j**: tools to support a containerized neo4j instance of a graph database populated with data 
imported from a file that conforms to the [JSON Knowledge Graph (JKG)](https://github.com/x-atlas-consortia/json-knowledge-graph) schema.

# Background

## JKG format
The JKG format is intended to support platform-agnostic transfers of
knowledge graphs. A file that conforms to the JKG JSON schema is called a JKG JSON file.

It should be possible:
+ to import data from a JKG JSON file into a graph database
+ to export data from a graph database to a JKG JSON file

## Dockerized neo4j distributions
A useful method to demonstrate the features of a knowledge graph is to provide the graph 
as part of a distribution that includes a fully-functional instance of a graph database application 
configured to work with the knowledge graph.

If a distribution of a graph database application with its data is in a container such as Docker, 
users only need the container management application to run the graph database on local machines.

The tools in **jkg-neo4j** support the building of a Docker container host of
an instance of neo4j Community Edition, containing a graph database imported from a JKG JSON. 

The container can be distributed as a "turnkey" Zip archive. Users instantiate a local copy of the
distribution by unzipping the archive and running a single command. Users would be able to export data 
from the distribution's graph database to a file in JKG format.

# Architecture
The **jkg-neo4j** architecture comprises:
* a Docker image in Docker Hub running neo4j Community Edition
* a Docker Compose configuration
* a suite of custom Shell and Python scripts

The architecture supports both building a turnkey distribution from source and installing the 
distribution locally.

# Tool patterns
## Separation of concerns, common configuration

* Deployment tasks are separated where possible. The current tasks include:
  * validation of the source JSON
  * import of the source JSON into the neo4j instance
  * build of the Docker container
  * build of the distribution Zip
* All tools rely on a common framework configuration file named **container.cfg**. The template for the file is named **container.cfg.example**.

## Components
* Each tool comprises two scripts:
  * A [Bash](https://en.wikipedia.org/wiki/Bash_(Unix_shell)) script that:
    * verifies configuration specific to the tool
    * when necessary, creates a Python virtual environment
    * invokes a Python script
  * A Python script, usually with the same filename as its Bash script, but different file extension.
  
## Python script functionality
Python scripts:
  * employ reusable, common classes where possible
  * use a common logging method
  * read the common configuration file
  * display two types of real-time progress monitors (using [tqdm](https://tqdm.github.io/)):
    * progress bars for loop-based processes, including file reads
    * timers (spinners) for long-running black box processes
## File locations
* Bash scripts are in the _scripts_ directory.
* Python scripts are in the _scripts/python_ path.
* Common Python classes are in the _scripts/python/classes_ path.
* With respect to relative file locations, tools assume that they are in a local application directory that contains a copy of the entire _scripts_ directory. 

# Build Workflow (Work in Progress)
![img.png](img.png)

# Deployment Workflow (Work in Progress)
