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
const USER_SERVICE_URL_STAFF = 'https://gj.wojiacloud.com/users/getUserInfo';
const USER_SERVICE_URL_USER = 'https://wj.wojiacloud.com/h5/users/api/getUserInfo';

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

// 会话状态 (userId -> { status, staffId, endedAt })
const sessionStatus = new Map();

// 用户心跳时间戳 (userId -> lastHeartbeatTime)
const userHeartbeats = new Map();

// 心跳超时时间（1分钟）
const HEARTBEAT_TIMEOUT = 60 * 1000;

// 心跳检查间隔（30秒）
const HEARTBEAT_CHECK_INTERVAL = 30 * 1000;

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
    const userId = req.query.userId || null; // 按用户筛选
    
    if (!token) return res.json({ success: false, msg: 'token required' });
    const userType = (req.query.type === 'staff') ? 'staff' : 'user';
    const userInfo = await verifyUser(token, isdev, userType);
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    
    // 员工端获取所有消息，用户端只获取用户消息
    const senderType = userType === 'staff' ? 'all' : 'user';
    const messages = await chatDao.getMessages({
        senderType,
        limit,
        offset,
        beforeTimestamp: before,
        userId // 按用户筛选
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

// ============ 会话管理 API ============

// 获取会话列表
app.get('/api/sessions', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    if (!token) return res.json({ success: false, msg: 'token required' });
    
    const userType = (req.query.type === 'staff') ? 'staff' : 'user';
    const userInfo = await verifyUser(token, isdev, userType);
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    
    const filter = req.query.filter || 'all'; // 'mine' 或 'all'
    const status = req.query.status || null;  // 'pending', 'processing', 'ended'
    const limit = parseInt(req.query.limit) || 50;
    const offset = parseInt(req.query.offset) || 0;
    
    const staffId = userType === 'staff' ? userInfo.userId : null;
    
    const sessions = await chatDao.getSessions({
        filter,
        staffId,
        status,
        limit,
        offset
    });
    
    // 获取统计信息
    const stats = await chatDao.getSessionStats(staffId);
    
    return res.json({ 
        success: true, 
        data: sessions, 
        stats,
        hasMore: sessions.length === limit 
    });
});

// 获取会话统计
app.get('/api/sessions/stats', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    if (!token) return res.json({ success: false, msg: 'token required' });
    
    const userType = (req.query.type === 'staff') ? 'staff' : 'user';
    const userInfo = await verifyUser(token, isdev, userType);
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    
    const staffId = userType === 'staff' ? userInfo.userId : null;
    const stats = await chatDao.getSessionStats(staffId);
    
    return res.json({ success: true, data: stats });
});

// 接入会话（客服接入待处理的会话）
app.post('/api/sessions/:sessionId/accept', async (req, res) => {
    const token = req.query.access_token;
    const isdev = req.query.isdev || '0';
    if (!token) return res.json({ success: false, msg: 'token required' });
    
    const userInfo = await verifyUser(token, isdev, 'staff');
    if (!userInfo) return res.json({ success: false, msg: 'auth failed' });
    
    const { sessionId } = req.params;
    const staffId = userInfo.userId;
    const staffName = userInfo.userName || userInfo.empName || '客服';
    
    await chatDao.assignStaff(sessionId, staffId, staffName);
    
    return res.json({ success: true, msg: '已接入会话' });
});

// ============ WebSocket 处理 ============

function sendToUser(ws, type, data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type, data }));
    }
}

function broadcast(type, data, excludeWs = null, targetUserType = null) {
    // targetUserType: 如果指定，只发送给该类型的用户
    for (const [key, info] of onlineUsers) {
        if (info.ws !== excludeWs && info.ws.readyState === WebSocket.OPEN) {
            // 如果指定了目标用户类型，只发送给该类型
            if (targetUserType && info.userInfo?.type !== targetUserType) {
                continue;
            }
            info.ws.send(JSON.stringify({ type, data }));
        }
    }
}

