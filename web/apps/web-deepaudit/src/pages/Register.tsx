import { useEffect } from 'react';

import { redirectToFocusLogin } from '@/shared/focus/focusAuth';

export default function Register() {
  useEffect(() => {
    redirectToFocusLogin();
  }, []);

  return (
    <div className="min-h-screen cyber-bg-elevated flex items-center justify-center font-mono">
      <div className="text-center space-y-4">
        <div className="loading-spinner mx-auto" />
        <p className="text-muted-foreground text-sm uppercase tracking-wider">
          Registration is managed by Focus...
        </p>
      </div>
    </div>
  );
}
