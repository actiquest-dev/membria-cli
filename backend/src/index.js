require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { RedisClient } = require('./utils/redis');
const { Pool } = require('./utils/database');
const logger = require('./utils/logger');

const app = express();
const PORT = process.env.PORT || 3000;

let redisClient, dbPool;

async function connect() {
  try {
    redisClient = new RedisClient();
    await redisClient.connect();
    dbPool = new Pool();
    await dbPool.connect();
    logger.info('✅ Connected to Redis and PostgreSQL');
  } catch (error) {
    logger.error('❌ Database connection failed:', error);
    process.exit(1);
  }
}

app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/patterns', async (req, res) => {
  try {
    const result = await dbPool.query('SELECT * FROM patterns ORDER BY created_at DESC LIMIT 100');
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/mine', async (req, res) => {
  try {
    const { repoOwner, repoName } = req.body;
    if (!repoOwner || !repoName) {
      return res.status(400).json({ error: 'repoOwner and repoName required' });
    }
    await redisClient.publish('patterns:mine', JSON.stringify({ repoOwner, repoName }));
    res.json({ status: 'queued', message: `Mining pattern for ${repoOwner}/${repoName}` });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

async function start() {
  await connect();
  app.listen(PORT, () => {
    logger.info(`🚀 Membria Mining Backend running on port ${PORT}`);
  });

  process.on('SIGTERM', async () => {
    logger.info('SIGTERM received, shutting down gracefully...');
    await redisClient.disconnect();
    await dbPool.end();
    process.exit(0);
  });

  process.on('SIGINT', async () => {
    logger.info('SIGINT received, shutting down gracefully...');
    await redisClient.disconnect();
    await dbPool.end();
    process.exit(0);
  });
}

start().catch(error => {
  logger.error('Failed to start server:', error);
  process.exit(1);
});
