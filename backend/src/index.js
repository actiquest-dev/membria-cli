require('dotenv').config();
const path = require('path');
const express = require('express');
const cors = require('cors');
const { RedisClient } = require('./utils/redis');
const pool = require('./utils/database').pool;
const logger = require('./utils/logger');
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

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
require('./chat-handler')(app);

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
    const [repos, commits, occurrences, byPattern, diffs] = await Promise.all([
      dbPool.query('SELECT COUNT(*) as count FROM repos'),
      dbPool.query('SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE processed) as processed FROM commits'),
      dbPool.query('SELECT COUNT(*) as count FROM pattern_occurrences'),
      dbPool.query('SELECT pattern_id, action, COUNT(*) as count FROM pattern_occurrences GROUP BY pattern_id, action ORDER BY count DESC'),
      dbPool.query("SELECT COUNT(*) FILTER (WHERE diff_status = 'ready') as loaded, COUNT(*) FILTER (WHERE diff_status IN ('missing', 'failed')) as pending, COUNT(*) as total FROM commits"),
    ]);

    res.json({
      repos: parseInt(repos.rows[0].count),
      commits_total: parseInt(commits.rows[0].total),
      commits_processed: parseInt(commits.rows[0].processed),
      occurrences: parseInt(occurrences.rows[0].count),
      by_pattern: byPattern.rows,
      diffs_loaded: parseInt(diffs.rows[0].loaded),
      diffs_pending: parseInt(diffs.rows[0].pending),
      diffs_total: parseInt(diffs.rows[0].total),
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/occurrences', async (req, res) => {
  try {
    const offset = parseInt(req.query.offset) || 0;
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
    const result = await dbPool.query('SELECT po.pattern_id, po.action, po.file_path, po.line_number, po.confidence, po.detection_method, po.match_text, po.created_at, r.full_name as repo FROM pattern_occurrences po JOIN repos r ON po.repo_id = r.id ORDER BY po.created_at DESC LIMIT ' + limit + ' OFFSET ' + offset);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/repos', async (req, res) => {
  try {
    const result = await dbPool.query('SELECT r.id, r.full_name, r.stars, r.language, r.last_fetched_at, COUNT(DISTINCT c.id) as commits_count, COUNT(DISTINCT po.id) as occurrences_count FROM repos r LEFT JOIN commits c ON c.repo_id = r.id LEFT JOIN pattern_occurrences po ON po.repo_id = r.id GROUP BY r.id ORDER BY r.last_fetched_at DESC');
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
    res.json({ status: 'queued', message: 'Mining pattern for ' + repoOwner + '/' + repoName });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

async function getPm2List() {
  try {
    const { stdout } = await execPromise('pm2 jlist', { timeout: 10000 });
    return JSON.parse(stdout);
  } catch (error) {
    logger.error('Failed to get PM2 list: ' + error.message);
    return [];
  }
}

app.get('/api/services', async (req, res) => {
  try {
    const processes = await getPm2List();
    const services = processes.filter(p => p.name && p.name.startsWith('membria-')).map(p => ({ name: p.name, pid: p.pid, status: p.pm2_env.status, uptime: p.pm2_env.pm_uptime, cpu: p.monit.cpu, memory: p.monit.memory, restarts: p.pm2_env.restart_time }));
    res.json({ services });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/pipeline/start', async (req, res) => {
  try {
    const services = ['membria-worker', 'membria-crawler', 'membria-diff-loader'];
    for (const service of services) {
      try {
        await execPromise('pm2 start ' + service, { timeout: 10000 });
        logger.info('Started service: ' + service);
      } catch (error) {
        logger.warn('Failed to start ' + service + ': ' + error.message);
      }
    }
    res.json({ success: true, message: 'Pipeline start initiated' });
  } catch (error) {
    logger.error('Pipeline start error: ' + error.message);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/pipeline/stop', async (req, res) => {
  try {
    const services = ['membria-worker', 'membria-crawler', 'membria-diff-loader'];
    for (const service of services) {
      try {
        await execPromise('pm2 stop ' + service, { timeout: 10000 });
        logger.info('Stopped service: ' + service);
      } catch (error) {
        logger.warn('Failed to stop ' + service + ': ' + error.message);
      }
    }
    res.json({ success: true, message: 'Pipeline stopped' });
  } catch (error) {
    logger.error('Pipeline stop error: ' + error.message);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/services/worker/status', async (req, res) => {
  try {
    const queueCount = await dbPool.query('SELECT COUNT(*) as count FROM commits WHERE processed = FALSE');
    const processingCount = await dbPool.query('SELECT COUNT(*) as count FROM pattern_occurrences WHERE created_at > NOW() - INTERVAL \'1 minute\'');
    const recent = await dbPool.query('SELECT pattern_id, action, COUNT(*) as count FROM pattern_occurrences WHERE created_at > NOW() - INTERVAL \'5 minutes\' GROUP BY pattern_id ORDER BY count DESC LIMIT 3');
    
    let currentTask = 'Idle';
    if (processingCount.rows[0].count > 0) {
      const top = recent.rows[0];
      currentTask = 'Detecting: ' + top.pattern_id + ' (' + top.action + ')';
    }
    
    res.json({
      queue: parseInt(queueCount.rows[0].count),
      processing: parseInt(processingCount.rows[0].count),
      currentTask: currentTask,
      recentPatterns: recent.rows.map(r => r.pattern_id + ':' + r.count).join(', ')
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/services/diffloader/status', async (req, res) => {
  try {
    const total = await dbPool.query('SELECT COUNT(*) as count FROM commits');
    const loaded = await dbPool.query('SELECT COUNT(*) as count FROM commits WHERE diff_text IS NOT NULL AND diff_text != \'\'');
    const lastCommit = await dbPool.query('SELECT sha, repo_id FROM commits WHERE diff_fetched_at IS NOT NULL ORDER BY diff_fetched_at DESC LIMIT 1');
    
    let lastCommitInfo = 'None';
    if (lastCommit.rows.length > 0) {
      const repoInfo = await dbPool.query('SELECT full_name FROM repos WHERE id = ', [lastCommit.rows[0].repo_id]);
      lastCommitInfo = repoInfo.rows[0]?.full_name + '/' + lastCommit.rows[0].sha.substring(0, 7);
    }
    
    res.json({
      total: parseInt(total.rows[0].count),
      loaded: parseInt(loaded.rows[0].count),
      lastCommit: lastCommitInfo,
      progress: total.rows[0].count > 0 ? Math.round((loaded.rows[0].count / total.rows[0].count) * 100) : 0
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/services/crawler/status', async (req, res) => {
  try {
    const lastRepo = await dbPool.query('SELECT full_name, last_fetched_at FROM repos ORDER BY last_fetched_at DESC LIMIT 1');
    
    let crawling = 'Idle';
    if (lastRepo.rows.length > 0) {
      const lastFetched = new Date(lastRepo.rows[0].last_fetched_at);
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
      
      if (lastFetched > oneHourAgo) {
        crawling = 'Just finished: ' + lastRepo.rows[0].full_name;
      }
    }
    
    const queuedRepos = await dbPool.query('SELECT COUNT(*) as count FROM repos WHERE last_fetched_at IS NULL');
    
    res.json({
      crawling: crawling,
      queued: parseInt(queuedRepos.rows[0].count)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/services/detailed', async (req, res) => {
  try {
    const processes = await getPm2List();
    const services = processes.filter(p => p.name && p.name.startsWith('membria-'));
    
    const result = [];
    for (const p of services) {
      let details = {};
      
      if (p.name === 'membria-worker') {
        try {
          const queueCount = await dbPool.query('SELECT COUNT(*) as count FROM commits WHERE processed = FALSE');
          const processingCount = await dbPool.query('SELECT COUNT(*) as count FROM pattern_occurrences WHERE created_at > NOW() - INTERVAL \'1 minute\'');
          const recent = await dbPool.query('SELECT pattern_id, action, COUNT(*) as count FROM pattern_occurrences WHERE created_at > NOW() - INTERVAL \'5 minutes\' GROUP BY pattern_id ORDER BY count DESC LIMIT 3');
          
          let currentTask = 'Idle';
          if (processingCount.rows[0].count > 0 && recent.rows.length > 0) {
            currentTask = 'Detecting: ' + recent.rows[0].pattern_id + ' (' + recent.rows[0].action + ')';
          }
          
          details = {
            queue: parseInt(queueCount.rows[0].count),
            processing: parseInt(processingCount.rows[0].count),
            currentTask: currentTask
          };
        } catch (e) {
          details = { currentTask: 'Error', queue: 0, processing: 0 };
        }
      } else if (p.name === 'membria-diff-loader') {
        try {
          const total = await dbPool.query('SELECT COUNT(*) as count FROM commits');
          const loaded = await dbPool.query('SELECT COUNT(*) as count FROM commits WHERE diff_text IS NOT NULL AND diff_text != \'\'');
          const lastCommit = await dbPool.query('SELECT sha, repo_id FROM commits WHERE diff_fetched_at IS NOT NULL ORDER BY diff_fetched_at DESC LIMIT 1');
          
          let lastCommitInfo = 'None';
          if (lastCommit.rows.length > 0) {
            const repoInfo = await dbPool.query('SELECT full_name FROM repos WHERE id = ', [lastCommit.rows[0].repo_id]);
            lastCommitInfo = repoInfo.rows[0]?.full_name + '/' + lastCommit.rows[0].sha.substring(0, 7);
          }
          
          details = {
            total: parseInt(total.rows[0].count),
            loaded: parseInt(loaded.rows[0].count),
            lastCommit: lastCommitInfo,
            progress: total.rows[0].count > 0 ? Math.round((loaded.rows[0].count / total.rows[0].count) * 100) : 0
          };
        } catch (e) {
          details = { total: 0, loaded: 0, lastCommit: 'Error', progress: 0 };
        }
      } else if (p.name === 'membria-crawler') {
        try {
          const lastRepo = await dbPool.query('SELECT full_name, last_fetched_at FROM repos ORDER BY last_fetched_at DESC LIMIT 1');
          
          let crawling = 'Idle';
          if (lastRepo.rows.length > 0) {
            const lastFetched = new Date(lastRepo.rows[0].last_fetched_at);
            const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
            
            if (lastFetched > oneHourAgo) {
              crawling = 'Just finished: ' + lastRepo.rows[0].full_name;
            }
          }
          
          const queuedRepos = await dbPool.query('SELECT COUNT(*) as count FROM repos WHERE last_fetched_at IS NULL');
          
          details = {
            crawling: crawling,
            queued: parseInt(queuedRepos.rows[0].count)
          };
        } catch (e) {
          details = { crawling: 'Error', queued: 0 };
        }
      }
      
      result.push({
        name: p.name,
        pid: p.pid,
        status: p.pm2_env.status,
        uptime: p.pm2_env.pm_uptime,
        cpu: p.monit.cpu,
        memory: p.monit.memory,
        restarts: p.pm2_env.restart_time,
        details: details
      });
    }
    
    res.json({ services: result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

async function start() {
  await connect();
  app.listen(PORT, () => {
    logger.info('🚀 Membria Mining Backend running on port ' + PORT);
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
