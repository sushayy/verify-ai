const express = require('express');
const router = express.Router();
const { signup, login } = require('../controllers/auth.controller');
const requireAuth = require('../middleware/auth.middleware');
const { findUserById } = require('../models/user.model');

router.post('/signup', signup);
router.post('/login', login);

router.get('/me', requireAuth, async (req, res) => {
  const user = await findUserById(req.userId);
  res.json({ user });
});

module.exports = router;
