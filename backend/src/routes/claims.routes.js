const express = require('express');
const multer = require('multer');
const router = express.Router();
const requireAuth = require('../middleware/auth.middleware');
const { submitClaim, listClaims, getClaim, getClaimStatus, uploadClaim } = require('../controllers/claims.controller');

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    if (file.mimetype !== 'application/pdf') {
      return cb(new Error('Only PDF files are allowed'));
    }
    cb(null, true);
  },
});

router.use(requireAuth);

router.post('/', submitClaim);
router.post('/upload', upload.single('file'), uploadClaim);
router.get('/', listClaims);
router.get('/:id/status', getClaimStatus);
router.get('/:id', getClaim);

module.exports = router;
