# GITHUB MINING CRAWLER - КОРОТКОЕ ТЗ

## 1. СТРАТЕГИЯ ОБХОДА

### 1.1 Приоритизация репозиториев

```yaml
Priority Score Formula:
  score = (stars × 0.4) + (forks × 0.3) + (recent_activity × 0.2) + (age × 0.1)

Where:
  stars: GitHub stars count
  forks: Fork count
  recent_activity: Commits in last 90 days / 100
  age: min(years_old / 5, 1.0)  # Cap at 5 years
```

**Пример:**
```python
def calculate_priority(repo):
    stars_score = repo.stars * 0.4
    forks_score = repo.forks * 0.3
    activity_score = (repo.commits_last_90_days / 100) * 0.2
    age_score = min(repo.years_old / 5, 1.0) * 0.1
    
    return stars_score + forks_score + activity_score + age_score

# Repo A: 10K stars, 1K forks, 500 commits/90d, 3 years
# Score = 4000 + 300 + 100 + 60 = 4460

# Repo B: 1K stars, 100 forks, 10 commits/90d, 1 year  
# Score = 400 + 30 + 2 + 20 = 452

# Process Repo A first!
```

---

### 1.2 Фильтры качества (до приоритизации)

```yaml
MUST HAVE (hard filters):
  ✓ language: javascript, typescript, python
  ✓ stars: >= 100
  ✓ forks: >= 10
  ✓ last_push: within 1 year
  ✓ size: >= 100 KB
  ✓ has_commits: >= 50

MUST NOT HAVE (exclusions):
  ✗ is_fork: true
  ✗ archived: true
  ✗ disabled: true
  ✗ topics: contains "tutorial", "learning", "course", "example"
```

---

### 1.3 Crawling Strategy

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: SEED DISCOVERY (1-2 hours)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Step 1: Topic-based search                              │
│ ├─ Search: topic:nodejs stars:>1000                    │
│ ├─ Search: topic:typescript stars:>1000                │
│ ├─ Search: topic:python stars:>1000                    │
│ └─ Collect: ~5,000 repos                               │
│                                                          │
│ Step 2: Dependency-based search                         │
│ ├─ Search: "jsonwebtoken" language:javascript          │
│ ├─ Search: "passport" language:javascript              │
│ ├─ Search: "express" language:javascript               │
│ └─ Collect: ~3,000 more repos                          │
│                                                          │
│ Step 3: Apply filters                                   │
│ └─ 8,000 repos → 2,500 quality repos                   │
│                                                          │
│ Step 4: Calculate priority scores                       │
│ └─ Sort by score DESC                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ PHASE 2: COMMIT CRAWLING (4-6 hours)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ For each repo (priority order):                         │
│                                                          │
│   1. Check if already processed:                        │
│      SELECT last_fetched FROM repos WHERE id = ?        │
│                                                          │
│   2. Determine fetch mode:                              │
│      IF last_fetched IS NULL:                           │
│        mode = FULL (fetch all commits, limit 1000)      │
│      ELSE:                                               │
│        mode = INCREMENTAL (fetch since last_fetched)    │
│                                                          │
│   3. Fetch commits:                                     │
│      GET /repos/{owner}/{repo}/commits                  │
│        ?since={last_fetched}                            │
│        &per_page=100                                    │
│        &page={N}                                        │
│                                                          │
│   4. Store in PostgreSQL:                               │
│      INSERT INTO commits (...) ON CONFLICT DO NOTHING   │
│                                                          │
│   5. Rate limit check:                                  │
│      IF remaining < 100: WAIT until reset               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. ОБХОД С УЧЕТОМ RATE LIMITS

### 2.1 GitHub API Limits

```yaml
Authenticated API:
  Rate limit: 5,000 requests/hour
  Reset: Every hour (rolling)
  
Per-resource limits:
  Search API: 30 requests/minute
  
Strategy:
  - Use 80% of limit (4,000 requests/hour)
  - Reserve 20% for retries/errors
  - Monitor X-RateLimit-Remaining header
```

