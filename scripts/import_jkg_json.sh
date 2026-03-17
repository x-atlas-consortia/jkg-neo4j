#!/bin/bash
# -------------------------
# JSON Knowledge Graph (JKG)
# Database Import script:
# 1. Reads a configuration file of properties of a Docker container hosting an instance of neo4j with an external bind mount.
# 2. Connects to the Docker container.
# 3. Imports a source JSON in JKG format into a new database named ontology.
# 4. Replaces the content of the neo4j database directories (databases and transactions directories) with the content
#    from ontology.
#

# Assumptions:
# 1. The Docker container specified by the configuration file has external bind mounts to folders in the application
#    directory named
#    - data
#    - import
# 2. There is a folder, specified by configuration, that contains a JSON file in JSON Knowledge Graph format.
#    The contents of this folder will be copied into the import bind mount.
# 3. neo4j Community Edition, which can only have one database. Because the neo4j has already been instantiated,
#    the database name has to be neo4j.


###########
# Help function
##########
Help()
{
   # Display Help
   echo ""
   echo "****************************************"
   echo "HELP: JKG neo4j JSON import script"
   echo "Imports a JSON file in JKG format into a new ontology database in a neo4j instance hosted in a Docker container."
   echo
   echo "Syntax: ./export_db.sh [-c config file]"
   echo "options (in any order)"
   echo "-c   path to config file containing properties for the container (REQUIRED: default='container.cfg'."
   echo "-h   print this help"
   echo "example: './import_csvs.sh' exports the data folder of the container specified in the config file."
   echo "Review container.cfg.example for descriptions of parameters."
}
##############################
# Set defaults.
config_file="container.cfg"
container_name="jkg-neo4j"

# Default relative paths
# Get relative path to current directory.
base_dir="$(dirname -- "${BASH_SOURCE[0]}")"
# Convert to absolute path.
base_dir="$(cd -- "$base_dir" && pwd -P;)"

# External bind mount to import folder. This must be different than the CSV folder; if a bind mount
# points to a non-empty folder, Docker "obscures" the existing contents.
import_dir="$base_dir/import"

# Default Java max heap setting for CSV import, based on recommendations for
# a machine with 32 GB of RAM working with a neo4j instance with a 27 GB database
# (Data Distillery).
heap_import="1.003g"

# JKG JSON import defaults
log_dir="./python/log"
log_file="import_jkg_json.log"
jkg_json_dir="./json"
jkg_json_file="jkg.json"
jkg_batch_size=1000000


##############################
# PROCESS OPTIONS
while getopts ":hc:" option; do
  case $option in
    h) # display Help
      Help
      exit;;
    c) # config file
      config_file=$OPTARG;;
    \?) # Invalid option
      echo "Error: Invalid option"
      exit;;
  esac
done

##############################
# READ PARAMETERS FROM CONFIG FILE.

if [ "$config_file" == "" ]
then
  echo "Error: No configuration file specified. This script obtains parameters from a configuration file."
  echo "Either accept the default (container.cfg) or specify a file name using the -c flag."
  exit;
fi
if [ ! -e "$config_file" ]
then
  echo "Error: no config file '$config_file' exists."
  exit 1;
else
  source "$config_file";
fi

##############################
# VALIDATE PARAMETERS FROM CONFIG FILE.

# Check for Docker container name.
if [ "$container_name" == "" ]
then
  echo "Error: no Docker container name. Either accept the default (jkg-neo4j) or specify container_name in the config file."
  exit 1;
fi

if [ ! -e "$log_dir" ]
  then
    echo "Error: log dir '$log_dir' not found".
    echo "Either accept the defaults or specify log_dir in the config file."
    exit 1;
fi

if [ ! -e "$jkg_json_dir" ]
  then
    echo "Error: source path '$jkg_json_dir' not found."
    echo 'Either accept the default or specify jkg_json_dir in the config file.'
    exit 1;
fi

