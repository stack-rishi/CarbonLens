import axios from "axios";
import * as Sentry from "@sentry/react";
import { useAuthStore } from "../store/useAuthStore";

// Create Axios instance pointing to backend URL
// Defaulting to local development fallback
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor to dynamically inject authorization header token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor for centralized Sentry error logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log failures to Sentry
    Sentry.captureException(error);

    // Auto-logout on unauthorized token responses
    if (error.response && error.response.status === 401) {
      useAuthStore.getState().logout();
    }

    return Promise.reject(error);
  }
);
