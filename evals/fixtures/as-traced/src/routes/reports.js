const express = require('express');
const { loadProject } = require('../middleware/loadProject');
const { exportTasksCsv } = require('../reports/export');

const router = express.Router();

router.get('/projects/:projectId/export.csv', loadProject, async (req, res, next) => {
  try {
    const csv = await exportTasksCsv(req.session.user, req.project.id);
    res.set({
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="project-${req.project.id}-tasks.csv"`,
    });
    res.send(csv);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
