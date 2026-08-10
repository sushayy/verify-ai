const express = require('express');
const router = express.Router();
const requireAuth = require('../middleware/auth.middleware');
const { submitClaim, listClaims, getClaim } = require('../controllers/claims.controller');

router.use(requireAuth);

router.post('/', submitClaim);
router.get('/', listClaims);
router.get('/:id', getClaim);

module.exports = router;
