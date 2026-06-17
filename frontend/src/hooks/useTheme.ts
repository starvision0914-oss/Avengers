import { useState, useCallback, useEffect } from 'react';

export type ThemeMode = 'dark' | 'light';
const STORAGE_KEY = 'avengers-theme';

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() => {
    try {
      return (localStorage.getItem(STORAGE_KEY) as ThemeMode) || 'dark';
    } catch {
      return 'dark';
    }
  });

  const toggle = useCallback(() => {
    setMode(prev => {
      const next = prev === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(STORAGE_KEY, next); } catch {}
      return next;
    });
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', mode === 'dark');
  }, [mode]);

  return { mode, dark: mode === 'dark', toggle };
}
