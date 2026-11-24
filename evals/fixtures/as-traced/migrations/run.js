const fs = require('fs');
const path = require('path');
const db = require('../src/db');

(async () => {
  for (const f of fs.readdirSync(__dirname).filter((n) => n.endsWith('.sql')).sort()) {
    await db.query(fs.readFileSync(path.join(__dirname, f), 'utf8'));
    console.log('applied', f);
  }
  await db.pool.end();
})();
