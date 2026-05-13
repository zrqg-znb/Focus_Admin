const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

function getTokenStorages() {
  if (typeof window === 'undefined') {
    return [] as Storage[];
  }

  return [window.localStorage, window.sessionStorage];
}

function syncTokenValue(key: string, value: null | string) {
  for (const storage of getTokenStorages()) {
    try {
      if (value) {
        storage.setItem(key, value);
      } else {
        storage.removeItem(key);
      }
    } catch {
      // Ignore storage write failures so the main auth flow is unaffected.
    }
  }
}

export function clearFocusAuditSessionBridge() {
  syncTokenValue(ACCESS_TOKEN_KEY, null);
  syncTokenValue(REFRESH_TOKEN_KEY, null);
}

export function syncFocusAuditSessionBridge(
  accessToken: null | string,
  refreshToken: null | string,
) {
  syncTokenValue(ACCESS_TOKEN_KEY, accessToken);
  syncTokenValue(REFRESH_TOKEN_KEY, refreshToken);
}
