/**
 * 我家云即时通讯服务 - 增强版
 * 支持消息已读/撤回/引用/搜索/群聊等高级功能
 */
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

const PORT = 22309;

// MySQL 连接池
const pool = mysql.createPool({
    host: '47.98.238.209',
    user: 'root',
    password: 'Wojiacloud$2023',
    database: 'visit_system',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

// ============ 数据结构 ============

// 在线用户 Map: userId -> { ws, userInfo, status }
const onlineUsers = new Map();

// 消息缓存 Map: msgId -> messageData
const messageCache = new Map();

// 群聊 Map: groupId -> { name, members: Set, createdAt }
const groups = new Map();

// 消息已读状态 Map: msgId -> Set<userId>
const messageReadStatus = new Map();

// ============ 工具函数 ============

function generateId() {
    const timestamp = Date.now().toString();
    const random = Math.random().toString();
    return crypto.createHash('md5').update(timestamp + random).digest('hex');
}

function generateGroupId() {
    return 'group_' + generateId();
}

async function getConnection() {
    return await pool.getConnection();
}

// ============ 数据库操作 ============

async function initDatabase() {
    const conn = await getConnection();
    try {
        // 创建消息表（如果不存在）
        await conn.execute(`
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                msg_id VARCHAR(64) UNIQUE NOT NULL,
                msg_type VARCHAR(32) DEFAULT 'text',
                content LONGTEXT,
                sender_id VARCHAR(64) NOT NULL,
                sender_name VARCHAR(128),
                receiver_id VARCHAR(64) NOT NULL,
                receiver_name VARCHAR(128),
                session_id VARCHAR(64),
                group_id VARCHAR(64),
                reply_to_msg_id VARCHAR(64),
                is_recalled TINYINT DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted TINYINT DEFAULT 0,
                INDEX idx_sender (sender_id),
                INDEX idx_receiver (receiver_id),
                INDEX idx_session (session_id),
                INDEX idx_group (group_id),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        `);

        // 创建消息已读表
        await conn.execute(`
            CREATE TABLE IF NOT EXISTS chat_message_reads (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                msg_id VARCHAR(64) NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_read (msg_id, user_id),
                INDEX idx_msg (msg_id),
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        `);

        // 创建群聊表
        await conn.execute(`
            CREATE TABLE IF NOT EXISTS chat_groups (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                group_id VARCHAR(64) UNIQUE NOT NULL,
                group_name VARCHAR(100),
                creator_id VARCHAR(64),
                members JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted TINYINT DEFAULT 0,
                INDEX idx_group (group_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        `);

        console.log('数据库表初始化完成');
    } finally {
        conn.release();
    }
}

async function saveMessage(msgData) {
    const conn = await getConnection();
    try {
        const msgId = msgData.id || generateId();
        
        await conn.execute(`
            INSERT INTO chat_messages 
            (msg_id, msg_type, content, sender_id, sender_name, receiver_id, receiver_name, 
             session_id, group_id, reply_to_msg_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [
            msgId,
            msgData.msgType || 'text',
            msgData.content,
            msgData.senderId,
            msgData.senderName,
            msgData.receiverId,
            msgData.receiverName,
            msgData.sessionId,
            msgData.groupId,
            msgData.replyToMsgId,
            new Date()
        ]);

        // 缓存消息
        messageCache.set(msgId, msgData);
        messageReadStatus.set(msgId, new Set());

        return msgId;
    } finally {
        conn.release();
    }
}

async function markMessageAsRead(msgId, userId) {
    const conn = await getConnection();
    try {
        await conn.execute(`
            INSERT IGNORE INTO chat_message_reads (msg_id, user_id)
            VALUES (?, ?)
        `, [msgId, userId]);

        // 更新缓存
        if (messageReadStatus.has(msgId)) {
            messageReadStatus.get(msgId).add(userId);
        }
    } finally {
        conn.release();
    }
}

async function recallMessage(msgId, userId) {
    const conn = await getConnection();
    try {
        // 检查权限
        const [rows] = await conn.execute(
            'SELECT sender_id FROM chat_messages WHERE msg_id = ?',
            [msgId]
        );

        if (rows.length === 0 || rows[0].sender_id !== userId) {
            throw new Error('无权撤回此消息');
        }

        // 标记为已撤回
        await conn.execute(
            'UPDATE chat_messages SET is_recalled = 1 WHERE msg_id = ?',
            [msgId]
        );

        return true;
    } finally {
        conn.release();
    }
}

async function searchMessages(keyword, userId, limit = 20) {
    const conn = await getConnection();
    try {
        const [rows] = await conn.execute(`
            SELECT * FROM chat_messages 
            WHERE (sender_id = ? OR receiver_id = ?)
            AND (content LIKE ? OR sender_name LIKE ?)
            AND deleted = 0
            AND is_recalled = 0
            ORDER BY timestamp DESC
            LIMIT ?
        `, [userId, userId, `%${keyword}%`, `%${keyword}%`, limit]);

        return rows;
    } finally {
        conn.release();
    }
}

// ============ WebSocket 处理 ============

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(express.static(path.join(__dirname)));

wss.on('connection', (ws, req) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const token = url.searchParams.get('access_token');
    const isdev = url.searchParams.get('isdev') || '0';
    const type = url.searchParams.get('type') || 'user';

    let userId = null;
    let userInfo = null;

    // 验证用户
    if (token) {
        // 这里应该调用用户服务验证 token
        // 简化处理：直接使用 token 作为 userId
        userId = token.substring(0, 32);
        userInfo = { userId, type };
    }

    if (!userId) {
        ws.close(1008, 'Unauthorized');
        return;
    }

    // 记录在线用户
    onlineUsers.set(userId, {
        ws,
        userInfo,
        connectedAt: new Date(),
        status: 'online'
    });

    console.log(`用户上线: ${userId} (${type})`);

    // 发送欢迎消息
    ws.send(JSON.stringify({
        type: 'welcome',
        userId,
        timestamp: new Date().toISOString()
    }));

    // 处理消息
    ws.on('message', async (data) => {
        try {
            const msg = JSON.parse(data);

            switch (msg.type) {
                // 聊天消息
                case 'chat':
                    await handleChatMessage(msg, userId, userInfo);
                    break;

                // 消息已读
                case 'read':
                    await handleMessageRead(msg, userId);
                    break;

                // 消息撤回
                case 'recall':
                    await handleMessageRecall(msg, userId);
                    break;

                // 消息搜索
                case 'search':
                    await handleMessageSearch(msg, userId, ws);
                    break;

                // 创建群聊
                case 'create_group':
                    await handleCreateGroup(msg, userId, ws);
                    break;

                // 加入群聊
                case 'join_group':
                    await handleJoinGroup(msg, userId, ws);
                    break;

                // typing 状态
                case 'typing':
                    broadcastTypingStatus(msg, userId);
                    break;

                // 心跳
                case 'ping':
                    ws.send(JSON.stringify({ type: 'pong' }));
                    break;
            }
        } catch (err) {
            console.error('消息处理错误:', err);
            ws.send(JSON.stringify({
                type: 'error',
                msg: err.message
            }));
        }
    });

    ws.on('close', () => {
        onlineUsers.delete(userId);
        console.log(`用户离线: ${userId}`);
        broadcastUserStatus(userId, 'offline');
    });

    ws.on('error', (err) => {
        console.error('WebSocket 错误:', err);
    });
});

// ============ 消息处理函数 ============

async function handleChatMessage(msg, senderId, senderInfo) {
    const msgId = generateId();
    const msgData = {
        id: msgId,
        type: msg.type || 'chat',
        msgType: msg.msgType || 'text',
        content: msg.content,
        senderId,
        senderName: senderInfo.userName || senderId,
        receiverId: msg.receiverId,
        groupId: msg.groupId,
        replyToMsgId: msg.replyToMsgId,
        timestamp: new Date().toISOString()
    };

    // 保存到数据库
    await saveMessage(msgData);

    // 广播消息
    if (msg.groupId) {
        // 群聊消息
        broadcastToGroup(msg.groupId, {
            type: 'message',
            data: msgData
        });
    } else {
        // 单聊消息
        broadcastToUser(msg.receiverId, {
            type: 'message',
            data: msgData
        });
    }
}

async function handleMessageRead(msg, userId) {
    const msgId = msg.msgId;
    await markMessageAsRead(msgId, userId);

    // 通知发送者
    const conn = await getConnection();
    try {
        const [rows] = await conn.execute(
            'SELECT sender_id FROM chat_messages WHERE msg_id = ?',
            [msgId]
        );
        if (rows.length > 0) {
            broadcastToUser(rows[0].sender_id, {
                type: 'message_read',
                msgId,
                readBy: userId
            });
        }
    } finally {
        conn.release();
    }
}

async function handleMessageRecall(msg, userId) {
    try {
        await recallMessage(msg.msgId, userId);
        
        // 广播撤回事件
        broadcast({
            type: 'message_recalled',
            msgId: msg.msgId,
            recalledBy: userId
        });
    } catch (err) {
        console.error('撤回失败:', err);
    }
}

async function handleMessageSearch(msg, userId, ws) {
    const results = await searchMessages(msg.keyword, userId, msg.limit || 20);
    ws.send(JSON.stringify({
        type: 'search_results',
        results
    }));
}

async function handleCreateGroup(msg, userId, ws) {
    const groupId = generateGroupId();
    const members = new Set([userId, ...(msg.members || [])]);

    groups.set(groupId, {
        groupId,
        name: msg.groupName,
        creator: userId,
        members,
        createdAt: new Date()
    });

    // 保存到数据库
    const conn = await getConnection();
    try {
        await conn.execute(`
            INSERT INTO chat_groups (group_id, group_name, creator_id, members)
            VALUES (?, ?, ?, ?)
        `, [groupId, msg.groupName, userId, JSON.stringify(Array.from(members))]);
    } finally {
        conn.release();
    }

    ws.send(JSON.stringify({
        type: 'group_created',
        groupId,
        groupName: msg.groupName
    }));
}

async function handleJoinGroup(msg, userId, ws) {
    const group = groups.get(msg.groupId);
    if (!group) {
        ws.send(JSON.stringify({
            type: 'error',
            msg: '群聊不存在'
        }));
        return;
    }

    group.members.add(userId);

    // 通知群成员
    broadcastToGroup(msg.groupId, {
        type: 'user_joined_group',
        groupId: msg.groupId,
        userId,
        userName: msg.userName
    });
}

// ============ 广播函数 ============

function broadcast(data) {
    const message = JSON.stringify(data);
    onlineUsers.forEach(user => {
        if (user.ws.readyState === WebSocket.OPEN) {
            user.ws.send(message);
        }
    });
}

function broadcastToUser(userId, data) {
    const user = onlineUsers.get(userId);
    if (user && user.ws.readyState === WebSocket.OPEN) {
        user.ws.send(JSON.stringify(data));
    }
}

function broadcastToGroup(groupId, data) {
    const group = groups.get(groupId);
    if (!group) return;

    const message = JSON.stringify(data);
    group.members.forEach(memberId => {
        const user = onlineUsers.get(memberId);
        if (user && user.ws.readyState === WebSocket.OPEN) {
            user.ws.send(message);
        }
    });
}

function broadcastTypingStatus(msg, userId) {
    const data = {
        type: 'typing',
        userId,
        groupId: msg.groupId,
        receiverId: msg.receiverId
    };

    if (msg.groupId) {
        broadcastToGroup(msg.groupId, data);
    } else {
        broadcastToUser(msg.receiverId, data);
    }
}

function broadcastUserStatus(userId, status) {
    broadcast({
        type: 'user_status',
        userId,
        status,
        timestamp: new Date().toISOString()
    });
}

// ============ 启动服务 ============

async function start() {
    try {
        await initDatabase();
        
        server.listen(PORT, () => {
            console.log(`
========================================
  即时通讯服务已启动 (增强版)
  端口: ${PORT}
  WebSocket: ws://47.98.238.209:${PORT}
  功能: 消息已读/撤回/搜索/群聊/typing
========================================
            `);
        });
    } catch (err) {
        console.error('启动失败:', err);
        process.exit(1);
    }
}

start();

module.exports = { app, server };
