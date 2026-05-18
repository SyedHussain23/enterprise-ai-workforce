import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';
import { ErrorBoundary } from './components/shared/ErrorBoundary.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/*
      Global error boundary: catches any render-phase error in the entire tree
      and shows a recovery UI instead of a white screen.
      See: src/components/shared/ErrorBoundary.tsx
    */}
    <ErrorBoundary scope="root">
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
