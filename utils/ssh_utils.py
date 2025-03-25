import subprocess
import shutil
import platform
import sys
import os
import threading
import time
import signal
from typing import Tuple, Optional, Dict, List, Any

def check_ssh_client_installed() -> Tuple[bool, str]:
    """
    Check if SSH client is installed on the system.
    
    Returns:
        Tuple[bool, str]: (is_installed, binary_path or error message)
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            # Check for OpenSSH Client on Windows
            ssh_path = shutil.which("ssh")
            if ssh_path:
                return True, ssh_path
                
            # Check in Program Files
            potential_paths = [
                r"C:\Windows\System32\OpenSSH\ssh.exe",
                r"C:\Program Files\OpenSSH\ssh.exe",
                r"C:\Program Files (x86)\OpenSSH\ssh.exe"
            ]
            
            for path in potential_paths:
                if os.path.exists(path):
                    return True, path
                    
            return False, "OpenSSH client not found"
            
        else:  # Linux, macOS
            ssh_path = shutil.which("ssh")
            if ssh_path:
                return True, ssh_path
            return False, "SSH client not found"
            
    except Exception as e:
        return False, f"Error checking SSH client: {str(e)}"

def install_ssh_client() -> Tuple[bool, str]:
    """
    Attempt to install SSH client if missing.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            # On Windows, guide to enable OpenSSH client feature
            return False, (
                "Please install OpenSSH Client using Windows Features:\n"
                "1. Go to Settings > Apps > Optional Features\n"
                "2. Click 'Add a feature'\n"
                "3. Search for 'OpenSSH Client' and install it"
            )
            
        elif system == "Darwin":  # macOS
            # macOS should have SSH pre-installed
            return False, "SSH should be pre-installed on macOS. If missing, please install Xcode Command Line Tools."
            
        elif system == "Linux":
            # Try to detect the package manager and install
            if shutil.which("apt-get"):  # Debian/Ubuntu
                cmd = ["sudo", "apt-get", "update", "-y"]
                subprocess.run(cmd, check=True)
                
                cmd = ["sudo", "apt-get", "install", "-y", "openssh-client"]
                subprocess.run(cmd, check=True)
                return True, "Successfully installed OpenSSH client using apt-get"
                
            elif shutil.which("dnf"):  # Fedora
                cmd = ["sudo", "dnf", "install", "-y", "openssh-clients"]
                subprocess.run(cmd, check=True)
                return True, "Successfully installed OpenSSH client using dnf"
                
            elif shutil.which("yum"):  # CentOS/RHEL
                cmd = ["sudo", "yum", "install", "-y", "openssh-clients"]
                subprocess.run(cmd, check=True)
                return True, "Successfully installed OpenSSH client using yum"
                
            elif shutil.which("pacman"):  # Arch Linux
                cmd = ["sudo", "pacman", "-S", "--noconfirm", "openssh"]
                subprocess.run(cmd, check=True)
                return True, "Successfully installed OpenSSH client using pacman"
                
            else:
                return False, "Could not detect package manager. Please install SSH client manually."
                
        else:
            return False, f"Unsupported operating system: {system}"
            
    except subprocess.CalledProcessError as e:
        return False, f"Error installing SSH client: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def get_default_ssh_key_path() -> str:
    """Return the default SSH key path based on platform"""
    home = os.path.expanduser("~")
    
    if platform.system() == "Windows":
        return os.path.join(home, ".ssh", "id_rsa")
    else:  # macOS, Linux
        return os.path.join(home, ".ssh", "id_rsa")