jkg_json_full="$jkg_json_dir/$jkg_json_file"
if [ ! -e "$jkg_json_full" ]
  then
    echo "Error: source file '$jkg_json_file' not in '$jkg_json_dir."
    exit 1;
fi

if [ "$jkg_batch_size" -le 0 ]
  then
    echo "Invalid value for batch size: '$jkg_batch_size'"
    echo 'Either accept the default (1000000) or specify jkg_batch_size in the config file.'
    exit 1;
fi




# max Java heap memory
#if [ "$heap_import" == "" ]
#then
  #echo "Error: no value of max Java heap memory for CSV import specified."
  #echo "Either accept the default (1.003g) or specify a value for heap_indexing in the configuration file."
  #echo "(Run ./neo4j-admin import in the Docker container for recommendations for the size max Java heap memory for your machine.)"
  #exit 1;
#fi


echo ""
echo "**********************************************************************"
echo "Importing JSON"
echo " - JSON source file: $jkg_json "
echo " - Docker container: $container_name"

# Connect to the neo4j instance and import JSON.

# Neo4j installation directory.
NEO4J=/usr/src/app/neo4j

# The assumption is that the internal import folder has been linked to an external bind mount,
# by means of running build_container.sh and specifying db_mode=external in the config file.
IMPORT="$NEO4J"/import

# Copy the JKG JSON from the source directory to the import directory. This step is necessary: if you create a container with a
# bind mount to an non-empty directory, the bind mount will obscure the bound directory's existing content--i.e., it will not
# recognize it. To work around this, copy files to the bind mount after it is created.
cp "$jkg_json" "$import_dir"

# Delete the specified JKG database from the external bind mount, if it exists.
echo "Dropping existing ontology database files from external bind mount."
rm -fr "$base_dir/data/databases/data/ontology"
rm -fr "$base_dir/data/transactions/ontology"
echo ""

# MAX HEAP MEMORY
# THIS MAY NOT FACTOR INTO APOC JSON IMPORT.
# By default, neo4j uses heuristics to calculate max heap allocation. This can result in an overly large max
# heap size for the import, which will limit memory for other processes and result in slow imports.
# For example, on a MacBook Pro M1 with 32 GB of RAM, importing a set of CSVs with 1824 relationships results in
# a warning like:
# WARNING: heap size 1.705GiB is unnecessarily large for completing this import.
# The abundant heap memory will leave less memory for off-heap importer caches. Suggested heap size is 1.003GiBNodes
#
# The messages then show that each relationship is processed individually--e.g., the import displays messages like this
#Relationship <-- Relationship 6/1824, started 2023-12-13 15:09:21.716+0000

# When there is sufficient memory, the entire group of relationships is processed in parallel--e.g.,
#Relationship <-- Relationship 1-1824/1824, started 2023-12-12 00:07:53.244+0000

# Set heap memory explicitly immediately before import using the JAVA_OPTS environment variable instead of in the
# neo4j.conf file's dbms.memory.heap.initial_size setting.
# The machine building the Docker container from a distribution may not have the same memory
# as the development machine.
# bash -c directs the container to execute the command in the string.

#echo "Setting max heap size explicitly to recommended value for import ($heap_import)."
#docker exec "$container_name" \
#bash -c "export JAVA_OPTS='-server -Xms$heap_import -Xmx$heap_import'"


# Execute the python script to import the JSON.
VENV=./venv

echo "Executing Python script to import JKG JSON..."
if [[ -d ${VENV} ]] ; then
  echo "*** Using Python venv in ${VENV}"
  source ${VENV}/bin/activate
else
  echo "*** Installing Python venv to ${VENV}"
  python3 -m venv ${VENV}
  python3 -m pip install --upgrade pip
  source ${VENV}/bin/activate
  echo "*** Installing required packages..."
  pip install -r ./python/requirements.txt
  echo "*** Done installing python venv"
fi

python3 ./python/import_jkg_json.py
