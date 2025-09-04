#!/usr/bin/env node
/**
 * Reverse Proxy Server for Smart Financial Coach
 * Hosts both backend and frontend on localhost:3000
 * - /backend/* -> FastAPI backend (localhost:8000)
 * - /frontend/* -> Next.js frontend (localhost:3001)
 * - /* -> Next.js frontend (fallback)
 */

const http = require("http");
const httpProxy = require("http-proxy");
const url = require("url");

// Create proxy instance
const proxy = httpProxy.createProxyServer({});

// Backend and frontend targets
const BACKEND_TARGET = "http://localhost:8000";
const FRONTEND_TARGET = "http://localhost:3001";
const PORT = 3000;

// Error handling
proxy.on("error", (err, req, res) => {
  console.error("Proxy error:", err.message);
  if (!res.headersSent) {
    res.writeHead(500, {
      "Content-Type": "text/plain",
    });
    res.end("Proxy error: " + err.message);
  }
});

// Create the proxy server
const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const path = parsedUrl.pathname;

  // Add CORS headers for all responses
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader(
    "Access-Control-Allow-Methods",
    "GET, POST, PUT, DELETE, OPTIONS"
  );
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, X-User-Id"
  );

  // Handle preflight requests
  if (req.method === "OPTIONS") {
    res.writeHead(200);
    res.end();
    return;
  }

  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);

  // Route backend requests
  if (path.startsWith("/backend/")) {
    // Remove /backend prefix and proxy to FastAPI
    req.url = req.url.replace("/backend", "");
    console.log(`  -> Proxying to backend: ${BACKEND_TARGET}${req.url}`);

    proxy.web(req, res, {
      target: BACKEND_TARGET,
      changeOrigin: true,
      headers: {
        "X-Forwarded-Host": req.headers.host,
        "X-Forwarded-Proto": "http",
      },
    });
  }
  // Route frontend requests
  else if (path.startsWith("/frontend/")) {
    // Remove /frontend prefix and proxy to Next.js
    req.url = req.url.replace("/frontend", "") || "/";
    console.log(`  -> Proxying to frontend: ${FRONTEND_TARGET}${req.url}`);

    proxy.web(req, res, {
      target: FRONTEND_TARGET,
      changeOrigin: true,
      headers: {
        "X-Forwarded-Host": req.headers.host,
        "X-Forwarded-Proto": "http",
      },
    });
  }
  // Default to frontend for all other routes (root, assets, etc.)
  else {
    console.log(
      `  -> Proxying to frontend (fallback): ${FRONTEND_TARGET}${req.url}`
    );

    proxy.web(req, res, {
      target: FRONTEND_TARGET,
      changeOrigin: true,
      headers: {
        "X-Forwarded-Host": req.headers.host,
        "X-Forwarded-Proto": "http",
      },
    });
  }
});

// Handle proxy server errors
server.on("error", (err) => {
  console.error("Server error:", err);
});

// Start the proxy server
server.listen(PORT, () => {
  console.log("\n🚀 Smart Financial Coach Proxy Server");
  console.log("=====================================");
  console.log(`✅ Proxy server running on: http://localhost:${PORT}`);
  console.log(`📊 Backend API: http://localhost:${PORT}/backend/`);
  console.log(
    `🖥️  Frontend: http://localhost:${PORT}/frontend/ (or just http://localhost:${PORT}/)`
  );
  console.log("");
  console.log("📋 Route Mapping:");
  console.log(`   /backend/* -> ${BACKEND_TARGET}/*`);
  console.log(`   /frontend/* -> ${FRONTEND_TARGET}/*`);
  console.log(`   /* -> ${FRONTEND_TARGET}/* (fallback)`);
  console.log("");
  console.log("💡 Make sure FastAPI is running on port 8000");
  console.log("💡 Make sure Next.js is running on port 3001");
  console.log("=====================================\n");
});

// Graceful shutdown
process.on("SIGTERM", () => {
  console.log("\n👋 Shutting down proxy server...");
  server.close(() => {
    console.log("✅ Proxy server stopped.");
    process.exit(0);
  });
});

process.on("SIGINT", () => {
  console.log("\n👋 Shutting down proxy server...");
  server.close(() => {
    console.log("✅ Proxy server stopped.");
    process.exit(0);
  });
});
