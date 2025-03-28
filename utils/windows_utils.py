"""
Windows Compatibility Utilities for ZTalk

Helper functions for Windows-specific operations, compatibility fixes, and installer building.
"""

import os
import sys
import platform
import logging
import subprocess
import ctypes
import winreg
import socket
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def is_admin() -> bool:
    """
    Check if the current process has administrator privileges on Windows.
    
    Returns:
        True if running with admin privileges, False otherwise
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def restart_with_admin_rights(command: Optional[List[str]] = None) -> bool:
    """
    Restart the current Python script with administrator privileges.
    
    Args:
        command: Optional command to run instead of current script
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not command:
            command = [sys.executable] + sys.argv
            
        # Use Windows UAC elevation
        ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            command[0], 
            " ".join(f'"{x}"' for x in command[1:]), 
            None, 
            1
        )
        return True
    except Exception as e:
        logger.error(f"Failed to restart with admin rights: {e}")
        return False

def get_windows_version() -> Dict[str, Any]:
    """
    Get detailed Windows version information.
    
    Returns:
        Dictionary with Windows version details
    """
    try:
        version_info = {}
        
        # Get Windows release info from platform
        version_info["system"] = platform.system()
        version_info["release"] = platform.release()
        version_info["version"] = platform.version()
        
        # Get more detailed info from registry
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                         r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            version_info["product_name"] = winreg.QueryValueEx(key, "ProductName")[0]
            version_info["current_build"] = winreg.QueryValueEx(key, "CurrentBuild")[0]
            
            try:
                version_info["display_version"] = winreg.QueryValueEx(key, "DisplayVersion")[0]
            except:
                version_info["display_version"] = ""
                
            try:
                version_info["ubr"] = winreg.QueryValueEx(key, "UBR")[0]  # Update Build Revision
            except:
                version_info["ubr"] = ""
                
        # Get system architecture
        version_info["architecture"] = platform.machine()
        version_info["processor"] = platform.processor()
        
        # Check if running in Windows Subsystem for Linux (WSL)
        version_info["is_wsl"] = "WSL" in platform.uname().release or "Microsoft" in platform.uname().release
        
        return version_info
        
    except Exception as e:
        logger.error(f"Error getting Windows version: {e}")
        return {
            "system": platform.system(),
            "version": platform.version(),
            "error": str(e)
        }

def configure_windows_firewall(app_path: str, allow: bool = True, name: str = "ZTalk") -> bool:
    """
    Configure Windows Firewall for the application.
    
    Args:
        app_path: Path to the executable
        allow: True to allow, False to block
        name: Rule name
        
    Returns:
        True if successful, False otherwise
    """
    if not is_admin():
        logger.warning("Administrator privileges required to configure firewall")
        return False
        
    try:
        # Build firewall rule command
        action = "allow" if allow else "block"
        command = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={name}",
            f"dir=in",
            f"action={action}",
            f"program={app_path}",
            "enable=yes",
            "profile=any"
        ]
        
        # Execute command
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Check result
        if process.returncode == 0:
            logger.info(f"Successfully configured Windows Firewall for {app_path}")
            return True
        else:
            logger.error(f"Failed to configure Windows Firewall: {process.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error configuring Windows Firewall: {e}")
        return False