### 2.2 Rate Limiter Implementation

```typescript
// src/github/rate-limiter.ts

interface RateLimitState {
  remaining: number;
  reset: number; // Unix timestamp
  limit: number;
}

class GitHubRateLimiter {
  private state: RateLimitState;
  private redis: Redis;
  
  async checkAndWait(): Promise<void> {
    // Get current state from Redis
    const state = await this.redis.hgetall('ratelimit:github');
    
    if (state.remaining < 100) {
      const now = Date.now() / 1000;
      const waitSeconds = state.reset - now;
      
      console.log(`Rate limit low. Waiting ${waitSeconds}s...`);
      await this.sleep(waitSeconds * 1000);
    }
  }
  
  updateFromHeaders(headers: any): void {
    this.state = {
      remaining: parseInt(headers['x-ratelimit-remaining']),
      reset: parseInt(headers['x-ratelimit-reset']),
      limit: parseInt(headers['x-ratelimit-limit'])
    };
    
    // Store in Redis
    this.redis.hmset('ratelimit:github', this.state);
  }
}
```

---

## 3. CRAWLING ALGORITHM (детально)

### 3.1 Seed Discovery

```typescript
// Step 1: Topic-based discovery
async function discoverByTopics(): Promise<Repository[]> {
  const topics = [
    'nodejs', 'typescript', 'javascript', 'python',
    'express', 'react', 'vue', 'django', 'flask'
  ];
  
  const repos: Repository[] = [];
  
  for (const topic of topics) {
    const query = `topic:${topic} stars:>100 forks:>10 pushed:>2024-01-01`;
    
    const results = await github.search.repos({
      q: query,
      sort: 'stars',
      order: 'desc',
      per_page: 100
    });
    
    repos.push(...results.data.items);
    
    // Search API: 30 req/min limit
    await sleep(2000); // Wait 2s between searches
  }
  
  return repos;
}

// Step 2: Dependency-based discovery
async function discoverByDependencies(): Promise<Repository[]> {
  const libraries = [
    'jsonwebtoken', 'passport', 'express', 
    'typeorm', 'prisma', 'mongoose'
  ];
  
  const repos: Repository[] = [];
  
  for (const lib of libraries) {
    const query = `"${lib}" language:javascript stars:>100`;
    
    const results = await github.search.code({
      q: query,
      per_page: 100
    });
    
    // Extract unique repos from code results
    const uniqueRepos = extractReposFromCodeSearch(results);
    repos.push(...uniqueRepos);
    
    await sleep(2000);
  }
  
  return repos;
}

// Step 3: Filter and deduplicate
function filterRepos(repos: Repository[]): Repository[] {
  return repos
    .filter(r => !r.fork)
    .filter(r => !r.archived)
    .filter(r => r.size >= 100)
    .filter(r => {
      const topics = r.topics || [];
      return !topics.some(t => 
        ['tutorial', 'learning', 'example', 'course'].includes(t)
      );
    })
    .reduce((acc, repo) => {
      // Deduplicate by full_name
      if (!acc.some(r => r.full_name === repo.full_name)) {
        acc.push(repo);
      }
      return acc;
    }, []);
}

// Step 4: Prioritize
function prioritizeRepos(repos: Repository[]): Repository[] {
  return repos
    .map(repo => ({
      ...repo,
      priority: calculatePriority(repo)
    }))
    .sort((a, b) => b.priority - a.priority);
}
```

---

### 3.2 Commit Crawling (с параллелизацией)

