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
     * 初始化数据库表
     */
    async initTable() {
        const conn = await this.getConnection();
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
            console.log('DB tables ready');
        } finally {
            conn.release();
        }
    }

    /**
     * 保存消息
     */
    async saveMessage(msg) {
        const conn = await this.getConnection();
        try {
            const msgId = msg.id || this.generateId();
            
            // 使用 SQL 配置
            const sqlTemplate = sqlLoader.getSql('chat.saveMessage');
            const { sql, params } = sqlLoader.parseSql(sqlTemplate, {
                msgId,
                msgType: msg.msgType || 'text',
                content: msg.content || '',
                senderId: msg.senderId,
                senderName: msg.senderName || 'Unknown',
                senderType: msg.senderType || 'user',
                receiverId: msg.receiverId || null,
                timestamp: new Date()
            });
            
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
                beforeTimestamp = null
            } = options;

            let sql, params;

            if (beforeTimestamp) {
                // 使用时间戳分页
                const sqlTemplate = sqlLoader.getSql('chat.getMessagesByTime');
                const parsed = sqlLoader.parseSql(sqlTemplate, {
                    senderType,
                    beforeTimestamp,
                    limit: parseInt(limit)
                });
                sql = parsed.sql;
                params = parsed.params;
            } else {
                // 普通分页
                const sqlTemplate = sqlLoader.getSql('chat.getMessages');
                const parsed = sqlLoader.parseSql(sqlTemplate, {
                    senderType,
                    limit: parseInt(limit),
                    offset: parseInt(offset)
                });
                sql = parsed.sql;
                params = parsed.params;
            }
            
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
}

module.exports = ChatDao;
