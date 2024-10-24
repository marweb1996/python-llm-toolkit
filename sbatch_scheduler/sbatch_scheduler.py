import subprocess
import time
import argparse
import os
import re
import threading
from utils import parse_remote_host
from check_squeue import check_squeue

port_forwarding_process = None

def get_remote_home_directory(user_host, port):
    try:
        command = ['ssh', user_host, 'echo $HOME']
        if port:
            command = ['ssh', '-p', port, user_host, 'echo $HOME']
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        home_directory = result.stdout.strip()
        
        return home_directory
    except Exception as e:
        print(f"An error occurred while retrieving the home directory: {e}")
        return None

def replace_port_in_script(script_content, new_port_number):
    # Use regular expression to find a line that sets the port number
    return re.sub(r'PORT_NUMBER=\d+', f'PORT_NUMBER={new_port_number}', script_content)

def create_script_on_remote(script_content, script_name, remote_dir, host, skip_creation):
    try:
        # Parse remote host
        user_host, port = parse_remote_host(host)
        
        if not remote_dir:
            # Get home directory if no directory is specified
            remote_dir = get_remote_home_directory(user_host, port)
            if not remote_dir:
                print("Unable to retrieve the remote home directory.")
                return False

        remote_path = f"{remote_dir}/{script_name}"
        remote_check_command = f'ssh {user_host} "test -f {remote_path} && echo exists || echo not exists"'
        if port:
            remote_check_command = f'ssh -p {port} {user_host} "test -f {remote_path} && echo exists || echo not exists"'

        # Check if the remote script exists
        result = subprocess.run(remote_check_command, shell=True, capture_output=True, text=True)
        if result.stdout.strip() == "exists":
            if skip_creation:
                print("Skip creation: SBATCH script already exists on the remote host.")
                return True
            else:
                print("Re-creating SBATCH script on remote host...")
        
        # Create the script remotely
        remote_create_command = f'ssh {user_host} "cat > {remote_path}"'
        if port:
            remote_create_command = f'ssh -p {port} {user_host} "cat > {remote_path}"'
        
        process = subprocess.Popen(remote_create_command, shell=True, stdin=subprocess.PIPE)
        process.communicate(script_content.encode())
        
        if process.returncode == 0:
            print(f"Successfully created script at {remote_path} on remote host")
            return True
        else:
            print("Failed to create the script on the remote host")
            return False
        
    except Exception as e:
        print(f"An error occurred while creating the script on the remote host: {e}")
        return False

def submit_job(sbatch_script, host):
    try:
        # Parse remote host
        user_host, port = parse_remote_host(host) if host else (None, None)

        # Build the submit command
        command = ['sbatch', sbatch_script]
        if user_host:
            if port:
                command = ['ssh', '-p', port, user_host] + command
            else:
                command = ['ssh', user_host] + command

        # Submit the job using the sbatch command
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Parse the job ID from the output
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            if "Submitted batch job" in line:
                job_id = int(line.split()[-1])
                print(f"Submitted batch job {job_id}")
                return job_id

        print("Failed to parse job ID from submission output")
        return None

    except Exception as e:
        print(f"An error occurred while submitting job: {e}")
        return None

def monitor_job(job_id, user, host):
    try:
        running = False
        while not running:
            success, time_value, job_user, node = check_squeue(jobid=job_id, user=user, remote_host=host)
            if not success:
                print("Job not found, retrying in 10 seconds...")
                time.sleep(10)
                continue

            if time_value != "0:00":
                print(f"Job {job_id} is running for USER {job_user} (Time: {time_value})")
                running = True
            else:
                print(f"Job {job_id} for USER {job_user} is still pending. Checking again in 10 seconds...")
                time.sleep(10)

        return True, node

    except Exception as e:
        print(f"An error occurred while monitoring the job: {e}")
        return False

def stop_job(job_id, host):
    try:
        # Parse remote host
        user_host, port = parse_remote_host(host) if host else (None, None)

        # Build the scancel command
        command = ['scancel', str(job_id)]
        if user_host:
            if port:
                command = ['ssh', '-p', port, user_host] + command
            else:
                command = ['ssh', user_host] + command

        # Execute the scancel command
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.returncode == 0:
            print(f"Successfully canceled job {job_id}")
        else:
            print(f"Failed to cancel job {job_id}")
            print(result.stderr)

    except Exception as e:
        print(f"An error occurred while stopping the job: {e}")