```typescript
// src/pipeline/commit-collection.ts

async function crawlCommits(repos: Repository[]): Promise<void> {
  const queue = new BullMQ.Queue('commit-crawling', {
    connection: redis
  });
  
  // Add repos to queue
  for (const repo of repos) {
    await queue.add('fetch-commits', {
      repoId: repo.id,
      owner: repo.owner.login,
      name: repo.name,
      priority: repo.priority
    }, {
      priority: Math.floor(repo.priority) // BullMQ priority
    });
  }
  
  // Workers will process in parallel
}

// Worker implementation
async function processRepo(job: Job): Promise<void> {
  const { owner, name, repoId } = job.data;
  
  // 1. Check last fetch
  const lastFetch = await db.query(
    'SELECT last_fetched_at FROM repos WHERE id = $1',
    [repoId]
  );
  
  const since = lastFetch?.last_fetched_at || null;
  
  // 2. Fetch commits
  let page = 1;
  let hasMore = true;
  let commitCount = 0;
  
  while (hasMore && commitCount < 1000) {
    await rateLimiter.checkAndWait();
    
    const response = await github.repos.listCommits({
      owner,
      repo: name,
      per_page: 100,
      page,
      since: since?.toISOString()
    });
    
    rateLimiter.updateFromHeaders(response.headers);
    
    const commits = response.data;
    
    if (commits.length === 0) {
      hasMore = false;
      break;
    }
    
    // 3. Store commits
    for (const commit of commits) {
      await storeCommit(repoId, commit);
    }
    
    commitCount += commits.length;
    page++;
    
    // Progress update
    await job.updateProgress({
      page,
      commits: commitCount
    });
  }
  
  // 4. Update repo
  await db.query(
    'UPDATE repos SET last_fetched_at = NOW() WHERE id = $1',
    [repoId]
  );
}
```

---

## 4. INCREMENTAL STRATEGY

### 4.1 First Run vs Incremental

```yaml
FIRST RUN (Full Crawl):
  Duration: 6-8 hours
  Repos: 2,500
  Commits: ~400,000
  Strategy: Fetch all commits (limit 1000 per repo)
  
INCREMENTAL RUN (Monthly):
  Duration: 30-60 minutes
  Repos: Same 2,500
  Commits: ~20,000 new
  Strategy: Fetch only since last_fetched_at
```

### 4.2 Incremental Logic

```typescript
async function incrementalCrawl(): Promise<void> {
  // 1. Get repos that need update
  const repos = await db.query(`
    SELECT id, owner, name, last_fetched_at
    FROM repos
    WHERE last_fetched_at < NOW() - INTERVAL '30 days'
       OR last_fetched_at IS NULL
    ORDER BY priority DESC
  `);
  
  // 2. For each repo
  for (const repo of repos) {
    const since = repo.last_fetched_at || '2023-01-01';
    
    const commits = await fetchCommitsSince(
      repo.owner, 
      repo.name, 
      since
    );
    
    if (commits.length > 0) {
      await storeCommits(repo.id, commits);
      console.log(`${repo.name}: +${commits.length} new commits`);
    } else {
      console.log(`${repo.name}: no new commits`);
    }
  }
}
```

---

## 5. OPTIMIZATION STRATEGIES

### 5.1 Parallel Processing

```yaml
Workers Configuration:
  Seed discovery: 1 worker (sequential, API limits)
  Commit fetching: 10 workers (parallel)
  Pattern detection: 20 workers (CPU-bound)
  
BullMQ Setup:
  Queue: commit-crawling
  Concurrency: 10
  Rate limit: Shared via Redis
```

### 5.2 Caching Strategy

```typescript
// Cache repo metadata
async function getRepoMetadata(owner: string, name: string) {
  const cacheKey = `repo:${owner}/${name}`;
  
  // Check Redis
  const cached = await redis.get(cacheKey);
  if (cached) return JSON.parse(cached);
  
  // Fetch from GitHub
  const repo = await github.repos.get({ owner, repo: name });
  
  // Cache for 24 hours
  await redis.setex(cacheKey, 86400, JSON.stringify(repo.data));
  
  return repo.data;
}
```

