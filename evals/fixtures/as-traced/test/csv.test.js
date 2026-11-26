const test = require('node:test');
const assert = require('node:assert');
const { toCsv } = require('../src/reports/csv');

test('quotes cells and neutralises formulas', () => {
  const out = toCsv(['a', 'b'], [{ a: '=1+1', b: 'say "hi"' }]);
  assert.strictEqual(out, '"a","b"\r\n"\'=1+1","say ""hi"""\r\n');
});
