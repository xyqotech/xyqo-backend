/**
 * Absolute minimal server for Railway - guaranteed to work
 */

const http = require('http');
const PORT = process.env.PORT || 8000;

const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  
  if (req.url === '/health' || req.url === '/') {
    res.writeHead(200);
    res.end(JSON.stringify({
      status: 'healthy',
      service: 'xyqo-backend',
      timestamp: new Date().toISOString()
    }));
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

process.on('SIGTERM', () => server.close());
process.on('SIGINT', () => server.close());
