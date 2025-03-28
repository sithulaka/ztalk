#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Determine Python executable
const isWindows = os.platform() === 'win32';
const rootDir = path.resolve(__dirname);

// Find the virtual environment
let pythonCommand = 'python';
const venvPaths = [
  path.join(rootDir, '.venv'),
  path.join(rootDir, 'venv'),
  path.join(rootDir, '.venv312'),
  path.join(rootDir, 'env')
];

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

// Check if API server exists
if (!fs.existsSync(apiServerPath)) {
  console.error(`API server script not found at ${apiServerPath}`);
  process.exit(1);
}

// Command line arguments
const debug = process.argv.includes('--debug');
const args = [apiServerPath];
if (debug) {
  args.push('--debug');
}

console.log(`Starting API server: ${pythonCommand} ${args.join(' ')}`);

// Spawn API server process
const apiProcess = spawn(pythonCommand, args, {
  stdio: 'inherit',
  detached: false
});

// Handle process exit
apiProcess.on('exit', (code, signal) => {
  if (code !== 0) {
    console.error(`API server exited with code ${code} and signal ${signal}`);
  }
  process.exit(code || 0);
});

// Handle process error
apiProcess.on('error', (err) => {
  console.error(`Failed to start API server: ${err.message}`);
  process.exit(1);
});

// Handle termination signals
process.on('SIGINT', () => {
  console.log('Terminating API server...');
  
  if (isWindows) {
    // On Windows, we need to kill the process
    apiProcess.kill();
  } else {
    // On Unix, we can use the negative PID to kill the process group
    process.kill(-apiProcess.pid, 'SIGINT');
  }
  
  process.exit(0);
}); 