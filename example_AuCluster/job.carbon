#!/bin/bash
#PBS -l nodes=1:ppn=8
#PBS -l walltime=24:00:00
#PBS -A cnm99999
#PBS -N casting_AuCluster
#PBS -o job.out
#PBS -j oe
#PBS -m ea

cd $PBS_O_WORKDIR

python="/sandbox/hchan/env-casting/bin/python"

$python -m CASTING inputs.json
