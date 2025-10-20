#!/usr/bin/env python3
"""
Flask Server Management Utility

This script helps manage the Flask development server instances.
"""
import os
import signal
import subprocess
import sys
import argparse
from datetime import datetime

def find_running_processes():
    """Find running Flask processes"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        flask_processes = []

        for line in lines:
            if 'python -c' in line and 'create_app' in line:
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    cmd_line = ' '.join(parts[10:])
                    flask_processes.append((pid, cmd_line))

        return flask_processes
    except Exception as e:
        print(f"Error finding processes: {e}")
        return []

def kill_process(pid):
    """Kill a process by PID"""
    try:
        os.kill(int(pid), signal.SIGTERM)
        print(f"Sent SIGTERM to process {pid}")
        return True
    except ProcessLookupError:
        print(f"Process {pid} not found")
        return False
    except PermissionError:
        print(f"No permission to kill process {pid}")
        return False
    except Exception as e:
        print(f"Error killing process {pid}: {e}")
        return False

def start_server(port=8082):
    """Start Flask server on specified port"""
    venv_python = os.path.join(os.getcwd(), 'venv', 'bin', 'python')
    if not os.path.exists(venv_python):
        print(f"Virtual environment not found at {venv_python}")
        return False

    cmd = f'''
source venv/bin/activate
export FLASK_APP=run.py
python -c "
from app import create_app
app = create_app()
print('Starting Flask server on port {port}...')
app.run(debug=True, host='0.0.0.0', port={port})
"
'''

    try:
        print(f"Starting Flask server on port {port}...")
        process = subprocess.Popen(cmd, shell=True, cwd=os.getcwd())
        print(f"Server started with PID: {process.pid}")
        return True
    except Exception as e:
        print(f"Error starting server: {e}")
        return False

def status():
    """Show status of running Flask processes"""
    processes = find_running_processes()

    if not processes:
        print("No Flask processes found running.")
        return

    print(f"\n{'PID':<10} {'Command':<60}")
    print("-" * 70)

    for pid, cmd in processes:
        # Truncate command if too long
        display_cmd = cmd[:57] + "..." if len(cmd) > 60 else cmd
        print(f"{pid:<10} {display_cmd:<60}")

def cleanup():
    """Kill all running Flask processes"""
    processes = find_running_processes()

    if not processes:
        print("No Flask processes found to clean up.")
        return

    print(f"Found {len(processes)} Flask process(es). Cleaning up...")

    for pid, cmd in processes:
        if kill_process(pid):
            print(f"✓ Killed process {pid}")
        else:
            print(f"✗ Failed to kill process {pid}")

    print("Cleanup completed.")

def main():
    parser = argparse.ArgumentParser(description='Flask Server Management Utility')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'cleanup'],
                       help='Action to perform')
    parser.add_argument('--port', type=int, default=8082,
                       help='Port to start server on (default: 8082)')

    args = parser.parse_args()

    if args.action == 'start':
        start_server(args.port)
    elif args.action == 'status':
        status()
    elif args.action == 'cleanup':
        cleanup()
    elif args.action == 'stop':
        processes = find_running_processes()
        if processes:
            for pid, _ in processes:
                kill_process(pid)
        else:
            print("No Flask processes found to stop.")
    elif args.action == 'restart':
        processes = find_running_processes()
        if processes:
            for pid, _ in processes:
                kill_process(pid)
            print("Waiting 2 seconds for processes to terminate...")
            import time
            time.sleep(2)
        start_server(args.port)

if __name__ == "__main__":
    main()