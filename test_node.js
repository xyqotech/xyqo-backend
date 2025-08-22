/**
 * Test the Node.js server locally
 */

const http = require('http');

function testEndpoint(path, expectedStatus = 200) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: path,
      method: 'GET'
    };

    const req = http.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === expectedStatus) {
          console.log(`✅ ${path} - ${res.statusCode} OK`);
          try {
            if (res.headers['content-type']?.includes('application/json')) {
              const json = JSON.parse(data);
              console.log(`   Response: ${json.status || json.message || 'OK'}`);
            } else {
              console.log(`   Response: HTML (${data.length} chars)`);
            }
          } catch (e) {
            console.log(`   Response: ${data.substring(0, 100)}...`);
          }
          resolve({ status: res.statusCode, data });
        } else {
          reject(new Error(`Expected ${expectedStatus}, got ${res.statusCode}`));
        }
      });
    });

    req.on('error', (err) => {
      reject(err);
    });

    req.setTimeout(5000, () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    req.end();
  });
}

async function runTests() {
  console.log('🧪 Testing Node.js server...');
  
  try {
    await testEndpoint('/');
    await testEndpoint('/health');
    
    console.log('🎉 All tests passed! Node.js server is working correctly.');
    console.log('📋 Ready for Railway deployment.');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

// Wait a moment for server to start if needed
setTimeout(runTests, 1000);
