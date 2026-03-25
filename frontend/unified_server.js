const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');
const mysql = require('mysql2/promise');

const PORT = 22316;

// 静态文件目录
const VISIT_DIR = path.join(__dirname, 'visit');
const EQUIPMENT_DIR = path.join(__dirname, 'equipment');
const CHAT_DIR = path.join(__dirname, '..', 'chat');

// 用户服务配置
const USER_SERVICE_URL = 'http://127.0.0.1:22307/getUserInfo';

// 数据库配置
const DB_CONFIG = {
    host: '47.98.238.209',
    port: 3306,
    user: 'root',
    password: 'Wojiacloud$2023',
    database: 'visit_system',
    charset: 'utf8mb4'
};

let pool = null;

// 数据库初始化状态
let dbReady = false;

// 初始化数据库连接和表
async function initDatabase() {
    try {
        pool = mysql.createPool(DB_CONFIG);
        
        // 测试连接
        const conn = await pool.getConnection();
        console.log('✅ 数据库连接成功');
        
        // 创建聊天消息表
        await conn.execute(`
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                msg_id VARCHAR(64) NOT NULL COMMENT '消息ID',
                msg_type VARCHAR(32) DEFAULT 'text' COMMENT '消息类型: text/image/voice/video',
                content TEXT NOT NULL COMMENT '消息内容',
                sender_id VARCHAR(64) NOT NULL COMMENT '发送者ID',
                sender_name VARCHAR(128) COMMENT '发送者名称',
                sender_type VARCHAR(16) COMMENT '发送者类型: user/staff',
                receiver_id VARCHAR(64) NOT NULL COMMENT '接收者ID',
                receiver_name VARCHAR(128) COMMENT '接收者名称',
                receiver_type VARCHAR(16) COMMENT '接收者类型: user/staff',
                session_id VARCHAR(64) COMMENT '会话ID',
                timestamp DATETIME NOT NULL COMMENT '消息时间',
                
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted TINYINT DEFAULT 0 COMMENT '删除状态 0正常 1已删除',
                
                INDEX idx_sender_id (sender_id),
                INDEX idx_receiver_id (receiver_id),
                INDEX idx_session_id (session_id),
                INDEX idx_timestamp (timestamp),
                INDEX idx_deleted (deleted)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='聊天消息表'
        `);
        
        conn.release();
        dbReady = true;
        console.log('✅ chat_messages表已创建');
    } catch (e) {
        console.error('❌ 数据库初始化失败:', e.message);
        pool = null;
        dbReady = false;
    }
}
initDatabase();

// 消息存储函数 - 使用数据库
async function getMessages(userId, limit = 50) {
    if (pool) {
        try {
            const safeLimit = parseInt(limit) || 50;
            const [rows] = await pool.query(
                `SELECT * FROM chat_messages 
                 WHERE deleted = 0 AND (sender_id = ? OR receiver_id = ?) 
                 ORDER BY timestamp DESC LIMIT ?`,
                [userId, userId, safeLimit]
            );
            return rows.reverse(); // 按时间正序返回
        } catch (e) {
            console.error('获取消息失败:', e);
            return [];
        }
    }
    return [];
}

// 转换时间戳为MySQL格式
function toMysqlTime(isoString) {
    const date = new Date(isoString);
    return date.toISOString().slice(0, 19).replace('T', ' ');
}

