/**
 * Absolute minimal server for Railway - guaranteed to work
 */

const http = require('http');
const PORT = process.env.PORT || 8000;

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
    res.writeHead(200);
    res.end(JSON.stringify({
      status: 'healthy',
      service: 'xyqo-backend',
      timestamp: new Date().toISOString()
    }));
  } else if (req.url === '/api/v1/contract/analyze' && req.method === 'POST') {
    // Simulate contract analysis endpoint
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
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', 'attachment; filename="contract-summary.pdf"');
    res.writeHead(200);
    res.end('PDF simulation content');
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
});

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
