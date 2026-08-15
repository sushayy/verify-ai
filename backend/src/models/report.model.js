const pool = require('./db');

async function createReport(claimId, finalResult, confidenceScore, explanation) {
  const result = await pool.query(
    `INSERT INTO reports (claim_id, final_result, confidence_score, explanation)
     VALUES ($1, $2, $3, $4)
     RETURNING *`,
    [claimId, finalResult, confidenceScore, explanation]
  );
  return result.rows[0];
}

async function createEvidence(claimId, evidenceList) {
  const inserted = [];
  for (const e of evidenceList) {
    const result = await pool.query(
      `INSERT INTO evidence (claim_id, source_name, url, extracted_text, stance, reliability_score)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [claimId, e.source_name, e.url, e.extracted_text, e.stance, e.reliability_score]
    );
    inserted.push(result.rows[0]);
  }
  return inserted;
}

async function getReportByClaimId(claimId) {
  const result = await pool.query(`SELECT * FROM reports WHERE claim_id = $1`, [claimId]);
  return result.rows[0];
}

async function getEvidenceByClaimId(claimId) {
  const result = await pool.query(`SELECT * FROM evidence WHERE claim_id = $1`, [claimId]);
  return result.rows;
}

module.exports = { createReport, createEvidence, getReportByClaimId, getEvidenceByClaimId };