// 发送给特定用户
function sendToUserType(userId, type, msgType, data) {
    const key = userId + '_' + type;
    const info = onlineUsers.get(key);
    if (info && info.ws && info.ws.readyState === info.ws.OPEN) {
        info.ws.send(JSON.stringify({ type: msgType, data }));
        return true;
    }
    return false;
}

// ============ 会话状态管理 ============

// 结束会话
async function endSession(userId, staffId) {
    // 更新会话状态
    const session = await chatDao.getSessionByUserId(userId);
    if (session) {
        await chatDao.updateSessionStatus(session.session_id, 'ended', staffId, null);
    }
    
    // 更新内存状态
    const status = sessionStatus.get(userId) || {};
    status.status = 'ended';
    status.endedAt = new Date().toISOString();
    status.endedBy = staffId;
    sessionStatus.set(userId, status);
    
    // 保存系统消息到数据库
    const msgData = {
        id: chatDao.generateId(),
        msgType: 'system',
        content: '会话已结束',
        senderId: 'system',
        senderName: '系统',
        senderType: 'system',
        receiverId: userId,
        sessionId: session?.session_id,
        timestamp: new Date().toISOString()
    };
    await chatDao.saveMessage(msgData);
    
    // 通知用户端
    sendToUserType(userId, 'user', 'session_ended', { userId, staffId });
    
    console.log('Session ended:', userId, 'by:', staffId);
    return true;
}

// 重新开始会话
async function restartSession(userId, staffId) {
    // 更新会话状态
    const session = await chatDao.getSessionByUserId(userId);
    if (session) {
        await chatDao.updateSessionStatus(session.session_id, 'processing', staffId, null);
    }
    
    // 更新内存状态
    const status = sessionStatus.get(userId) || {};
    status.status = 'active';
    status.restartedAt = new Date().toISOString();
    status.restartedBy = staffId;
    sessionStatus.set(userId, status);
    
    // 保存系统消息到数据库
    const msgData = {
        id: chatDao.generateId(),
        msgType: 'system',
        content: '会话已重新开始',
        senderId: 'system',
        senderName: '系统',
        senderType: 'system',
        receiverId: userId,
        sessionId: session?.session_id,
        timestamp: new Date().toISOString()
    };
    await chatDao.saveMessage(msgData);
    
    // 通知用户端
    sendToUserType(userId, 'user', 'session_restarted', { userId, staffId });
    
    console.log('Session restarted:', userId, 'by:', staffId);
    return true;
}

// 转接会话
async function transferSession(userId, fromStaffId, toStaffId) {
    // 更新会话状态
    const session = await chatDao.getSessionByUserId(userId);
    if (session) {
        await chatDao.assignStaff(session.session_id, toStaffId, null);
    }
    
    // 更新内存状态
    const status = sessionStatus.get(userId) || {};
    status.status = 'active';
    status.staffId = toStaffId;
    status.transferredAt = new Date().toISOString();
    status.transferredFrom = fromStaffId;
    sessionStatus.set(userId, status);
    
    // 保存系统消息到数据库
    const msgData = {
        id: chatDao.generateId(),
        msgType: 'system',
        content: '会话已转接',
        senderId: 'system',
        senderName: '系统',
        senderType: 'system',
        receiverId: userId,
        sessionId: session?.session_id,
        timestamp: new Date().toISOString()
    };
    await chatDao.saveMessage(msgData);
    
    // 通知目标客服
    sendToUserType(toStaffId, 'staff', 'session_transferred', { 
        userId, 
        fromStaffId, 
        toStaffId 
    });
    
    // 通知用户端
    sendToUserType(userId, 'user', 'session_transferred', { fromStaffId, toStaffId });
    
    console.log('Session transferred:', userId, 'from:', fromStaffId, 'to:', toStaffId);
    return true;
}

// 获取会话状态
function getSessionStatus(userId) {
    return sessionStatus.get(userId) || { status: 'active' };
}

