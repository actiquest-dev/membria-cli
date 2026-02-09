require('dotenv').config();
const axios = require('axios');
const Bull = require('bull');
const { pool } = require('./utils/database');
const { RedisClient } = require('./utils/redis');
const logger = require('./utils/logger');
const { PatternDetector } = require('./detection');
const { loadPatternConfigs } = require('./config/patterns');
const { parseDiff, getLanguage } = require('./detection/diff-parser');

const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';
const REDIS_HOST = process.env.REDIS_HOST || 'localhost';
const REDIS_PORT = process.env.REDIS_PORT || 6379;

// Bull queue for pattern detection
const detectQueue = new Bull('pattern-detect', {
  redis: { host: REDIS_HOST, port: parseInt(REDIS_PORT) },
});

// Load pattern configs once at startup
let patterns = null;
let detector = null;

// --- GitHub API ---

async function fetchCommitsPage(owner, name, page = 1) {
  const url = `https://api.github.com/repos/${owner}/${name}/commits?page=${page}&per_page=100`;
  const headers = {
    'Accept': 'application/vnd.github.v3+json',
  };
  if (GITHUB_TOKEN) {
    headers['Authorization'] = `token ${GITHUB_TOKEN}`;
  }
  const response = await axios.get(url, { headers });
  return response.data;
}

async function fetchCommitDiff(owner, name, sha) {
  const url = `https://api.github.com/repos/${owner}/${name}/commits/${sha}`;
  const headers = {
    'Accept': 'application/vnd.github.v3.diff',
  };
  if (GITHUB_TOKEN) {
    headers['Authorization'] = `token ${GITHUB_TOKEN}`;
  }
  try {
    const response = await axios.get(url, { headers, timeout: 30000 });
    return response.data;
  } catch (error) {
    logger.warn(`Failed to fetch diff for ${sha}: ${error.message}`);
    return null;
  }
}

// --- Database operations ---

async function upsertRepo(owner, name) {
  const fullName = `${owner}/${name}`;
  const result = await pool.query(
    `INSERT INTO repos (owner, name, full_name)
     VALUES ($1, $2, $3)
     ON CONFLICT (full_name) DO UPDATE SET last_fetched_at = NOW()
     RETURNING id`,
    [owner, name, fullName]
  );
  return result.rows[0].id;
}

async function storeCommit(repoId, commit, diffText) {
  const result = await pool.query(
    `INSERT INTO commits (sha, repo_id, message, author, date, diff_text, files_changed)
     VALUES ($1, $2, $3, $4, $5, $6, $7)
     ON CONFLICT (sha, repo_id) DO NOTHING
     RETURNING id`,
    [
      commit.sha,
      repoId,
      commit.commit.message,
      commit.commit.author?.name || 'unknown',
      commit.commit.author?.date || null,
      diffText,
      JSON.stringify(commit.files?.map(f => f.filename) || []),
    ]
  );
  return result.rows[0]?.id || null;
}

async function storeOccurrence(commitSha, repoId, patternId, action, filePath, result) {
  for (const match of result.matches) {
    await pool.query(
      `INSERT INTO pattern_occurrences
       (commit_sha, repo_id, pattern_id, action, file_path, line_number, confidence, detection_method, match_text)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        commitSha,
        repoId,
        patternId,
        action,
        filePath,
        match.line,
        result.confidence,
        result.method,
        match.text.substring(0, 500),
      ]
    );
  }
}

async function markCommitProcessed(sha, repoId) {
  await pool.query(
    'UPDATE commits SET processed = TRUE WHERE sha = $1 AND repo_id = $2',
    [sha, repoId]
  );
}

// --- Mining pipeline ---

async function mineRepository(owner, repo) {
  logger.info(`Mining ${owner}/${repo}...`);

  const repoId = await upsertRepo(owner, repo);
  let page = 1;
  let totalCommits = 0;

  while (true) {
    let commits;
    try {
      commits = await fetchCommitsPage(owner, repo, page);
    } catch (error) {
      if (error.response?.status === 403) {
        logger.warn('GitHub API rate limit reached, stopping');
      } else if (error.response?.status === 404) {
        logger.error(`Repo ${owner}/${repo} not found`);
      } else {
        logger.error(`Error fetching commits page ${page}: ${error.message}`);
      }
      break;
    }

    if (!commits || commits.length === 0) break;

    for (const commit of commits) {
      const diff = await fetchCommitDiff(owner, repo, commit.sha);
      const commitId = await storeCommit(repoId, commit, diff);

      if (commitId) {
        await detectQueue.add({
          commitSha: commit.sha,
          repoId,
          diffText: diff,
        });
        totalCommits++;
      }

      // Rate limit protection
      await new Promise(r => setTimeout(r, 500));
    }

    page++;
    if (commits.length < 100) break;

    await new Promise(r => setTimeout(r, 1000));
  }

  logger.info(`Mining ${owner}/${repo} complete: ${totalCommits} commits queued for detection`);
  return totalCommits;
}

// --- Bull queue processor ---

detectQueue.process(5, async (job) => {
  const { commitSha, repoId, diffText } = job.data;

  if (!diffText) {
    await markCommitProcessed(commitSha, repoId);
    return;
  }

  const changes = parseDiff(diffText);

  for (const change of changes) {
    const language = getLanguage(change.file);
    if (!language || !['javascript', 'typescript'].includes(language)) {
      continue;
    }

    for (const pattern of patterns) {
      if (!pattern.languages.includes(language)) continue;

      // Detect in added lines
      if (change.addedLines.length > 0) {
        const code = change.addedLines.join('\n');
        const result = await detector.detect(code, language, pattern);
        if (result.detected) {
          await storeOccurrence(commitSha, repoId, pattern.id, 'add', change.file, result);
        }
      }

      // Detect in removed lines
      if (change.removedLines.length > 0) {
        const code = change.removedLines.join('\n');
        const result = await detector.detect(code, language, pattern);
        if (result.detected) {
          await storeOccurrence(commitSha, repoId, pattern.id, 'remove', change.file, result);
        }
      }
    }
  }

  await markCommitProcessed(commitSha, repoId);
});

detectQueue.on('failed', (job, err) => {
  logger.error(`Detection job failed for commit ${job.data.commitSha}: ${err.message}`);
});

// --- Start ---

async function start() {
  patterns = loadPatternConfigs();
  logger.info(`Loaded ${patterns.length} pattern configs`);

  const redisClient = new RedisClient();
  await redisClient.connect();
  detector = new PatternDetector(redisClient);

  logger.info('Worker connected to Redis');

  // Listen for mining tasks via pub/sub
  await redisClient.subscribe('patterns:mine', async (message) => {
    try {
      const data = JSON.parse(message);
      const owner = data.repoOwner || data.owner;
      const repo = data.repoName || data.repo;

      if (!owner || !repo) {
        logger.error('Invalid mining task: missing owner or repo');
        return;
      }

      await mineRepository(owner, repo);
    } catch (error) {
      logger.error(`Error processing mining task: ${error.message}`);
    }
  });

  logger.info('Waiting for mining tasks...');

  // Graceful shutdown
  const shutdown = async () => {
    logger.info('Shutting down worker...');
    await detectQueue.close();
    await redisClient.disconnect();
    await pool.end();
    process.exit(0);
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

start().catch(error => {
  logger.error('Worker error:', error);
  process.exit(1);
});
