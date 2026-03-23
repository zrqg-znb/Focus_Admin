import axios, {
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';

import {
  API_BASE_URL,
  getStoredToken,
  mapApiPath,
} from './focusAdapter';
import {
  redirectToFocusLogin,
  refreshFocusAccessToken,
  resetFocusSession,
} from '@/shared/focus/focusAuth';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  maxRedirects: 5,
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (config.url) {
      config.url = mapApiPath(config.url);
    }

    const token = getStoredToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshedToken = await refreshFocusAccessToken();
      if (refreshedToken) {
        originalRequest.headers.Authorization = `Bearer ${refreshedToken}`;
        return apiClient(originalRequest);
      }
    }

    if (error.response?.status === 401) {
      resetFocusSession();
      redirectToFocusLogin();
    }

    return Promise.reject(error);
  }
);
