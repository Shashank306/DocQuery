// src/utils/auth.js

// Get access token from localStorage
export function getAuthToken() {
  return localStorage.getItem("access_token");
}

// Get refresh token from localStorage
export function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

// Set tokens in localStorage
export function setTokens(accessToken, refreshToken) {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
}

// Clear all tokens (logout)
export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// Check if user is authenticated
export function isAuthenticated() {
  return !!getAuthToken();
}

// Get authorization header
export function getAuthHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
