import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useNetwork } from '../contexts/NetworkContext';

import {
  HomeIcon,
  ChatBubbleLeftRightIcon,
  CommandLineIcon,
  WrenchScrewdriverIcon,
  Cog6ToothIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
  XMarkIcon
} from '@heroicons/react/24/outline';

interface LayoutProps {
  children: React.ReactNode;
  title: string;
}

const Layout: React.FC<LayoutProps> = ({ children, title }) => {
  const { theme, toggleTheme } = useTheme();
  const { isConnected, peers } = useNetwork();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: HomeIcon },
    { path: '/chat', label: 'Chat', icon: ChatBubbleLeftRightIcon },
    { path: '/ssh', label: 'SSH', icon: CommandLineIcon },
    { path: '/network-tools', label: 'Network Tools', icon: WrenchScrewdriverIcon },
    { path: '/settings', label: 'Settings', icon: Cog6ToothIcon },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar for desktop */}
      <div className="hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-center h-16 px-4 bg-primary-600 dark:bg-primary-700">
            <h1 className="text-xl font-bold text-white">ZTalk</h1>
          </div>
          
          <div className="flex flex-col flex-grow px-4 pt-5 pb-4 overflow-y-auto">
            <nav className="flex-1 space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                      location.pathname === item.path
                        ? 'bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-200'
                        : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                    }`}
                  >
                    <Icon className="mr-3 h-6 w-6" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            
            <div className="mt-auto pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={toggleTheme}
                className="flex items-center w-full px-2 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
              >
                {theme === 'dark' ? (
                  <SunIcon className="mr-3 h-6 w-6" />
                ) : (
                  <MoonIcon className="mr-3 h-6 w-6" />
                )}
                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile header */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <div className="md:hidden bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between h-16 px-4">
            <div className="flex items-center">
              <button
                onClick={() => setIsMobileMenuOpen(true)}
                className="text-gray-600 dark:text-gray-300 focus:outline-none"
              >
                <Bars3Icon className="h-6 w-6" />
              </button>
              <h1 className="ml-3 text-xl font-bold text-gray-900 dark:text-white">ZTalk</h1>
            </div>
            
            <div className="flex items-center">
              <span className={`mr-2 h-2 w-2 rounded-full ${isConnected ? 'bg-success-500' : 'bg-danger-500'}`}></span>
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {isConnected ? `${peers.length} peers` : 'Offline'}
              </span>
            </div>
          </div>
        </div>
        
        {/* Mobile sidebar */}
        {isMobileMenuOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setIsMobileMenuOpen(false)}></div>
            
            <div className="relative flex flex-col w-full max-w-xs pt-5 pb-4 bg-white dark:bg-gray-800 h-full">
              <div className="absolute top-0 right-0 p-1">
                <button
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="flex items-center justify-center h-10 w-10 rounded-full focus:outline-none"
                >
                  <XMarkIcon className="h-6 w-6 text-gray-600 dark:text-gray-300" />
                </button>
              </div>
              
              <div className="flex items-center justify-center h-16 px-4">
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">ZTalk</h1>
              </div>
              
              <div className="flex-1 px-2 mt-5 overflow-y-auto">
                <nav className="space-y-2">
                  {navItems.map((item) => {
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        className={`group flex items-center px-2 py-2 text-base font-medium rounded-md ${
                          location.pathname === item.path
                            ? 'bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-200'
                            : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                        }`}
                        onClick={() => setIsMobileMenuOpen(false)}
                      >
                        <Icon className="mr-4 h-6 w-6" />
                        {item.label}
                      </Link>
                    );
                  })}
                </nav>
              </div>
              
              <div className="px-2 mt-auto pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => {
                    toggleTheme();
                    setIsMobileMenuOpen(false);
                  }}
                  className="flex items-center w-full px-2 py-2 text-base font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
                >
                  {theme === 'dark' ? (
                    <SunIcon className="mr-3 h-6 w-6" />
                  ) : (
                    <MoonIcon className="mr-3 h-6 w-6" />
                  )}
                  {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Main content */}
        <main className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              <div className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{title}</h1>
                <div className="hidden md:flex items-center">
                  <span className={`mr-2 h-2 w-2 rounded-full ${isConnected ? 'bg-success-500' : 'bg-danger-500'}`}></span>
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    {isConnected ? `${peers.length} peers` : 'Offline'}
                  </span>
                </div>
              </div>
            </div>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-4">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout; 