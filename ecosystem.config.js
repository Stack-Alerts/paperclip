// PM2 process manager config for BTC Trade Engine
// Usage:
//   pm2 start ecosystem.config.js        # start both processes under PM2
//   pm2 save && pm2 startup              # persist across reboots (run as shown)
//   pm2 status                           # live status
//   pm2 logs bte-api --lines 50          # tail API logs
//   pm2 restart bte-api                  # manual restart
//
// Auto-recovery behaviour:
//   - Restarts bte-api on crash (up to 20 times, then manual intervention needed)
//   - Kills and restarts if RSS exceeds 1 GB — catches stuck backtest subprocess
//     trees that previously made the server unresponsive (BTCAAAAA-36104)
//   - health_check_url polls /health every 60 s; 3 consecutive failures → restart

const path = require('path');
const projectRoot = __dirname;

const API_PORT = process.env.BTE_API_PORT || 8765;
const WEB_PORT = process.env.PORT || 3010;

module.exports = {
  apps: [
    {
      name: 'bte-api',
      script: path.join(projectRoot, 'scripts/start_api.sh'),
      interpreter: 'bash',
      cwd: projectRoot,

      autorestart: true,
      max_restarts: 20,
      min_uptime: '10s',
      restart_delay: 3000,

      // Kills the process if RSS > 1 GB — prevents stuck backtest subprocesses
      // from holding the worker indefinitely
      max_memory_restart: '1G',

      // PM2 health check: restart if /health is unreachable 3× in a row
      health_check_interval: 60000,
      health_check_grace_period: 15000,
      health_check_fatal_count: 3,
      health_check_url: `http://127.0.0.1:${API_PORT}/health`,

      out_file: path.join(projectRoot, 'logs/bte-api-out.log'),
      error_file: path.join(projectRoot, 'logs/bte-api-err.log'),
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },

    {
      name: 'bte-web',
      script: 'npm',
      args: 'run dev',
      cwd: path.join(projectRoot, 'packages/web-ui'),
      interpreter: 'none',

      autorestart: true,
      max_restarts: 10,
      min_uptime: '15s',
      restart_delay: 5000,

      out_file: path.join(projectRoot, 'logs/bte-web-out.log'),
      error_file: path.join(projectRoot, 'logs/bte-web-err.log'),
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      env: {
        PORT: String(WEB_PORT),
      },
    },
  ],
};
