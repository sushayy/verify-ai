const { createClaim, getClaimsByUser, getClaimById, updateClaimStatus } = require('../models/claim.model');
const { createReport, createEvidence, getReportByClaimId, getEvidenceByClaimId } = require('../models/report.model');
const { verifyClaim } = require('../services/aiService');

async function submitClaim(req, res) {
  try {
    const { claim_text } = req.body;

    if (!claim_text || claim_text.trim().length === 0) {
      return res.status(400).json({ error: 'claim_text is required' });
    }

    const claim = await createClaim(req.userId, claim_text.trim());
    res.status(201).json({ claim });

    // Run verification asynchronously — don't block the response
    runVerification(claim.claim_id, claim.claim_text);
  } catch (err) {
    console.error('Submit claim error:', err);
    res.status(500).json({ error: 'Something went wrong submitting the claim' });
  }
}

async function runVerification(claimId, claimText) {
  try {
    await updateClaimStatus(claimId, 'processing');

    const aiResult = await verifyClaim(claimText);

    await createReport(claimId, aiResult.final_result, aiResult.confidence_score, aiResult.explanation);
    await createEvidence(claimId, aiResult.evidence);

    await updateClaimStatus(claimId, 'completed');
  } catch (err) {
    console.error(`Verification failed for claim ${claimId}:`, err);
    await updateClaimStatus(claimId, 'failed');
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

    const report = await getReportByClaimId(claim.claim_id);
    const evidence = await getEvidenceByClaimId(claim.claim_id);

    res.json({ claim, report: report || null, evidence });
  } catch (err) {
    console.error('Get claim error:', err);
    res.status(500).json({ error: 'Something went wrong fetching the claim' });
  }
}

module.exports = { submitClaim, listClaims, getClaim };

async function getClaimStatus(req, res) {
  try {
    const claim = await getClaimById(req.params.id, req.userId);
    if (!claim) {
      return res.status(404).json({ error: 'Claim not found' });
    }
    res.json({ claim_id: claim.claim_id, verification_status: claim.verification_status });
  } catch (err) {
    console.error('Get claim status error:', err);
    res.status(500).json({ error: 'Something went wrong fetching claim status' });
  }
}

module.exports.getClaimStatus = getClaimStatus;
