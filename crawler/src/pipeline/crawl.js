const GitHubClient = require('../github/client');
const Repository = require('../db/repository');
const Commit = require('../db/commit');

class CrawlPipeline {
  constructor(token) {
    this.github = new GitHubClient(token);
    this.stats = {
      reposProcessed: 0,
      commitsFetched: 0,
      errors: 0
    };
  }

  async crawlRepo(owner, name) {
    console.log(`\n🏗️  Crawling ${owner}/${name}...`);

    try {
      // Get repo from database
      const repo = await Repository.getRepoByName(owner, name);

      if (!repo) {
        console.log(`  ⚠️  Repo not found in database, skipping`);
        return 0;
      }

      // Check if recently processed (within 24 hours)
      if (repo.last_fetched_at) {
        const hoursSinceLastFetch = (Date.now() - new Date(repo.last_fetched_at).getTime()) / (1000 * 60 * 60);
        if (hoursSinceLastFetch < 24) {
          console.log(`  ⏭️  Skipping (last fetched ${hoursSinceLastFetch.toFixed(1)}h ago)`);
          return 0;
        }
      }

      // Fetch commits
      const commits = await this.fetchCommits(owner, name, repo.id, repo.last_fetched_at);

      if (commits > 0) {
        console.log(`  ✓ Fetched ${commits} commits`);
      } else if (repo.last_fetched_at) {
        console.log(`  ✓ No new commits`);
      } else {
        console.log(`  ✓ No commits found`);
      }

      // Update last fetched timestamp
      await Repository.updateLastFetched(repo.id);

      this.stats.reposProcessed++;
      this.stats.commitsFetched += commits;

      return commits;
    } catch (error) {
      console.error(`  ✗ Error crawling ${owner}/${name}:`, error.message);
      this.stats.errors++;
      return 0;
    }
  }

  async fetchCommits(owner, name, repoId, since = null) {
    let totalStored = 0;
    let page = 1;
    let hasMore = true;
    const maxCommits = 1000; // Limit commits per repo
    const maxPages = 10; // 10 pages * 100 = 1000 commits

    while (hasMore && page <= maxPages && totalStored < maxCommits) {
      // Rate limiting check
      await this.github.waitIfNeeded();

      try {
        const data = await this.github.listCommits(owner, name, page, 100, since);

        if (!data || data.length === 0) {
          hasMore = false;
          break;
        }

        // Store commits
        for (const commit of data) {
          // Check if we've stored this commit before
          const existingCheck = await Commit.create({
            sha: commit.sha,
            repoId: repoId,
            message: commit.commit?.message?.split('\n')[0] || '',
            author: commit.author?.login || commit.commit?.author?.name || 'unknown',
            date: commit.commit?.author?.date || null,
            diffText: null, // Will be fetched later if needed
            filesChanged: null
          });

          if (existingCheck) {
            totalStored++;
          }
        }

        page++;
        hasMore = data.length === 100;

        // Small delay to avoid hitting rate limits
        await this.wait(500);

      } catch (error) {
        if (error.response?.status === 404) {
          console.log(`  ⚠️  Repo not found (404), skipping`);
          break;
        } else if (error.response?.status === 403) {
          console.log(`  ⚠️  Access forbidden (403), skipping`);
          break;
        } else {
          console.error(`  Error fetching page ${page}:`, error.message);
          // Continue to next page on transient errors
        }
      }
    }

    return totalStored;
  }

  async crawlAll(limit = 100) {
    console.log('🏗️  Starting full commit crawling...\n');

    const repos = await Repository.getUnprocessed(limit);

    if (repos.length === 0) {
      console.log('✅ No unprocessed repositories found.');
      return this.stats;
    }

    console.log(`Found ${repos.length} repositories to crawl\n`);

    for (let i = 0; i < repos.length; i++) {
      const repo = repos[i];
      console.log(`[${i + 1}/${repos.length}] ${repo.owner}/${repo.name} (priority: ${repo.priority_score || 0})`);
      await this.crawlRepo(repo.owner, repo.name);
    }

    console.log(`\n✅ Crawling complete!`);
    console.log(`   Repos processed: ${this.stats.reposProcessed}`);
    console.log(`   Commits fetched: ${this.stats.commitsFetched}`);
    console.log(`   Errors: ${this.stats.errors}`);

    return this.stats;
  }

  async crawlIncremental(days = 30, limit = 100) {
    console.log(`🏗️  Starting incremental crawl (repos updated in last ${days} days)...\n`);

    const repos = await Repository.getNeedsUpdate(days, limit);

    if (repos.length === 0) {
      console.log('✅ No repositories need updating.');
      return this.stats;
    }

    console.log(`Found ${repos.length} repositories to update\n`);

    for (let i = 0; i < repos.length; i++) {
      const repo = repos[i];
      console.log(`[${i + 1}/${repos.length}] ${repo.owner}/${repo.name}`);
      await this.crawlRepo(repo.owner, repo.name);
    }

    console.log(`\n✅ Incremental crawl complete!`);
    console.log(`   Repos processed: ${this.stats.reposProcessed}`);
    console.log(`   Commits fetched: ${this.stats.commitsFetched}`);
    console.log(`   Errors: ${this.stats.errors}`);

    return this.stats;
  }

  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = CrawlPipeline;
