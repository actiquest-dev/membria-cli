require('dotenv').config();
const { Pool } = require('pg');
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'membria',
  user: process.env.DB_USER || 'membria',
  password: process.env.DB_PASSWORD,
});
console.log('Config user:', pool.options.user);
console.log('Config password:', pool.options.password);
console.log('Config password type:', typeof pool.options.password);
pool.connect().then(() => console.log('Pool connected!')).catch(e => console.error('Pool error:', e.message));
