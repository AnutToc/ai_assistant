import { createRoot } from 'react-dom/client';
import { FloatingChat } from './components/FloatingChat';
import { FullPageChat } from './components/FullPageChat';
import './styles/globals.css';

export function mountFloating(container: HTMLElement) {
  const root = createRoot(container);
  root.render(<FloatingChat />);
  return () => root.unmount();
}

export function mountFullPage(container: HTMLElement) {
  const root = createRoot(container);
  root.render(<FullPageChat />);
  return () => root.unmount();
}

// Expose to window for Odoo
// @ts-ignore
window.AIChatWidget = { mountFloating, mountFullPage };

// Auto-mount when running standalone Vite dev server (npm run dev)
if (import.meta.env.DEV) {
  const rootEl = document.getElementById('root');
  if (rootEl) {
    createRoot(rootEl).render(
      <div style={{ height: '100vh', width: '100vw' }}>
        <FullPageChat />
        <FloatingChat />
      </div>
    );
  }
}
