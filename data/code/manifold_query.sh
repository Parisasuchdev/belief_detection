#!/bin/sh
# Specify a partition
#SBATCH --partition=bluemoon
# Request nodes
#SBATCH --nodes=1
# Request some processor cores
#SBATCH --ntasks=1
# Request memory
#SBATCH --mem=30G
# Run for 24 hours minutes
#SBATCH --time=30:00:00
# Name job
#SBATCH --job-name=manifold_data
# Name output file
#SBATCH --output=logs/%x_%j.out
# Set email address (for user with email "usr1234@uvm.edu")
#SBATCH --mail-user=psuchdev@uvm.edu
# Request email to be sent at begin and end, and if fails
#SBATCH --mail-type=FAIL
# change to the directory where you submitted this script
cd ${SLURM_SUBMIT_DIR}
# Executable section: echoing some Slurm data
echo "Assigned nodes: ${SLURM_JOB_NODELIST}"
echo "Job ID:     ${SLURM_JOBID}"
python connect.py
