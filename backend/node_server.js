/**
 * Ultra minimal Node.js server for Railway
 * No dependencies - uses only Node.js built-ins
 */

const http = require('http');
const url = require('url');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8000;

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  if (pathname === '/health') {
    res.setHeader('Content-Type', 'application/json');
    const response = {
      status: 'healthy',
      service: 'xyqo-backend',
      timestamp: new Date().toISOString(),
      node_version: process.version
    };
    
    res.writeHead(200);
    res.end(JSON.stringify(response, null, 2));
    console.log(`✅ ${req.method} ${pathname} - 200`);
  } else if (pathname === '/') {
    // Serve HTML page
    try {
      const htmlPath = path.join(__dirname, '..', '..', 'index.html');
      const html = fs.readFileSync(htmlPath, 'utf8');
      res.setHeader('Content-Type', 'text/html');
      res.writeHead(200);
      res.end(html);
      console.log(`✅ ${req.method} ${pathname} - 200 (HTML)`);
    } catch (error) {
      // Fallback JSON response
      res.setHeader('Content-Type', 'application/json');
      const response = {
        status: 'healthy',
        service: 'xyqo-backend',
        message: 'XYQO Backend is running',
        timestamp: new Date().toISOString()
      };
      res.writeHead(200);
      res.end(JSON.stringify(response, null, 2));
      console.log(`✅ ${req.method} ${pathname} - 200 (JSON fallback)`);
    }
  } else {
    res.setHeader('Content-Type', 'application/json');
    const response = {
      error: 'Not found',
      path: pathname
    };
    
    res.writeHead(404);
    res.end(JSON.stringify(response, null, 2));
    console.log(`❌ ${req.method} ${pathname} - 404`);
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 XYQO Backend running on http://0.0.0.0:${PORT}`);
  console.log(`📊 Health: http://0.0.0.0:${PORT}/health`);
  console.log(`🏠 Home: http://0.0.0.0:${PORT}/`);
  console.log(`🔧 Node: ${process.version}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('🛑 SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});
