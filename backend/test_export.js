const pool = require('./utils/database').pool;
console.log('Pool type:', typeof pool);
console.log('Pool config:', pool.options.user);