def get_windows_network_adapters() -> List[Dict[str, Any]]:
    """
    Get detailed information about Windows network adapters.
    
    Returns:
        List of dictionaries containing adapter details
    """
    adapters = []
    
    try:
        # Run ipconfig /all to get adapter details
        process = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if process.returncode != 0:
            logger.error(f"Failed to get adapter info: {process.stderr}")
            return adapters
            
        output = process.stdout
        
        # Parse the output
        current_adapter = None
        for line in output.splitlines():
            line = line.strip()
            
            # New adapter section
            if not line.startswith(" ") and "adapter" in line.lower():
                if current_adapter:  # Save previous adapter if it exists
                    adapters.append(current_adapter)
                    
                # Extract adapter name
                adapter_name = line.split(":")[0].strip()
                current_adapter = {
                    "name": adapter_name,
                    "description": "",
                    "mac_address": "",
                    "ip_addresses": [],
                    "gateway": "",
                    "dhcp_enabled": False,
                    "dns_servers": []
                }
                continue
                
            # Skip blank lines
            if not line or not current_adapter:
                continue
                
            # Parse adapter details
            if "description" in line.lower():
                current_adapter["description"] = line.split(":", 1)[1].strip()
            elif "physical address" in line.lower():
                current_adapter["mac_address"] = line.split(":", 1)[1].strip()
            elif "ipv4 address" in line.lower():
                ip = line.split(":", 1)[1].strip()
                # Remove (Preferred) suffix if present
                ip = re.sub(r'\(.*\)', '', ip).strip()
                current_adapter["ip_addresses"].append(ip)
            elif "default gateway" in line.lower():
                gateway = line.split(":", 1)[1].strip()
                if gateway:
                    current_adapter["gateway"] = gateway
            elif "dhcp enabled" in line.lower():
                current_adapter["dhcp_enabled"] = "yes" in line.lower()
            elif "dns servers" in line.lower():
                dns = line.split(":", 1)[1].strip()
                if dns:
                    current_adapter["dns_servers"].append(dns)
                    
        # Add the last adapter
        if current_adapter:
            adapters.append(current_adapter)
            
        return adapters
        
    except Exception as e:
        logger.error(f"Error getting Windows network adapters: {e}")
        return adapters

def configure_windows_ip(adapter_name: str, new_ip: str, subnet_mask: str = "255.255.255.0", 
                       gateway: Optional[str] = None) -> bool:
    """
    Configure a Windows network adapter's IP address.
    
    Args:
        adapter_name: Name of the network adapter
        new_ip: New IP address
        subnet_mask: Subnet mask
        gateway: Default gateway (optional)
        
    Returns:
        True if successful, False otherwise
    """
    if not is_admin():
        logger.warning("Administrator privileges required to configure IP")
        return False
        
    try:
        # Build netsh command for IP configuration
        command = [
            "netsh", "interface", "ip", "set", "address",
            f"name={adapter_name}",
            "static",
            new_ip,
            subnet_mask
        ]
        
        # Add gateway if provided
        if gateway:
            command.append(gateway)
            
        # Execute command
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Check result
        if process.returncode == 0:
            logger.info(f"Successfully configured IP for {adapter_name}: {new_ip}")
            return True
        else:
            logger.error(f"Failed to configure IP: {process.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error configuring Windows IP: {e}")
        return False

