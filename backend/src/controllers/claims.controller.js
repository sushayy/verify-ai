const { createClaim, getClaimsByUser, getClaimById } = require('../models/claim.model');

async function submitClaim(req, res) {
  try {
    const { claim_text } = req.body;

    if (!claim_text || claim_text.trim().length === 0) {
      return res.status(400).json({ error: 'claim_text is required' });
    }

    const claim = await createClaim(req.userId, claim_text.trim());
    res.status(201).json({ claim });

    // NOTE: AI verification pipeline call goes here in Phase 10.
  } catch (err) {
    console.error('Submit claim error:', err);
    res.status(500).json({ error: 'Something went wrong submitting the claim' });
  }
}

async function listClaims(req, res) {
  try {
    const claims = await getClaimsByUser(req.userId);
    res.json({ claims });
  } catch (err) {
    console.error('List claims error:', err);
    res.status(500).json({ error: 'Something went wrong fetching claims' });
  }
}

async function getClaim(req, res) {
  try {
    const claim = await getClaimById(req.params.id, req.userId);
    if (!claim) {
      return res.status(404).json({ error: 'Claim not found' });
    }
    res.json({ claim });
  } catch (err) {
    console.error('Get claim error:', err);
    res.status(500).json({ error: 'Something went wrong fetching the claim' });
  }
}

module.exports = { submitClaim, listClaims, getClaim };
