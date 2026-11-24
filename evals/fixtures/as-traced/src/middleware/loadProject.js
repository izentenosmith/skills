const db = require('../db');

// Loads :projectId for the caller's tenant, or 404s. Routes under a project use this.
async function loadProject(req, res, next) {
  try {
    const { rows } = await db.query(
      'SELECT id, tenant_id, name FROM projects WHERE id = $1 AND tenant_id = $2',
      [req.params.projectId, req.session.user.tenantId],
    );
    if (!rows.length) return res.status(404).json({ error: 'not found' });
    req.project = rows[0];
    next();
  } catch (err) {
    next(err);
  }
}

module.exports = { loadProject };
