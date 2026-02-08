const { Pool } = require('pg');
const pool = new Pool({host: 'localhost', port: 5432, database: 'membria', user: 'membria', password: '123zXc123!~~'});
pool.query('SELECT 1').then(() => console.log('Connected!')).catch(e => console.error(e.message));
