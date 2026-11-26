// RFC 4180 quoting, plus a leading quote on values a spreadsheet would read as a formula.
function cell(value) {
  let s = value == null ? '' : String(value);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return `"${s.replace(/"/g, '""')}"`;
}

function toCsv(header, rows) {
  const lines = [header.map(cell).join(',')];
  for (const row of rows) lines.push(header.map((h) => cell(row[h])).join(','));
  return lines.join('\r\n') + '\r\n';
}

module.exports = { toCsv };
