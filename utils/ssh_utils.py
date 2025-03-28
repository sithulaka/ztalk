"""
SSH Utilities for ZTalk

Helper functions for SSH operations, key management, tunneling, and file transfers.
"""

import os
import sys
import socket
import threading
import time
import logging
import paramiko
import base64
import ipaddress
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def close_ssh_connection(conn):
    """
    Close an SSH connection object.
    Compatible with both Paramiko SSH connections and ZTalk SSHConnection objects.
    """
    if conn is None:
        return
        
    try:
        # Check if it's a paramiko.SSHClient
        if hasattr(conn, 'close') and callable(conn.close):
            conn.close()
            return
            
        # Check if it's a ZTalk SSHConnection
        if hasattr(conn, 'disconnect') and callable(conn.disconnect):
            conn.disconnect()
            return
            
    except Exception as e:
        logger.error(f"Error closing SSH connection: {e}")

def generate_ssh_key(key_path: str, key_type: str = "rsa", bits: int = 2048, 
                    passphrase: Optional[str] = None, comment: Optional[str] = None) -> bool:
    """
    Generate a new SSH key pair.
    
    Args:
        key_path: Path to save the private key
        key_type: Type of key (rsa, dsa, ecdsa, ed25519)
        bits: Key size in bits (for RSA and DSA)
        passphrase: Optional passphrase to encrypt the private key
        comment: Optional comment to add to the public key
        
    Returns:
        True if successful, False otherwise
    """
    try:
        key_dir = os.path.dirname(key_path)
        if key_dir and not os.path.exists(key_dir):
            os.makedirs(key_dir, exist_ok=True)
            
        # Generate key based on type
        if key_type.lower() == "rsa":
            key = paramiko.RSAKey.generate(bits)
        elif key_type.lower() == "dsa":
            key = paramiko.DSSKey.generate(bits)
        elif key_type.lower() == "ecdsa":
            key = paramiko.ECDSAKey.generate()
        elif key_type.lower() == "ed25519":
            key = paramiko.Ed25519Key.generate()
        else:
            logger.error(f"Unsupported key type: {key_type}")
            return False
            
        # Save private key
        key.write_private_key_file(key_path, password=passphrase)
        
        # Save public key
        public_key_path = f"{key_path}.pub"
        with open(public_key_path, 'w') as f:
            if comment:
                f.write(f"{key.get_name()} {key.get_base64()} {comment}\n")
            else:
                f.write(f"{key.get_name()} {key.get_base64()}\n")
                
        logger.info(f"Generated {key_type} key pair at {key_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating SSH key: {e}")
        return False

def load_ssh_key(key_path: str, passphrase: Optional[str] = None) -> Optional[paramiko.PKey]:
    """
    Load an SSH private key.
    
    Args:
        key_path: Path to the private key file
        passphrase: Passphrase for the key if encrypted
        
    Returns:
        Paramiko PKey object if successful, None otherwise
    """
    if not os.path.exists(key_path):
        logger.error(f"Key file not found: {key_path}")
        return None
        
    try:
        # Try each key type in sequence
        key_types = [
            paramiko.RSAKey,
            paramiko.DSSKey,
            paramiko.ECDSAKey,
            paramiko.Ed25519Key
        ]
        
        for key_class in key_types:
            try:
                return key_class.from_private_key_file(key_path, password=passphrase)
            except paramiko.ssh_exception.SSHException:
                continue
                
        logger.error(f"Unknown or unsupported key type: {key_path}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading SSH key: {e}")
        return None

