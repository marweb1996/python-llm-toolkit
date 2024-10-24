# SBATCH Job Scheduler

This project provides a Python script to submit and monitor SBATCH jobs on a remote host. The script allows you to:
- Submit an SBATCH job to a remote cluster.
- Monitor the job's status until it starts running.
- Optionally stop the SBATCH job on the remote host after the local script has completed.
- Support for SSH port forwarding for secure connections.

## Prerequisites

1. **Python Environment**: Ensure you have Python 3.x installed.
2. **SSH Access**: Set up SSH keys for passwordless access to the remote cluster (ssh-copy-id).

## Usage

### Example Command
```sh
python3 sbatch_scheduler.py --sbatch-script ollama_serve.sh -u <username> -host <username>@nvcluster.tugraz.at --keep-alive --ollama-port=<port-number> --port-forwarding
```

### Arguments

- `--sbatch-script`: The SBATCH script file to submit.
- `--remote-sbatch-script`: The path to an SBATCH script already on the remote host.
- `--script` (optional): The Python script to run locally when the job starts running.
- `-u, --user` (default: `marweb`): The user name for filtering jobs in the queue.
- `-host, --host`: The remote host in the format `user@host:port` to submit and monitor the job.
- `--sbatch-script-dir`: Directory on remote host where SBATCH script should be created. Defaults to the user's home directory.
- `--ollama-port`: Specify the port number used in the SBATCH script. Default is `28010`.
- `--local-ollama-port`: Specify the local port for forwarding. Default is `11434`.
- `--port-forwarding`: Enable or disable port forwarding. Use `true` to enable.
- `--skip-sbatch-script-creation`: Skip creating the SBATCH script on the remote host if it already exists.
- `--stop` (optional): Stop the specific SBATCH job after running the specified script.
- `--keep-alive`: Keep the job running until manually stopped using Ctrl+C.

## SSH Port Forwarding

If `--port-forwarding` is enabled, a secure channel is established to forward a local port to a remote port. This can be helpful when you want to access services running on the remote cluster locally.

## Error Handling and Interrupts

In case of a keyboard interrupt (Ctrl+C), the script will terminate any running processes gracefully and clean up by stopping any ongoing port forwarding and submitted jobs if specified.