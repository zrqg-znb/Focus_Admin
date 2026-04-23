import { useEffect } from 'react';

import { redirectToFocusLogin } from '@/shared/focus/focusAuth';

export default function Login() {
  useEffect(() => {
    redirectToFocusLogin();
  }, []);

  return (
    <div className="min-h-screen cyber-bg-elevated flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="loading-spinner mx-auto" />
        <p className="text-muted-foreground text-sm uppercase tracking-wider">
          Redirecting to Focus Login...
        </p>
      </div>
    </div>
  );
}