def upload_using_scp(local_path: str, remote_path: str, host: str, port: int = 22,
                   username: str = "", password: Optional[str] = None, 
                   key_path: Optional[str] = None, 
                   callback: Optional[Callable[[int, int], None]] = None) -> bool:
    """
    Upload a file using SCP.
    
    Args:
        local_path: Path to the local file
        remote_path: Path where to store the file on the remote server
        host: Remote host
        port: SSH port
        username: SSH username
        password: SSH password (optional)
        key_path: Path to private key file (optional)
        callback: Progress callback function (bytes_sent, total_bytes)
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(local_path):
        logger.error(f"Local file not found: {local_path}")
        return False
        
    try:
        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to server
        connect_kwargs = {
            "hostname": host,
            "port": port,
            "username": username,
            "timeout": 10
        }
        
        if password:
            connect_kwargs["password"] = password
        elif key_path:
            key = load_ssh_key(key_path)
            if key:
                connect_kwargs["pkey"] = key
            else:
                logger.error("Failed to load SSH key")
                return False
                
        client.connect(**connect_kwargs)
        
        # Create SCP client
        with client.open_sftp() as sftp:
            # Get file size for progress reporting
            file_size = os.path.getsize(local_path)
            
            # Prepare callback wrapper if a callback was provided
            cb_func = None
            if callback:
                def callback_wrapper(bytes_transferred, total_bytes):
                    callback(bytes_transferred, file_size)
                cb_func = callback_wrapper
                
            # Upload file
            sftp.put(local_path, remote_path, callback=cb_func)
            
        logger.info(f"Uploaded {local_path} to {host}:{remote_path}")
        return True
        
    except Exception as e:
        logger.error(f"SCP upload error: {e}")
        return False
        
    finally:
        if 'client' in locals():
            client.close()

def download_using_scp(remote_path: str, local_path: str, host: str, port: int = 22,
                     username: str = "", password: Optional[str] = None, 
                     key_path: Optional[str] = None,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
    """
    Download a file using SCP.
    
    Args:
        remote_path: Path to the file on the remote server
        local_path: Path where to store the downloaded file
        host: Remote host
        port: SSH port
        username: SSH username
        password: SSH password (optional)
        key_path: Path to private key file (optional)
        callback: Progress callback function (bytes_received, total_bytes)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
            
        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to server
        connect_kwargs = {
            "hostname": host,
            "port": port,
            "username": username,
            "timeout": 10
        }
        
        if password:
            connect_kwargs["password"] = password
        elif key_path:
            key = load_ssh_key(key_path)
            if key:
                connect_kwargs["pkey"] = key
            else:
                logger.error("Failed to load SSH key")
                return False
                
        client.connect(**connect_kwargs)
        
        # Create SCP client
        with client.open_sftp() as sftp:
            # Get file stats for progress reporting
            file_stats = sftp.stat(remote_path)
            file_size = file_stats.st_size
            
            # Prepare callback wrapper if a callback was provided
            cb_func = None
            if callback:
                def callback_wrapper(bytes_transferred, total_bytes):
                    callback(bytes_transferred, file_size)
                cb_func = callback_wrapper
                
            # Download file
            sftp.get(remote_path, local_path, callback=cb_func)
            
        logger.info(f"Downloaded {host}:{remote_path} to {local_path}")
        return True
        
    except FileNotFoundError:
        logger.error(f"Remote file not found: {remote_path}")
        return False
        
    except Exception as e:
        logger.error(f"SCP download error: {e}")
        return False
        
    finally:
        if 'client' in locals():
            client.close()

def create_ssh_tunnel(local_port: int, remote_host: str, remote_port: int,
                    ssh_host: str, ssh_port: int = 22, username: str = "",
                    password: Optional[str] = None, key_path: Optional[str] = None) -> Optional[paramiko.SSHClient]:
    """
    Create an SSH tunnel.
    
    This creates a tunnel from local_port to remote_host:remote_port through ssh_host.
    
    Args:
        local_port: Local port to listen on
        remote_host: Remote host to connect to
        remote_port: Remote port to connect to
        ssh_host: SSH server to tunnel through
        ssh_port: SSH port
        username: SSH username
        password: SSH password (optional)
        key_path: Path to private key file (optional)
        
    Returns:
        SSHClient object if successful, None otherwise
    """
    try:
        # Check if local port is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', local_port))
        sock.close()
        
        if result == 0:
            logger.error(f"Local port {local_port} is already in use")
            return None
            
        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to SSH server
        connect_kwargs = {
            "hostname": ssh_host,
            "port": ssh_port,
            "username": username,
            "timeout": 10
        }
        
        if password:
            connect_kwargs["password"] = password
        elif key_path:
            key = load_ssh_key(key_path)
            if key:
                connect_kwargs["pkey"] = key
            else:
                logger.error("Failed to load SSH key")
                return None
                
        client.connect(**connect_kwargs)
        
        # Start port forwarding
        transport = client.get_transport()
        transport.request_port_forward('127.0.0.1', local_port, remote_host, remote_port)
        
        logger.info(f"Created tunnel: localhost:{local_port} -> {remote_host}:{remote_port} via {ssh_host}")
        return client
        
    except Exception as e:
        logger.error(f"Error creating SSH tunnel: {e}")
        if 'client' in locals():
            client.close()
        return None

