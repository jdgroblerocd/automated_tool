import os
import shutil
import subprocess

def create_directory(path):
    """Create a directory if it does not exist."""
    os.makedirs(path, exist_ok=True)

def get_project_name():
    """Prompt the user for a project name and create the project directory."""
    project_name = input("Enter the project name: ").strip()
    create_directory(project_name)
    return project_name

def get_scope_file():
    """Prompt the user for the project scope file."""
    while True:
        scope_file = input("Enter the path to the project scope file: ").strip()
        if os.path.isfile(scope_file):
            return scope_file
        else:
            print("File not found. Please enter a valid file path.")

def prompt_for_tools(tools):
    """Prompt the user for which tools to run and create corresponding directories."""
    selected_tools = []
    for tool in tools:
        choice = input(f"Do you want to run {tool}? (yes/no): ").strip().lower()
        if choice == "yes":
            selected_tools.append(tool)
    return selected_tools

def setup_tool_directories(project_name, selected_tools):
    """Create directories for each selected tool and return their paths."""
    tool_directories = []
    for tool in selected_tools:
        tool_directory = os.path.join(project_name, tool)
        create_directory(tool_directory)
        tool_directories.append(tool_directory)
    return tool_directories

def run_nmap_host_discovery(input_file, output_directory):
    """Run Nmap host discovery and clean the output to list only IP addresses."""
    create_directory(output_directory)
    output_base = os.path.join(output_directory, "alive_hosts")
    subprocess.run(['nmap', '-sn', '-iL', input_file, '-oA', output_base], check=True)

    # Extract IP addresses from the Nmap output
    with open(f"{output_base}.gnmap", "r") as file:
        lines = file.readlines()

    alive_hosts = [line.split()[1] for line in lines if "Status: Up" in line]

    # Write the cleaned IP addresses to a file
    alive_hosts_file = os.path.join(output_directory, "alive_hosts.txt")
    with open(alive_hosts_file, "w") as file:
        file.write("\n".join(alive_hosts))

    return alive_hosts_file

def run_nmap_port_scan(alive_hosts_file, output_directory):
    """Run Nmap SYN port scan on alive hosts and clean the output for processing."""
    output_base = os.path.join(output_directory, "open_ports")
    subprocess.run(['sudo', 'nmap', '-sS', '-p-', '-iL', alive_hosts_file, '-oA', output_base], check=True)

    # Extract IP addresses and ports from the Nmap output
    processed_output = []
    with open(f"{output_base}.gnmap", "r") as file:
        lines = file.readlines()

    for line in lines:
        if "Ports:" in line:
            ip = line.split()[1]
            ports = line.split("Ports: ")[1].split(", ")
            open_ports = [port.split("/")[0] for port in ports if "/open/" in port]
            for port in open_ports:
                processed_output.append(f"{ip}:{port}")

    processed_output_file = os.path.join(output_directory, "nmap_processed_output.txt")
    with open(processed_output_file, "w") as file:
        file.write("\n".join(processed_output))

    return processed_output_file

def copy_file_to_tool_directories(file_path, tool_directories):
    """Copy a file to each of the tool directories."""
    for tool_dir in tool_directories:
        shutil.copy(file_path, tool_dir)

def run_gowitness(directory, nmap_output_file):
    """Run Gowitness in the specified directory using the Nmap processed output file."""
    os.chdir(directory)
    subprocess.run([
        'docker', 'run', '--rm', '-v', f'{os.getcwd()}:/data', 'leonjza/gowitness',
        'gowitness', 'file', '-f', os.path.basename(nmap_output_file)
    ], check=True)

def main():
    # Step 1: Get project name and scope file
    project_name = get_project_name()
    scope_file = get_scope_file()

    # Step 2: Prompt for tools and create directories
    tools = ["gowitness", "shodan", "nikto"]
    selected_tools = prompt_for_tools(tools)
    tool_directories = setup_tool_directories(project_name, selected_tools)

    # Step 3: Run Nmap host discovery
    nmap_directory = os.path.join(project_name, "nmap")
    alive_hosts_file = run_nmap_host_discovery(scope_file, nmap_directory)

    # Step 4: Run Nmap port scan with SYN scan
    nmap_processed_output = run_nmap_port_scan(alive_hosts_file, nmap_directory)

    # Step 5: Copy the Nmap processed output file to the tool directories
    copy_file_to_tool_directories(nmap_processed_output, tool_directories)

    # Step 6: Run Gowitness if selected
    if "gowitness" in selected_tools:
        gowitness_directory = os.path.join(project_name, "gowitness")
        run_gowitness(gowitness_directory, nmap_processed_output)

if __name__ == "__main__":
    main()
