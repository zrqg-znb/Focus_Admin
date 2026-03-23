import axios from 'axios';

import {
  API_BASE_URL,
  clearStoredFocusAccess,
  getCurrentAppPath,
  getStoredFocusAccess,
  persistStoredFocusAccess,
} from '@/shared/api/focusAdapter';

const focusAuthClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshPromise: null | Promise<null | string> = null;

function buildFocusLoginUrl(redirectPath: string) {
  const normalizedRedirect = redirectPath || getCurrentAppPath();
  return `/auth/login?redirect=${encodeURIComponent(normalizedRedirect)}`;
}

export async function ensureFocusSession() {
  const stored = getStoredFocusAccess();
  if (stored.accessToken) {
    return stored;
  }

  if (!stored.refreshToken) {
    return null;
  }

  const accessToken = await refreshFocusAccessToken();
  if (!accessToken) {
    return null;
  }

  return getStoredFocusAccess();
}

export async function refreshFocusAccessToken(): Promise<null | string> {
  const stored = getStoredFocusAccess();
  if (!stored.refreshToken) {
    return null;
  }

  if (!refreshPromise) {
    refreshPromise = focusAuthClient
      .post('/core/refresh_token', undefined, {
        headers: {
          Authorization: `Bearer ${stored.refreshToken}`,
        },
      })
      .then((response) => {
        const accessToken = response.data?.accessToken;
        const refreshToken = response.data?.refreshToken || stored.refreshToken;
        if (typeof accessToken !== 'string' || !accessToken) {
          return null;
        }
        persistStoredFocusAccess({
          accessToken,
          refreshToken,
        });
        return accessToken;
      })
      .catch(() => {
        clearStoredFocusAccess();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

export function redirectToFocusLogin(redirectPath?: string) {
  const loginUrl = buildFocusLoginUrl(redirectPath || getCurrentAppPath());
  window.location.assign(loginUrl);
}

export function resetFocusSession() {
  clearStoredFocusAccess();
}