def close_ssh_tunnel(client: paramiko.SSHClient, local_port: int) -> bool:
    """
    Close an SSH tunnel.
    
    Args:
        client: SSHClient object
        local_port: Local port the tunnel is listening on
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Cancel port forwarding
        transport = client.get_transport()
        if transport:
            transport.cancel_port_forward('127.0.0.1', local_port)
            
        # Close client
        client.close()
        
        logger.info(f"Closed SSH tunnel on localhost:{local_port}")
        return True
        
    except Exception as e:
        logger.error(f"Error closing SSH tunnel: {e}")
        return False
        
def execute_remote_command(host: str, port: int = 22, username: str = "",
                         password: Optional[str] = None, key_path: Optional[str] = None,
                         command: str = "", timeout: int = 30) -> Tuple[bool, str, str]:
    """
    Execute a command on a remote host.
    
    Args:
        host: Remote host
        port: SSH port
        username: SSH username
        password: SSH password (optional)
        key_path: Path to private key file (optional)
        command: Command to execute
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to server
        connect_kwargs = {
            "hostname": host,
            "port": port,
            "username": username,
            "timeout": 10
        }
        
        if password:
            connect_kwargs["password"] = password
        elif key_path:
            key = load_ssh_key(key_path)
            if key:
                connect_kwargs["pkey"] = key
            else:
                logger.error("Failed to load SSH key")
                return (False, "", "Failed to load SSH key")
                
        client.connect(**connect_kwargs)
        
        # Execute command
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        stdin.close()
        
        # Get command output
        stdout_str = stdout.read().decode('utf-8', errors='replace')
        stderr_str = stderr.read().decode('utf-8', errors='replace')
        
        # Check exit status
        exit_status = stdout.channel.recv_exit_status()
        success = exit_status == 0
        
        logger.info(f"Executed command on {host}: {command} (exit code: {exit_status})")
        return (success, stdout_str, stderr_str)
        
    except Exception as e:
        logger.error(f"Error executing remote command: {e}")
        return (False, "", str(e))
        
    finally:
        if 'client' in locals():
            client.close()

def scan_host_for_ssh(host: str, ports: List[int] = None, timeout: float = 0.5) -> List[int]:
    """
    Scan a host for open SSH ports.
    
    Args:
        host: Host to scan
        ports: List of ports to scan (default: [22])
        timeout: Connection timeout in seconds
        
    Returns:
        List of open ports
    """
    if not ports:
        ports = [22]
        
    open_ports = []
    
    for port in ports:
        try:
            # Try to connect to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                # Check if it's an SSH service by trying to get the server banner
                try:
                    transport = paramiko.Transport((host, port))
                    transport.start_client(timeout=timeout)
                    server_banner = transport.get_banner().decode('utf-8', errors='replace')
                    transport.close()
                    
                    if "ssh" in server_banner.lower():
                        open_ports.append(port)
                        logger.debug(f"Found SSH service on {host}:{port} ({server_banner.strip()})")
                except:
                    # Even if the banner check fails, it might still be an SSH port
                    open_ports.append(port)
                    logger.debug(f"Found possibly SSH port {host}:{port}")
                    
        except Exception:
            pass
            
    return open_ports

