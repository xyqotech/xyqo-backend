/**
 * Railway-optimized server with health checks and keep-alive
 */

const http = require('http');
const PORT = process.env.PORT || 8000;

// Create server instance
const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle preflight OPTIONS requests
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  if (req.url === '/health' || req.url === '/') {
    // Railway health check response
    res.writeHead(200, {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache'
    });
    const healthData = {
      status: 'healthy',
      service: 'xyqo-backend',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      port: PORT,
      version: '1.0.0'
    };
    console.log(`Health check: ${req.url} - ${healthData.status}`);
    res.end(JSON.stringify(healthData));
  } else if (req.url === '/api/v1/contract/analyze' && req.method === 'POST') {
    // Simulate contract analysis endpoint
    console.log('Contract analysis request received');
    res.writeHead(200);
    res.end(JSON.stringify({
      success: true,
      summary: {
        title: "Contrat Commercial - Simulation",
        parties: ["Entreprise A", "Entreprise B"],
        contract_type: "Service Agreement",
        key_terms: ["Durée: 12 mois", "Montant: €50,000", "Résiliation: 30 jours"]
      },
      processing_time: 1.2,
      cost_euros: 0.01,
      pdf_download_url: "/download/simulation.pdf",
      processing_id: `sim-${Date.now()}`
    }));
  } else if (req.url.startsWith('/download/') && req.method === 'GET') {
    // Simulate PDF download
    console.log(`PDF download request: ${req.url}`);
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', 'attachment; filename="contract-summary.pdf"');
    res.writeHead(200);
    res.end('PDF simulation content');
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

// Railway-specific server configuration
server.keepAliveTimeout = 65000; // Longer than Railway's 60s
server.headersTimeout = 66000;
server.timeout = 120000;

// Keep process alive with heartbeat
setInterval(() => {
  console.log(`[${new Date().toISOString()}] Server heartbeat - Uptime: ${Math.floor(process.uptime())}s`);
}, 30000);

// Prevent Railway timeout
process.stdout.write('\n');

// Start server with comprehensive error handling
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 XYQO Backend Server started`);
  console.log(`📡 Listening on 0.0.0.0:${PORT}`);
  console.log(`🏥 Health check: /health`);
  console.log(`🔗 API endpoint: /api/v1/contract/analyze`);
  console.log(`⏰ Started at: ${new Date().toISOString()}`);
  
  // Immediate health check to verify server is working
  setTimeout(() => {
    const healthReq = http.request({
      hostname: 'localhost',
      port: PORT,
      path: '/health',
      method: 'GET'
    }, (healthRes) => {
      console.log(`✅ Self health check passed: ${healthRes.statusCode}`);
    });
    healthReq.on('error', (err) => {
      console.log(`❌ Self health check failed: ${err.message}`);
    });
    healthReq.end();
  }, 1000);
});

server.on('error', (err) => {
  console.error(`❌ Server error: ${err.message}`);
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use`);
    process.exit(1);
  }
});

// Graceful shutdown handlers
process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down gracefully');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('Received SIGINT, shutting down gracefully');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});
