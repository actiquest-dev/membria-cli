class Utils {
  static async waitIfNeeded() {
    const rateLimit = this.github.getRateLimit();

    if (rateLimit.remaining < 100) {
      const waitSeconds = rateLimit.reset - Math.floor(Date.now() / 1000);
      console.log(`  ⏱️  Rate limit low. Waiting ${waitSeconds}s...`);
      await new Promise(resolve => setTimeout(resolve, waitSeconds * 1000));
    }
  }

  static wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = Utils;
