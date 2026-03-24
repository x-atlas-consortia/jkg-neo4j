#!/bin/bash
# -------------------------
# JSON Knowledge Graph (JKG)
# Database batch distribution script:
# 1. Reads a configuration file of properties of a Docker container hosting an instance of neo4j with an external bind mount.
# 2. Reads a JSON file that complies with JKG format
# 3. Divides the JKG JSON file into sets of smaller JSON files. Each file contains
#    an array of objects that are of one of the following types:
#    a. nodes
#    b. rels (relationships between concepts)
#    c. coderels (relationships between concepts and codes)
#

# Assumptions:
# 1. There is a folder, specified by configuration, that contains a JSON file in JSON Knowledge Graph format.


###########
# Help function
##########
Help()
{
   # Display Help
   echo ""
   echo "****************************************"
   echo "HELP: JKG neo4j JSON batch script"
   echo "Divides a JSON file in JKG format into a set of smaller batch files."
   echo
   echo "Syntax: ./batch_jkg_json.sh [-c config file]"
   echo "options (in any order)"
   echo "-c   path to config file containing properties for the container (REQUIRED: default='container.cfg'."
   echo "-h   print this help"
   echo "example: './batch_jkg_json.sh' distributes a JKG JSON file"
   echo "Review container.cfg.example for descriptions of parameters."
}
##############################
# Set defaults.
config_file="container.cfg"

# Default relative paths
# Get relative path to current directory.
base_dir="$(dirname -- "${BASH_SOURCE[0]}")"
# Convert to absolute path.
base_dir="$(cd -- "$base_dir" && pwd -P;)"

# JKG JSON batch defaults
log_dir="./python/log"
log_file="batch_jkg_json.log"
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
# VALIDATE RELEVANT PARAMETERS FROM CONFIG FILE.

# Common logging directory
if [ ! -e "$log_dir" ]
  then
    echo "Error: log dir '$log_dir' not found".
    echo "Either accept the defaults or specify log_dir in the config file."
    exit 1;
fi

# JKG JSON file
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

# Batch size
if [ "jkg_batch_size" == "" ]
then
  echo "Error: No batch size specified."
  echo "Either accept the default (1000000) or specify a value in container.cfg."
  exit;
fi

echo ""
echo "**********************************************************************"
echo "Batching JKG JSON"
echo " - JSON source file: $jkg_json "

# Run the Python script, setting up a virtual environment if necessary.
bash "$(dirname "${BASH_SOURCE[0]}")/run_python_venv.sh" ./python/batch_jkg_json.py

