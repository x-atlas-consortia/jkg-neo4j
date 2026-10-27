#!/bin/bash
# -------------------------
# JSON Knowledge Graph (JBKG)
# Shuts down the JKG neo4j instance, waiting until all transactions are complete.
#

###########
# Help function
##########
Help()
{
   # Display Help
   echo ""
   echo "****************************************"
   echo "HELP: JKG neo4j shutdown script"
   echo "Shuts down a JKG database in a neo4j instance hosted in a Docker container."
   echo
   echo "Syntax: ./shutdown_neo4j.sh [-c config file]"
   echo "options (in any order)"
   echo "-c   path to config file containing properties for the container (REQUIRED: default='container.cfg'."
   echo "-h   print this help"
   echo "example: './shudown_neo4j.sh' shuts down the container/instance specified in the config file."
   echo "Review container.cfg.example for descriptions of parameters."
}
##############################
# Set defaults.
config_file="container.cfg"
container_name="jkg-neo4j"
neo4j_user="neo4j"

# Default relative paths
# Get relative path to current directory.
base_dir="$(dirname -- "${BASH_SOURCE[0]}")"
# Convert to absolute path.
base_dir="$(cd -- "$base_dir" && pwd -P;)"


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
  echo "Error: no Docker container name. Either accept the default (ubkg-neo4j) or specify container_name in the config file."
  exit 1;
fi

echo ""
echo "**********************************************************************"
echo "Shutting down neo4j server"
echo " - Docker container: $container_name"

# Neo4j binary directory.
NEO4J=/usr/src/app/neo4j/bin

# Set the shutdown timeout to 5 minutes.
echo "Stopping container $container_name..."
docker stop -t 300 "$container_name"

while [ "$(docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null)" == "true" ]; do
  sleep 2
  echo "Still waiting for container $container_name to stop..."
done
echo "Container $container_name has stopped."

##############################
# VERIFY CLEAN SHUTDOWN — run all checks before declaring success.
all_checks_passed=true

echo "Verifying clean shutdown and checkpoint in debug.log..."
debug_log="$base_dir/logs/debug.log"
if [ ! -f "$debug_log" ]; then
  echo "WARNING: debug.log not found at $debug_log."
  all_checks_passed=false
else
  shutdown_confirmation=$(tail -200 "$debug_log" | grep -iE "checkpoint (completed|triggered)|Stopped\.")
  if [ -z "$shutdown_confirmation" ]; then
    echo "WARNING: No checkpoint/clean-stop confirmation found in debug.log."
    all_checks_passed=false
  else
    echo "Confirmed shutdown/checkpoint evidence:"
    echo "$shutdown_confirmation"
  fi
fi

echo "Checking for stale store_lock file on host bind mount..."
store_lock="$db_mount_dir/databases/neo4j/store_lock"
if [ -f "$store_lock" ]; then
  echo "WARNING: store_lock file still present at $store_lock — process may not have exited cleanly."
  all_checks_passed=false
else
  echo "No store_lock file present."
fi

##############################
# FINAL VERDICT.
if [ "$all_checks_passed" == "true" ]; then
  echo "All checks passed. Safe to zip the data directory at $db_mount_dir."
else
  echo "One or more checks failed. Do NOT trust the store as zip-safe without manual inspection."
  exit 1
fi