def create_windows_shortcut(target_path: str, shortcut_path: str, 
                         description: str = "", icon_path: Optional[str] = None,
                         working_dir: Optional[str] = None) -> bool:
    """
    Create a Windows shortcut (.lnk file).
    
    Args:
        target_path: Path to the target file
        shortcut_path: Path where to create the shortcut
        description: Description for the shortcut
        icon_path: Path to icon file (optional)
        working_dir: Working directory (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import pythoncom
        from win32com.client import Dispatch
        
        # Ensure shortcut has .lnk extension
        if not shortcut_path.endswith('.lnk'):
            shortcut_path += '.lnk'
            
        # Create shell object
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        
        # Set shortcut properties
        shortcut.Targetpath = target_path
        shortcut.Description = description
        
        if working_dir:
            shortcut.WorkingDirectory = working_dir
        else:
            shortcut.WorkingDirectory = os.path.dirname(target_path)
            
        if icon_path:
            shortcut.IconLocation = icon_path
            
        # Save shortcut
        shortcut.save()
        logger.info(f"Created shortcut: {shortcut_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating Windows shortcut: {e}")
        return False

def create_windows_startup_shortcut(target_path: str, name: str) -> bool:
    """
    Create a shortcut in the Windows Startup folder.
    
    Args:
        target_path: Path to the target file
        name: Name for the shortcut
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get Startup folder path
        startup_folder = os.path.join(
            os.environ["APPDATA"],
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        
        # Create shortcut path
        shortcut_path = os.path.join(startup_folder, f"{name}.lnk")
        
        # Create the shortcut
        return create_windows_shortcut(
            target_path=target_path,
            shortcut_path=shortcut_path,
            description=f"Start {name} on boot",
            working_dir=os.path.dirname(target_path)
        )
        
    except Exception as e:
        logger.error(f"Error creating Windows startup shortcut: {e}")
        return False

def build_windows_installer(source_dir: str, output_dir: str, 
                         app_name: str, version: str,
                         icon_path: Optional[str] = None) -> Optional[str]:
    """
    Build a Windows installer using NSIS.
    
    Args:
        source_dir: Directory containing the application files
        output_dir: Directory where to save the installer
        app_name: Application name
        version: Application version
        icon_path: Path to application icon
        
    Returns:
        Path to the created installer if successful, None otherwise
    """
    try:
        # Check if NSIS is installed
        nsis_path = None
        for possible_path in [
            r"C:\Program Files\NSIS\makensis.exe",
            r"C:\Program Files (x86)\NSIS\makensis.exe"
        ]:
            if os.path.exists(possible_path):
                nsis_path = possible_path
                break
                
        if not nsis_path:
            logger.error("NSIS not found. Please install NSIS from https://nsis.sourceforge.io/")
            return None
            
        # Create temporary NSIS script
        script_path = os.path.join(output_dir, f"{app_name}_installer.nsi")
        installer_path = os.path.join(output_dir, f"{app_name}_{version}_Setup.exe")
        
        # Format app name for file paths (remove spaces)
        app_name_safe = app_name.replace(" ", "")
        
        # Generate NSIS script
        with open(script_path, 'w') as f:
            f.write(f"""
; {app_name} Installer Script
; Generated by ZTalk

!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "{app_name}"
OutFile "{installer_path}"
InstallDir "$PROGRAMFILES\\{app_name}"
InstallDirRegKey HKLM "Software\\{app_name_safe}" "Install_Dir"
RequestExecutionLevel admin

; UI settings
!define MUI_ABORTWARNING
!define MUI_ICON "{icon_path or os.path.join(source_dir, 'icon.ico')}"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "{os.path.join(source_dir, 'LICENSE')}"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite on
    
    ; Copy all files from source directory
    File /r "{source_dir}\\*.*"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    
    ; Create start menu shortcut
    CreateDirectory "$SMPROGRAMS\\{app_name}"
    CreateShortCut "$SMPROGRAMS\\{app_name}\\{app_name}.lnk" "$INSTDIR\\{app_name_safe}.exe"
    CreateShortCut "$SMPROGRAMS\\{app_name}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"
    
    ; Create desktop shortcut
    CreateShortCut "$DESKTOP\\{app_name}.lnk" "$INSTDIR\\{app_name_safe}.exe"
    
    ; Write registry keys for uninstall info
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name_safe}" \\
                 "DisplayName" "{app_name}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name_safe}" \\
                 "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name_safe}" \\
                 "DisplayVersion" "{version}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name_safe}" \\
                 "Publisher" "ZTalk Team"
    
    ; Register firewall rule
    ExecWait 'netsh advfirewall firewall add rule name="{app_name}" dir=in action=allow program="$INSTDIR\\{app_name_safe}.exe" enable=yes profile=any'
SectionEnd

Section "Uninstall"
    ; Remove firewall rule
    ExecWait 'netsh advfirewall firewall delete rule name="{app_name}" program="$INSTDIR\\{app_name_safe}.exe"'
    
    ; Remove shortcuts
    Delete "$DESKTOP\\{app_name}.lnk"
    Delete "$SMPROGRAMS\\{app_name}\\*.*"
    RMDir "$SMPROGRAMS\\{app_name}"
    
    ; Remove files
    RMDir /r "$INSTDIR"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name_safe}"
    DeleteRegKey HKLM "Software\\{app_name_safe}"
SectionEnd
            """)
            
        # Run NSIS to create installer
        process = subprocess.run(
            [nsis_path, script_path],
            capture_output=True,
            text=True
        )
        
        # Check if installer was created successfully
        if process.returncode == 0 and os.path.exists(installer_path):
            logger.info(f"Created Windows installer: {installer_path}")
            return installer_path
        else:
            logger.error(f"Failed to create installer: {process.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Error building Windows installer: {e}")
        return None

def create_pythonw_launcher(script_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Create a pythonw launcher for a Python script to run without console window.
    
    Args:
        script_path: Path to the Python script
        output_path: Path for the output exe (default: same as script with .exe extension)
        
    Returns:
        Path to the created exe if successful, None otherwise
    """
    try:
        # Default output path
        if not output_path:
            output_path = os.path.splitext(script_path)[0] + ".exe"
            
        # Get path to pythonw.exe
        pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw_path):
            logger.error(f"pythonw.exe not found at {pythonw_path}")
            return None
            
        # Create a simple batch file that runs the script with pythonw
        bat_path = os.path.splitext(output_path)[0] + ".bat"
        with open(bat_path, 'w') as f:
            f.write(f'@echo off\r\n"{pythonw_path}" "{script_path}" %*\r\n')
            
        # Create a simple VBScript to run the batch file without a console window
        vbs_path = os.path.splitext(output_path)[0] + ".vbs"
        with open(vbs_path, 'w') as f:
            f.write(f'CreateObject("WScript.Shell").Run """" & WScript.Arguments(0) & """", 0, False\r\n')
            
        # Use iexpress to create a self-extracting exe
        sed_path = os.path.splitext(output_path)[0] + ".sed"
        with open(sed_path, 'w') as f:
            f.write(f"""
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName={output_path}
FriendlyName={os.path.basename(script_path)}
AppLaunched=wscript.exe "{vbs_path}" "{bat_path}"
PostInstallCmd=<None>
AdminQuietInstCmd=<None>
UserQuietInstCmd=<None>
SourceFiles=SourceFiles
[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=
[SourceFiles]
SourceFiles0=.
[SourceFiles0]
%FILE0%="{bat_path}"
%FILE1%="{vbs_path}"
%FILE2%="{script_path}"
%FILE3%="{pythonw_path}"
            """)
            
        # Run iexpress to create the exe
        process = subprocess.run(
            ["iexpress", "/N", sed_path],
            capture_output=True,
            text=True
        )
        
        # Clean up temporary files
        for temp_file in [bat_path, vbs_path, sed_path]:
            try:
                os.remove(temp_file)
            except:
                pass
                
        # Check if exe was created
        if os.path.exists(output_path):
            logger.info(f"Created Windows launcher: {output_path}")
            return output_path
        else:
            logger.error("Failed to create Windows launcher")
            return None
            
    except Exception as e:
        logger.error(f"Error creating Windows launcher: {e}")
        return None

def set_file_association(extension: str, app_path: str, description: str) -> bool:
    """
    Associate a file extension with the application.
    
    Args:
        extension: File extension (e.g., ".ztk")
        app_path: Path to the application
        description: Description for the file type
        
    Returns:
        True if successful, False otherwise
    """
    if not is_admin():
        logger.warning("Administrator privileges required to set file association")
        return False
        
    try:
        # Remove leading dot if present
        if extension.startswith('.'):
            extension = extension[1:]
            
        # Create file type in registry
        prog_id = f"ZTalk.{extension}"
        
        # Create ProgID entry
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, prog_id) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, description)
            
        # Set icon
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\DefaultIcon") as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f"{app_path},0")
            
        # Set open command
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\shell\\open\\command") as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{app_path}" "%1"')
            
        # Associate extension with ProgID
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f".{extension}") as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, prog_id)
            
        # Notify the system about the change
        try:
            import win32gui
            win32gui.SendMessage(0xFFFF, 0x001F, 0, 0)  # HWND_BROADCAST, WM_SETTINGCHANGE
        except:
            pass
            
        logger.info(f"Associated file extension .{extension} with {app_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting file association: {e}")
        return False

def fix_pyinstaller_temp_path() -> bool:
    """
    Fix PyInstaller temporary directory issue on Windows.
    
    This addresses a known issue with PyInstaller-packaged applications
    not being able to find or create temporary directories.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if running in a PyInstaller bundle
        if not getattr(sys, 'frozen', False):
            return True  # Not a PyInstaller bundle, nothing to fix
            
        # Check if running on Windows
        if platform.system() != 'Windows':
            return True  # Not Windows, nothing to fix
            
        # Create a custom temp directory
        app_temp_dir = os.path.join(os.path.dirname(sys.executable), 'temp')
        os.makedirs(app_temp_dir, exist_ok=True)
        
        # Set environment variables
        os.environ['TEMP'] = app_temp_dir
        os.environ['TMP'] = app_temp_dir
        
        # Ensure the directory is writable
        test_file = os.path.join(app_temp_dir, 'test.txt')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            logger.error(f"Temp directory is not writable: {e}")
            return False
            
        logger.info(f"Fixed PyInstaller temp directory: {app_temp_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing PyInstaller temp path: {e}")
        return False 