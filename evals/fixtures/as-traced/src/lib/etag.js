const crypto = require('crypto');

// Weak validator for HTTP caching only (If-None-Match). Not used for anything security-relevant.
function etag(value) {
  return `W/"${crypto.createHash('md5').update(String(value)).digest('hex')}"`;
}

module.exports = { etag };
