/**
 * 我家云即时通讯服务 - 修复版 (Staff消息推送修复)
 */
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const crypto = require('crypto');
const path = require('path');
const mysql = require('mysql2/promise');

const PORT = 22309;
const USER_SERVICE_URL = 'http://127.0.0.1:22307/getUserInfo';

// MySQL连接池
const pool = mysql.createPool({
    host: '47.98.238.209',
    user: 'root',
    password: 'Wojiacloud$2023',
    database: 'visit_system',
    waitForConnections: true,
    connectionLimit: 10
});

// 在线用户
const onlineUsers = new Map();

// ============ 工具函数 ============

function generateId() {
    const ts = Date.now().toString();
    const rnd = Math.random().toString();
    return crypto.createHash('md5').update(ts + rnd).digest('hex');
}

async function getConnection() {
    return await pool.getConnection();
}

// ============ 用户验证 ============

async function verifyUser(token, isdev) {
    try {
        const url = USER_SERVICE_URL + '?access_token=' + encodeURIComponent(token) + '&isdev=' + (isdev || '0');
        const resp = await fetch(url);
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
        return null;
    } catch (e) {
        console.error('verifyUser error:', e.message);
        return null;
    }
}

// ============ 数据库初始化 ============

async function initDatabase() {
    const conn = await getConnection();
    try {
        await conn.execute(`
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                msg_id VARCHAR(64) UNIQUE NOT NULL,
                msg_type VARCHAR(32) DEFAULT 'text',
                content LONGTEXT,
                sender_id VARCHAR(64) NOT NULL,
                sender_name VARCHAR(128),
                sender_type VARCHAR(32) DEFAULT 'user',
                receiver_id VARCHAR(64),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted TINYINT DEFAULT 0,
                INDEX idx_sender (sender_id),
                INDEX idx_receiver (receiver_id),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        `);
        console.log('DB tables ready');
    } finally {
        conn.release();
    }
}

// ============ 消息存储 ============

async function saveMessage(msg) {
    const conn = await getConnection();
    try {
        const msgId = msg.id || generateId();
        const senderType = msg.senderType || 'user';
        await conn.execute(
            'INSERT INTO chat_messages (msg_id, msg_type, content, sender_id, sender_name, sender_type, receiver_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [msgId, msg.msgType || 'text', msg.content || '', msg.senderId, msg.senderName || 'Unknown', senderType, msg.receiverId || null, new Date()]
        );
        return msgId;
    } finally {
        conn.release();
    }
}

async function getMessages(userId, userName, isStaff, limit) {
    const conn = await getConnection();
    try {
        let sql, params;
        const senderType = isStaff ? 'staff' : 'user';
        sql = "SELECT msg_id as id, msg_id, msg_type, content, sender_id as senderId, sender_name as senderName, sender_type, receiver_id as receiverId, timestamp FROM chat_messages WHERE sender_type = ? AND deleted = 0 ORDER BY timestamp DESC LIMIT ?";
        params = [senderType, limit || 50];
        const [rows] = await conn.query(sql, params);
        return rows;
    } finally {
        conn.release();
    }
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
    const userInfo = await verifyUser(token, isdev);
    if (userInfo) return res.json({ success: true, data: userInfo });
    return res.json({ success: false, msg: 'auth failed' });
});

// 获取消息
app.get('/api/messages', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    const limit = Math.max(1, Math.min(100, parseInt(req.query.limit) || 50));
    if (!token) return res.json({ success: false, msg: 'token required' });
    const userInfo = await verifyUser(token, isdev);
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    
    const senderType = req.query.type === 'staff' ? 'staff' : 'user';
    const messages = await getMessages(senderType, limit);
    return res.json({ success: true, data: messages });
});

// 获取在线用户
app.get('/api/online-users', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    if (!token) return res.json({ success: false, msg: 'token required' });
    const userInfo = await verifyUser(token, isdev);
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    const users = [];
    for (const [uid, info] of onlineUsers) {
        if (info.userInfo) {
            users.push({ userId: uid, userName: info.userInfo.userName || 'User' });
        }
    }
    return res.json({ success: true, data: users });
});

// ============ WebSocket ============

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
        userInfo = await verifyUser(token, isdev);
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

// ============ 消息处理 - 修复Staff推送 ============

async function handleChatMessage(msg, senderId, senderInfo, senderType, ws) {
    console.log('handleChatMessage called:', senderId, senderType, msg.content);
    const senderName = senderInfo.userName || senderInfo.empName || senderId;
    const msgSenderType = senderType || 'user';
    
    // 判断是否为员工/staff发送
    const isStaff = senderInfo.empId || senderInfo.staffId || msgSenderType === 'staff';
    
    const msgId = await saveMessage({
        id: msg.id,
        msgType: msg.msgType || 'text',
        content: msg.content,
        senderId,
        senderName,
        senderType: msgSenderType,
        receiverId: msg.receiverId || (isStaff ? null : 'staff')
    });

    const msgData = {
        id: msgId,
        msgType: msg.msgType || 'text',
        content: msg.content,
        senderId,
        senderName,
        senderType: msgSenderType,
        receiverId: msg.receiverId || (isStaff ? null : 'staff'),
        timestamp: new Date().toISOString()
    };

    // Staff 发送消息给用户 - 修复：主动推送给目标用户
    if (isStaff && msg.receiverId && msg.receiverId !== 'staff') {
        const targetUser = onlineUsers.get(msg.receiverId);
        if (targetUser && targetUser.ws && targetUser.ws.readyState === WebSocket.OPEN) {
            targetUser.ws.send(JSON.stringify({ type: 'message', data: msgData }));
            console.log('Staff message sent to user:', msg.receiverId);
        } else {
            console.log('Target user not online:', msg.receiverId);
        }
    }
    // 用户发送消息给 staff
    else if (msg.receiverId === 'staff' || !msg.receiverId) {
        for (const [uid, info] of onlineUsers) {
            if (info.userInfo && (info.userInfo.empId || info.userInfo.staffId)) {
                if (info.ws && info.ws.readyState === WebSocket.OPEN) {
                    info.ws.send(JSON.stringify({ type: 'message', data: msgData }));
                }
            }
        }
    }

    // 发送回给发送者(确认收到)
    ws.send(JSON.stringify({ type: 'message', data: msgData }));
}

// ============ 启动 ============

async function start() {
    try {
        await initDatabase();
        server.listen(PORT, '0.0.0.0', () => {
            console.log('Chat service OK on port ' + PORT);
        });
    } catch (e) {
        console.error('Start error:', e);
        process.exit(1);
    }
}

start();