def scan_network_for_ssh(network: str, ports: List[int] = None, timeout: float = 0.5,
                       max_threads: int = 10, callback: Optional[Callable[[str, List[int]], None]] = None) -> Dict[str, List[int]]:
    """
    Scan a network for hosts with SSH ports open.
    
    Args:
        network: Network to scan in CIDR notation (e.g., "192.168.1.0/24")
        ports: List of ports to scan (default: [22])
        timeout: Connection timeout in seconds
        max_threads: Maximum number of concurrent threads
        callback: Callback function called when a host is found (host, open_ports)
        
    Returns:
        Dictionary of hosts and their open SSH ports
    """
    if not ports:
        ports = [22]
        
    results = {}
    threads = []
    results_lock = threading.Lock()
    
    try:
        # Generate IP addresses from network
        network_ips = list(ipaddress.IPv4Network(network))
        
        def scan_worker(ip_list):
            for ip in ip_list:
                ip_str = str(ip)
                open_ports = scan_host_for_ssh(ip_str, ports, timeout)
                
                if open_ports:
                    with results_lock:
                        results[ip_str] = open_ports
                        
                    if callback:
                        callback(ip_str, open_ports)
        
        # Split work among threads
        chunk_size = max(1, len(network_ips) // max_threads)
        for i in range(0, len(network_ips), chunk_size):
            chunk = network_ips[i:i+chunk_size]
            thread = threading.Thread(target=scan_worker, args=(chunk,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        logger.info(f"Scanned {len(network_ips)} hosts, found {len(results)} with SSH")
        return results
        
    except Exception as e:
        logger.error(f"Error scanning network: {e}")
        return results

def deploy_ssh_key(host: str, port: int = 22, username: str = "", 
                 password: Optional[str] = None, key_path: Optional[str] = None) -> bool:
    """
    Deploy an SSH public key to a remote host for passwordless login.
    
    Args:
        host: Remote host
        port: SSH port
        username: SSH username
        password: SSH password
        key_path: Path to private key file to deploy the public key for
        
    Returns:
        True if successful, False otherwise
    """
    if not key_path:
        logger.error("No key path specified")
        return False
        
    # Check if the key exists
    public_key_path = f"{key_path}.pub"
    if not os.path.exists(public_key_path):
        logger.error(f"Public key not found: {public_key_path}")
        return False
        
    try:
        # Read the public key
        with open(public_key_path, 'r') as f:
            public_key = f.read().strip()
            
        # Create SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to server with password
        if not password:
            logger.error("Password required to deploy key")
            return False
            
        client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
        
        # Ensure .ssh directory exists with proper permissions
        setup_commands = [
            "mkdir -p ~/.ssh",
            "chmod 700 ~/.ssh",
            f"echo '{public_key}' >> ~/.ssh/authorized_keys",
            "chmod 600 ~/.ssh/authorized_keys"
        ]
        
        for cmd in setup_commands:
            stdin, stdout, stderr = client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode('utf-8', errors='replace')
                logger.error(f"Command failed ({exit_status}): {cmd}\nError: {error}")
                return False
                
        logger.info(f"Deployed SSH key to {username}@{host}")
        return True
        
    except Exception as e:
        logger.error(f"Error deploying SSH key: {e}")
        return False
        
    finally:
        if 'client' in locals():
            client.close()
            
def create_ssh_config_entry(name: str, host: str, port: int = 22, username: str = "",
                          identity_file: Optional[str] = None, other_options: Optional[Dict[str, str]] = None) -> str:
    """
    Create an SSH config entry for the ~/.ssh/config file.
    
    Args:
        name: Host alias/name
        host: Hostname or IP
        port: SSH port
        username: SSH username
        identity_file: Path to private key file
        other_options: Dictionary of other SSH options
        
    Returns:
        SSH config entry as string
    """
    config_lines = [f"Host {name}"]
    config_lines.append(f"    HostName {host}")
    config_lines.append(f"    Port {port}")
    
    if username:
        config_lines.append(f"    User {username}")
        
    if identity_file:
        config_lines.append(f"    IdentityFile {identity_file}")
        
    # Add other options
    if other_options:
        for key, value in other_options.items():
            config_lines.append(f"    {key} {value}")
            
    return "\n".join(config_lines)

def add_to_ssh_config(config_entry: str) -> bool:
    """
    Add an entry to the user's SSH config file.
    
    Args:
        config_entry: SSH config entry to add
        
    Returns:
        True if successful, False otherwise
    """
    try:
        ssh_config_path = os.path.expanduser("~/.ssh/config")
        
        # Create directory if it doesn't exist
        ssh_dir = os.path.dirname(ssh_config_path)
        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir, mode=0o700)
            
        # Create file if it doesn't exist
        if not os.path.exists(ssh_config_path):
            with open(ssh_config_path, 'w') as f:
                f.write(f"# SSH Config File created by ZTalk\n\n{config_entry}\n")
            os.chmod(ssh_config_path, 0o600)
            return True
            
        # Check if the host is already in the config
        host_name = config_entry.split()[1]
        with open(ssh_config_path, 'r') as f:
            config_content = f.read()
            
        if f"Host {host_name}" in config_content:
            logger.warning(f"Host {host_name} already exists in SSH config")
            return False
            
        # Append to file
        with open(ssh_config_path, 'a') as f:
            f.write(f"\n{config_entry}\n")
            
        logger.info(f"Added entry for {host_name} to SSH config")
        return True
        
    except Exception as e:
        logger.error(f"Error updating SSH config: {e}")
        return False 