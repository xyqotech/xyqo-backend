/**
 * Debug server to identify HTTP response issue
 */

const http = require('http');
const PORT = 8000;

console.log('🔍 Starting debug analysis...');

// Test 1: Minimal server with explicit response handling
const server = http.createServer((req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`📥 ${timestamp} - ${req.method} ${req.url}`);
  console.log(`📋 Headers: ${JSON.stringify(req.headers)}`);

  try {
    // Set headers explicitly
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    console.log(`🔧 Headers set for ${req.url}`);

    // Handle preflight
    if (req.method === 'OPTIONS') {
      console.log('✈️ Handling OPTIONS preflight');
      res.writeHead(200);
      res.end();
      console.log('✅ OPTIONS response sent');
      return;
    }

    // Health check with detailed logging
    if (req.url === '/health' || req.url === '/') {
      console.log('🏥 Processing health check');
      
      const healthData = {
        status: 'healthy',
        service: 'debug-server',
        timestamp: timestamp,
        port: PORT,
        uptime: process.uptime(),
        test: 'response_working'
      };
      
      const jsonResponse = JSON.stringify(healthData, null, 2);
      console.log(`📤 Sending response: ${jsonResponse.substring(0, 100)}...`);
      
      res.writeHead(200, {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(jsonResponse)
      });
      
      res.write(jsonResponse);
      res.end();
      
      console.log('✅ Health response sent and ended');
      return;
    }

    // Contract analysis with detailed logging
    if (req.url === '/api/v1/contract/analyze' && req.method === 'POST') {
      console.log('📄 Processing contract analysis');
      
      const responseData = {
        success: true,
        message: 'Debug server working',
        timestamp: timestamp,
        summary: {
          title: "Test Contract Analysis",
          parties: ["Debug Party A", "Debug Party B"],
          contract_type: "Test Agreement"
        }
      };
      
      const jsonResponse = JSON.stringify(responseData, null, 2);
      console.log(`📤 Sending analysis response: ${jsonResponse.substring(0, 100)}...`);
      
      res.writeHead(200, {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(jsonResponse)
      });
      
      res.write(jsonResponse);
      res.end();
      
      console.log('✅ Analysis response sent and ended');
      return;
    }

    // 404 with logging
    console.log(`❌ 404 for ${req.url}`);
    const errorResponse = JSON.stringify({ error: 'Not found', url: req.url });
    res.writeHead(404, {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(errorResponse)
    });
    res.write(errorResponse);
    res.end();
    console.log('✅ 404 response sent');

  } catch (error) {
    console.error(`💥 Error processing ${req.url}:`, error);
    res.writeHead(500);
    res.end(JSON.stringify({ error: 'Internal server error' }));
  }
});

// Enhanced error handling
server.on('error', (err) => {
  console.error(`💥 Server error: ${err.message}`);
  if (err.code === 'EADDRINUSE') {
    console.error(`🚫 Port ${PORT} is already in use`);
    process.exit(1);
  }
});

server.on('connection', (socket) => {
  console.log('🔌 New connection established');
  socket.on('close', () => {
    console.log('🔌 Connection closed');
  });
});

// Start server with explicit binding
server.listen(PORT, '127.0.0.1', () => {
  console.log(`🚀 Debug Server started successfully`);
  console.log(`📡 URL: http://127.0.0.1:${PORT}`);
  console.log(`🏥 Health: http://127.0.0.1:${PORT}/health`);
  console.log(`⏰ Started: ${new Date().toISOString()}`);
  console.log(`🔍 Ready for debugging...`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down debug server...');
  server.close(() => {
    console.log('✅ Debug server closed');
    process.exit(0);
  });
});
