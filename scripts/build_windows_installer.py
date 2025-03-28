#!/usr/bin/env python3
"""
Windows Installer Builder for ZTalk

This script creates a Windows installer for ZTalk using the windows_utils module.
It handles packaging the application, building the installer, and optionally
deploying it to a specified location.
"""

import os
import sys
import argparse
import logging
import shutil
import subprocess
import tempfile
import platform
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Once parent directory is in path, import our modules
from utils import windows_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("windows_installer")

# Version information
APP_NAME = "ZTalk"
VERSION = "1.0.0"  # Update this when necessary

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Build Windows installer for ZTalk")
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist"),
        help="Directory where to save the installer (default: ./dist)"
    )
    
    parser.add_argument(
        "--version", "-v",
        type=str,
        default=VERSION,
        help=f"Version number for the installer (default: {VERSION})"
    )
    
    parser.add_argument(
        "--icon", "-i",
        type=str,
        help="Path to icon file (.ico)"
    )
    
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip building the executable (use existing build in ./dist)"
    )
    
    parser.add_argument(
        "--deploy", "-d",
        type=str,
        help="Path where to deploy the installer after building"
    )
    
    return parser.parse_args()

def check_prerequisites():
    """Check if all prerequisites are installed"""
    if platform.system() != "Windows":
        logger.error("This script must be run on Windows")
        return False
        
    # Check if PyInstaller is installed
    try:
        subprocess.check_output(["pyinstaller", "--version"], stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("PyInstaller is not installed. Please install it using: pip install pyinstaller")
        return False
        
    # Check if NSIS is installed (not critical but warn)
    nsis_found = False
    for path in [r"C:\Program Files\NSIS\makensis.exe", r"C:\Program Files (x86)\NSIS\makensis.exe"]:
        if os.path.exists(path):
            nsis_found = True
            break
            
    if not nsis_found:
        logger.warning("NSIS not found. Please install NSIS from https://nsis.sourceforge.io/")
        return False
        
    return True

def build_executable(args):
    """Build the executable using PyInstaller"""
    logger.info("Building executable with PyInstaller...")
    
    # Root directory of the project
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create spec file for PyInstaller
    spec_file = os.path.join(project_root, f"{APP_NAME.lower()}.spec")
    
    # Check if icon exists
    icon_arg = f"--icon={args.icon}" if args.icon and os.path.exists(args.icon) else ""
    
    # Clean previous build if it exists
    for path in ["build", "dist", spec_file]:
        full_path = os.path.join(project_root, path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
    
    # Build PyInstaller command
    pyinstaller_cmd = [
        "pyinstaller",
        "--name", APP_NAME.lower(),
        "--onedir",
        "--windowed",
        "--clean",
        "--add-data", f"assets{os.pathsep}assets",
        "--add-data", f"configs{os.pathsep}configs",
        "--hidden-import", "pkg_resources.py2_warn",
        "--hidden-import", "netifaces",
        "--hidden-import", "zeroconf",
        "--hidden-import", "paramiko",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "numpy",
        "--noconfirm",
    ]
    
    # Add icon if provided
    if icon_arg:
        pyinstaller_cmd.append(icon_arg)
        
    # Add main script
    pyinstaller_cmd.append(os.path.join(project_root, "main.py"))
    
    # Run PyInstaller
    process = subprocess.run(
        pyinstaller_cmd,
        cwd=project_root,
        capture_output=True,
        text=True
    )
    
    if process.returncode != 0:
        logger.error(f"PyInstaller failed with exit code {process.returncode}")
        logger.error(f"Error output: {process.stderr}")
        return False
        
    logger.info(f"PyInstaller completed successfully, output in {os.path.join(project_root, 'dist')}")
    return True

def create_portable_version(args):
    """Create a portable version of the application"""
    logger.info("Creating portable version...")
    
    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_dir = os.path.join(project_root, "dist")
    app_dir = os.path.join(dist_dir, APP_NAME.lower())
    portable_dir = os.path.join(dist_dir, f"{APP_NAME}_Portable")
    
    # Create portable directory
    os.makedirs(portable_dir, exist_ok=True)
    
    # Copy application files
    for item in os.listdir(app_dir):
        src = os.path.join(app_dir, item)
        dst = os.path.join(portable_dir, item)
        
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    
    # Create portable flag file
    with open(os.path.join(portable_dir, "portable.flag"), "w") as f:
        f.write("This is a portable version of ZTalk. All data will be stored in this directory.")
        
    # Create ZIP archive
    portable_zip = os.path.join(args.output_dir, f"{APP_NAME}_Portable_{args.version}.zip")
    shutil.make_archive(os.path.splitext(portable_zip)[0], "zip", dist_dir, f"{APP_NAME}_Portable")
    
    logger.info(f"Created portable version at {portable_zip}")
    return True

def build_installer(args):
    """Build the Windows installer using NSIS"""
    logger.info("Building Windows installer...")
    
    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(project_root, "dist", APP_NAME.lower())
    
    if not os.path.exists(source_dir):
        logger.error(f"Source directory not found: {source_dir}")
        return False
        
    # Copy license file if it exists
    license_file = os.path.join(project_root, "LICENSE")
    if not os.path.exists(os.path.join(source_dir, "LICENSE")) and os.path.exists(license_file):
        shutil.copy2(license_file, source_dir)
        
    # Copy icon to source directory if provided
    icon_path = None
    if args.icon and os.path.exists(args.icon):
        icon_name = os.path.basename(args.icon)
        dest_icon = os.path.join(source_dir, icon_name)
        shutil.copy2(args.icon, dest_icon)
        icon_path = dest_icon
        
    # Build installer
    installer_path = windows_utils.build_windows_installer(
        source_dir=source_dir,
        output_dir=args.output_dir,
        app_name=APP_NAME,
        version=args.version,
        icon_path=icon_path
    )
    
    if installer_path:
        logger.info(f"Successfully built installer: {installer_path}")
        return installer_path
    else:
        logger.error("Failed to build installer")
        return None

def deploy_installer(installer_path, deploy_path):
    """Deploy the installer to the specified path"""
    if not installer_path or not os.path.exists(installer_path):
        logger.error("Installer not found, cannot deploy")
        return False
        
    if not deploy_path:
        logger.warning("No deploy path specified, skipping deployment")
        return False
        
    try:
        # Create deployment directory if it doesn't exist
        os.makedirs(deploy_path, exist_ok=True)
        
        # Copy installer to deploy path
        dest_file = os.path.join(deploy_path, os.path.basename(installer_path))
        shutil.copy2(installer_path, dest_file)
        
        logger.info(f"Deployed installer to {dest_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error deploying installer: {e}")
        return False

def main():
    """Main entry point"""
    args = parse_arguments()
    
    logger.info(f"Starting Windows installer build for {APP_NAME} v{args.version}")
    
    # Check prerequisites
    if not check_prerequisites():
        logger.error("Prerequisites not met, aborting")
        return 1
        
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Build executable
    if not args.no_build:
        if not build_executable(args):
            logger.error("Failed to build executable, aborting")
            return 1
    else:
        logger.info("Skipping executable build (--no-build specified)")
        
    # Create portable version
    create_portable_version(args)
    
    # Build installer
    installer_path = build_installer(args)
    if not installer_path:
        logger.error("Failed to build installer")
        return 1
        
    # Deploy installer if requested
    if args.deploy:
        if not deploy_installer(installer_path, args.deploy):
            logger.warning("Failed to deploy installer")
            
    logger.info("Windows installer build completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 