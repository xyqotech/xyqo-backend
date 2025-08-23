/**
 * Minimal working backend for immediate testing
 */

const http = require('http');
const PORT = 8003;

const server = http.createServer((req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Content-Type', 'application/json');

  console.log(`${req.method} ${req.url}`);

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.url === '/health' || req.url === '/') {
    res.writeHead(200);
    res.end(JSON.stringify({
      status: 'healthy',
      service: 'xyqo-backend-test',
      timestamp: new Date().toISOString()
    }));
    return;
  }

  if (req.url === '/api/v1/contract/analyze' && req.method === 'POST') {
    res.writeHead(200);
    res.end(JSON.stringify({
      success: true,
      summary: {
        title: "Contrat Test",
        parties: ["Test A", "Test B"],
        contract_type: "Test Agreement",
        key_terms: ["Test term 1", "Test term 2"]
      },
      processing_time: 1.0,
      cost_euros: 0.01,
      pdf_download_url: "/download/test.pdf",
      processing_id: `test-${Date.now()}`
    }));
    return;
  }

  if (req.url.startsWith('/download/')) {
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', 'attachment; filename="test.pdf"');
    res.writeHead(200);
    res.end('Test PDF content');
    return;
  }

  res.writeHead(404);
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
