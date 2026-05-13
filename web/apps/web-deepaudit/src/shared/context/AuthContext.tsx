import type { PermissionRequirement } from '@/shared/focus/focusPermission';
import type { ReactNode } from 'react';

import { persistStoredFocusAccess } from '@/shared/api/focusAdapter';
import {
  ensureFocusSession,
  redirectToFocusLogin,
  resetFocusSession,
} from '@/shared/focus/focusAuth';
import {
  hasAllPermissions,
  hasAnyPermission,
  hasPermission,
} from '@/shared/focus/focusPermission';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

import { normalizeProfile } from '../api/focusAdapter';
import { apiClient } from '../api/serverClient';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  avatar_url?: string;
}

interface AuthContextType {
  accessCodes: string[];
  user: null | User;
  isAuthenticated: boolean;
  isLoading: boolean;
  hasAccess: (requirement?: PermissionRequirement) => boolean;
  hasAllAccess: (codes: string[]) => boolean;
  hasAnyAccess: (codes: string[]) => boolean;
  logout: (redirectPath?: string) => Promise<void>;
  redirectToLogin: (redirectPath?: string) => void;
  refreshPermissions: () => Promise<string[]>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [accessCodes, setAccessCodes] = useState<string[]>([]);
  const [user, setUser] = useState<null | User>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const refreshPermissions = useCallback(async () => {
    const response = await apiClient.get<string[]>('/core/permCode');
    const nextAccessCodes = Array.isArray(response.data) ? response.data : [];
    setAccessCodes(nextAccessCodes);
    persistStoredFocusAccess({ accessCodes: nextAccessCodes });
    return nextAccessCodes;
  }, []);

  useEffect(() => {
    let mounted = true;

    const bootstrapAuth = async () => {
      try {
        const session = await ensureFocusSession();
        if (!session) {
          if (mounted) {
            setAccessCodes([]);
            setUser(null);
            setIsAuthenticated(false);
          }
          return;
        }

        let resolvedAccessCodes = session.accessCodes;
        try {
          resolvedAccessCodes = await refreshPermissions();
        } catch (error) {
          if (resolvedAccessCodes.length === 0) {
            throw error;
          }
        }

        let normalizedUser = null;
        try {
          const response = await apiClient.get('/users/me');
          normalizedUser = normalizeProfile(response.data);
        } catch {
          const response = await apiClient.get('/core/userinfo');
          normalizedUser = normalizeProfile(response.data);
        }

        if (!mounted) {
          return;
        }

        setAccessCodes(resolvedAccessCodes);
        setUser(normalizedUser);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Focus auth bootstrap failed', error);
        if (mounted) {
          setAccessCodes([]);
          setUser(null);
          setIsAuthenticated(false);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    bootstrapAuth();

    return () => {
      mounted = false;
    };
  }, [refreshPermissions]);

  const logout = async (redirectPath?: string) => {
    try {
      await apiClient.get('/core/logout');
    } catch {
      // ignore logout errors, local cleanup still needs to happen
    }

    resetFocusSession();
    setAccessCodes([]);
    setUser(null);
    setIsAuthenticated(false);
    redirectToFocusLogin(redirectPath);
  };

  return (
    <AuthContext.Provider
      value={{
        accessCodes,
        user,
        isAuthenticated,
        isLoading,
        hasAccess: (requirement) => hasPermission(accessCodes, requirement),
        hasAllAccess: (codes) => hasAllPermissions(accessCodes, codes),
        hasAnyAccess: (codes) => hasAnyPermission(accessCodes, codes),
        logout,
        redirectToLogin: redirectToFocusLogin,
        refreshPermissions,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
