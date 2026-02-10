const GitHubClient = require('../github/client');
const Repository = require('../db/repository');

class DiscoveryPipeline {
  constructor(token) {
    this.github = new GitHubClient(token);
  }

  // Priority Score Formula
  // score = (stars × 0.4) + (forks × 0.3) + (recent_activity × 0.2) + (age × 0.1)
  calculatePriority(repo) {
    const stars = repo.stargazers_count || repo.stars || 0;
    const forks = repo.forks_count || repo.forks || 0;

    const starsScore = stars * 0.4;
    const forksScore = forks * 0.3;

    // Recent activity: pushes in last 90 days
    const ninetyDaysAgo = new Date();
    ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
    let activityScore = 0;
    if (repo.pushed_at && new Date(repo.pushed_at) > ninetyDaysAgo) {
      activityScore = 100; // 100 max for recent activity
    }

    // Age score (max 5 years, capped at 10 points)
    const ageInYears = (Date.now() - new Date(repo.created_at).getTime()) / (365 * 24 * 60 * 60 * 1000);
    const ageScore = Math.min(ageInYears / 5, 1.0) * 10;

    return Math.round(starsScore + forksScore + activityScore + ageScore);
  }

  // Filter repos based on quality criteria
  filterRepos(repos) {
    return repos.filter(repo => {
      // Must have language: JavaScript, TypeScript, Python
      const lang = (repo.language || '').toLowerCase();
      if (!['javascript', 'typescript', 'python'].includes(lang)) {
        return false;
      }

      const stars = repo.stargazers_count || repo.stars || 0;
      const forks = repo.forks_count || repo.forks || 0;

      // Must have stars >= 100
      if (stars < 100) {
        return false;
      }

      // Must have forks >= 10
      if (forks < 10) {
        return false;
      }

      // Must not be archived
      if (repo.archived) {
        return false;
      }

      // Must not be a fork
      if (repo.fork) {
        return false;
      }

      // Cannot have certain topics
      const topics = (repo.topics || []);
      const excludedTopics = ['tutorial', 'learning', 'example', 'course', 'demo'];
      if (topics.some(t => excludedTopics.includes(t.toLowerCase()))) {
        return false;
      }

      return true;
    });
  }

  async discoverByTopics() {
    console.log('🔍 Discovering repositories by topics...');

    const topics = [
      'nodejs', 'typescript', 'javascript',
      'express', 'react', 'vue', 'nextjs',
      'python', 'django', 'flask',
      'backend', 'api', 'rest'
    ];

    const allRepos = [];
    let total = 0;

    for (const topic of topics) {
      console.log(`  Searching: topic:${topic} stars:>100`);

      // Search API rate limit: 30 req/min
      const repos = await this.github.searchRepos(`topic:${topic} stars:>100 forks:>10 pushed:>2024-01-01`, 100);
      allRepos.push(...repos);
      total += repos.length;

      // Rate limiting: wait 2s between searches
      await this.wait(2000);
    }

    console.log(`  Found ${allRepos.length} repos by topics`);
    return allRepos;
  }

  async discoverByDependencies() {
    console.log('🔍 Discovering repositories by dependencies...');

    const libraries = [
      'jsonwebtoken', 'passport', 'express',
      'typeorm', 'prisma', 'mongoose',
      'axios', 'fetch', 'node-fetch'
    ];

    const allRepos = [];
    let total = 0;

    for (const lib of libraries) {
      console.log(`  Searching: "${lib}" language:javascript stars:>100`);

      // Search code for dependency usage
      const results = await this.github.searchCode(`"${lib}" language:javascript stars:>100`, 100);
      const repos = new Set();

      // Extract unique repos from code search results
      for (const item of results) {
        const match = item.repository.full_name.match(/(.+)\/(.+)/);
        if (match) {
          repos.add(match[1]);
          repos.add(match[2]);
        }
      }

      repos.forEach(name => {
        allRepos.push({
          owner: name.split('/')[0],
          name: name.split('/')[1]
        });
      });

      total += repos.size;
      await this.wait(2000);
    }

    console.log(`  Found ${allRepos.length} repos by dependencies`);
    return allRepos;
  }

  async process(repos, existingCount = 0) {
    console.log(`\n📊 Processing ${repos.length} repositories...`);

    let skipped = 0;
    let added = 0;

    for (const repo of repos) {
      try {
        // Get full repo data
        const fullRepo = await this.github.getRepo(repo.owner, repo.name);

        // Calculate priority
        const priority = this.calculatePriority(fullRepo);

        // Filter
        if (!this.filterRepos([fullRepo]).length) {
          skipped++;
          continue;
        }

        // Save to database
        await Repository.create({
          full_name: fullRepo.full_name,
          owner: fullRepo.owner.login,
          name: fullRepo.name,
          description: fullRepo.description,
          stars: fullRepo.stargazers_count,
          forks: fullRepo.forks_count,
          language: fullRepo.language,
          size: fullRepo.size,
          pushed_at: fullRepo.pushed_at,
          archived: fullRepo.archived,
          fork: fullRepo.fork,
          topics: fullRepo.topics,
          priority_score: priority
        });

        added++;
      } catch (error) {
        console.error(`  Error processing ${repo.full_name || repo.owner}/${repo.name}:`, error.message);
      }

      // Rate limiting
      await this.wait(500);
    }

    const totalProcessed = existingCount + added + skipped;
    console.log(`\n✅ Discovery complete!`);
    console.log(`   Total found: ${repos.length}`);
    console.log(`   Added: ${added}`);
    console.log(`   Skipped: ${skipped}`);
    console.log(`   Total in DB: ${totalProcessed}`);
  }

  async run() {
    console.log('🚀 Starting repository discovery...\n');

    // Check existing repos
    const existingCount = await Repository.count();
    console.log(`📦 Found ${existingCount} repositories in database\n`);

    // Discover by topics
    let repos = await this.discoverByTopics();

    // Discover by dependencies
    const depRepos = await this.discoverByDependencies();

    // Merge and deduplicate
    const uniqueRepos = new Map();
    [...repos, ...depRepos].forEach(repo => {
      const fullName = repo.full_name || `${repo.owner}/${repo.name}`;
      if (!uniqueRepos.has(fullName)) {
        uniqueRepos.set(fullName, repo);
      }
    });

    repos = Array.from(uniqueRepos.values());

    // Process all repos
    await this.process(repos, existingCount);

    console.log('\n✨ Discovery pipeline complete!');
  }

  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = DiscoveryPipeline;
