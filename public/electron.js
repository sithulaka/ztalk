const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron');
const path = require('path');
const url = require('url');
const os = require('os');
const { networkInterfaces } = require('os');
const fs = require('fs');
const { exec } = require('child_process');

// Keep a global reference of the window object to avoid garbage collection
let mainWindow;

function createWindow() {
  // Create the browser window.
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    backgroundColor: '#f5f5f5'
  });

  // In development mode, load from localhost:3000
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  const loadUrl = isDev ? 'http://localhost:3000' : url.format({
    pathname: path.join(__dirname, '../build/index.html'),
    protocol: 'file:',
    slashes: true
  });
  
  mainWindow.loadURL(loadUrl).catch(err => {
    console.error('Failed to load URL:', err);
    if (isDev) {
      mainWindow.loadFile(path.join(__dirname, 'index.html')).catch(err => {
        console.error('Failed to load file as fallback:', err);
      });
    }
  });

  // Open DevTools automatically in development mode
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // Show window when it's ready to avoid flickering
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Emitted when the window is closed.
  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
app.whenReady().then(createWindow);

// Quit when all windows are closed, except on macOS.
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', function () {
  if (mainWindow === null) createWindow();
});

// IPC handlers for main process communication

// Handle file open dialog
ipcMain.handle('open-file-dialog', async (event, options) => {
  const { canceled, filePaths } = await dialog.showOpenDialog(options);
  if (canceled) {
    return null;
  } else {
    return filePaths[0];
  }
});

// Handle file save dialog
ipcMain.handle('save-file-dialog', async (event, options) => {
  const { canceled, filePath } = await dialog.showSaveDialog(options);
  if (canceled) {
    return null;
  } else {
    return filePath;
  }
});

// Get network interfaces
ipcMain.handle('get-network-interfaces', async () => {
  try {
    const interfaces = networkInterfaces();
    return interfaces;
  } catch (error) {
    console.error('Error getting network interfaces:', error);
    throw error;
  }
});

// Get IP configuration and stats
ipcMain.handle('get-ip-config', async (event, interfaceName) => {
  try {
    // This would be platform-specific code to get IP configuration
    // For now, we'll return dummy data
    return {
      ip: '192.168.1.5',
      netmask: '255.255.255.0',
      gateway: '192.168.1.1',
      dns: ['8.8.8.8', '8.8.4.4']
    };
  } catch (error) {
    console.error('Error getting IP config:', error);
    throw error;
  }
});

// Apply IP configuration
ipcMain.handle('apply-ip-config', async (event, config) => {
  try {
    // This would be platform-specific code to set IP configuration
    console.log('Applying IP config:', config);
    
    // Simulate delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return { success: true };
  } catch (error) {
    console.error('Error applying IP config:', error);
    throw error;
  }
});

// Scan network for devices
ipcMain.handle('scan-network', async () => {
  try {
    // This would be platform-specific code to scan network
    // For now, we'll return dummy data
    return [
      { ip: '192.168.1.1', mac: '00:11:22:33:44:55', name: 'Router', isActive: true },
      { ip: '192.168.1.5', mac: '11:22:33:44:55:66', name: 'This device', isActive: true },
      { ip: '192.168.1.10', mac: '22:33:44:55:66:77', name: 'Desktop-123', isActive: true },
      { ip: '192.168.1.15', mac: '33:44:55:66:77:88', name: 'Laptop-456', isActive: true },
      { ip: '192.168.1.20', mac: '44:55:66:77:88:99', name: 'Phone-789', isActive: false }
    ];
  } catch (error) {
    console.error('Error scanning network:', error);
    throw error;
  }
});

// Ping host
ipcMain.handle('ping-host', async (event, target) => {
  try {
    // This would be platform-specific code to ping host
    console.log('Pinging:', target);
    
    // Simulate delay and results
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    return {
      min: 10,
      avg: 15,
      max: 30,
      loss: Math.random() > 0.8 ? 5 : 0
    };
  } catch (error) {
    console.error('Error pinging host:', error);
    throw error;
  }
});

// SSH operations
ipcMain.handle('ssh-connect', async (event, connection) => {
  try {
    // This would use ssh2 to connect
    console.log('Connecting to SSH server:', connection);
    
    // Simulate delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Simulate success/failure
    const success = Math.random() > 0.2;
    if (!success) {
      throw new Error('Connection refused');
    }
    
    return { success: true };
  } catch (error) {
    console.error('Error connecting to SSH server:', error);
    throw error;
  }
});

// SSH disconnect
ipcMain.handle('ssh-disconnect', async (event, connectionId) => {
  try {
    console.log('Disconnecting SSH connection:', connectionId);
    
    return { success: true };
  } catch (error) {
    console.error('Error disconnecting SSH server:', error);
    throw error;
  }
});

// Select SSH key file
ipcMain.handle('select-ssh-key', async () => {
  try {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [
        { name: 'SSH Keys', extensions: ['pem', 'key', 'pub'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    
    if (result.canceled) {
      return null;
    }
    
    return result.filePaths[0];
  } catch (error) {
    console.error('Error selecting SSH key:', error);
    throw error;
  }
});

// Save SSH connection
ipcMain.handle('save-ssh-connection', async (event, connection) => {
  try {
    // In a real app, this would save to a database or config file
    console.log('Saving SSH connection:', connection);
    
    return { success: true, id: Date.now().toString() };
  } catch (error) {
    console.error('Error saving SSH connection:', error);
    throw error;
  }
});

// Load SSH connections
ipcMain.handle('load-ssh-connections', async () => {
  try {
    // In a real app, this would load from a database or config file
    return [
      {
        id: '1',
        name: 'Development Server',
        host: '192.168.1.100',
        port: 22,
        username: 'dev',
        authType: 'key',
        keyPath: '~/.ssh/id_rsa',
        status: 'disconnected'
      },
      {
        id: '2',
        name: 'Production Server',
        host: 'example.com',
        port: 2222,
        username: 'admin',
        authType: 'password',
        status: 'disconnected'
      }
    ];
  } catch (error) {
    console.error('Error loading SSH connections:', error);
    throw error;
  }
});

// Delete SSH connection
ipcMain.handle('delete-ssh-connection', async (event, connectionId) => {
  try {
    console.log('Deleting SSH connection:', connectionId);
    
    return { success: true };
  } catch (error) {
    console.error('Error deleting SSH connection:', error);
    throw error;
  }
});

// Handle notifications
ipcMain.handle('show-notification', (event, options) => {
  const notification = new Notification(options);
  notification.show();
  return true;
});

// Handle app exit
ipcMain.handle('quit-app', () => {
  app.quit();
});

// Add handlers for SSH connections, file transfers, etc.
// These will be implemented later 