const pool = require('./db');

async function createClaim(userId, claimText) {
  const result = await pool.query(
    `INSERT INTO claims (user_id, claim_text, verification_status)
     VALUES ($1, $2, 'pending')
     RETURNING claim_id, user_id, claim_text, submission_date, verification_status`,
    [userId, claimText]
  );
  return result.rows[0];
}

async function getClaimsByUser(userId) {
  const result = await pool.query(
    `SELECT claim_id, claim_text, submission_date, verification_status
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

module.exports = { createClaim, getClaimsByUser, getClaimById };
