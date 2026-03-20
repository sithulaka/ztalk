const { app, BrowserWindow, ipcMain, dialog, Menu, Notification, session, globalShortcut } = require('electron');
const path = require('path');
const url = require('url');
const os = require('os');
const { networkInterfaces } = require('os');
const fs = require('fs');
const { exec } = require('child_process');
const axios = require('axios');

const API_URL = 'http://localhost:5000/api';

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
app.whenReady().then(() => {
  // #6: Add Content Security Policy headers
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({ responseHeaders: { ...details.responseHeaders,
      'Content-Security-Policy': ["default-src 'self'; script-src 'self'; connect-src 'self' http://localhost:5000 ws://localhost:5000; style-src 'self' 'unsafe-inline'"]
    }})
  });

  // #55: Register keyboard shortcut to toggle DevTools
  const shortcut = process.platform === 'darwin' ? 'Cmd+Option+I' : 'Ctrl+Shift+I';
  globalShortcut.register(shortcut, () => {
    if (mainWindow) {
      mainWindow.webContents.toggleDevTools();
    }
  });

  createWindow();
});

// Unregister shortcuts before quitting
app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

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
    const response = await axios.get(`${API_URL}/network/interfaces/${interfaceName}`);
    return response.data;
  } catch (error) {
    console.error('Error getting IP config:', error);
    throw error;
  }
});

// Apply IP configuration
ipcMain.handle('apply-ip-config', async (event, config) => {
  try {
    const response = await axios.post(`${API_URL}/network/interfaces/${config.interfaceName}/config`, config);
    return response.data;
  } catch (error) {
    console.error('Error applying IP config:', error);
    throw error;
  }
});

// Scan network for devices
ipcMain.handle('scan-network', async () => {
  try {
    const response = await axios.get(`${API_URL}/network/scan`);
    return response.data;
  } catch (error) {
    console.error('Error scanning network:', error);
    throw error;
  }
});

// Ping host
ipcMain.handle('ping-host', async (event, target) => {
  try {
    const response = await axios.post(`${API_URL}/network/ping`, { target });
    return response.data;
  } catch (error) {
    console.error('Error pinging host:', error);
    throw error;
  }
});

// SSH operations
ipcMain.handle('ssh-connect', async (event, connection) => {
  try {
    const response = await axios.post(`${API_URL}/ssh/connect`, connection);
    return response.data;
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