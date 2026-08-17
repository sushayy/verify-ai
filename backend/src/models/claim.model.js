const pool = require('./db');

async function createClaim(userId, claimText, inputType = 'text', sourceUrl = null, sourceFilename = null) {
  const result = await pool.query(
    `INSERT INTO claims (user_id, claim_text, verification_status, input_type, source_url, source_filename)
     VALUES ($1, $2, 'pending', $3, $4, $5)
     RETURNING claim_id, user_id, claim_text, submission_date, verification_status, input_type, source_url, source_filename`,
    [userId, claimText, inputType, sourceUrl, sourceFilename]
  );
  return result.rows[0];
}

async function getClaimsByUser(userId) {
  const result = await pool.query(
    `SELECT claim_id, claim_text, submission_date, verification_status, input_type
     FROM claims
     WHERE user_id = $1
     ORDER BY submission_date DESC`,
    [userId]
  );
  return result.rows;
}

async function getClaimById(claimId, userId) {
  const result = await pool.query(
    `SELECT * FROM claims WHERE claim_id = $1 AND user_id = $2`,
    [claimId, userId]
  );
  return result.rows[0];
}

async function updateClaimStatus(claimId, status) {
  const result = await pool.query(
    `UPDATE claims SET verification_status = $1 WHERE claim_id = $2 RETURNING *`,
    [status, claimId]
  );
  return result.rows[0];
}

module.exports = { createClaim, getClaimsByUser, getClaimById, updateClaimStatus };
