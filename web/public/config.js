/**
 * API Configuration
 * Sets the base URL for API requests based on environment
 * 
 * Note: In browser JavaScript, process.env is not available by default.
 * For production builds, this would typically be replaced at build time.
 * For now, we use relative paths which are proxied by server.js
 */
const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "http://python-app:5001"
    : "http://localhost:5001";

