const express = require('express');
const cors = require('cors');
const https = require('https');
const http = require('http');

const app = express();
const PORT = process.env.PORT || 22314;

// 配置
const CONFIG = {
    // 腾讯云 AI 密钥
    TENCENT_APP_KEY: 'ISIwDbRWVRHRREjjayEKitsdivztFGZDhCOduWhvGKpmcOShEyHODlVxByvsVeBUtZYECgQAzTtBJSeRCRGAOouZlvqZhjUYykYlXpHfOGnwMPxwYGhjpmDmofgDtyuq',
    // 腾讯云 AI 接口地址
    TENCENT_API_URL: 'https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse',
    // 我家云接口域名
    WOJIA_API_HOST: 'gj.wojiacloud.com'
};

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

// 辅助函数：发起 HTTPS 请求
function makeHttpsRequest(options, postData = null) {
    return new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    resolve({ status: res.statusCode, data: jsonData });
                } catch (e) {
                    resolve({ status: res.statusCode, data: data });
                }
            });
        });

        req.on('error', (e) => {
            reject(e);
        });

        if (postData) {
            req.write(JSON.stringify(postData));
        }
        req.end();
    });
}

// API: 获取用户信息
app.get('/api/userinfo', async (req, res) => {
    try {
        const accessToken = req.query.access_token;
        
        if (!accessToken) {
            return res.status(400).json({ 
                success: false, 
                error: '缺少 access_token 参数' 
            });
        }

        // 调用我家云接口获取用户信息
        const options = {
            hostname: CONFIG.WOJIA_API_HOST,
            port: 443,
            path: `/users/getUserInfo?access_token=${accessToken}`,
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        };

        const response = await makeHttpsRequest(options);
        
        if (response.status === 200 && response.data) {
            res.json({
                success: true,
                data: response.data
            });
        } else {
            res.status(response.status).json({
                success: false,
                error: '获取用户信息失败',
                detail: response.data
            });
        }
    } catch (error) {
        console.error('获取用户信息错误:', error);
        res.status(500).json({ 
            success: false, 
            error: '服务器内部错误',
            message: error.message 
        });
    }
});

// API: 聊天接口（转发到腾讯云）
app.post('/api/chat', async (req, res) => {
    try {
        const { session_id, visitor_biz_id, content, model_name } = req.body;

        if (!content) {
            return res.status(400).json({ 
                success: false, 
                error: '缺少 content 参数' 
            });
        }

        if (!visitor_biz_id) {
            return res.status(400).json({ 
                success: false, 
                error: '缺少 visitor_biz_id 参数' 
            });
        }

        // 构建请求体
        const requestBody = {
            session_id: session_id || generateUUID(),
            bot_app_key: CONFIG.TENCENT_APP_KEY,
            visitor_biz_id: visitor_biz_id,
            content: content,
            stream: 'enable',
            incremental: true
        };

        if (model_name) {
            requestBody.model_name = model_name;
        }

        // 设置 SSE 响应头
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');
        res.setHeader('X-Accel-Buffering', 'no');

        // 发起腾讯云请求
        const options = {
            hostname: 'wss.lke.cloud.tencent.com',
            port: 443,
            path: '/v1/qbot/chat/sse',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(JSON.stringify(requestBody))
            }
        };

        const tencentReq = https.request(options, (tencentRes) => {
            tencentRes.on('data', (chunk) => {
                // 直接转发数据
                res.write(chunk);
            });

            tencentRes.on('end', () => {
                res.end();
            });
        });

        tencentReq.on('error', (error) => {
            console.error('腾讯云请求错误:', error);
            res.write(`data: ${JSON.stringify({ type: 'error', error: { message: error.message } })}\n\n`);
            res.end();
        });

        tencentReq.write(JSON.stringify(requestBody));
        tencentReq.end();

    } catch (error) {
        console.error('聊天接口错误:', error);
        res.status(500).json({ 
            success: false, 
            error: '服务器内部错误',
            message: error.message 
        });
    }
});

// 生成 UUID
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// 健康检查
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        service: 'aichat',
        timestamp: new Date().toISOString()
    });
});

// 启动服务
app.listen(PORT, () => {
    console.log(`🤖 AI Chat 服务已启动`);
    console.log(`📍 本地地址: http://localhost:${PORT}`);
    console.log(`📍 健康检查: http://localhost:${PORT}/health`);
    console.log(`🔑 腾讯云 AppKey: ${CONFIG.TENCENT_APP_KEY.substring(0, 20)}...`);
});
