module.exports = {
  apps: [
    // 走访台账后端 - 端口 22306
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
    // 统一前端 + API代理 + WebSocket聊天 - 端口 22316
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
    // 用户服务代理 - 端口 22307
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
    // 聊天服务 - 端口 22309
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
    },
    // 用户端 H5 - 端口 22311
    {
      name: 'wojiayun-userH5',
      script: '/www/wwwroot/wojiayun/business-userH5/app.py',
      interpreter: '/www/wwwroot/wojiayun/venv/bin/python',
      cwd: '/www/wwwroot/wojiayun/business-userH5',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_file: '/var/log/pm2/wojiayun-userH5.log',
      out_file: '/var/log/pm2/wojiayun-userH5-out.log',
      error_file: '/var/log/pm2/wojiayun-userH5-error.log',
      time: true
    },
    // 员工端 H5 - 端口 22312
    {
      name: 'wojiayun-staffH5',
      script: '/www/wwwroot/wojiayun/business-staffH5/app.py',
      interpreter: '/www/wwwroot/wojiayun/venv/bin/python',
      cwd: '/www/wwwroot/wojiayun/business-staffH5',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_file: '/var/log/pm2/wojiayun-staffH5.log',
      out_file: '/var/log/pm2/wojiayun-staffH5-out.log',
      error_file: '/var/log/pm2/wojiayun-staffH5-error.log',
      time: true
    },
    // 管理后台 - 端口 22313
    {
      name: 'wojiayun-admin',
      script: '/www/wwwroot/wojiayun/business-admin/app.py',
      interpreter: '/www/wwwroot/wojiayun/venv/bin/python',
      cwd: '/www/wwwroot/wojiayun/business-admin',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_file: '/var/log/pm2/wojiayun-admin.log',
      out_file: '/var/log/pm2/wojiayun-admin-out.log',
      error_file: '/var/log/pm2/wojiayun-admin-error.log',
      time: true
    }
  ]
};
