const express = require('express');
const cors = require('cors');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.WEB_PORT || 8080;

// CORS middleware
app.use(cors());

// Static middleware for public files
app.use(express.static('public'));

// Proxy route for API calls to Python app
app.use(
  '/api',
  createProxyMiddleware({
    target: 'http://python-app:5001',
    changeOrigin: true,
  }),
);

// Root route
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Web server running on port ${PORT}`);
});

