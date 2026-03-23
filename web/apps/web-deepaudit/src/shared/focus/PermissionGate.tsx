import type { ReactNode } from 'react';

import { useAuth } from '@/shared/context/AuthContext';
import type { PermissionRequirement } from '@/shared/focus/focusPermission';

interface PermissionGateProps {
  children: ReactNode;
  fallback?: ReactNode;
  requirement?: PermissionRequirement;
}

export function PermissionGate({
  children,
  fallback = null,
  requirement,
}: PermissionGateProps) {
  const { hasAccess } = useAuth();
  return hasAccess(requirement) ? <>{children}</> : <>{fallback}</>;
}
