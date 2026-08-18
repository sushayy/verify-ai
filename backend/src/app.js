const express = require('express');
const cors = require('cors');
require('dotenv').config();

const authRoutes = require('./routes/auth.routes');
const claimsRoutes = require('./routes/claims.routes');

const app = express();

app.set('trust proxy', 1);

app.use(cors());
app.use(express.json());

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Verify AI backend is running' });
});

app.use('/api/auth', authRoutes);
app.use('/api/claims', claimsRoutes);

module.exports = app;
