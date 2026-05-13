import routes from '@/app/routes';
import AccessDenied from '@/pages/AccessDenied';
import { useAuth } from '@/shared/context/AuthContext';
import { useEffect, useRef, useState } from 'react';
import { matchPath, Navigate, Outlet, useLocation } from 'react-router-dom';

export const ProtectedRoute = () => {
  const {
    hasAccess,
    isAuthenticated,
    isLoading,
    redirectToLogin,
    refreshPermissions,
  } = useAuth();
  const location = useLocation();
  const [isRevalidating, setIsRevalidating] = useState(false);
  const revalidatedRouteRef = useRef<null | string>(null);

  const matchedRoute = routes.find((route) =>
    Boolean(matchPath({ end: true, path: route.path }, location.pathname)),
  );

  const firstAccessibleRoute = routes.find(
    (route) =>
      route.visible !== false &&
      !route.path.includes('/:') &&
      hasAccess(route.requiredAccess),
  );

  useEffect(() => {
    const requiredAccess = matchedRoute?.requiredAccess;

    if (!isAuthenticated || isLoading || !requiredAccess) {
      revalidatedRouteRef.current = null;
      setIsRevalidating(false);
      return;
    }

    if (hasAccess(requiredAccess)) {
      revalidatedRouteRef.current = null;
      setIsRevalidating(false);
      return;
    }

    const revalidationKey = `${location.pathname}::${JSON.stringify(requiredAccess)}`;
    if (revalidatedRouteRef.current === revalidationKey) {
      return;
    }

    let cancelled = false;
    revalidatedRouteRef.current = revalidationKey;
    setIsRevalidating(true);

    refreshPermissions()
      .catch(() => {
        // 保留当前权限状态，让后续的最终判定继续走 AccessDenied 分支
      })
      .finally(() => {
        if (!cancelled) {
          setIsRevalidating(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    hasAccess,
    isAuthenticated,
    isLoading,
    location.pathname,
    matchedRoute?.requiredAccess,
    refreshPermissions,
  ]);

  if (isLoading || isRevalidating) {
    return (
      <div className="flex h-screen items-center justify-center">
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginRedirect redirectToLogin={redirectToLogin} />;
  }

  if (matchedRoute?.requiredAccess && !hasAccess(matchedRoute.requiredAccess)) {
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

  return (
    <div className="flex h-screen items-center justify-center">
      Redirecting...
    </div>
  );
}
