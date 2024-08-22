export PYTHONPATH=${PYTHONPATH}:$SANDBOX/bin/lammps/python
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:$SANDBOX/bin/lammps/src

$SANDBOX/env-casting/bin/python -m CASTING inputs.json
