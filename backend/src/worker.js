require('dotenv').config();
const { Pool } = require('pg');
const redis = require('redis');
const axios = require('axios');

const dbPool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'membria',
  user: process.env.DB_USER || 'membria',
  password: process.env.DB_PASSWORD,
});

const redisClient = redis.createClient({
  socket: {
    host: process.env.REDIS_HOST || 'localhost',
    port: process.env.REDIS_PORT || 6379,
  }
});

const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';

async function fetchRepo(owner, name, page = 1) {
  try {
    const url = `https://api.github.com/repos/${owner}/${name}/commits?page=${page}&per_page=100`;
    const headers = {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json'
    };
    const response = await axios.get(url, { headers });
    return response.data;
  } catch (error) {
    if (error.response?.status === 403) {
      console.error('GitHub API rate limit reached');
    }
    throw error;
  }
}

async function analyzeCommit(commit) {
  const messages = commit.commit.message.split('\n');

  // Check for common patterns
  const issues = [];

  // TODO: Add more patterns
  if (messages.some(m => m.trim().startsWith('TODO:') || m.trim().startsWith('FIXME'))) {
    issues.push({ type: 'todo', message: m.trim() });
  }

  if (messages.some(m => m.trim().includes('fixme') || m.trim().includes('hack'))) {
    issues.push({ type: 'fixme', message: m.trim() });
  }

  return issues;
}

async function savePattern(owner, name, sha, issues) {
  try {
    await dbPool.query(
      `INSERT INTO patterns (owner, repo, sha, issues, created_at)
       VALUES ($1, $2, $3, $4, NOW())
       ON CONFLICT (sha) DO NOTHING`,
      [owner, name, sha, JSON.stringify(issues)]
    );
  } catch (error) {
    console.error('Failed to save pattern:', error.message);
  }
}

async function processMiningTask(message) {
  try {
    const { owner, repo } = JSON.parse(message);

    // Fetch commits
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const commits = await fetchRepo(owner, repo, page);

      if (commits.length === 0) {
        hasMore = false;
        break;
      }

      for (const commit of commits) {
        const sha = commit.sha;
        const issues = await analyzeCommit(commit);

        if (issues.length > 0) {
          await savePattern(owner, repo, sha, issues);
          console.log(`Found ${issues.length} issues in ${commit.sha.substring(0, 7)}:`, issues);
        }
      }

      page++;
      hasMore = commits.length === 100;
    }

    console.log(`Mining complete for ${owner}/${repo}`);
  } catch (error) {
    console.error('Error processing mining task:', error.message);
  }
}

async function start() {
  await dbPool.connect();
  await redisClient.connect();
  console.log('✅ Worker connected to DB and Redis');

  // Listen for mining tasks
  redisClient.subscribe('patterns:mine', (message) => {
    processMiningTask(message).catch(console.error);
  });

  console.log('📡 Waiting for mining tasks...');

  // Start listening
  await new Promise(() => {}); // Keep running
}

start().catch(error => {
  console.error('Worker error:', error);
  process.exit(1);
});