async function saveMessage(msgData, senderType = 'user', receiverType = 'staff') {
    console.log('保存消息: senderType=' + senderType + ', receiverType=' + receiverType);
    if (dbReady && pool) {
        try {
            const mysqlTime = toMysqlTime(msgData.timestamp);
            await pool.execute(
                `INSERT INTO chat_messages (msg_id, msg_type, content, sender_id, sender_name, sender_type, receiver_id, receiver_name, receiver_type, session_id, timestamp) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    msgData.id,
                    msgData.type || 'text',
                    msgData.content,
                    msgData.senderId,
                    msgData.senderName || '',
                    senderType,
                    msgData.receiverId,
                    '',
                    receiverType,
                    msgData.senderId + '_' + msgData.receiverId,
                    mysqlTime
                ]
            );
            console.log('消息已保存到数据库');
        } catch (e) {
            console.error('保存消息失败:', e);
        }
    } else {
        console.log('数据库未就绪，使用内存存储');
    }
}

// 备用内存存储
const memoryMessages = [];
function getMessagesMem(userId, limit = 50) {
    return memoryMessages.filter(m => m.senderId === userId || m.receiverId === userId)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, limit).reverse();
}
function saveMessageMem(msgData) {
    memoryMessages.push(msgData);
    if (memoryMessages.length > 1000) memoryMessages.shift();
}

// 验证用户
async function verifyUser(token, isdev = '0') {
    try {
        const url = `${USER_SERVICE_URL}?access_token=${token}&isdev=${isdev}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.success && data.data) return data.data;
        return null;
    } catch (e) { return null; }
}

// 处理用户信息API请求
function handleUserInfo(res, token, isdev) {
    if (!token) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, msg: 'token不能为空' }));
        return;
    }
    
    verifyUser(token, isdev).then(userInfo => {
        if (userInfo) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true, data: userInfo }));
        } else {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: false, msg: '用户验证失败' }));
        }
    }).catch(e => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, msg: '验证失败: ' + e.message }));
    });
}

// 处理获取消息API请求
async function handleMessages(res, token, isdev, limit) {
    if (!token) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, msg: 'token不能为空' }));
        return;
    }
    
    verifyUser(token, isdev).then(async userInfo => {
        if (!userInfo) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: false, msg: '用户验证失败' }));
            return;
        }
        
        const userId = userInfo.userId || userInfo.empId || userInfo.id;
        let messages = await getMessages(userId, limit);
        
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, data: messages }));
    }).catch(e => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, msg: '获取消息失败: ' + e.message }));
    });
}

const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    let filePath = req.url;
    
    // 处理API请求（先解析URL）
    const urlObj = new URL(filePath, `http://${req.headers.host}`);
    const pathname = urlObj.pathname;
    
    // API请求 - 转发到用户服务
    if (pathname === '/api/userinfo') {
        const token = urlObj.searchParams.get('access_token') || urlObj.searchParams.get('token');
        const isdev = urlObj.searchParams.get('isdev') || '0';
        handleUserInfo(res, token, isdev);
        return;
    }
    
    // 获取历史消息
    if (pathname === '/api/messages') {
        const token = urlObj.searchParams.get('access_token') || urlObj.searchParams.get('token');
        const isdev = urlObj.searchParams.get('isdev') || '0';
        const limit = parseInt(urlObj.searchParams.get('limit')) || 50;
        handleMessages(res, token, isdev, limit);
        return;
    }
    
    let baseDir = VISIT_DIR;

    // 处理 /equipment/ 前缀
    if (filePath.startsWith('/equipment/') || filePath.startsWith('/equipment')) {
        baseDir = EQUIPMENT_DIR;
        if (filePath.startsWith('/equipment/')) {
            filePath = filePath.substring('/equipment/'.length);
        } else if (filePath === '/equipment') {
            filePath = 'report.html';
        }
    } else if (filePath.startsWith('/chat/') || filePath.startsWith('/chat') || filePath === 'chat.html') {
        baseDir = CHAT_DIR;
        // 先去除查询参数
        const queryIndex = filePath.indexOf('?');
        if (queryIndex > -1) {
            filePath = filePath.substring(0, queryIndex);
        }
        if (filePath.startsWith('/chat/')) {
            filePath = filePath.substring('/chat/'.length);
        } else if (filePath === '/chat' || filePath === '/chat?') {
            // 默认打开用户端
            filePath = 'user.html';
        } else if (filePath === 'chat.html') {
            filePath = 'index.html';
        }
    } else if (filePath.startsWith('/visit/') || filePath.startsWith('/visit')) {
        if (filePath.startsWith('/visit/')) {
            filePath = filePath.substring('/visit/'.length);
        } else if (filePath === '/visit') {
            filePath = 'index.html';
        }
    }

    // 去掉前导 /
    if (filePath.startsWith('/')) {
        filePath = filePath.substring(1);
    }

    // 默认文件
    if (filePath === '' || filePath === '/') {
        filePath = 'index.html';
    }

    // 安全检查
    if (filePath.includes('..')) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
    }

    const fullPath = path.join(baseDir, filePath);
    const ext = path.extname(fullPath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(fullPath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404);
                res.end('Not Found: ' + filePath);
            } else {
                res.writeHead(500);
                res.end('Server Error');
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content);
        }
    });
});

