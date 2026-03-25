/**
 * 我家云即时通讯服务
 * 支持WebSocket即时消息、消息存储
 */
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');

const PORT = 22309;
const HTTP_PORT = 22310;

// 用户服务配置
const USER_SERVICE_URL = 'http://127.0.0.1:22307/getUserInfo';

// 消息存储文件
const MESSAGES_FILE = path.join(__dirname, 'messages.json');
const USERS_FILE = path.join(__dirname, 'users.json');

// 初始化存储文件
function initStorage() {
    if (!fs.existsSync(MESSAGES_FILE)) {
        fs.writeFileSync(MESSAGES_FILE, JSON.stringify([], null, 2));
    }
    if (!fs.existsSync(USERS_FILE)) {
        fs.writeFileSync(USERS_FILE, JSON.stringify({}, null, 2));
    }
}

// 读取消息
function getMessages() {
    try {
        return JSON.parse(fs.readFileSync(MESSAGES_FILE, 'utf-8'));
    } catch (e) {
        return [];
    }
}

// 保存消息
function saveMessages(messages) {
    fs.writeFileSync(MESSAGES_FILE, JSON.stringify(messages, null, 2));
}

// 读取用户
function getUsers() {
    try {
        return JSON.parse(fs.readFileSync(USERS_FILE, 'utf-8'));
    } catch (e) {
        return {};
    }
}

// 保存用户
function saveUsers(users) {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
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

// 初始化存储
initStorage();

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
    const before = req.query.before; // 消息ID，用于分页
    
    if (!token) {
        return res.json({ success: false, msg: 'token不能为空' });
    }
    
    const userInfo = await verifyUser(token, isdev);
    if (!userInfo) {
        return res.json({ success: false, msg: '用户验证失败' });
    }
    
    let messages = getMessages();
    
    // 获取用户ID
    const userId = userInfo.userId || userInfo.empId || userInfo.id;
    const isStaff = userInfo.empId || userInfo.staffId; // 客服有 empId
    
    // 过滤消息
    if (isStaff) {
        // 客服：显示所有用户发给客服的消息，以及客服发送的消息
        messages = messages.filter(m => 
            m.receiverId === 'staff' || 
            m.senderId === userId ||
            m.senderId === isStaff
        );
    } else {
        // 普通用户：显示自己发送/接收的消息
        messages = messages.filter(m => m.senderId === userId || m.receiverId === userId || m.receiverId === 'all');
    }
    
    // 按时间倒序
    messages.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // 分页
    if (before) {
        const beforeIndex = messages.findIndex(m => m.id === before);
        if (beforeIndex > 0) {
            messages = messages.slice(0, beforeIndex);
        }
    }
    
    messages = messages.slice(0, limit);
    
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

// 上传文件
app.post('/api/upload', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    
    if (!token) {
        return res.json({ success: false, msg: 'token不能为空' });
    }
    
    const userInfo = await verifyUser(token, isdev);
    if (!userInfo) {
        return res.json({ success: false, msg: '用户验证失败' });
    }
    
    // 文件处理由前端直接发送base64，这里简单返回成功
    return res.json({ success: true, msg: '上传接口已准备' });
});

// 创建HTTP服务器
const server = http.createServer(app);

// 创建WebSocket服务器
const wss = new WebSocket.Server({ server });

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
                // 查找所有在线客服并通知
                for (const [uid, info] of onlineUsers) {
                    if (info.userInfo && (info.userInfo.empId || info.userInfo.staffId)) {
                        // 这是一个客服账号
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
                    // 处理聊天消息
                    if (!userInfo) {
                        ws.send(JSON.stringify({ type: 'error', msg: '用户未认证' }));
                        return;
                    }
                    
                    const msgData = {
                        id: uuidv4(),
                        type: message.msgType || 'text', // text, image, voice, video
                        content: message.content,
                        senderId: userId,
                        senderName: userInfo.userName || userInfo.empName || userInfo.name,
                        receiverId: message.receiverId || 'all',
                        timestamp: new Date().toISOString()
                    };
                    
                    // 保存消息
                    const messages = getMessages();
                    messages.push(msgData);
                    // 只保留最近1000条消息
                    if (messages.length > 1000) {
                        messages.splice(0, messages.length - 1000);
                    }
                    saveMessages(messages);
                    
                    // 广播消息给所有相关用户
                    broadcast({
                        type: 'message',
                        data: msgData,
                        // 额外信息，用于区分消息类型
                        isToStaff: msgData.receiverId === 'staff'
                    });
                    
                    // 如果是发给客服的消息，也直接推送给在线的客服
                    if (msgData.receiverId === 'staff' || msgData.receiverId === 'all') {
                        for (const [uid, info] of onlineUsers) {
                            if (info.userInfo && (info.userInfo.empId || info.userInfo.staffId)) {
                                // 这是客服
                                info.ws.send(JSON.stringify({
                                    type: 'message',
                                    data: msgData
                                }));
                            }
                        }
                    }
                    break;
                    
                case 'ping':
                    // 心跳
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
            
            // 广播用户离线消息
            broadcast({
                type: 'user_offline',
                userId,
                users: getOnlineUsers()
            });
        }
    });
    
    ws.on('error', (err) => {
        console.error('WebSocket错误:', err);
    });
});

// 获取在线用户列表
function getOnlineUsers() {
    const users = [];
    for (const [userId, info] of onlineUsers) {
        if (info.userInfo) {
            users.push({
                userId,
                userName: info.userInfo.userName || info.userInfo.empName || info.userInfo.name,
                avatar: info.userInfo.avatar || ''
            });
        }
    }
    return users;
}

// 广播消息给所有在线用户
function broadcast(data) {
    const message = JSON.stringify(data);
    for (const [, info] of onlineUsers) {
        if (info.ws.readyState === WebSocket.OPEN) {
            info.ws.send(message);
        }
    }
}

// 定时清理离线用户
setInterval(() => {
    const now = Date.now();
    for (const [userId, info] of onlineUsers) {
        if (now - info.lastTime > 60000) { // 60秒无响应视为离线
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
    console.log(`即时通讯服务已启动: ws://localhost:${PORT}`);
    console.log(`HTTP API: http://localhost:${PORT}`);
    console.log(`WebSocket: ws://localhost:${PORT}`);
});
