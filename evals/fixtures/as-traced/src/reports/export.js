const db = require('../db');
const { toCsv } = require('./csv');

const COLUMNS = ['id', 'title', 'status', 'due_date', 'assignee_email'];

// Exports a project's tasks in the order the user chose in their report preferences.
async function exportTasksCsv(user, projectId) {
  const { rows: [me] } = await db.query('SELECT preferences FROM users WHERE id = $1', [user.id]);
  const sort = (me && me.preferences && me.preferences.reportSort) || 'due_date';
  const { rows } = await db.query(
    `SELECT id, title, status, due_date, assignee_email FROM tasks
     WHERE project_id = $1 AND tenant_id = $2
     ORDER BY ${sort}`,
    [projectId, user.tenantId],
  );
  return toCsv(COLUMNS, rows);
}

module.exports = { exportTasksCsv };