// WebSocket 服务
const wss = new WebSocket.Server({ server, path: '/ws' });

// 在线用户和员工
const onlineUsers = new Map();    // userId -> { ws, userInfo, type, lastTime }
const onlineStaff = new Map();     // staffId -> { ws, userInfo, lastTime, assignedUsers: Set }
const userToStaff = new Map();    // userId -> staffId 用户分配的客服

wss.on('connection', async (ws, req) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const token = url.searchParams.get('access_token');
    const isdev = url.searchParams.get('isdev') || '0';
    const connType = url.searchParams.get('type') || 'user'; // user 或 staff
    
    let userInfo = null;
    let userId = null;
    
    if (token) {
        userInfo = await verifyUser(token, isdev);
        if (userInfo) {
            userId = userInfo.userId || userInfo.empId || userInfo.id;
            
            if (connType === 'staff') {
                // 员工端
                onlineStaff.set(userId, { ws, userInfo, lastTime: Date.now(), assignedUsers: new Set() });
                console.log(`客服上线: ${userId} (${userInfo.userName || userInfo.empName})`);
                console.log(`当前在线客服列表:`, Array.from(onlineStaff.keys()));
                
                ws.send(JSON.stringify({
                    type: 'welcome',
                    msg: '客服端连接成功',
                    userId,
                    userName: userInfo.userName || userInfo.empName || userInfo.name
                }));
            } else {
                // 用户端
                onlineUsers.set(userId, { ws, userInfo, type: 'user', lastTime: Date.now() });
                console.log(`用户上线: ${userId} (${userInfo.userName || userInfo.empName})`);
                console.log(`当前在线用户:`, Array.from(onlineUsers.keys()));
                console.log(`当前在线客服:`, Array.from(onlineStaff.keys()));
                
                // 自动分配客服
                const staff = assignStaff(userId, userInfo);
                console.log(`分配客服结果:`, staff);
                
                ws.send(JSON.stringify({
                    type: 'welcome',
                    msg: '连接成功',
                    userId,
                    userName: userInfo.userName || userInfo.empName || userInfo.name,
                    assigned: staff ? true : false,
                    staffId: staff?.staffId,
                    staffName: staff?.staffName
                }));
            }
        }
    }
    
    ws.on('message', async (data) => {
        try {
            const message = JSON.parse(data.toString());
            
            if (message.type === 'chat' && userInfo) {
                const msgData = {
                    id: uuidv4(),
                    type: message.msgType || 'text',
                    content: message.content,
                    senderId: userId,
                    senderName: userInfo.userName || userInfo.empName || userInfo.name,
                    receiverId: message.receiverId,
                    timestamp: new Date().toISOString()
                };
                
                // 根据发送者类型推送给不同的人并保存消息
                const senderIsUser = onlineUsers.has(userId);
                
                if (senderIsUser) {
                    // 用户发的消息 -> 推送给分配的客服
                    const staffId = userToStaff.get(userId);
                    console.log(`用户 ${userId} 发送消息，分配的客服: ${staffId}`);
                    console.log(`在线客服列表:`, Array.from(onlineStaff.keys()));
                    
                    // 保存消息
                    await saveMessage(msgData, 'user', 'staff');
                    
                    if (staffId) {
                        const staff = onlineStaff.get(staffId);
                        console.log(`客服 ${staffId} 连接状态:`, staff ? staff.ws.readyState : '不存在');
                        if (staff && staff.ws.readyState === WebSocket.OPEN) {
                            staff.ws.send(JSON.stringify({
                                type: 'message',
                                data: msgData
                            }));
                            console.log(`消息已推送给客服 ${staffId}`);
                            // 通知员工新会话
                            if (!staff.assignedUsers.has(userId)) {
                                staff.assignedUsers.add(userId);
                                staff.ws.send(JSON.stringify({
                                    type: 'new_session',
                                    userId: userId,
                                    userName: userInfo.userName || userInfo.empName || userInfo.name
                                }));
                                console.log(`已发送新会话通知给客服 ${staffId}`);
                            }
                        }
                    }
                } else {
                    // 客服发的消息 -> 推送给指定用户
                    const targetUserId = message.receiverId;
                    const targetUser = onlineUsers.get(targetUserId);
                    
                    // 保存消息
                    await saveMessage(msgData, 'staff', 'user');
                    
                    if (targetUser && targetUser.ws.readyState === WebSocket.OPEN) {
                        targetUser.ws.send(JSON.stringify({
                            type: 'message',
                            data: msgData
                        }));
                    }
                }
            } 
            else if (message.type === 'ping' && userId) {
                if (onlineUsers.has(userId)) {
                    onlineUsers.get(userId).lastTime = Date.now();
                }
                if (onlineStaff.has(userId)) {
                    onlineStaff.get(userId).lastTime = Date.now();
                }
                ws.send(JSON.stringify({ type: 'pong' }));
            }
        } catch (e) { console.error('消息处理错误:', e); }
    });
    
    ws.on('close', () => {
        if (userId) {
            if (onlineUsers.has(userId)) {
                // 用户离线
                onlineUsers.delete(userId);
                const staffId = userToStaff.get(userId);
                if (staffId) {
                    userToStaff.delete(userId);
                    const staff = onlineStaff.get(staffId);
                    if (staff) {
                        staff.assignedUsers.delete(userId);
                        staff.ws.send(JSON.stringify({
                            type: 'user_offline',
                            userId: userId
                        }));
                    }
                }
            }
            if (onlineStaff.has(userId)) {
                // 客服离线
                const staff = onlineStaff.get(userId);
                onlineStaff.delete(userId);
                
                // 通知分配给该客服的用户
                if (staff.assignedUsers) {
                    staff.assignedUsers.forEach(assignedUserId => {
                        userToStaff.delete(assignedUserId);
                        const user = onlineUsers.get(assignedUserId);
                        if (user) {
                            user.ws.send(JSON.stringify({
                                type: 'staff_offline',
                                staffId: userId
                            }));
                        }
                    });
                }
            }
        }
    });
});

