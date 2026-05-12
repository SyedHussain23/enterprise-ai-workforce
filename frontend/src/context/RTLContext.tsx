import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface RTLContextType {
  isRTL: boolean;
  toggleRTL: () => void;
}

const RTLContext = createContext<RTLContextType | null>(null);

export function RTLProvider({ children }: { children: ReactNode }) {
  const [isRTL, setIsRTL] = useState(() => localStorage.getItem('rtl') === 'true');

  useEffect(() => {
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = isRTL ? 'ar' : 'en';
    localStorage.setItem('rtl', String(isRTL));
  }, [isRTL]);

  function toggleRTL() {
    setIsRTL((v) => !v);
  }

  return (
    <RTLContext.Provider value={{ isRTL, toggleRTL }}>
      {children}
    </RTLContext.Provider>
  );
}

export function useRTL() {
  const ctx = useContext(RTLContext);
  if (!ctx) throw new Error('useRTL must be used within RTLProvider');
  return ctx;
}
