const express = require("express");
const cors = require("cors");
const path = require("path");
const https = require("https");
const http = require("http");
const fs = require("fs");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();
const HTTP_PORT = process.env.WEB_PORT || 8080;
const HTTPS_PORT = process.env.HTTPS_PORT || 8443;

// CORS middleware
app.use(cors());

// Proxy route for API calls to Python app (must be before static files)
app.use(
  "/api",
  createProxyMiddleware({
    target: "http://python-app:5001",
    changeOrigin: true,
  })
);

// Specific routes (must be before static middleware)
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.get("/rationale", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "rationale.html"));
});

app.get("/dashboard", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "dashboard.html"));
});

app.get("/video-ideas", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.get("/output", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// Static middleware for public files (CSS, JS, images, etc.)
app.use(express.static("public"));

// 404 handler for undefined routes
app.use((req, res) => {
  res.status(404).sendFile(path.join(__dirname, "public", "index.html"));
});

// SSL certificate paths
const SSL_CERT_PATH = process.env.SSL_CERT_PATH || "/app/ssl/cert.pem";
const SSL_KEY_PATH = process.env.SSL_KEY_PATH || "/app/ssl/key.pem";

// Check if SSL certificates exist
const hasSSL = fs.existsSync(SSL_CERT_PATH) && fs.existsSync(SSL_KEY_PATH);

// Start HTTP server (always)
const httpServer = http.createServer(app);
httpServer.listen(HTTP_PORT, "0.0.0.0", () => {
  console.log(`HTTP server running on port ${HTTP_PORT}`);
  if (!hasSSL) {
    console.log(
      `⚠️  HTTPS not enabled. SSL certificates not found at:\n   ${SSL_CERT_PATH}\n   ${SSL_KEY_PATH}\n   Set SSL_CERT_PATH and SSL_KEY_PATH environment variables to enable HTTPS.`
    );
  }
});

// Start HTTPS server (if certificates exist)
if (hasSSL) {
  try {
    const httpsOptions = {
      cert: fs.readFileSync(SSL_CERT_PATH),
      key: fs.readFileSync(SSL_KEY_PATH),
    };

    const httpsServer = https.createServer(httpsOptions, app);
    httpsServer.listen(HTTPS_PORT, "0.0.0.0", () => {
      console.log(`HTTPS server running on port ${HTTPS_PORT}`);
    });
  } catch (error) {
    console.error("Failed to start HTTPS server:", error.message);
  }
}
