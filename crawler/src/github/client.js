const axios = require('axios');
const Utils = require('./utils');

class GitHubClient {
  constructor(token) {
    this.token = token;
    this.baseURL = 'https://api.github.com';
    this.headers = {
      'Authorization': `token ${token}`,
      'Accept': 'application/vnd.github.v3+json',
      'X-GitHub-Api-Version': '2022-11-28'
    };
    this.rateLimit = {
      remaining: 5000,
      limit: 5000,
      reset: Date.now() / 1000
    };
    this.searchRateLimit = {
      remaining: 30,
      limit: 30
    };
  }

  async request(method, endpoint, params = {}) {
    const config = {
      method,
      url: `${this.baseURL}${endpoint}`,
      headers: this.headers,
      params
    };

    try {
      const response = await axios(config);
      this.updateRateLimit(response.headers);
      return response.data;
    } catch (error) {
      if (error.response?.status === 403 && error.response?.data?.message === 'API rate limit exceeded') {
        this.handleRateLimitError(error);
      }
      throw error;
    }
  }

  updateRateLimit(headers) {
    this.rateLimit.remaining = parseInt(headers['x-ratelimit-remaining']);
    this.rateLimit.limit = parseInt(headers['x-ratelimit-limit']);
    this.rateLimit.reset = parseInt(headers['x-ratelimit-reset']);
  }

  updateSearchRateLimit(headers) {
    this.searchRateLimit.remaining = parseInt(headers['ratelimit-remaining']);
    this.searchRateLimit.limit = parseInt(headers['ratelimit-limit']);
  }

  async waitIfNeeded() {
    const rateLimit = this.getRateLimit();

    if (rateLimit.remaining < 100) {
      const waitSeconds = rateLimit.reset - Math.floor(Date.now() / 1000);
      console.log(`  ⏱️  Rate limit low. Waiting ${waitSeconds}s...`);
      await new Promise(resolve => setTimeout(resolve, waitSeconds * 1000));
    }
  }

  async searchRepos(query, perPage = 100) {
    const endpoint = '/search/repositories';
    const params = {
      q: query,
      per_page: perPage,
      sort: 'stars',
      order: 'desc'
    };
    const data = await this.request('GET', endpoint, params);
    this.updateSearchRateLimit(data.headers || {});
    return data.items || [];
  }

  async getRepo(owner, name) {
    return this.request('GET', `/repos/${owner}/${name}`);
  }

  async listCommits(owner, name, page = 1, perPage = 100, since = null) {
    const endpoint = `/repos/${owner}/${name}/commits`;
    const params = {
      per_page: perPage,
      page
    };
    if (since) params.since = since;
    return this.request('GET', endpoint, params);
  }

  async listTopics(owner, name) {
    return this.request('GET', `/repos/${owner}/${name}/topics`);
  }

  async searchCode(query, perPage = 100) {
    const endpoint = '/search/code';
    const params = {
      q: query,
      per_page: perPage
    };
    const data = await this.request('GET', endpoint, params);
    this.updateSearchRateLimit(data.headers || {});
    return data.items || [];
  }

  getRateLimit() {
    return { ...this.rateLimit };
  }

  getSearchRateLimit() {
    return { ...this.searchRateLimit };
  }
}

module.exports = GitHubClient;
