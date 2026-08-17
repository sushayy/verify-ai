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

const { PDFParse } = require('pdf-parse');
const cheerio = require('cheerio');

async function extractTextFromPdf(buffer) {
  const parser = new PDFParse({ data: buffer });
  try {
    const result = await parser.getText();
    return result.text.trim();
  } finally {
    await parser.destroy();
  }
}

async function extractTextFromUrl(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch URL: ${response.status}`);
  }
  const html = await response.text();
  const $ = cheerio.load(html);
  $('script, style, nav, footer, header').remove();
  const text = $('body').text().replace(/\s+/g, ' ').trim();
  return text;
}

async function uploadClaim(req, res) {
  try {
    let claimText, inputType, sourceUrl, sourceFilename;

    if (req.file) {
      // PDF upload
      claimText = await extractTextFromPdf(req.file.buffer);
      inputType = 'document';
      sourceFilename = req.file.originalname;
    } else if (req.body.url) {
      // URL input
      claimText = await extractTextFromUrl(req.body.url);
      inputType = 'url';
      sourceUrl = req.body.url;
    } else {
      return res.status(400).json({ error: 'Provide either a PDF file or a url' });
    }

    if (!claimText || claimText.trim().length === 0) {
      return res.status(400).json({ error: 'Could not extract any text from the provided source' });
    }

    // Cap extremely long extracted text to keep the pipeline responsive
    const MAX_LENGTH = 5000;
    if (claimText.length > MAX_LENGTH) {
      claimText = claimText.slice(0, MAX_LENGTH);
    }

    const claim = await createClaim(req.userId, claimText, inputType, sourceUrl, sourceFilename);
    res.status(201).json({ claim });

    runVerification(claim.claim_id, claim.claim_text);
  } catch (err) {
    console.error('Upload claim error:', err);
    res.status(500).json({ error: 'Something went wrong processing the uploaded source' });
  }
}

module.exports.uploadClaim = uploadClaim;
