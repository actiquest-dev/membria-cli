const Redis = require('redis');

class RedisClient {
  constructor() {
    this.client = Redis.createClient({
      socket: {
        host: process.env.REDIS_HOST || 'localhost',
        port: process.env.REDIS_PORT || 6379,
      },
      retry_strategy: (options) => {
        if (options.total_retry_time > 1000 * 60 * 60) {
          return new Error('Retry time exhausted');
        }
        if (options.attempt > 0) {
          return options.attempt * 100;
        }
        return 1000;
      }
    });

    this.client.on('error', (err) => {
      console.error('Redis Client Error:', err);
    });
  }

  async connect() {
    await this.client.connect();
  }

  disconnect() {
    return this.client.disconnect();
  }

  async publish(channel, message) {
    return this.client.publish(channel, message);
  }

  async get(key) {
    return this.client.get(key);
  }

  async set(key, value) {
    return this.client.set(key, value);
  }

  async setex(key, seconds, value) {
    return this.client.setEx(key, seconds, value);
  }

  async subscribe(channel, callback) {
    const subscriber = this.client.duplicate();
    await subscriber.connect();
    await subscriber.subscribe(channel, callback);
    return subscriber;
  }

  getClient() {
    return this.client;
  }
}

module.exports = { RedisClient };
