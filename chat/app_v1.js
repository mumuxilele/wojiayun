/**
 * 我家云即时通讯服务
 * 支持WebSocket即时消息、MySQL数据库存储
 */
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const crypto = require('crypto');
const mysql = require('mysql2/promise');
const path = require('path');

const PORT = 22309;

// 用户服务配置
const USER_SERVICE_URL = 'http://127.0.0.1:22307/getUserInfo';

// 数据库配置
const dbConfig = {
    host: '47.98.238.209',
    port: 3306,
    user: 'root',
    password: 'Wojiacloud$2023',
    database: 'visit_system',
    waitForConnections: true,
    connectionLimit: 10
};

// 创建数据库连接池
const pool = mysql.createPool(dbConfig);

// 生成32位MD5 ID
function generateId() {
    const timestamp = Date.now().toString();
    const random = Math.random().toString();
    return crypto.createHash('md5').update(timestamp + random).digest('hex');
}

// 初始化数据库表
async function initDatabase() {
    try {
        const conn = await pool.getConnection();
        // 表已存在，只需验证连接
        await conn.execute('SELECT 1');
        conn.release();
        console.log('数据库连接成功');
    } catch (e) {
        console.error('数据库连接失败:', e);
    }
}

// 保存消息到数据库
async function saveMessage(msgData) {
    try {
        const conn = await pool.getConnection();
        await conn.execute(
            'INSERT INTO chat_messages (msg_id, msg_type, content, sender_id, sender_name, receiver_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
            [msgData.id, msgData.type || 'text', msgData.content, msgData.senderId, msgData.senderName, msgData.receiverId, msgData.timestamp]
        );
        conn.release();
        return true;
    } catch (e) {
        console.error('保存消息失败:', e);
        return false;
    }
}

// 获取消息历史
async function getMessages(userId, isStaff, limit = 50) {
    try {
        const conn = await pool.getConnection();
        let rows;
        
        if (isStaff) {
            // 客服：显示所有发给客服的消息，以及客服发送的消息
            [rows] = await conn.execute(
                `SELECT * FROM chat_messages WHERE receiver_id = 'staff' OR sender_id = ? ORDER BY timestamp DESC LIMIT ?`,
                [userId, limit]
            );
        } else {
            // 普通用户：显示自己发送/接收的消息
            [rows] = await conn.execute(
                `SELECT * FROM chat_messages WHERE sender_id = ? OR receiver_id = ? OR receiver_id = 'all' ORDER BY timestamp DESC LIMIT ?`,
                [userId, userId, limit]
            );
        }
        
        conn.release();
        return rows.map(r => ({
            id: r.msg_id,
            type: r.msg_type,
            content: r.content,
            senderId: r.sender_id,
            senderName: r.sender_name,
            receiverId: r.receiver_id,
            timestamp: r.timestamp instanceof Date ? r.timestamp.toISOString() : r.timestamp
        }));
    } catch (e) {
        console.error('获取消息失败:', e);
        return [];
    }
}

