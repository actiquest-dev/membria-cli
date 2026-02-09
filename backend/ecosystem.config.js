module.exports = {
  apps: [
    {
      name: 'membria-miner',
      script: 'src/index.js',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PORT: 4000
      },
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      time: true
    },
    {
      name: 'membria-worker',
      script: 'src/worker.js',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/worker-error.log',
      out_file: './logs/worker-output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      time: true
    }
  ]
};
