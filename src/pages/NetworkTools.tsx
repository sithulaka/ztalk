import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { toast } from 'react-toastify';
import { ArrowPathIcon, ServerIcon, SignalIcon, ComputerDesktopIcon } from '@heroicons/react/24/outline';

interface NetworkInterface {
  name: string;
  displayName: string;
  ipv4: string;
  ipv6: string;
  mac: string;
  isUp: boolean;
  isInternal: boolean;
}

interface NetworkStat {
  rxBytes: number;
  txBytes: number;
  rxPackets: number;
  txPackets: number;
  latency: number;
}

interface NetworkDevice {
  ip: string;
  mac: string;
  hostname: string;
  isActive: boolean;
}

const NetworkTools: React.FC = () => {
  // Network interfaces state
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [selectedInterface, setSelectedInterface] = useState<string>('');
  const [customIpConfig, setCustomIpConfig] = useState({
    ipv4: '',
    subnet: '255.255.255.0',
    gateway: '',
    dns: ''
  });
  
  // Network scanning state
  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState<NetworkDevice[]>([]);
  const [deviceCount, setDeviceCount] = useState(0);
  
  // Network stats
  const [stats, setStats] = useState<NetworkStat | null>(null);
  const [isPinging, setIsPinging] = useState(false);
  const [pingTarget, setPingTarget] = useState('8.8.8.8');
  const [pingResults, setPingResults] = useState<{min: number, avg: number, max: number, loss: number} | null>(null);
  
  // Fetch network interfaces on mount
  useEffect(() => {
    fetchNetworkInterfaces();
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      if (!isScanning && !isPinging) {
        fetchNetworkInterfaces();
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, [isScanning, isPinging]);
  
  // Fetch network interfaces from the Electron backend
  const fetchNetworkInterfaces = async () => {
    try {
      // This would normally use Electron's IPC to fetch from OS
      // For demo, we'll simulate with mock data
      const mockInterfaces: NetworkInterface[] = [
        {
          name: 'en0',
          displayName: 'Wi-Fi',
          ipv4: '192.168.1.5',
          ipv6: 'fe80::1234:5678:abcd:ef01',
          mac: '00:11:22:33:44:55',
          isUp: true,
          isInternal: false
        },
        {
          name: 'lo0',
          displayName: 'Loopback',
          ipv4: '127.0.0.1',
          ipv6: '::1',
          mac: '00:00:00:00:00:00',
          isUp: true,
          isInternal: true
        },
        {
          name: 'eth0',
          displayName: 'Ethernet',
          ipv4: '192.168.2.10',
          ipv6: 'fe80::5678:abcd:ef01:1234',
          mac: 'AA:BB:CC:DD:EE:FF',
          isUp: false,
          isInternal: false
        }
      ];
      
      setInterfaces(mockInterfaces);
      
      // Set first non-internal interface as default
      const defaultInterface = mockInterfaces.find(iface => !iface.isInternal && iface.isUp);
      if (defaultInterface && !selectedInterface) {
        setSelectedInterface(defaultInterface.name);
        setCustomIpConfig({
          ipv4: defaultInterface.ipv4,
          subnet: '255.255.255.0',
          gateway: defaultInterface.ipv4.split('.').slice(0, 3).join('.') + '.1',
          dns: '8.8.8.8'
        });
        
        // Fetch initial stats for the selected interface
        fetchNetworkStats(defaultInterface.name);
      }
    } catch (error) {
      console.error('Failed to fetch network interfaces:', error);
      toast.error('Failed to load network interfaces');
    }
  };
  
  // Fetch network statistics for the selected interface
  const fetchNetworkStats = async (interfaceName: string) => {
    try {
      // This would normally use Electron's IPC to fetch stats
      // For demo, we'll simulate with mock data
      const mockStats: NetworkStat = {
        rxBytes: Math.floor(Math.random() * 10000000),
        txBytes: Math.floor(Math.random() * 5000000),
        rxPackets: Math.floor(Math.random() * 10000),
        txPackets: Math.floor(Math.random() * 5000),
        latency: Math.floor(Math.random() * 50) + 10
      };
      
      setStats(mockStats);
    } catch (error) {
      console.error('Failed to fetch network stats:', error);
      toast.error('Failed to load network statistics');
    }
  };
  
  // Handle interface selection change
  const handleInterfaceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const ifaceName = e.target.value;
    setSelectedInterface(ifaceName);
    
    const iface = interfaces.find(i => i.name === ifaceName);
    if (iface) {
      setCustomIpConfig({
        ipv4: iface.ipv4,
        subnet: '255.255.255.0',
        gateway: iface.ipv4.split('.').slice(0, 3).join('.') + '.1',
        dns: '8.8.8.8'
      });
      
      fetchNetworkStats(ifaceName);
    }
  };
  
  // Start a network scan
  const startNetworkScan = async () => {
    if (isScanning) return;
    
    setIsScanning(true);
    setScanResults([]);
    
    // Get the selected interface
    const iface = interfaces.find(i => i.name === selectedInterface);
    if (!iface) {
      toast.error('Please select a valid network interface');
      setIsScanning(false);
      return;
    }
    
    toast.info(`Scanning network on ${iface.displayName} (${iface.ipv4})...`);
    
    // Extract network prefix from IP
    const ipPrefix = iface.ipv4.split('.').slice(0, 3).join('.');
    
    // Simulate scan progress
    const totalDevices = Math.floor(Math.random() * 10) + 5;
    setDeviceCount(0);
    const foundDevices: NetworkDevice[] = [];
    
    // Simulate finding devices over time
    for (let i = 0; i < totalDevices; i++) {
      await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));
      
      const newDevice: NetworkDevice = {
        ip: `${ipPrefix}.${Math.floor(Math.random() * 254) + 1}`,
        mac: Array(6).fill(0).map(() => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')).join(':'),
        hostname: ['Desktop', 'Laptop', 'Phone', 'Tablet', 'TV', 'Printer'][Math.floor(Math.random() * 6)] + `-${Math.floor(Math.random() * 100)}`,
        isActive: Math.random() > 0.2
      };
      
      foundDevices.push(newDevice);
      setDeviceCount(i + 1);
      setScanResults([...foundDevices]);
    }
    
    toast.success(`Scan complete. Found ${totalDevices} devices.`);
    setIsScanning(false);
  };
  
  // Start a ping test
  const startPingTest = async () => {
    if (isPinging) return;
    
    if (!pingTarget) {
      toast.error('Please enter a valid IP address or domain');
      return;
    }
    
    setIsPinging(true);
    setPingResults(null);
    
    toast.info(`Pinging ${pingTarget}...`);
    
    // Simulate ping test
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Random results between 10-100ms with 0-5% packet loss
    const min = Math.floor(Math.random() * 50) + 10;
    const max = min + Math.floor(Math.random() * 50) + 10;
    const avg = Math.floor((min + max) / 2);
    const loss = Math.random() > 0.8 ? Math.random() * 5 : 0;
    
    setPingResults({ min, avg, max, loss });
    setIsPinging(false);
    
    if (loss === 0) {
      toast.success(`Ping complete: ${avg}ms average`);
    } else {
      toast.warning(`Ping complete: ${avg}ms average with ${loss.toFixed(1)}% packet loss`);
    }
  };
  
  // Apply custom IP configuration
  const applyCustomIpConfig = () => {
    // Validate IP format
    const ipv4Regex = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
    if (!ipv4Regex.test(customIpConfig.ipv4)) {
      toast.error('Invalid IPv4 address format');
      return;
    }
    
    if (!ipv4Regex.test(customIpConfig.gateway)) {
      toast.error('Invalid gateway address format');
      return;
    }
    
    toast.info(`Applying IP configuration to ${selectedInterface}...`);
    
    // This would normally use Electron's IPC to apply config
    // For demo, we'll simulate the process
    setTimeout(() => {
      // Update the interfaces array with the new IP
      setInterfaces(prev => 
        prev.map(iface => 
          iface.name === selectedInterface 
            ? { ...iface, ipv4: customIpConfig.ipv4 } 
            : iface
        )
      );
      
      toast.success('IP configuration applied successfully');
    }, 2000);
  };
  
  // Format bytes to human-readable format
  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };
  
  return (
    <Layout title="Network Tools">
      <div className="space-y-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-card">
          <h2 className="text-xl font-semibold mb-4">Network Interfaces</h2>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Select Interface
            </label>
            <select 
              className="input" 
              value={selectedInterface} 
              onChange={handleInterfaceChange}
            >
              <option value="">Select an interface</option>
              {interfaces.map(iface => (
                <option 
                  key={iface.name} 
                  value={iface.name}
                  disabled={!iface.isUp}
                >
                  {iface.displayName} ({iface.ipv4}) {!iface.isUp && '- Down'}
                </option>
              ))}
            </select>
          </div>
          
          {selectedInterface && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Interface Details */}
              <div className="space-y-2">
                <h3 className="text-lg font-medium">Interface Details</h3>
                {interfaces.find(i => i.name === selectedInterface) && (
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 space-y-2">
                    {(() => {
                      const iface = interfaces.find(i => i.name === selectedInterface);
                      if (!iface) return null;
                      
                      return (
                        <>
                          <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Name:</span>
                            <span className="font-medium">{iface.displayName} ({iface.name})</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Status:</span>
                            <span className={`font-medium ${iface.isUp ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                              {iface.isUp ? 'Up' : 'Down'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">MAC Address:</span>
                            <span className="font-medium">{iface.mac}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">IPv4 Address:</span>
                            <span className="font-medium">{iface.ipv4}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">IPv6 Address:</span>
                            <span className="font-medium text-xs md:text-sm truncate max-w-[200px]">{iface.ipv6}</span>
                          </div>
                          
                          {stats && (
                            <>
                              <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">RX/TX:</span>
                                  <span className="font-medium">
                                    {formatBytes(stats.rxBytes)} / {formatBytes(stats.txBytes)}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Packets:</span>
                                  <span className="font-medium">
                                    {stats.rxPackets.toLocaleString()} / {stats.txPackets.toLocaleString()}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Latency:</span>
                                  <span className="font-medium">
                                    {stats.latency} ms
                                  </span>
                                </div>
                              </div>
                              <div className="text-right text-xs text-gray-500 dark:text-gray-400">
                                <button
                                  onClick={() => fetchNetworkStats(selectedInterface)}
                                  className="text-primary-600 dark:text-primary-400 hover:underline"
                                >
                                  Refresh Stats
                                </button>
                              </div>
                            </>
                          )}
                        </>
                      );
                    })()}
                  </div>
                )}
              </div>
              
              {/* IP Configuration */}
              <div className="space-y-2">
                <h3 className="text-lg font-medium">IP Configuration</h3>
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      IP Address
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={customIpConfig.ipv4}
                      onChange={(e) => setCustomIpConfig(prev => ({ ...prev, ipv4: e.target.value }))}
                      placeholder="192.168.1.10"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Subnet Mask
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={customIpConfig.subnet}
                      onChange={(e) => setCustomIpConfig(prev => ({ ...prev, subnet: e.target.value }))}
                      placeholder="255.255.255.0"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Default Gateway
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={customIpConfig.gateway}
                      onChange={(e) => setCustomIpConfig(prev => ({ ...prev, gateway: e.target.value }))}
                      placeholder="192.168.1.1"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      DNS Server
                    </label>
                    <input
                      type="text"
                      className="input"
                      value={customIpConfig.dns}
                      onChange={(e) => setCustomIpConfig(prev => ({ ...prev, dns: e.target.value }))}
                      placeholder="8.8.8.8"
                    />
                  </div>
                  
                  <button
                    onClick={applyCustomIpConfig}
                    className="btn-primary w-full mt-2"
                  >
                    Apply Configuration
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Network Diagnostics */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-card">
          <h2 className="text-xl font-semibold mb-4">Network Diagnostics</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Network Scan */}
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Network Scan</h3>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                  Scan your local network to discover connected devices.
                </p>
                
                <button
                  onClick={startNetworkScan}
                  disabled={isScanning || !selectedInterface}
                  className="btn-primary w-full flex justify-center items-center"
                >
                  {isScanning ? (
                    <>
                      <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                      Scanning... ({deviceCount} devices found)
                    </>
                  ) : (
                    <>
                      <SignalIcon className="h-5 w-5 mr-2" />
                      Scan Network
                    </>
                  )}
                </button>
                
                {scanResults.length > 0 && (
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-100 dark:bg-gray-800">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">IP Address</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Hostname</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {scanResults.map((device, idx) => (
                          <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">{device.ip}</td>
                            <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">{device.hostname}</td>
                            <td className="px-3 py-2 whitespace-nowrap text-sm">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                device.isActive 
                                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' 
                                  : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                              }`}>
                                {device.isActive ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
            
            {/* Ping Test */}
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Latency Test</h3>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                  Test the connection to a specific host.
                </p>
                
                <div className="flex mb-4">
                  <input
                    type="text"
                    className="input rounded-r-none flex-1"
                    value={pingTarget}
                    onChange={(e) => setPingTarget(e.target.value)}
                    placeholder="8.8.8.8 or example.com"
                  />
                  <button
                    onClick={startPingTest}
                    disabled={isPinging}
                    className="btn-primary rounded-l-none whitespace-nowrap"
                  >
                    {isPinging ? (
                      <>
                        <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                        Pinging...
                      </>
                    ) : (
                      'Run Test'
                    )}
                  </button>
                </div>
                
                {pingResults && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Min Latency</div>
                        <div className="text-lg font-medium">{pingResults.min} ms</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Max Latency</div>
                        <div className="text-lg font-medium">{pingResults.max} ms</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Average</div>
                        <div className="text-lg font-medium">{pingResults.avg} ms</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Packet Loss</div>
                        <div className={`text-lg font-medium ${
                          pingResults.loss > 0 
                            ? 'text-yellow-600 dark:text-yellow-400' 
                            : 'text-green-600 dark:text-green-400'
                        }`}>
                          {pingResults.loss.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                    
                    <div className="mt-4">
                      <div className="h-2 w-full bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${
                            pingResults.avg < 30 
                              ? 'bg-green-500' 
                              : pingResults.avg < 80 
                                ? 'bg-yellow-500' 
                                : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(100, (pingResults.avg / 2))}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                        <span>0 ms</span>
                        <span>100 ms</span>
                        <span>200+ ms</span>
                      </div>
                    </div>
                  </div>
                )}
                
                <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                  <div className="flex items-center mb-1">
                    <span className="h-2 w-2 rounded-full bg-green-500 mr-1"></span>
                    &lt; 30ms: Excellent
                  </div>
                  <div className="flex items-center mb-1">
                    <span className="h-2 w-2 rounded-full bg-yellow-500 mr-1"></span>
                    30-80ms: Good
                  </div>
                  <div className="flex items-center">
                    <span className="h-2 w-2 rounded-full bg-red-500 mr-1"></span>
                    &gt; 80ms: Poor
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default NetworkTools; 