require('dotenv').config();

const GitHubClient = require('./github/client');
const Repository = require('./db/repository');
const Commit = require('./db/commit');
const DiscoveryPipeline = require('./pipeline/discover');
const CrawlPipeline = require('./pipeline/crawl');

const token = process.env.GITHUB_TOKEN || '';

if (!token) {
  console.error('❌ GITHUB_TOKEN is required');
  process.exit(1);
}

async function showStats() {
  console.log('📊 Membria Crawler Statistics\n');

  const repoStats = await Repository.getStats();
  const commitStats = await Commit.countTotal();
  const unprocessedCommits = await Commit.getUnprocessed(1);

  console.log(`Repositories:`);
  console.log(`  Total:        ${repoStats.total_repos || 0}`);
  console.log(`  Processed:    ${repoStats.processed_repos || 0}`);
  console.log(`  Unprocessed:  ${repoStats.unprocessed_repos || 0}`);
  console.log(`  Total Stars:  ${repoStats.total_stars || 0}`);

  console.log(`\nCommits:`);
  console.log(`  Total:        ${commitStats}`);

  const github = new GitHubClient(token);
  const rateLimit = github.getRateLimit();
  console.log(`\nGitHub API Rate Limit:`);
  console.log(`  Remaining:    ${rateLimit.remaining}/${rateLimit.limit}`);
  const resetMinutes = Math.ceil((rateLimit.reset * 1000 - Date.now()) / 60000);
  console.log(`  Resets in:    ${resetMinutes} minutes`);
}

async function runFull() {
  console.log('🚀 Starting full mining pipeline...\n');

  // Step 1: Discover repositories
  console.log('--- STEP 1: Discovery ---');
  const discover = new DiscoveryPipeline(token);
  await discover.run();

  console.log('\n--- STEP 2: Crawling ---');
  const crawl = new CrawlPipeline(token);
  await crawl.crawlAll(100);

  console.log('\n✅ Full mining pipeline complete!');
}

async function main() {
  const command = process.argv[2];

  try {
    switch (command) {
      case 'discover':
        const discover = new DiscoveryPipeline(token);
        await discover.run();
        break;

      case 'crawl':
        const limit = parseInt(process.argv[3]) || 100;
        const crawl = new CrawlPipeline(token);
        await crawl.crawlAll(limit);
        break;

      case 'crawl-incremental':
        const days = parseInt(process.argv[3]) || 30;
        const crawlInc = new CrawlPipeline(token);
        await crawlInc.crawlIncremental(days, 100);
        break;

      case 'stats':
        await showStats();
        break;

      case 'full':
        await runFull();
        break;

      default:
        console.log('Membria GitHub Crawler');
        console.log('\nUsage:');
        console.log('  node src/index.js discover          - Discover new repositories');
        console.log('  node src/index.js crawl [limit]     - Crawl unprocessed repositories');
        console.log('  node src/index.js crawl-incremental - Crawl repositories needing updates');
        console.log('  node src/index.js full              - Run full pipeline (discover + crawl)');
        console.log('  node src/index.js stats             - Show statistics');
        console.log('\nExamples:');
        console.log('  node src/index.js discover');
        console.log('  node src/index.js crawl 50');
        console.log('  node src/index.js full');
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

main();