// 分配客服
function assignStaff(userId, userInfo) {
    console.log('assignStaff被调用，用户:', userId, '在线客服数:', onlineStaff.size);
    
    // 找在线且分配用户最少的客服
    let minUsers = Infinity;
    let bestStaff = null;
    
    for (const [staffId, staff] of onlineStaff) {
        const userCount = staff.assignedUsers ? staff.assignedUsers.size : 0;
        console.log('客服:', staffId, '当前用户数:', userCount);
        if (userCount < minUsers) {
            minUsers = userCount;
            bestStaff = { staffId, staff };
        }
    }
    
    if (bestStaff) {
        console.log('分配客服:', bestStaff.staffId);
        userToStaff.set(userId, bestStaff.staffId);
        bestStaff.staff.assignedUsers.add(userId);
        
        // 通知客服有新用户
        if (bestStaff.staff.ws.readyState === WebSocket.OPEN) {
            bestStaff.staff.ws.send(JSON.stringify({
                type: 'new_session',
                userId: userId,
                userName: userInfo.userName || userInfo.empName || userInfo.name
            }));
            console.log('已发送new_session给客服');
        }
        
        // 通知用户已分配
        const user = onlineUsers.get(userId);
        if (user && user.ws.readyState === WebSocket.OPEN) {
            user.ws.send(JSON.stringify({
                type: 'assigned',
                staffId: bestStaff.staffId,
                staffName: bestStaff.staff.userInfo.userName || bestStaff.staff.userInfo.empName
            }));
        }
        
        return { staffId: bestStaff.staffId, staffName: bestStaff.staff.userInfo.userName || bestStaff.staff.userInfo.empName };
    }
    
    return null;
}

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

function broadcast(data) {
    const msg = JSON.stringify(data);
    for (const [, info] of onlineUsers) {
        if (info.ws.readyState === WebSocket.OPEN) {
            info.ws.send(msg);
        }
    }
}

server.listen(PORT, '0.0.0.0', () => {
    console.log(`统一服务已启动: http://localhost:${PORT}`);
    console.log(`Visit: http://localhost:${PORT}/visit/`);
    console.log(`Equipment: http://localhost:${PORT}/equipment/`);
    console.log(`Chat: http://localhost:${PORT}/chat/`);
    console.log(`WebSocket: ws://localhost:${PORT}/ws`);
});
