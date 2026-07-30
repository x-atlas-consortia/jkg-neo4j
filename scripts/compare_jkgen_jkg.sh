#!/bin/bash

# Set strict mode for Bash so that failures in subtasks such as python or pip install
# fail loudly.
set -euo pipefail

# Run the version of run_python_env specific to the compare script, which has an additional argument for a list of SABs.
./run_python_venv_sablist.sh ./python/compare_jkgen_jkg.py "$@"