// 消息处理
async function handleChatMessage(msg, userId, userInfo, senderType, ws) {
    // 确定用户ID和名称
    let targetUserId, targetUserName, staffId, staffName;
    
    if (senderType === 'user') {
        targetUserId = userId;
        targetUserName = userInfo.userName || '用户';
        // 获取或创建会话
        const session = await chatDao.getOrCreateSession(targetUserId, targetUserName);
        staffId = session.staff_id;
        staffName = session.staff_name;
    } else {
        // 员工发送消息
        targetUserId = msg.receiverId;
        targetUserName = msg.receiverName || '用户';
        staffId = userId;
        staffName = userInfo.userName || userInfo.empName || '客服';
    }
    
    // 获取会话
    let session = await chatDao.getSessionByUserId(targetUserId);
    if (!session) {
        session = await chatDao.getOrCreateSession(targetUserId, targetUserName);
    }
    
    // 如果是员工发送消息且会话未分配，分配给该员工
    if (senderType === 'staff' && !session.staff_id) {
        await chatDao.assignStaff(session.session_id, staffId, staffName);
    }
    
    // 如果会话状态是pending，更新为processing
    if (session.status === 'pending' && senderType === 'staff') {
        await chatDao.updateSessionStatus(session.session_id, 'processing', staffId, staffName);
    }
    
    const msgData = {
        id: msg.id || chatDao.generateId(),
        msgType: msg.msgType || msg.type || 'text',
        content: msg.content,
        senderId: userId,
        senderName: userInfo.userName || userInfo.empName || 'User',
        senderType: senderType,
        receiverId: msg.receiverId,
        sessionId: session.session_id,
        timestamp: new Date().toISOString()
    };

    // 保存到数据库
    const msgId = await chatDao.saveMessage(msgData);
    msgData.id = msgId;

    // 更新会话最后消息
    const contentPreview = msg.content.length > 100 ? msg.content.substring(0, 100) + '...' : msg.content;
    await chatDao.updateSessionLastMessage(session.session_id, contentPreview, msgData.timestamp);

    console.log('Message saved:', msgId, 'from:', userId, 'type:', senderType, 'to:', msg.receiverId, 'session:', session.session_id);

    // 发送给自己（确认已发送）
    sendToUser(ws, 'message', msgData);

    // 根据发送者类型路由消息
    if (senderType === 'user') {
        // 用户发送的消息，广播给所有员工端
        broadcast('message', msgData, ws, 'staff');
        console.log('Broadcasted to all staff');
    } else if (senderType === 'staff') {
        // 员工发送的消息，发送给指定的用户
        if (msg.receiverId) {
            const sent = sendToUserType(msg.receiverId, 'user', 'message', msgData);
            console.log('Sent to user:', msg.receiverId, 'result:', sent);
        }
    }
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
    let connectionKey = null; // 使用 userId_type 作为唯一标识

    ws.on('message', (data) => {
        if (!isVerified) {
            messageQueue.push(data);
            return;
        }
        processMessage(data);
    });

    ws.on('close', () => {
        if (connectionKey) {
            onlineUsers.delete(connectionKey);
            console.log('Offline: ' + connectionKey);
        }
        // 注意：不在这里清理心跳时间戳，让心跳检查器来处理超时
    });

    if (token) {
        userInfo = await verifyUser(token, isdev, type);
        if (!userInfo) {
            ws.close(1008, 'Unauthorized');
            return;
        }
        userId = userInfo.userId;
        userInfo.type = type;
        connectionKey = userId + '_' + type; // 组合 key，区分用户端和员工端
    }

    if (!userId) {
        ws.close(1008, 'Unauthorized');
        return;
    }

    isVerified = true;

    onlineUsers.set(connectionKey, { ws, userInfo, userId, connectedAt: new Date() });
    console.log('Online: ' + connectionKey);
    
    // 初始化用户心跳时间戳
    if (type === 'user') {
        userHeartbeats.set(userId, Date.now());
        console.log('Heartbeat initialized for user:', userId);
    }

    ws.send(JSON.stringify({ type: 'welcome', userId, userName: userInfo.userName || userInfo.empName || 'User', userType: type, timestamp: new Date().toISOString() }));

    while (messageQueue.length > 0) {
        processMessage(messageQueue.shift());
    }

    function processMessage(data) {
        console.log('WS message received:', data.toString());
        try {
            const msg = JSON.parse(data);
            const connectionType = userInfo.type || 'user';
            
            if (msg.type === 'chat') {
                // 检查会话是否已结束
                const sessStatus = getSessionStatus(msg.receiverId || userId);
                if (connectionType === 'staff' && sessStatus.status === 'ended') {
                    // 会话已结束，提示客服
                    ws.send(JSON.stringify({ type: 'error', msg: '会话已结束，请重新开始会话' }));
                    return;
                }
                handleChatMessage(msg, userId, userInfo, connectionType, ws);
            } else if (msg.type === 'ping') {
                ws.send(JSON.stringify({ type: 'pong' }));
            } else if (msg.type === 'heartbeat') {
                // 处理心跳消息，更新心跳时间戳
                if (connectionType === 'user') {
                    userHeartbeats.set(userId, Date.now());
                    console.log('Heartbeat received from user:', userId);
                }
                ws.send(JSON.stringify({ type: 'heartbeat_ack' }));
            } else if (msg.type === 'end_session') {
                // 结束会话
                if (connectionType === 'staff' && msg.userId) {
                    endSession(msg.userId, userId);
                    ws.send(JSON.stringify({ type: 'session_ended', data: { userId: msg.userId } }));
                }
            } else if (msg.type === 'restart_session') {
                // 重新开始会话
                if (connectionType === 'staff' && msg.userId) {
                    restartSession(msg.userId, userId);
                    ws.send(JSON.stringify({ type: 'session_restarted', data: { userId: msg.userId } }));
                }
            } else if (msg.type === 'transfer') {
                // 转接会话
                if (connectionType === 'staff' && msg.userId && msg.toStaffId) {
                    transferSession(msg.userId, userId, msg.toStaffId);
                    ws.send(JSON.stringify({ type: 'session_transferred', data: { userId: msg.userId, toStaffId: msg.toStaffId } }));
                }
            }
        } catch (err) {
            console.error('Msg error:', err.message);
            ws.send(JSON.stringify({ type: 'error', msg: err.message }));
        }
    }
});