// 验证用户
async function verifyUser(token, isdev = '0') {
    try {
        const url = `${USER_SERVICE_URL}?access_token=${token}&isdev=${isdev}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.success && data.data) {
            return data.data;
        }
        return null;
    } catch (e) {
        console.error('验证用户失败:', e);
        return null;
    }
}

// 初始化数据库
initDatabase();

// 创建Express应用
const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(express.static(__dirname));

// CORS
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') {
        res.send(200);
    } else {
        next();
    }
});

// 用户列表 (内存)
const onlineUsers = new Map(); // userId -> { ws, userInfo, lastTime }

// HTTP API

// 获取用户信息
app.get('/api/userinfo', async (req, res) => {
    const token = req.query.access_token || req.query.token;
    const isdev = req.query.isdev || '0';
    
    if (!token) {
        return res.json({ success: false, msg: 'token不能为空' });
    }
    
    const userInfo = await verifyUser(token, isdev);
    if (userInfo) {
        return res.json({ success: true, data: userInfo });
    }
    return res.json({ success: false, msg: '用户验证失败' });
});

// 获取历史消息
app.get('/api/messages', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    const limit = parseInt(req.query.limit) || 50;
    
    if (!token) {
        return res.json({ success: false, msg: 'token不能为空' });
    }
    
    const userInfo = await verifyUser(token, isdev);
    if (!userInfo) {
        return res.json({ success: false, msg: '用户验证失败' });
    }
    
    const userId = userInfo.userId || userInfo.empId || userInfo.id;
    const isStaff = userInfo.empId || userInfo.staffId;
    
    const messages = await getMessages(userId, isStaff, limit);
    
    return res.json({ success: true, data: messages });
});

// 获取在线用户列表
app.get('/api/online-users', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    
    if (!token) {
        return res.json({ success: false, msg: 'token不能为空' });
    }
    
    const userInfo = await verifyUser(token, isdev);
    if (!userInfo) {
        return res.json({ success: false, msg: '用户验证失败' });
    }
    
    const users = [];
    for (const [userId, info] of onlineUsers) {
        if (info.userInfo) {
            users.push({
                userId,
                userName: info.userInfo.userName || info.userInfo.empName || info.userInfo.name,
                avatar: info.userInfo.avatar || '',
                lastTime: info.lastTime
            });
        }
    }
    
    return res.json({ success: true, data: users });
});

// 创建HTTP服务器
const server = http.createServer(app);

// 创建WebSocket服务器
const wss = new WebSocket.Server({ server });

// 广播消息给所有在线用户
function broadcast(data) {
    const message = JSON.stringify(data);
    for (const [, info] of onlineUsers) {
        if (info.ws.readyState === WebSocket.OPEN) {
            info.ws.send(message);
        }
    }
}

// 获取在线用户列表
function getOnlineUsers() {
    const users = [];
    for (const [userId, info] of onlineUsers) {
        if (info.userInfo) {
            users.push({
                userId,
                userName: info.userInfo.userName || info.userInfo.empName || info.userInfo.name
            });
        }
    }
    return users;
}

// WebSocket连接处理
wss.on('connection', async (ws, req) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const token = url.searchParams.get('access_token');
    const isdev = url.searchParams.get('isdev') || '0';
    
    let userInfo = null;
    let userId = null;
    
    // 验证用户
    if (token) {
        userInfo = await verifyUser(token, isdev);
        if (userInfo) {
            userId = userInfo.userId || userInfo.empId || userInfo.id;
            onlineUsers.set(userId, { ws, userInfo, lastTime: Date.now() });
            console.log(`用户上线: ${userId} (${userInfo.userName || userInfo.empName})`);
            
            // 广播用户上线消息
            broadcast({
                type: 'user_online',
                userId,
                userName: userInfo.userName || userInfo.empName || userInfo.name,
                users: getOnlineUsers()
            });
            
            // 如果是在线的用户（非客服），通知所有客服有新会话
            if (!userInfo.empId && !userInfo.staffId) {
                for (const [uid, info] of onlineUsers) {
                    if (info.userInfo && (info.userInfo.empId || info.userInfo.staffId)) {
                        info.ws.send(JSON.stringify({
                            type: 'new_session',
                            userId: userId,
                            userName: userInfo.userName || userInfo.name || '用户',
                            users: getOnlineUsers()
                        }));
                    }
                }
            }
        }
    }
    
    // 发送欢迎消息
    if (userInfo) {
        ws.send(JSON.stringify({
            type: 'welcome',
            msg: '连接成功',
            userId,
            userName: userInfo.userName || userInfo.empName || userInfo.name,
            users: getOnlineUsers()
        }));
    } else {
        ws.send(JSON.stringify({
            type: 'error',
            msg: '用户验证失败，请检查token'
        }));
    }
    
    // 消息处理
    ws.on('message', async (data) => {
        try {
            const message = JSON.parse(data.toString());
            console.log('收到消息:', message.type);
            
            switch (message.type) {
                case 'chat':
                    if (!userInfo) {
                        ws.send(JSON.stringify({ type: 'error', msg: '用户未认证' }));
                        return;
                    }
                    
                    const msgData = {
                        id: generateId(),
                        type: message.msgType || 'text',
                        content: message.content,
                        senderId: userId,
                        senderName: userInfo.userName || userInfo.empName || userInfo.name,
                        receiverId: message.receiverId || 'all',
                        timestamp: new Date().toISOString()
                    };
                    
                    // 保存消息到数据库
                    await saveMessage(msgData);
                    
                    // 广播消息
                    broadcast({
                        type: 'message',
                        data: msgData,
                        isToStaff: msgData.receiverId === 'staff'
                    });
                    
                    // 如果是发给客服的消息，直接推送给在线的客服
                    if (msgData.receiverId === 'staff' || msgData.receiverId === 'all') {
                        for (const [uid, info] of onlineUsers) {
                            if (info.userInfo && (info.userInfo.empId || info.userInfo.staffId)) {
                                info.ws.send(JSON.stringify({
                                    type: 'message',
                                    data: msgData
                                }));
                            }
                        }
                    }
                    break;
                    
                case 'ping':
                    if (userId) {
                        const user = onlineUsers.get(userId);
                        if (user) {
                            user.lastTime = Date.now();
                        }
                    }
                    ws.send(JSON.stringify({ type: 'pong' }));
                    break;
                    
                default:
                    console.log('未知消息类型:', message.type);
            }
        } catch (e) {
            console.error('处理消息失败:', e);
        }
    });
    
    // 断开连接
    ws.on('close', () => {
        if (userId) {
            onlineUsers.delete(userId);
            console.log(`用户离线: ${userId}`);
            
            broadcast({
                type: 'user_offline',
                userId,
                users: getOnlineUsers()
            });
        }
    });
});

// 定时清理离线用户
setInterval(() => {
    const now = Date.now();
    for (const [userId, info] of onlineUsers) {
        if (now - info.lastTime > 60000) {
            onlineUsers.delete(userId);
            console.log(`用户超时离线: ${userId}`);
            broadcast({
                type: 'user_offline',
                userId,
                users: getOnlineUsers()
            });
        }
    }
}, 30000);

// 启动服务器
server.listen(PORT, '0.0.0.0', () => {
    console.log(`========================================`);
    console.log(`  即时通讯服务已启动 (MySQL数据库存储)`);
    console.log(`  端口: ${PORT}`);
    console.log(`  WebSocket: ws://47.98.238.209:${PORT}`);
    console.log(`========================================`);
});
