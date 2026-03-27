/**
 * 我家云即时通讯服务 - DAO 架构版
 * SQL 语句分离到 sql/queries.json 配置文件中
 */
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const mysql = require('mysql2/promise');

// 引入 DAO 层
const ChatDao = require('./ChatDao');

const PORT = 22309;
const USER_SERVICE_URL_LOCAL = 'http://127.0.0.1:22307/getUserInfo';
const USER_SERVICE_URL_STAFF = 'https://gj.wojiacloud.com/getUserInfo';
const USER_SERVICE_URL_USER = 'https://wj.wojiacloud.com/getUserInfo';

// MySQL连接池
const pool = mysql.createPool({
    host: '47.98.238.209',
    user: 'root',
    password: 'Wojiacloud$2023',
    database: 'visit_system',
    waitForConnections: true,
    connectionLimit: 10
});

// 初始化 DAO
const chatDao = new ChatDao(pool);

// 在线用户
const onlineUsers = new Map();

// ============ 工具函数 ============

async function verifyUser(token, isdev, userType = 'user') {
    // 优先使用云端服务，如果失败则回退到本地
    const urls = userType === 'staff' 
        ? [USER_SERVICE_URL_STAFF, USER_SERVICE_URL_LOCAL]
        : [USER_SERVICE_URL_USER, USER_SERVICE_URL_LOCAL];
    
    for (const baseUrl of urls) {
        try {
            console.log('verifyUser: userType=', userType, 'trying:', baseUrl);
            const url = baseUrl + '?access_token=' + encodeURIComponent(token) + '&isdev=' + (isdev || '0');
            const resp = await fetch(url, { signal: AbortSignal.timeout(5000) });
            const data = await resp.json();
            
            if (data && data.success && data.data) {
                const u = data.data;
                return {
                    userId: u.userId || u.id || u.empId || token.substring(0, 32),
                    userName: u.userName || u.empName || u.name || 'User',
                    empName: u.empName || u.name,
                    empId: u.empId,
                    staffId: u.staffId,
                    phone: u.userPhone || u.empPhone
                };
            }
            // 如果是云端失败，继续尝试下一个
            console.log('verifyUser failed, trying next...');
        } catch (e) {
            console.log('verifyUser error:', e.message, 'trying next...');
        }
    }
    return null;
}

// ============ HTTP服务器 ============

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });
app.use(express.static(path.join(__dirname)));

// 获取用户信息
app.get('/api/userinfo', async (req, res) => {
    const token = req.query.access_token || req.query.token;
    const isdev = req.query.isdev || '0';
    if (!token) return res.json({ success: false, msg: 'token required' });
    const userType = (req.query.type === 'staff') ? 'staff' : 'user';
    const userInfo = await verifyUser(token, isdev, userType);
    if (userInfo) return res.json({ success: true, data: userInfo });
    return res.json({ success: false, msg: 'auth failed' });
});

// 获取消息列表 (支持分页)
app.get('/api/messages', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    const limit = Math.max(1, Math.min(100, parseInt(req.query.limit) || 50));
    const offset = parseInt(req.query.offset) || 0;
    const before = req.query.before || null;
    
    if (!token) return res.json({ success: false, msg: 'token required' });
    const userType = (req.query.type === 'staff') ? 'staff' : 'user';
    const userInfo = await verifyUser(token, isdev, userType);
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    
    const senderType = req.query.type === 'staff' ? 'staff' : 'user';
    const messages = await chatDao.getMessages({
        senderType,
        limit,
        offset,
        beforeTimestamp: before
    });
    return res.json({ success: true, data: messages, hasMore: messages.length === limit });
});

// 获取在线用户
app.get('/api/online-users', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    if (!token) return res.json({ success: false, msg: 'token required' });
    const userInfo = await verifyUser(token, isdev, req.query.type || 'user');
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    const users = [];
    for (const [userId, info] of onlineUsers) {
        users.push({ userId, userName: info.userInfo?.userName, type: info.userInfo?.type });
    }
    return res.json({ success: true, data: users });
});

// ============ WebSocket 处理 ============

function sendToUser(ws, type, data) {
    if (ws && ws.readyState === ws.OPEN) {
        ws.send(JSON.stringify({ type, data }));
    }
}

function broadcast(type, data, excludeWs = null) {
    for (const [, info] of onlineUsers) {
        if (info.ws !== excludeWs && info.ws.readyState === info.ws.OPEN) {
            info.ws.send(JSON.stringify({ type, data }));
        }
    }
}

// 消息处理
async function handleChatMessage(msg, userId, userInfo, senderType, ws) {
    const msgData = {
        id: msg.id || chatDao.generateId(),
        msgType: msg.msgType || msg.type || 'text',
        content: msg.content,
        senderId: userId,
        senderName: userInfo.userName || userInfo.empName || 'User',
        senderType: senderType,
        receiverId: msg.receiverId,
        timestamp: new Date().toISOString()
    };

    // 保存到数据库
    const msgId = await chatDao.saveMessage(msgData);
    msgData.id = msgId;

    // 发送给自己
    sendToUser(ws, 'message', msgData);

    // 广播给其他人
    broadcast('message', msgData, ws);
}

// WebSocket 连接
wss.on('connection', async (ws, req) => {
    const url = new URL(req.url, 'http://' + req.headers.host);
    const token = url.searchParams.get('access_token');
    const isdev = url.searchParams.get('isdev') || '0';
    const type = url.searchParams.get('type') || 'user';

    let messageQueue = [];
    let isVerified = false;
    let userId = null;
    let userInfo = null;

    ws.on('message', (data) => {
        if (!isVerified) {
            messageQueue.push(data);
            return;
        }
        processMessage(data);
    });

    ws.on('close', () => {
        if (userId) {
            onlineUsers.delete(userId);
            console.log('Offline: ' + userId);
        }
    });

    if (token) {
        userInfo = await verifyUser(token, isdev, type);
        if (!userInfo) {
            ws.close(1008, 'Unauthorized');
            return;
        }
        userId = userInfo.userId;
        userInfo.type = type;
    }

    if (!userId) {
        ws.close(1008, 'Unauthorized');
        return;
    }

    isVerified = true;

    onlineUsers.set(userId, { ws, userInfo, connectedAt: new Date() });
    console.log('Online: ' + userId + ' (' + type + ')');

    ws.send(JSON.stringify({ type: 'welcome', userId, timestamp: new Date().toISOString() }));

    while (messageQueue.length > 0) {
        processMessage(messageQueue.shift());
    }

    function processMessage(data) {
        console.log('WS message received:', data.toString());
        try {
            const msg = JSON.parse(data);
            const connectionType = userInfo.type || 'user';
            if (msg.type === 'chat') {
                handleChatMessage(msg, userId, userInfo, connectionType, ws);
            } else if (msg.type === 'ping') {
                ws.send(JSON.stringify({ type: 'pong' }));
            }
        } catch (err) {
            console.error('Msg error:', err.message);
            ws.send(JSON.stringify({ type: 'error', msg: err.message }));
        }
    }
});

// ============ 启动 ============

async function start() {
    try {
        await chatDao.initTable();
        server.listen(PORT, '0.0.0.0', () => {
            console.log('Chat service OK on port ' + PORT);
        });
    } catch (e) {
        console.error('Start error:', e);
        process.exit(1);
    }
}

start();
