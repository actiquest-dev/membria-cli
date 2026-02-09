require('dotenv').config();
const path = require('path');
const express = require('express');
const cors = require('cors');
const { RedisClient } = require('./utils/redis');
const pool = require('./utils/database').pool;
const logger = require('./utils/logger');

const app = express();
const PORT = process.env.PORT || 3000;

let redisClient, dbPool;

async function connect() {
  try {
    redisClient = new RedisClient();
    await redisClient.connect();
    dbPool = pool;
    await dbPool.connect();
    logger.info('Connected to Redis and PostgreSQL');
  } catch (error) {
    logger.error('Database connection failed:', error);
    process.exit(1);
  }
}

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));

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

app.get('/api/stats', async (req, res) => {
  try {
    const [repos, commits, occurrences, byPattern] = await Promise.all([
      dbPool.query('SELECT COUNT(*) as count FROM repos'),
      dbPool.query('SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE processed) as processed FROM commits'),
      dbPool.query('SELECT COUNT(*) as count FROM pattern_occurrences'),
      dbPool.query(`
        SELECT pattern_id, action, COUNT(*) as count
        FROM pattern_occurrences
        GROUP BY pattern_id, action
        ORDER BY count DESC
      `),
    ]);

    res.json({
      repos: parseInt(repos.rows[0].count),
      commits_total: parseInt(commits.rows[0].total),
      commits_processed: parseInt(commits.rows[0].processed),
      occurrences: parseInt(occurrences.rows[0].count),
      by_pattern: byPattern.rows,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/occurrences', async (req, res) => {
  try {
    const offset = parseInt(req.query.offset) || 0;
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);

    const result = await dbPool.query(`
      SELECT
        po.pattern_id, po.action, po.file_path, po.line_number,
        po.confidence, po.detection_method, po.match_text, po.created_at,
        r.full_name as repo
      FROM pattern_occurrences po
      JOIN repos r ON po.repo_id = r.id
      ORDER BY po.created_at DESC
      LIMIT $1 OFFSET $2
    `, [limit, offset]);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/repos', async (req, res) => {
  try {
    const result = await dbPool.query(`
      SELECT
        r.id, r.full_name, r.stars, r.language, r.last_fetched_at,
        COUNT(DISTINCT c.id) as commits_count,
        COUNT(DISTINCT po.id) as occurrences_count
      FROM repos r
      LEFT JOIN commits c ON c.repo_id = r.id
      LEFT JOIN pattern_occurrences po ON po.repo_id = r.id
      GROUP BY r.id
      ORDER BY r.last_fetched_at DESC
    `);
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
