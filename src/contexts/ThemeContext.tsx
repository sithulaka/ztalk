import React, { createContext, useContext, useState, useEffect } from 'react';

type Theme = 'light' | 'dark' | 'darkblue';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  // Check if user has previously set theme
  const getInitialTheme = (): Theme => {
    const savedTheme = localStorage.getItem('theme') as Theme | null;
    
    // If user has previously set a theme, use it
    if (savedTheme && ['dark', 'light', 'darkblue'].includes(savedTheme)) {
      return savedTheme;
    }
    
    // Otherwise, check system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'darkblue' : 'light';  // Default to darkblue for dark preference
  };

  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  // Set a specific theme
  const setTheme = (newTheme: Theme) => {
    localStorage.setItem('theme', newTheme);
    setThemeState(newTheme);
  };

  // Toggle between light, dark, and darkblue themes
  const toggleTheme = () => {
    setThemeState(prevTheme => {
      let newTheme: Theme;
      
      if (prevTheme === 'light') {
        newTheme = 'dark';
      } else if (prevTheme === 'dark') {
        newTheme = 'darkblue';
      } else {
        newTheme = 'light';
      }
      
      localStorage.setItem('theme', newTheme);
      return newTheme;
    });
  };

  // Apply theme to document
  useEffect(() => {
    const root = window.document.documentElement;
    
    // Remove previous theme class
    root.classList.remove('light', 'dark', 'darkblue');
    
    // Add current theme class
    root.classList.add(theme);
    
    // Update meta theme-color for mobile browsers
    let themeColor = '#ffffff';  // default for light
    if (theme === 'dark') {
      themeColor = '#111827';  // dark gray for dark theme
    } else if (theme === 'darkblue') {
      themeColor = '#0f172a';  // dark blue color
    }
    
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', themeColor);
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = () => {
      // Only update if user hasn't set a preference
      if (!localStorage.getItem('theme')) {
        setThemeState(mediaQuery.matches ? 'darkblue' : 'light');
      }
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const value = { theme, toggleTheme, setTheme };
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

// Custom hook to use the theme context
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
}; 