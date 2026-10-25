const http = require('node:http');
const port = process.env.PORT || 8080;
http.createServer((req, res) => {
  if (req.url === '/healthz') { res.writeHead(200); return res.end('ok'); }
  res.writeHead(200, { 'content-type': 'application/json' });
  res.end(JSON.stringify({ service: 'storefront-api', env: process.env.APP_ENV }));
}).listen(port);