// ============ 启动 ============

// 心跳超时检查器
async function checkHeartbeatTimeout() {
    const now = Date.now();
    const timeoutUsers = [];
    
    for (const [userId, lastHeartbeat] of userHeartbeats) {
        if (now - lastHeartbeat > HEARTBEAT_TIMEOUT) {
            timeoutUsers.push(userId);
        }
    }
    
    // 处理超时用户
    for (const userId of timeoutUsers) {
        console.log('User heartbeat timeout:', userId);
        
        // 检查是否有活跃会话
        const session = await chatDao.getSessionByUserId(userId);
        if (session && (session.status === 'pending' || session.status === 'processing')) {
            // 结束会话
            await endSession(userId, 'system');
            console.log('Session auto-ended due to heartbeat timeout:', userId, 'session:', session.session_id);
        }
        
        // 清理心跳记录
        userHeartbeats.delete(userId);
    }
}

async function start() {
    try {
        await chatDao.initTable();
        server.listen(PORT, '0.0.0.0', () => {
            console.log('Chat service OK on port ' + PORT);
        });
        
        // 启动心跳超时检查器
        setInterval(checkHeartbeatTimeout, HEARTBEAT_CHECK_INTERVAL);
        console.log('Heartbeat timeout checker started (interval: ' + (HEARTBEAT_CHECK_INTERVAL / 1000) + 's, timeout: ' + (HEARTBEAT_TIMEOUT / 1000) + 's)');
    } catch (e) {
        console.error('Start error:', e);
        process.exit(1);
    }
}

start();
