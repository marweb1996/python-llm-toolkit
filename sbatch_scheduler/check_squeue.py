import subprocess
from utils import parse_remote_host

def check_squeue(jobid=None, user=None, remote_host=None):
    try:
        # Build the command
        command = ['squeue', '-u', user]
        if jobid:
            command.append('-j')
            command.append(str(jobid))
        
        if remote_host:
            # Parse remote_host in format user@host:port
            user_host, port = parse_remote_host(remote_host)
            if port:
                ssh_command = ['ssh', '-p', port, user_host] + command
            else:
                ssh_command = ['ssh', user_host] + command

            command = ssh_command

        # Execute the squeue command
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Split the command output into lines
        output_lines = result.stdout.strip().split('\n')

        # Check if there are at least two lines (header and one job entry)
        if len(output_lines) < 2:
            print("No jobs found")
            return False, None, None

        # Iterate over the lines, skip the header
        for line in output_lines[1:]:
            # Split the line into columns
            columns = line.split()

            # JobID is the first column, USER is the 4th column, TIME is the 5th column
            job_user = columns[3]
            time_value = columns[5]
            node = columns[7]

            # Return the values
            return True, time_value, job_user, node

        return False, None, None
    except Exception as e:
        print(f"An error occurred: {e}")
        return False, None, None

# Example usage
if __name__ == "__main__":
    import argparse

    # Argument parser for optional JOBID, USER, and HOST
    parser = argparse.ArgumentParser(description="Check squeue for jobs with TIME != 0:00")
    parser.add_argument('-j', '--jobid', type=int, help="Specify JOBID to filter")
    parser.add_argument('-u', '--user', type=str, help="Specify USER to filter")
    parser.add_argument('-host', '--host', type=str, help="Specify HOST in format user@host:port to run the squeue command")

    args = parser.parse_args()
    success, time_value, user = check_squeue(args.jobid, args.user, args.host)
    if success:
        print(f"TIME: {time_value}, USER: {user}")
    else:
        print("Job not found or an error occurred.")
