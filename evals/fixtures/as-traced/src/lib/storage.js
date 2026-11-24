const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = process.env.FILE_STORE_DIR || '/var/lib/tasklane/files';

// Files are stored under a random key the server generates; user-supplied names never reach the path.
function newKey() {
  return crypto.randomBytes(16).toString('hex');
}

function write(key, buffer) {
  return fs.promises.writeFile(path.join(ROOT, key), buffer);
}

function stream(key) {
  return fs.createReadStream(path.join(ROOT, key));
}

function remove(key) {
  return fs.promises.rm(path.join(ROOT, key), { force: true });
}

module.exports = { newKey, write, stream, remove };
