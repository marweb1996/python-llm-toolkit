#!/bin/bash
#SBATCH --partition=isds
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --output=ollama_serve_batch.log
#SBATCH --error=ollama_serve_batch_error.log

# Define a variable for the port number
PORT_NUMBER=11434

# Run the Python program
OLLAMA_HOST=0.0.0.0:$PORT_NUMBER ~/ollama-linux-amd64 serve >> ollama_serve.log
