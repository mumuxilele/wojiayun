module.exports = {
  apps: [
    {
      name: 'wojiayun-backend',
      script: '/www/wwwroot/wojiayun/backend/app.py',
      interpreter: '/www/wwwroot/wojiayun/venv/bin/python',
      cwd: '/www/wwwroot/wojiayun/backend',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_file: '/var/log/pm2/wojiayun-backend.log',
      out_file: '/var/log/pm2/wojiayun-backend-out.log',
      error_file: '/var/log/pm2/wojiayun-backend-error.log',
      time: true
    },
    {
      name: 'wojiayun-business',
      script: '/www/wwwroot/wojiayun/business_app.py',
      interpreter: '/www/wwwroot/wojiayun/venv/bin/python',
      cwd: '/www/wwwroot/wojiayun',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_file: '/var/log/pm2/wojiayun-business.log',
      out_file: '/var/log/pm2/wojiayun-business-out.log',
      error_file: '/var/log/pm2/wojiayun-business-error.log',
      time: true
    },
    {
      name: 'wojiayun-frontend',
      script: '/www/wwwroot/wojiayun/frontend/unified_server.js',
      cwd: '/www/wwwroot/wojiayun/frontend',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production'
      },
      log_file: '/var/log/pm2/wojiayun-frontend.log',
      out_file: '/var/log/pm2/wojiayun-frontend-out.log',
      error_file: '/var/log/pm2/wojiayun-frontend-error.log',
      time: true
    },
    {
      name: 'wojiayun-node-service',
      script: '/www/wwwroot/wojiayun/node-service/app.js',
      cwd: '/www/wwwroot/wojiayun/node-service',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        NODE_ENV: 'production'
      },
      log_file: '/var/log/pm2/wojiayun-node-service.log',
      out_file: '/var/log/pm2/wojiayun-node-service-out.log',
      error_file: '/var/log/pm2/wojiayun-node-service-error.log',
      time: true
    },
    {
      name: 'wojiayun-chat',
      script: '/www/wwwroot/wojiayun/chat/app.js',
      cwd: '/www/wwwroot/wojiayun/chat',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production'
      },
      log_file: '/var/log/pm2/wojiayun-chat.log',
      out_file: '/var/log/pm2/wojiayun-chat-out.log',
      error_file: '/var/log/pm2/wojiayun-chat-error.log',
      time: true
    }
  ]
};
