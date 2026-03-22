#!/bin/bash
# -------------------------
# JSON Knowledge Graph (JKG)
# JKG JSON validation script:
# 1. Reads a common configuration file of properties of a Docker container hosting an instance of neo4j with an external bind mount.
# 2. Validates a JSON file in JSON Knowledge Graph (JKG) format, using [jsonschema](https://python-jsonschema.readthedocs.io/en/latest/)
# 3. Logs validation errors to a CSV file.

# Assumptions:
# 1. The validation script is part of a suite of tools supporting a Docker deployment of a neo4j host of a JKG instance.
# 2. The script uses the jkg-neo common configuration file (container.cfg).
# 3. There is a folder, specified by configuration, that contains a JSON file in JSON Knowledge Graph format.
#    The contents of this folder will be copied into the import bind mount.

###########
# Help function
##########
Help()
{
   # Display Help
   echo ""
   echo "****************************************"
   echo "HELP: JKG neo4j JSON validation script"
   echo "Validates a JSON file in JKG format against the JKG Schema."
   echo
   echo "Syntax: ./validate_jkg_json.sh [-c config file]"
   echo "options (in any order)"
   echo "-c   path to config file containing properties for the container (REQUIRED: default='container.cfg'."
   echo "-h   print this help"
   echo "example: './validate_jkg_json.sh' validates the JSON file specified in the config file."
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

# JKG JSON import defaults
log_dir="./python/log"
log_file="import_jkg_json.log"
jkg_json_dir="./json"
jkg_json_file="jkg.json"
jkg_batch_size=1000000
jkg_schema_json="JKG_Schema.json"


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

jkg_schema_full="$jkg_json_dir/$jkg_schema_json"
if [ ! -e "$jkg_schema_full" ]
  then
    echo "Error: schema file '$jkg_schema_full' not in '$jkg_json_dir."
    exit 1;
fi

if [ "$jkg_batch_size" -le 0 ]
  then
    echo "Invalid value for batch size: '$jkg_batch_size'"
    echo 'Either accept the default (1000000) or specify jkg_batch_size in the config file.'
    exit 1;
fi



echo ""
echo "**********************************************************************"
echo "Validating JSON"
echo " - JSON source file: $jkg_json "


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

python3 ./python/validate_jkg_json.py