def execute_port_forwarding(local_port, remote_port, user, node):
    def port_forward():
        global port_forwarding_process
        try:
            cmd = [
                'ssh',
                '-o', 'TCPKeepAlive=yes',
                '-o', 'ServerAliveInterval=30',
                '-L', f'{local_port}:127.0.0.1:{remote_port}',
                '-N',
                f'{user}@{node}.tugraz.at'
            ]
            port_forwarding_process = subprocess.Popen(cmd)
            port_forwarding_process.wait()  # Wait for process to complete
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while executing port forwarding: {e}")

    # Run port forwarding in a new thread
    thread = threading.Thread(target=port_forward)
    thread.start()
    
def cleanup(job_id, host):
    """Terminate port forwarding process and stop the job."""
    if port_forwarding_process:
        port_forwarding_process.terminate()
        print("Port forwarding stopped.")
    stop_job(job_id, host)

def main():
    parser = argparse.ArgumentParser(description="Submit and monitor SBATCH job on a remote host, then execute a script locally when the job starts running, optionally stopping the job after completion.")
    parser.add_argument('--sbatch-script', type=str, help="The local SBATCH script file to copy and submit.")
    parser.add_argument('--remote-sbatch-script', type=str, help="The SBATCH script path to use on the remote host if it exists.")
    parser.add_argument('--sbatch-script-dir', type=str, help="The directory on the remote host where the SBATCH script should be created. Defaults to the user's home directory.")
    parser.add_argument('--skip-sbatch-script-creation', action='store_true', help="Skip the creation of the SBATCH script on the remote host if it already exists.")
    parser.add_argument('--ollama-port', type=int, default=11434, help="The PORT_NUMBER to be used in the SBATCH script.")
    parser.add_argument('--local-ollama-port', type=int, default=11434, help="The local port for port forwarding.")
    parser.add_argument('--script', type=str, help="The Python script to run locally when the job starts running.")
    parser.add_argument('-u', '--user', type=str, required=True, help="Specify USER to filter.")
    parser.add_argument('-host', '--host', type=str, required=True, help="Specify the remote HOST in format user@host:port to submit and monitor the job.")
    parser.add_argument('--stop', action='store_true', help="Stop the specific SBATCH job after running the script.")
    parser.add_argument('--keep-alive', action='store_true', help="Keep the job running until the script is manually stopped using Ctrl+D.")
    parser.add_argument('--port-forwarding', action='store_true', help="Enable port forwarding.")

    args = parser.parse_args()

    # Check for required script arguments
    if not (args.sbatch_script or args.remote_sbatch_script):
        print("You must specify either --sbatch-script or --remote-sbatch-script.")
        return

    # Create the SBATCH script content with the specified port
    if args.sbatch_script:
        with open(args.sbatch_script, 'r') as file:
            original_script_content = file.read()
        script_content = replace_port_in_script(original_script_content, args.ollama_port)
        
        script_name = os.path.basename(args.sbatch_script)
        success = create_script_on_remote(
            script_content, 
            script_name, 
            args.sbatch_script_dir, 
            args.host, 
            args.skip_sbatch_script_creation
        )
        if not success:
            print("Script creation failed. Exiting.")
            return
        
        sbatch_script = f"{args.sbatch_script_dir}/{script_name}" if args.sbatch_script_dir else f"{get_remote_home_directory(*parse_remote_host(args.host))}/{script_name}"
    else:
        sbatch_script = args.remote_sbatch_script

    # Submit and monitor the job
    job_id = None
    try:
        job_id = submit_job(sbatch_script, args.host)
        if job_id is not None:
            success, node = monitor_job(job_id, args.user, args.host)

            if success:
                print(f"Job ({job_id}) running on node '{node}'")
                if args.port_forwarding:
                    execute_port_forwarding(args.local_ollama_port, args.ollama_port, args.user, node)
                else:
                    print(f"To enable port forwarding, run the following command:\nssh -o TCPKeepAlive=yes -o ServerAliveInterval=30 -L {args.local_ollama_port}:127.0.0.1:{args.ollama_port} {args.user}@{node}.tugraz.at")

                if args.script:
                    print("Running the script: {}".format(args.script))
                    subprocess.run(['python3', args.script])
            else:
                print(f"Error running job ({job_id})")
                cleanup(job_id, args.host)

            if args.keep_alive:
                print("Keep-alive mode enabled. Press Ctrl+C to stop the job and exit.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("Detected script termination. Stopping job...")
                    cleanup(job_id, args.host)
            elif args.stop:
                print("Stopping job ID: {}".format(job_id))
                stop_job(job_id, args.host)
    except KeyboardInterrupt:
        print("Program interrupted. Cleaning up...")
        cleanup(job_id, args.host)

if __name__ == "__main__":
    main()
