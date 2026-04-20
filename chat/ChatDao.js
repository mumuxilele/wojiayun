/**
 * 聊天数据访问层 (DAO)
 * 分离数据库操作，使用 SQL 配置文件
 */
const sqlLoader = require('./SqlLoader');
const crypto = require('crypto');

class ChatDao {
    constructor(pool) {
        this.pool = pool;
    }

    /**
     * 获取数据库连接
     */
    async getConnection() {
        return await this.pool.getConnection();
    }

    /**
     * 生成消息 ID
     */
    generateId() {
        const ts = Date.now().toString();
        const rnd = Math.random().toString();
        return crypto.createHash('md5').update(ts + rnd).digest('hex');
    }

    /**
     * V47.0: 生成FID主键
     */
    generateFid() {
        const ts = Date.now().toString();
        const rnd = Math.random().toString();
        const uuid = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36);
        return crypto.createHash('md5').update(ts + rnd + uuid).digest('hex');
    }

    /**
     * 初始化数据库表
     */
    async initTable() {
        const conn = await this.getConnection();
        try {
            // 消息表
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
                    receiver_name VARCHAR(128),
                    receiver_type VARCHAR(16),
                    session_id VARCHAR(64),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted TINYINT DEFAULT 0,
                    group_id VARCHAR(64),
                    reply_to_msg_id VARCHAR(64),
                    INDEX idx_sender (sender_id),
                    INDEX idx_receiver (receiver_id),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_session (session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            `);
            
            // 会话表
            await conn.execute(`
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(64) UNIQUE NOT NULL,
                    user_id VARCHAR(64) NOT NULL,
                    user_name VARCHAR(128),
                    staff_id VARCHAR(64),
                    staff_name VARCHAR(128),
                    status VARCHAR(32) DEFAULT 'pending',
                    last_message TEXT,
                    last_message_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    ended_at DATETIME,
                    ended_by VARCHAR(64),
                    INDEX idx_user (user_id),
                    INDEX idx_staff (staff_id),
                    INDEX idx_status (status),
                    INDEX idx_updated (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            `);
            
            console.log('DB tables ready');
        } finally {
            conn.release();
        }
    }

    /**
     * 保存消息 - V47.0: 添加fid字段
     */
    async saveMessage(msg) {
        const conn = await this.getConnection();
        try {
            const msgId = msg.id || this.generateId();
            const fid = this.generateFid(); // V47.0: 生成FID主键
            
            // 直接执行SQL，支持sessionId，V47.0添加fid字段
            const sql = `INSERT INTO chat_messages (fid, msg_id, msg_type, content, sender_id, sender_name, sender_type, receiver_id, session_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`;
            const params = [
                fid, // V47.0: FID主键
                msgId,
                msg.msgType || 'text',
                msg.content || '',
                msg.senderId,
                msg.senderName || 'Unknown',
                msg.senderType || 'user',
                msg.receiverId || null,
                msg.sessionId || null,
                new Date()
            ];
            
            await conn.execute(sql, params);
            return msgId;
        } finally {
            conn.release();
        }
    }

    /**
     * 获取消息列表
     */
    async getMessages(options = {}) {
        const conn = await this.getConnection();
        try {
            const {
                senderType,
                limit = 50,
                offset = 0,
                beforeTimestamp = null,
                userId = null
            } = options;

            let sql, params = [];

            // 构建基础查询
            let baseSql = `SELECT msg_id as id, msg_id, msg_type, content, sender_id as senderId, sender_name as senderName, sender_type, receiver_id as receiverId, session_id as sessionId, timestamp FROM chat_messages WHERE deleted = 0`;
            
            // 根据 senderType 添加过滤条件
            if (senderType && senderType !== 'all') {
                baseSql += ` AND sender_type = ?`;
                params.push(senderType);
            }
            
            // 按用户筛选（发送者或接收者）
            if (userId) {
                baseSql += ` AND (sender_id = ? OR receiver_id = ?)`;
                params.push(userId, userId);
            }
            
            // 添加时间戳过滤
            if (beforeTimestamp) {
                baseSql += ` AND timestamp < ?`;
                params.push(beforeTimestamp);
            }
            
            // 添加排序和分页
            baseSql += ` ORDER BY timestamp DESC LIMIT ? OFFSET ?`;
            params.push(parseInt(limit), parseInt(offset));
            
            sql = baseSql;
            
            const [rows] = await conn.query(sql, params);
            return rows;
        } finally {
            conn.release();
        }
    }

    /**
     * 根据 ID 获取消息
     */
    async getMessageById(msgId) {
        const conn = await this.getConnection();
        try {
            const sqlTemplate = sqlLoader.getSql('chat.getMessageById');
            const { sql, params } = sqlLoader.parseSql(sqlTemplate, { msgId });
            const [rows] = await conn.execute(sql, params);
            return rows[0] || null;
        } finally {
            conn.release();
        }
    }

    /**
     * 软删除消息
     */
    async deleteMessage(msgId) {
        const conn = await this.getConnection();
        try {
            const sqlTemplate = sqlLoader.getSql('chat.deleteMessage');
            const { sql, params } = sqlLoader.parseSql(sqlTemplate, { msgId });
            await conn.execute(sql, params);
            return true;
        } finally {
            conn.release();
        }
    }

    // ============ 会话管理 ============

    /**
     * 生成会话 ID
     */
    generateSessionId() {
        const ts = Date.now().toString();
        const rnd = Math.random().toString();
        return crypto.createHash('md5').update(ts + rnd).digest('hex');
    }

    /**
     * 获取或创建会话
     */
    async getOrCreateSession(userId, userName) {
        const conn = await this.getConnection();
        try {
            // 查找用户最近的活跃会话
            const [rows] = await conn.execute(
                `SELECT * FROM chat_sessions WHERE user_id = ? AND status IN ('pending', 'processing') ORDER BY updated_at DESC LIMIT 1`,
                [userId]
            );
            
            if (rows.length > 0) {
                return rows[0];
            }
            
            // 创建新会话
            const sessionId = this.generateSessionId();
            await conn.execute(
                `INSERT INTO chat_sessions (session_id, user_id, user_name, status) VALUES (?, ?, ?, 'pending')`,
                [sessionId, userId, userName || '用户']
            );
            
            const [newRows] = await conn.execute(
                `SELECT * FROM chat_sessions WHERE session_id = ?`,
                [sessionId]
            );
            return newRows[0];
        } finally {
            conn.release();
        }
    }

    /**
     * 更新会话状态
     */
    async updateSessionStatus(sessionId, status, staffId = null, staffName = null) {
        const conn = await this.getConnection();
        try {
            if (status === 'ended') {
                await conn.execute(
                    `UPDATE chat_sessions SET status = ?, staff_id = ?, staff_name = ?, ended_at = NOW(), updated_at = NOW() WHERE session_id = ?`,
                    [status, staffId, staffName, sessionId]
                );
            } else {
                await conn.execute(
                    `UPDATE chat_sessions SET status = ?, staff_id = COALESCE(?, staff_id), staff_name = COALESCE(?, staff_name), updated_at = NOW() WHERE session_id = ?`,
                    [status, staffId, staffName, sessionId]
                );
            }
            return true;
        } finally {
            conn.release();
        }
    }

    /**
     * 分配客服
     */
    async assignStaff(sessionId, staffId, staffName) {
        const conn = await this.getConnection();
        try {
            await conn.execute(
                `UPDATE chat_sessions SET staff_id = ?, staff_name = ?, status = 'processing', updated_at = NOW() WHERE session_id = ?`,
                [staffId, staffName, sessionId]
            );
            return true;
        } finally {
            conn.release();
        }
    }

    /**
     * 更新会话最后消息
     */
    async updateSessionLastMessage(sessionId, message, messageTime) {
        const conn = await this.getConnection();
        try {
            await conn.execute(
                `UPDATE chat_sessions SET last_message = ?, last_message_time = ?, updated_at = NOW() WHERE session_id = ?`,
                [message, messageTime, sessionId]
            );
            return true;
        } finally {
            conn.release();
        }
    }

    /**
     * 获取会话列表
     * @param {Object} options - 查询选项
     * @param {string} options.filter - 筛选类型: 'mine'(我处理的), 'all'(全部)
     * @param {string} options.staffId - 当前客服ID
     * @param {string} options.status - 状态筛选: 'pending', 'processing', 'ended'
     * @param {number} options.limit - 分页限制
     * @param {number} options.offset - 分页偏移
     */
    async getSessions(options = {}) {
        const conn = await this.getConnection();
        try {
            const { filter = 'all', staffId, status, limit = 50, offset = 0 } = options;
            
            let sql = `SELECT * FROM chat_sessions WHERE 1=1`;
            const params = [];
            
            // 按客服筛选
            if (filter === 'mine' && staffId) {
                sql += ` AND (staff_id = ? OR status = 'pending')`;
                params.push(staffId);
            }
            
            // 按状态筛选
            if (status) {
                sql += ` AND status = ?`;
                params.push(status);
            }
            
            sql += ` ORDER BY updated_at DESC LIMIT ? OFFSET ?`;
            params.push(parseInt(limit), parseInt(offset));
            
            const [rows] = await conn.query(sql, params);
            return rows;
        } finally {
            conn.release();
        }
    }

    /**
     * 根据用户ID获取会话
     */
    async getSessionByUserId(userId) {
        const conn = await this.getConnection();
        try {
            const [rows] = await conn.execute(
                `SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1`,
                [userId]
            );
            return rows[0] || null;
        } finally {
            conn.release();
        }
    }

    /**
     * 获取会话统计
     */
    async getSessionStats(staffId = null) {
        const conn = await this.getConnection();
        try {
            const stats = {
                pending: 0,
                processing: 0,
                ended: 0,
                myPending: 0,
                myProcessing: 0,
                myEnded: 0
            };
            
            // 全部统计
            const [allRows] = await conn.execute(
                `SELECT status, COUNT(*) as cnt FROM chat_sessions GROUP BY status`
            );
            allRows.forEach(row => {
                if (row.status === 'pending') stats.pending = row.cnt;
                else if (row.status === 'processing') stats.processing = row.cnt;
                else if (row.status === 'ended') stats.ended = row.cnt;
            });
            
            // 我的统计
            if (staffId) {
                const [myRows] = await conn.execute(
                    `SELECT status, COUNT(*) as cnt FROM chat_sessions WHERE staff_id = ? GROUP BY status`,
                    [staffId]
                );
                myRows.forEach(row => {
                    if (row.status === 'processing') stats.myProcessing = row.cnt;
                    else if (row.status === 'ended') stats.myEnded = row.cnt;
                });
                
                // 待处理的（未分配客服的）
                const [pendingRows] = await conn.execute(
                    `SELECT COUNT(*) as cnt FROM chat_sessions WHERE status = 'pending'`
                );
                stats.myPending = pendingRows[0]?.cnt || 0;
            }
            
            return stats;
        } finally {
            conn.release();
        }
    }
}

module.exports = ChatDao;