---

## 6. ERROR HANDLING

### 6.1 Retry Strategy

```yaml
Transient Errors (retry):
  - 500, 502, 503: GitHub server errors
  - Network timeouts
  - Rate limit exceeded (wait and retry)
  
Permanent Errors (skip):
  - 404: Repo deleted
  - 403: Access denied (private repo)
  - 451: DMCA takedown
  
Retry Configuration:
  Max attempts: 3
  Backoff: exponential (1s, 2s, 4s)
  Jitter: ±20% random
```

### 6.2 Implementation

```typescript
async function fetchWithRetry(
  fn: () => Promise<any>,
  maxRetries = 3
): Promise<any> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (error.status === 404 || error.status === 403) {
        throw error; // Don't retry permanent errors
      }
      
      if (attempt === maxRetries) {
        throw error; // Max retries exceeded
      }
      
      // Exponential backoff with jitter
      const baseDelay = Math.pow(2, attempt) * 1000;
      const jitter = Math.random() * 0.4 - 0.2; // ±20%
      const delay = baseDelay * (1 + jitter);
      
      console.log(`Retry ${attempt}/${maxRetries} after ${delay}ms`);
      await sleep(delay);
    }
  }
}
```

---

## 7. MONITORING

### 7.1 Metrics to Track

```yaml
Real-time:
  - API rate limit remaining
  - Repos processed / hour
  - Commits fetched / minute
  - Error rate by type
  
Cumulative:
  - Total repos processed
  - Total commits collected
  - Average commits per repo
  - Processing time per repo
```

### 7.2 Logging

```typescript
// Structured logging
logger.info('crawl_start', {
  repos_total: 2500,
  mode: 'incremental',
  since: '2025-01-01'
});

logger.info('repo_processed', {
  repo: 'facebook/react',
  commits_fetched: 147,
  duration_ms: 3200,
  priority: 8540
});

logger.warn('rate_limit_low', {
  remaining: 95,
  reset_in: 180
});

logger.error('fetch_failed', {
  repo: 'example/repo',
  error: '404 Not Found',
  attempts: 3
});
```

---

## 8. EXAMPLE EXECUTION PLAN

```bash
# Day 1: First full run
npm run mining:full

Output:
[00:00] Starting seed discovery...
[00:15] Found 8,247 repos via topics
[00:30] Found 3,156 repos via dependencies
[00:45] Filtered to 2,531 quality repos
[01:00] Calculated priorities, sorted
[01:00] Starting commit crawling (10 workers)...
[01:30] Progress: 500/2531 repos (20%)
[03:00] Progress: 1265/2531 repos (50%)
[05:00] Progress: 2024/2531 repos (80%)
[06:30] Completed: 2531 repos, 412,847 commits
[06:30] Starting pattern detection...
[08:00] Mining complete!

# Day 31: Incremental update
npm run mining:incremental

Output:
[00:00] Loading 2,531 repos from database
[00:00] Starting incremental crawl...
[00:15] Progress: 500/2531 repos
[00:30] Completed: 2531 repos, 18,234 new commits
[00:35] Pattern detection on new commits...
[00:45] Incremental mining complete!
```

---

## SUMMARY TABLE

| Stage | Duration | API Calls | Output |
|-------|----------|-----------|--------|
| Seed Discovery | 1 hour | ~500 | 2,500 repos |
| Priority Calculation | 5 min | 0 | Sorted list |
| Commit Crawling (full) | 6 hours | ~25,000 | 400K commits |
| Commit Crawling (incremental) | 30 min | ~2,500 | 20K commits |
| Pattern Detection | 2 hours | 0 | 50K patterns |
| **Total (first run)** | **8 hours** | **25,500** | **Ready** |
| **Total (monthly)** | **3 hours** | **2,500** | **Updated** |

---

**Вот теперь полное ТЗ с алгоритмом обхода!**