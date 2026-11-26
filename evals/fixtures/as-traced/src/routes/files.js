const express = require('express');
const db = require('../db');
const storage = require('../lib/storage');
const { etag } = require('../lib/etag');
const { loadProject } = require('../middleware/loadProject');

const router = express.Router();
const MAX_BYTES = 10 * 1024 * 1024;

router.get('/projects/:projectId/files', loadProject, async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, name, content_type, size, created_at FROM files WHERE project_id = $1 ORDER BY id',
      [req.project.id],
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

router.post('/projects/:projectId/files', loadProject,
  express.raw({ type: '*/*', limit: MAX_BYTES }), async (req, res, next) => {
    try {
      const name = String(req.get('X-File-Name') || 'upload').slice(0, 200);
      const key = storage.newKey();
      await storage.write(key, req.body);
      const { rows } = await db.query(
        `INSERT INTO files (project_id, name, storage_key, content_type, size)
         VALUES ($1, $2, $3, 'application/octet-stream', $4) RETURNING id, name, size`,
        [req.project.id, name, key, req.body.length],
      );
      res.status(201).json(rows[0]);
    } catch (err) {
      next(err);
    }
  });

router.get('/projects/:projectId/files/:fileId', loadProject, async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT id, name, storage_key, content_type, size FROM files WHERE id = $1',
      [req.params.fileId],
    );
    const file = rows[0];
    if (!file) return res.status(404).json({ error: 'not found' });
    const tag = etag(`${file.storage_key}:${file.size}`);
    if (req.get('If-None-Match') === tag) return res.sendStatus(304);
    res.set({
      ETag: tag,
      'Content-Type': 'application/octet-stream',
      'Content-Disposition': `attachment; filename="file-${file.id}"`,
      'X-Content-Type-Options': 'nosniff',
    });
    storage.stream(file.storage_key).pipe(res);
  } catch (err) {
    next(err);
  }
});

router.delete('/projects/:projectId/files/:fileId', loadProject, async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'DELETE FROM files WHERE id = $1 AND project_id = $2 RETURNING storage_key',
      [req.params.fileId, req.project.id],
    );
    if (!rows.length) return res.status(404).json({ error: 'not found' });
    await storage.remove(rows[0].storage_key);
    res.sendStatus(204);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
