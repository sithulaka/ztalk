const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

/**
 * Start the Flask API server
 * @param {boolean} debug Whether to run in debug mode
 * @returns {ChildProcess} The spawned process
 */
function startApiServer(debug = false) {
  // Determine the Python executable to use
  let pythonCommand = 'python';
  
  // Check for virtual environment
  const isWindows = os.platform() === 'win32';
  const rootDir = path.resolve(__dirname, '..');
  
  const venvPaths = [
    path.join(rootDir, '.venv'),
    path.join(rootDir, 'venv'),
    path.join(rootDir, '.venv312'),
    path.join(rootDir, 'env')
  ];
  
  // Find the correct Python executable
  for (const venvPath of venvPaths) {
    const pythonBinDir = isWindows ? path.join(venvPath, 'Scripts') : path.join(venvPath, 'bin');
    const pythonExe = path.join(pythonBinDir, isWindows ? 'python.exe' : 'python');
    
    if (fs.existsSync(pythonExe)) {
      pythonCommand = pythonExe;
      console.log(`Using Python from virtual environment: ${pythonCommand}`);
      break;
    }
  }
  
  // API server script path
  const apiServerPath = path.join(rootDir, 'app.py');
  
  // Check if the API server exists
  if (!fs.existsSync(apiServerPath)) {
    throw new Error(`API server script not found at ${apiServerPath}`);
  }
  
  // Command line arguments for the API server
  const args = [apiServerPath];
  if (debug) {
    args.push('--debug');
  }
  
  // Spawn the API server process
  const apiProcess = spawn(pythonCommand, args, {
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false
  });
  
  // Log stdout and stderr from the API server
  apiProcess.stdout.on('data', (data) => {
    console.log(`[API Server] ${data.toString().trim()}`);
  });
  
  apiProcess.stderr.on('data', (data) => {
    console.error(`[API Server ERROR] ${data.toString().trim()}`);
  });
  
  // Handle process exit
  apiProcess.on('exit', (code, signal) => {
    if (code !== 0) {
      console.error(`API server exited with code ${code} and signal ${signal}`);
    }
  });
  
  // Handle process error
  apiProcess.on('error', (err) => {
    console.error(`Failed to start API server: ${err.message}`);
  });
  
  return apiProcess;
}

// Check if this script is being run directly
if (require.main === module) {
  console.log('Starting API server...');
  const debug = process.argv.includes('--debug');
  const apiProcess = startApiServer(debug);
  
  // Handle termination signals to clean up the child process
  process.on('SIGINT', () => {
    console.log('Terminating API server...');
    
    if (os.platform() === 'win32') {
      // On Windows, we need to kill the process
      apiProcess.kill();
    } else {
      // On Unix, we can use the negative PID to kill the process group
      process.kill(-apiProcess.pid, 'SIGINT');
    }
    
    process.exit(0);
  });
} else {
  // Export the function if this script is being imported
  module.exports = { startApiServer };
} 