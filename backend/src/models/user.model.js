const pool = require('./db');

async function createUser(name, email, passwordHash) {
  const result = await pool.query(
    `INSERT INTO users (name, email, password_hash)
     VALUES ($1, $2, $3)
     RETURNING user_id, name, email, created_at`,
    [name, email, passwordHash]
  );
  return result.rows[0];
}

async function findUserByEmail(email) {
  const result = await pool.query(
    `SELECT * FROM users WHERE email = $1`,
    [email]
  );
  return result.rows[0];
}

async function findUserById(userId) {
  const result = await pool.query(
    `SELECT user_id, name, email, created_at FROM users WHERE user_id = $1`,
    [userId]
  );
  return result.rows[0];
}

module.exports = { createUser, findUserByEmail, findUserById };
