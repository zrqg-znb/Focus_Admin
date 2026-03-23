import { useEffect } from 'react';
import { matchPath, Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/shared/context/AuthContext';
import routes from '@/app/routes';
import AccessDenied from '@/pages/AccessDenied';

export const ProtectedRoute = () => {
  const { hasAccess, isAuthenticated, isLoading, redirectToLogin } = useAuth();
  const location = useLocation();

  const matchedRoute = routes.find((route) =>
    Boolean(matchPath({ end: true, path: route.path }, location.pathname)),
  );

  const firstAccessibleRoute = routes.find(
    (route) =>
      route.visible !== false &&
      !route.path.includes('/:') &&
      hasAccess(route.requiredAccess),
  );

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <LoginRedirect redirectToLogin={redirectToLogin} />;
  }

  if (
    matchedRoute?.requiredAccess &&
    !hasAccess(matchedRoute.requiredAccess)
  ) {
    if (
      matchedRoute.redirectToFirstAccessible &&
      firstAccessibleRoute &&
      firstAccessibleRoute.path !== location.pathname
    ) {
      return <Navigate replace to={firstAccessibleRoute.path} />;
    }

    return <AccessDenied />;
  }

  return <Outlet />;
};

function LoginRedirect({
  redirectToLogin,
}: {
  redirectToLogin: (redirectPath?: string) => void;
}) {
  useEffect(() => {
    redirectToLogin();
  }, [redirectToLogin]);

  return <div className="flex h-screen items-center justify-center">Redirecting...</div>;
}



