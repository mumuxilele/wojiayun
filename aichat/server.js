const express = require('express');
const cors = require('cors');
const https = require('https');
const http = require('http');
const multer = require('multer');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 22314;

// 配置 multer 用于文件上传
const upload = multer({ 
    storage: multer.memoryStorage(),
    limits: { fileSize: 10 * 1024 * 1024 } // 限制10MB
});

// 配置
const CONFIG = {
    // 腾讯云 AI 密钥
    TENCENT_APP_KEY: 'ISIwDbRWVRHRREjjayEKitsdivztFGZDhCOduWhvGKpmcOShEyHODlVxByvsVeBUtZYECgQAzTtBJSeRCRGAOouZlvqZhjUYykYlXpHfOGnwMPxwYGhjpmDmofgDtyuq',
    // 腾讯云 AI 接口地址
    TENCENT_API_URL: 'https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse',
    // 我家云接口域名
    WOJIA_API_HOST: 'gj.wojiacloud.com',
    // 腾讯云语音识别配置
    TENCENT_SECRET_ID: process.env.TENCENT_SECRET_ID || '',
    TENCENT_SECRET_KEY: process.env.TENCENT_SECRET_KEY || ''
};

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));
// 提供 SDK 静态文件
app.use('/sdk', express.static(require('path').join(__dirname, '../aichat-sdk/dist')));

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
        const { session_id, visitor_biz_id, content, model_name, custom_variables } = req.body;

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

        // 添加自定义变量
        if (custom_variables) {
            requestBody.custom_variables = custom_variables;
        }

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

// API: 语音识别接口
app.post('/api/speech-to-text', upload.single('audio'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ 
                success: false, 
                error: '缺少音频文件' 
            });
        }

        const audioBuffer = req.file.buffer;
        const accessToken = req.body.access_token;

        // 方案1: 使用浏览器内置的 Web Speech API（前端已处理）
        // 方案2: 调用腾讯云语音识别服务
        
        // 如果配置了腾讯云密钥，使用腾讯云语音识别
        if (CONFIG.TENCENT_SECRET_ID && CONFIG.TENCENT_SECRET_KEY) {
            const result = await callTencentASR(audioBuffer);
            return res.json(result);
        }

        // 方案3: 使用浏览器 Web Speech API 的结果（前端传递）
        // 这种情况下前端应该直接处理，不需要调用后端
        
        // 临时方案：返回提示信息
        res.json({ 
            success: false, 
            error: '语音识别服务未配置，请联系管理员配置腾讯云语音识别密钥',
            hint: '请在 .env 文件中配置 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY'
        });

    } catch (error) {
        console.error('语音识别错误:', error);
        res.status(500).json({ 
            success: false, 
            error: '语音识别失败',
            message: error.message 
        });
    }
});

// 调用腾讯云语音识别（一句话识别）
async function callTencentASR(audioBuffer) {
    const host = 'asr.tencentcloudapi.com';
    const service = 'asr';
    const action = 'SentenceRecognition';
    const version = '2019-06-14';
    const timestamp = Math.floor(Date.now() / 1000);
    const date = new Date(timestamp * 1000).toISOString().split('T')[0];

    // 请求体
    const audioBase64 = audioBuffer.toString('base64');
    const payload = JSON.stringify({
        EngSerViceType: '16k', // 16k 采样率
        SourceType: 1, // 语音数据来源：1为语音 URL，0为语音数据（base64）
        VoiceFormat: 'webm', // 音频格式
        Data: audioBase64,
        UsrAudioKey: generateUUID()
    });

    // 构建签名
    const algorithm = 'TC3-HMAC-SHA256';
    const httpRequestMethod = 'POST';
    const canonicalUri = '/';
    const canonicalQueryString = '';
    const canonicalHeaders = `content-type:application/json\nhost:${host}\n`;
    const signedHeaders = 'content-type;host';
    const hashedRequestPayload = crypto.createHash('sha256').update(payload).digest('hex');
    const canonicalRequest = `${httpRequestMethod}\n${canonicalUri}\n${canonicalQueryString}\n${canonicalHeaders}\n${signedHeaders}\n${hashedRequestPayload}`;

    const credentialScope = `${date}/${service}/tc3_request`;
    const hashedCanonicalRequest = crypto.createHash('sha256').update(canonicalRequest).digest('hex');
    const stringToSign = `${algorithm}\n${timestamp}\n${credentialScope}\n${hashedCanonicalRequest}`;

    // 计算签名
    const secretDate = hmac(`TC3${CONFIG.TENCENT_SECRET_KEY}`, date);
    const secretService = hmac(secretDate, service);
    const secretSigning = hmac(secretService, 'tc3_request');
    const signature = hmac(secretSigning, stringToSign, 'hex');

    const authorization = `${algorithm} Credential=${CONFIG.TENCENT_SECRET_ID}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;

    // 发送请求
    return new Promise((resolve, reject) => {
        const options = {
            hostname: host,
            port: 443,
            path: '/',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Host': host,
                'X-TC-Action': action,
                'X-TC-Version': version,
                'X-TC-Timestamp': timestamp.toString(),
                'Authorization': authorization
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    if (jsonData.Response && jsonData.Response.Result) {
                        resolve({ 
                            success: true, 
                            text: jsonData.Response.Result 
                        });
                    } else if (jsonData.Response && jsonData.Response.Error) {
                        resolve({ 
                            success: false, 
                            error: jsonData.Response.Error.Message 
                        });
                    } else {
                        resolve({ 
                            success: false, 
                            error: '语音识别返回格式错误' 
                        });
                    }
                } catch (e) {
                    resolve({ 
                        success: false, 
                        error: '解析语音识别结果失败' 
                    });
                }
            });
        });

        req.on('error', (e) => {
            resolve({ 
                success: false, 
                error: `请求失败: ${e.message}` 
            });
        });

        req.write(payload);
        req.end();
    });
}

// HMAC 辅助函数
function hmac(key, data, encoding = 'buffer') {
    const result = crypto.createHmac('sha256', typeof key === 'string' ? Buffer.from(key, 'utf8') : key)
        .update(data)
        .digest();
    return encoding === 'hex' ? result.toString('hex') : result;
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
