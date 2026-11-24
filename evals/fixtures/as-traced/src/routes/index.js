const express = require('express');

const router = express.Router();

router.use(require('./me'));
router.use(require('./projects'));
router.use(require('./tasks'));
router.use(require('./files'));
router.use(require('./reports'));
router.use('/admin', require('../admin/router'));

module.exports = router;
