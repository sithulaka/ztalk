import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'react-toastify';

const Settings: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [username, setUsername] = useState('');
  const [notifications, setNotifications] = useState(true);

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedUsername = localStorage.getItem('settings:username') || '';
    const savedNotifications = localStorage.getItem('settings:notifications');
    setUsername(savedUsername);
    if (savedNotifications !== null) {
      setNotifications(savedNotifications === 'true');
    }
  }, []);

  const handleSaveUsername = () => {
    localStorage.setItem('settings:username', username);
    toast.success('Username saved');
  };

  const handleNotificationsChange = (checked: boolean) => {
    setNotifications(checked);
    localStorage.setItem('settings:notifications', String(checked));
  };

  return (
    <Layout title="Settings">
      <div className="space-y-6 max-w-2xl">
        <h2 className="text-xl font-semibold">Settings</h2>

        {/* Username */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-card space-y-4">
          <h3 className="text-lg font-medium">Profile</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Username
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                className="input flex-1"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
              />
              <button
                onClick={handleSaveUsername}
                className="btn-primary"
              >
                Save
              </button>
            </div>
          </div>
        </div>

        {/* Theme */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-card space-y-4">
          <h3 className="text-lg font-medium">Appearance</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Theme
            </label>
            <div className="flex space-x-4">
              {(['light', 'dark', 'darkblue'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTheme(t)}
                  className={`px-4 py-2 rounded-md text-sm font-medium border ${
                    theme === t
                      ? 'bg-primary-100 text-primary-700 border-primary-300 dark:bg-primary-900 dark:text-primary-300 dark:border-primary-700'
                      : 'bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'
                  }`}
                >
                  {t === 'darkblue' ? 'Dark Blue' : t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-card space-y-4">
          <h3 className="text-lg font-medium">Notifications</h3>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={notifications}
              onChange={(e) => handleNotificationsChange(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Enable desktop notifications for new messages
            </span>
          </label>
        </div>
      </div>
    </Layout>
  );
};

export default Settings;
