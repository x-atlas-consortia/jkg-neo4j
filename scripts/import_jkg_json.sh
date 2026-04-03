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
   echo "Syntax: ./import_jkg_json.sh [-c config file]"
   echo "options (in any order)"
   echo "-c   path to config file containing properties for the container (REQUIRED: default='container.cfg'."
   echo "-h   print this help"
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

# Copy the JKG JSON path (including the batch subdirectory) from the source directory to the import directory. This step is necessary: if you create a container with a
# bind mount to an non-empty directory, the bind mount will obscure the bound directory's existing content--i.e., it will not
# recognize it. To work around this, copy files to the bind mount after it is created.
echo "Copying JKG JSON files to $import_dir"
cp -rp "$jkg_json_dir" "$import_dir"

# Delete the specified JKG database from the external bind mount, if it exists.
echo "Dropping existing ontology database files from external bind mount."
rm -fr "$base_dir/data/databases/data/ontology"
rm -fr "$base_dir/data/transactions/ontology"
echo ""


# Run the validation Python script, setting up a virtual environment if necessary.
bash "$(dirname "${BASH_SOURCE[0]}")/run_python_venv.sh" ./python/import_jkg_json.py
