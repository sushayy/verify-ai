const rateLimit = require('express-rate-limit');

const claimSubmissionLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 5,
  message: { error: 'Too many claims submitted. Please wait a minute and try again.' },
  standardHeaders: true,
  legacyHeaders: false,
});

module.exports = { claimSubmissionLimiter };
