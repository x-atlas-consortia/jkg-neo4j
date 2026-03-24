#!/bin/bash
# -------------------------
# Common helper script that:
# 1. Sets up Python virtual environment
# 2. Installs dependencies
# 3. Runs a Python script
# Usage: ./run_python_venv.sh <path_to_python_script> <path_to_requirements>
# Example: ./run_python_venv.sh ./python/validate_jkg_json.py ./python/requirements.txt

# Set strict mode for Bash so that failures in subtasks such as python or pip install
# fail loudly.
set -euo pipefail

# Get arguments:
# 1. Path to the python script
PYTHON_SCRIPT="${1:-}"
# 2. Path to the requirements.txt file of dependencies.
#    Default path is in the python subdirectory.
REQUIREMENTS="${2:-./python/requirements.txt}"

if [[ -z "$PYTHON_SCRIPT" ]]; then
  echo "Error: No Python script specified."
  echo "Usage: $0 <path_to_python_script>"
  exit 1
fi

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
  echo "Error: Python script '$PYTHON_SCRIPT' not found."
  exit 1
fi

if [[ -z "$REQUIREMENTS" ]]; then
  echo "Error: No Python script specified."
  echo "Usage: $0 <path_to_requirements>"
  exit 1
fi

if [[ ! -f "$REQUIREMENTS" ]]; then
  echo "Error: '$REQUIREMENTS' not found."
  exit 1
fi

# Set the virtual environment path.
unset VENV
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VENV="${SCRIPT_DIR}/venv"

echo "Executing Python script: $PYTHON_SCRIPT"

if [[ -d "${VENV}" ]]; then
  echo "*** Using existing Python venv in ${VENV}"
  source "${VENV}/bin/activate"
else
  echo "*** Installing Python venv to ${VENV}"
  python3 -m venv "${VENV}"
  python3 -m pip install --upgrade pip
  source "${VENV}/bin/activate"
  echo "*** Installing required packages..."
  pip install -r "$REQUIREMENTS"
  echo "*** Done installing Python venv"
fi

python3 "$PYTHON_SCRIPT"