def generate_ssh_key(key_path: Optional[str] = None, passphrase: str = "") -> Tuple[bool, str]:
    """
    Generate a new SSH key pair.
    
    Args:
        key_path: Path to save the key, defaults to platform-specific location
        passphrase: Optional passphrase to protect the key
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    if not key_path:
        key_path = get_default_ssh_key_path()
        
    # Make sure .ssh directory exists
    ssh_dir = os.path.dirname(key_path)
    os.makedirs(ssh_dir, exist_ok=True)
    
    try:
        # Create the command
        cmd = ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", key_path]
        
        if passphrase:
            # If passphrase provided, add it to command
            cmd.extend(["-N", passphrase])
        else:
            # Empty passphrase
            cmd.extend(["-N", ""])
        
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, f"SSH key generated successfully at {key_path}"
        
    except subprocess.CalledProcessError as e:
        return False, f"Error generating SSH key: {e.stderr or str(e)}"
    except Exception as e:
        return False, f"Unexpected error generating SSH key: {str(e)}"

def is_ssh_available():
    """Check if SSH client is available on the system"""
    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call(["ssh", "-V"], stdout=devnull, stderr=devnull)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def create_ssh_connection(host: str, port: int = 22, username: str = None, 
                          password: str = None, key_file: str = None, 
                          terminal_widget=None, source_ip: str = None):
    """Create an SSH connection to a remote host using the system's SSH client"""
    if not is_ssh_available():
        if terminal_widget:
            terminal_widget.append_text("SSH client not found on this system.\n", "error")
        return None
    
    # Build the SSH command
    cmd = ["ssh"]
    
    # Force pseudo-terminal allocation to fix the "stdin is not a terminal" error
    cmd.append("-tt")
    
    # Additional flags for more reliable connection
    cmd.append("-o")
    cmd.append("ConnectTimeout=10")  # Set connection timeout
    
    cmd.append("-o")
    cmd.append("ServerAliveInterval=10")  # Keep connection alive
    
    cmd.append("-o")
    cmd.append("StrictHostKeyChecking=no")  # Don't ask for host key verification (use carefully)
    
    # Add port if not default
    if port != 22:
        cmd.extend(["-p", str(port)])
    
    # Add key file if provided
    if key_file:
        cmd.extend(["-i", key_file])
    
    # Add source IP binding if specified
    if source_ip:
        cmd.extend(["-b", source_ip])
    
    # Add username and host
    if username:
        target = f"{username}@{host}"
    else:
        target = host
    
    cmd.append(target)
    
    if terminal_widget:
        terminal_widget.append_text(f"Running: {' '.join(cmd)}\n", "info")
        terminal_widget.append_text(f"SSH binary path: {shutil.which('ssh')}\n", "info")
    
    try:
        # Create a process to interact with
        if platform.system() == "Windows":
            # On Windows, open in a new console but also try to show output
            if terminal_widget:
                terminal_widget.append_text(f"Using Windows-specific SSH approach\n", "info")
                
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            if terminal_widget:
                terminal_widget.append_text("SSH connection opened in a new console window.\n", "info")
                terminal_widget.append_text("This terminal widget is read-only on Windows.\n", "warning")
                
                # Set up a command handler that informs the user
                def windows_command_handler(command):
                    terminal_widget.append_text("On Windows, commands must be entered in the SSH console window.\n", "warning")
                
                terminal_widget.set_command_handler(windows_command_handler)
                
            return {
                "process": process,
                "platform": "windows"
            }
            
        else:  # Unix-like systems (Linux, macOS)
            # Ensure we're creating a proper pseudo-terminal for SSH
            # Use pty to create a pseudo-terminal pair
            if terminal_widget:
                terminal_widget.append_text(f"Using Unix-specific SSH approach\n", "info")
                
            import pty
            import fcntl
            import termios
            
            # Create a PTY for the subprocess
            try:
                master, slave = pty.openpty()
                if terminal_widget:
                    terminal_widget.append_text(f"PTY created: master={master}, slave={slave}\n", "info")
            except Exception as e:
                if terminal_widget:
                    terminal_widget.append_text(f"Error creating PTY: {str(e)}\n", "error")
                raise
            
            # Set raw mode on the PTY to avoid strange translations
            try:
                mode = termios.tcgetattr(slave)
                mode[3] = mode[3] & ~termios.ECHO  # Turn off echoing
                termios.tcsetattr(slave, termios.TCSAFLUSH, mode)
                if terminal_widget:
                    terminal_widget.append_text(f"PTY configured successfully\n", "info")
            except Exception as e:
                if terminal_widget:
                    terminal_widget.append_text(f"Error configuring PTY: {str(e)}\n", "error")
                os.close(slave)
                os.close(master)
                raise
            
            # Start the SSH process
            try:
                process = subprocess.Popen(
                    cmd,
                    stdin=slave,
                    stdout=slave,
                    stderr=slave,
                    text=False,
                    close_fds=True,
                    shell=False,
                    preexec_fn=os.setsid  # Create a new process group
                )
                if terminal_widget:
                    terminal_widget.append_text(f"SSH process started with PID: {process.pid}\n", "info")
            except Exception as e:
                if terminal_widget:
                    terminal_widget.append_text(f"Error starting SSH process: {str(e)}\n", "error")
                os.close(slave)
                os.close(master)
                raise
            
            # Close the slave end of the pty from this parent process
            try:
                os.close(slave)
                if terminal_widget:
                    terminal_widget.append_text(f"Slave PTY closed in parent process\n", "info")
            except Exception as e:
                if terminal_widget:
                    terminal_widget.append_text(f"Error closing slave PTY: {str(e)}\n", "error")
                os.close(master)
                process.terminate()
                raise
            
            # Set the master to non-blocking mode
            try:
                fl = fcntl.fcntl(master, fcntl.F_GETFL)
                fcntl.fcntl(master, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                if terminal_widget:
                    terminal_widget.append_text(f"Master PTY set to non-blocking mode\n", "info")
            except Exception as e:
                if terminal_widget:
                    terminal_widget.append_text(f"Error setting non-blocking mode: {str(e)}\n", "error")
                os.close(master)
                process.terminate()
                raise
            
            # Set up output reading threads if we have a terminal widget
            if terminal_widget:
                terminal_widget.append_text(f"Setting up SSH I/O handling...\n", "info")
                
                # Set command handler
                def send_command(command):
                    if process.poll() is None:  # Check if process is still running
                        try:
                            # Add newline to the command
                            os.write(master, (command + "\n").encode())
                            terminal_widget.append_text(f"> {command}\n", "command")
                        except OSError as e:
                            terminal_widget.append_text(f"Failed to send command: {str(e)}\n", "error")
                    else:
                        terminal_widget.append_text("Connection is closed.\n", "error")
                
                terminal_widget.set_command_handler(send_command)
                
                # Thread for reading output
                def read_output():
                    # Buffer for incomplete lines
                    buffer = bytearray()
                    
                    terminal_widget.append_text(f"Starting SSH output reader thread\n", "info")
                    
                    # Send an initial newline to get a prompt
                    try:
                        os.write(master, b"\n")
                    except:
                        pass
                    
                    while process.poll() is None:
                        try:
                            # Try to read from the master pty
                            data = os.read(master, 1024)
                            if data:
                                # Add to buffer
                                buffer.extend(data)
                                
                                # Process complete lines
                                while b'\n' in buffer or b'\r' in buffer:
                                    # Find the first newline
                                    nl_pos = min(
                                        buffer.find(b'\n') if buffer.find(b'\n') != -1 else float('inf'),
                                        buffer.find(b'\r') if buffer.find(b'\r') != -1 else float('inf')
                                    )
                                    
                                    # If found a newline
                                    if nl_pos != float('inf'):
                                        # Extract the line
                                        line = buffer[:nl_pos+1].decode('utf-8', errors='replace')
                                        buffer = buffer[nl_pos+1:]
                                        
                                        # Check for password prompt and handle it
                                        if password and ("password" in line.lower() or "password:" in line.lower()):
                                            try:
                                                os.write(master, (password + "\n").encode())
                                                terminal_widget.append_text("Password sent automatically\n", "info")
                                            except:
                                                terminal_widget.append_text("Failed to send password\n", "error")
                                        
                                        # Display the line
                                        terminal_widget.append_text(line)
                                    else:
                                        break
                            else:
                                # End of stream
                                time.sleep(0.1)
                        except BlockingIOError:
                            # No data available, just wait
                            time.sleep(0.1)
                        except OSError as e:
                            # Probably broken pipe, exit the loop
                            terminal_widget.append_text(f"Connection error: {str(e)}\n", "error")
                            break
                        except Exception as e:
                            terminal_widget.append_text(f"Unexpected error: {str(e)}\n", "error")
                            break
                    
                    # Flush any remaining data in the buffer
                    if buffer:
                        terminal_widget.append_text(buffer.decode('utf-8', errors='replace'))
                    
                    # Get the exit code
                    exit_code = process.poll()
                    terminal_widget.append_text(f"\nConnection closed (exit code: {exit_code}).\n", "info")
                    
                    # Clean up the master fd
                    try:
                        os.close(master)
                        terminal_widget.append_text("PTY master closed\n", "info")
                    except:
                        pass
                
                # Start reading thread
                output_thread = threading.Thread(target=read_output, daemon=True, name="SSHOutputReader")
                output_thread.start()
                terminal_widget.append_text("SSH reader thread started\n", "info")
            
            # No need for automatic password sending, it's handled in the read_output function
            
            return {
                "process": process,
                "master_fd": master,
                "platform": "unix"
            }
            
    except Exception as e:
        if terminal_widget:
            terminal_widget.append_text(f"Error creating SSH connection: {str(e)}\n", "error")
            if hasattr(e, "__traceback__"):
                import traceback
                tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
                for line in tb_lines:
                    terminal_widget.append_text(line, "error")
        return None
        
def close_ssh_connection(connection):
    """Close an SSH connection"""
    if not connection:
        return False
        
    try:
        # First try to close gracefully
        if "process" in connection:
            if "master_fd" in connection:
                # Send exit command
                try:
                    os.write(connection["master_fd"], b"exit\n")
                    time.sleep(0.5)  # Give it a moment to exit gracefully
                except:
                    pass
                
                # Close the master fd
                try:
                    os.close(connection["master_fd"])
                except:
                    pass
                
            # Send SIGTERM to process
            if connection["process"].poll() is None:
                connection["process"].terminate()
                time.sleep(0.5)  # Give it some time to terminate
            
            # If still running, force kill
            if connection["process"].poll() is None:
                if platform.system() == "Windows":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(connection["process"].pid)])
                else:
                    os.killpg(os.getpgid(connection["process"].pid), signal.SIGKILL)
        
        return True
    except Exception as e:
        print(f"Error closing SSH connection: {e}")
        return False 