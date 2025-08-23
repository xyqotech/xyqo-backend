/**
 * Ultra-simple backend server for immediate testing
 */

const http = require('http');
const PORT = 8002;

const server = http.createServer((req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Content-Type', 'application/json');

  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);

  // Handle preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Health check
  if (req.url === '/health' || req.url === '/') {
    res.writeHead(200);
    res.end(JSON.stringify({
      status: 'healthy',
      service: 'xyqo-backend-local',
      timestamp: new Date().toISOString(),
      port: PORT
    }));
    return;
  }

  // Contract analysis endpoint
  if (req.url === '/api/v1/contract/analyze' && req.method === 'POST') {
    console.log('Contract analysis request received');
    res.writeHead(200);
    res.end(JSON.stringify({
      success: true,
      summary: {
        title: "Contrat Commercial - Test Local",
        parties: ["Entreprise A", "Entreprise B"],
        contract_type: "Service Agreement",
        key_terms: ["Durée: 12 mois", "Montant: €50,000", "Résiliation: 30 jours"],
        analysis_date: new Date().toISOString()
      },
      processing_time: 0.8,
      cost_euros: 0.01,
      pdf_download_url: "/download/test-local.pdf",
      processing_id: `local-${Date.now()}`
    }));
    return;
  }

  // PDF download simulation
  if (req.url.startsWith('/download/') && req.method === 'GET') {
    console.log(`PDF download: ${req.url}`);
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', 'attachment; filename="contract-summary-local.pdf"');
    res.writeHead(200);
    res.end('PDF simulation content - Local Backend Test');
    return;
  }

  // 404 for everything else
  res.writeHead(404);
  res.end(JSON.stringify({ error: 'Not found', url: req.url }));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`🚀 Simple Backend Server started on http://127.0.0.1:${PORT}`);
  console.log(`🏥 Health check: http://127.0.0.1:${PORT}/health`);
  console.log(`🔗 API: http://127.0.0.1:${PORT}/api/v1/contract/analyze`);
});

server.on('error', (err) => {
  console.error(`❌ Server error: ${err.message}`);
});
