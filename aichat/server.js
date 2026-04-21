const express = require('express');
const cors = require('cors');
const https = require('https');
const http = require('http');
const multer = require('multer');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

const app = express();
const PORT = process.env.PORT || 22314;

// 配置 multer 用于文件上传
const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 10 * 1024 * 1024 } // 限制10MB
});

// 配置图片上传存储
const imageStorage = multer.diskStorage({
    destination: function (req, file, cb) {
        const uploadDir = path.join(__dirname, 'uploads');
        // 确保上传目录存在
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: function (req, file, cb) {
        // 生成唯一文件名
        const ext = path.extname(file.originalname) || '.jpg';
        const filename = `${Date.now()}-${generateUUID()}${ext}`;
        cb(null, filename);
    }
});

const imageUpload = multer({
    storage: imageStorage,
    limits: { fileSize: 10 * 1024 * 1024 },
    fileFilter: function (req, file, cb) {
        // 只接受图片文件
        if (file.mimetype.startsWith('image/')) {
            cb(null, true);
        } else {
            cb(new Error('只允许上传图片文件'));
        }
    }
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
// 提供上传图片的静态访问
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));
// 提供 SDK 静态文件
app.use('/sdk', express.static(require('path').join(__dirname, '../aichat-sdk/dist')));

// 辅助函数：发起 HTTPS 请求
function makeHttpsRequest(options, postData = null) {
    return new Promise((resolve, reject) => {
        // 强制使用 IPv4，避免 IPv6 不可达导致崩溃
        const dns = require('dns');
        const opts = {
            ...options,
            family: 4,
            lookup: (hostname, _opts, callback) => {
                dns.lookup(hostname, { family: 4 }, callback);
            },
            servername: options.hostname,
        };
        const req = https.request(opts, (res) => {
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
            console.error('HTTPS request error:', e.message);
            reject(e);
        });

        req.setTimeout(15000, () => {
            console.error('HTTPS request timeout:', options.hostname + options.path);
            req.destroy(new Error('Request timeout'));
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
        const { session_id, visitor_biz_id, content, model_name, custom_variables, widget_action, image_ids, image_urls } = req.body;

        if (!content && !widget_action) {
            return res.status(400).json({
                success: false,
                error: '缺少 content 或 widget_action 参数'
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
            content: content || '',
            stream: 'enable',
            incremental: true
        };

        // 添加自定义变量（包含图片信息）
        let finalCustomVars = custom_variables || {};
        if (image_ids) {
            finalCustomVars.image_ids = image_ids;
        }
        if (image_urls) {
            finalCustomVars.image_urls = image_urls;
        }
        if (Object.keys(finalCustomVars).length > 0) {
            requestBody.custom_variables = finalCustomVars;
        }

        if (model_name) {
            requestBody.model_name = model_name;
        }

        // 添加 widget_action 支持（驼峰式命名，payload 为字符串）
        if (widget_action) {
            requestBody.widget_action = {
                widgetId: widget_action.widgetId || widget_action.widget_id,
                widgetRunId: widget_action.widgetRunId || widget_action.widget_run_id,
                actionType: widget_action.actionType || widget_action.action_type,
                payload: typeof widget_action.payload === 'string' ? widget_action.payload : JSON.stringify(widget_action.payload || {})
            };
            console.log('Widget Action:', JSON.stringify(requestBody.widget_action));
        }

        // 设置 SSE 响应头
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');
        res.setHeader('X-Accel-Buffering', 'no');

        // 发起腾讯云请求
        const tencentOptions = {
            hostname: 'wss.lke.cloud.tencent.com',
            port: 443,
            path: '/v1/qbot/chat/sse',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(JSON.stringify(requestBody))
            },
            // 强制 IPv4
            family: 4,
            lookup: (hostname, _opts, callback) => {
                require('dns').lookup(hostname, { family: 4 }, callback);
            },
            servername: 'wss.lke.cloud.tencent.com',
        };

        const tencentReq = https.request(tencentOptions, (tencentRes) => {
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

// API: 图片上传接口 - 批量转发到我家云
app.post('/api/upload-image', upload.array('images', 10), async (req, res) => {
    try {
        const files = req.files;
        if (!files || files.length === 0) {
            return res.status(400).json({
                success: false,
                error: '缺少图片文件'
            });
        }

        const accessToken = req.body.access_token;
        if (!accessToken) {
            return res.status(400).json({
                success: false,
                error: '缺少 access_token'
            });
        }

        console.log(`批量转发 ${files.length} 张图片到云端`);
        files.forEach((file, i) => {
            console.log(`  [${i + 1}] ${file.originalname}, size: ${file.size}`);
        });

        // 创建 FormData 对象，批量添加所有图片
        const formData = new FormData();
        formData.append('access_token', accessToken);
        
        // 添加所有图片文件
        files.forEach(file => {
            formData.append('files', file.buffer, {
                filename: file.originalname || 'image.jpg',
                contentType: file.mimetype || 'image/jpeg'
            });
        });

        // 发送到我家云上传接口，直接返回云端原始响应
        await uploadToWojiaCloud(formData, res);

    } catch (error) {
        console.error('图片上传错误:', error);
        res.status(500).json({
            success: false,
            error: '图片上传失败',
            message: error.message
        });
    }
});

// 转发到我家云上传接口 - 直接透传响应
function uploadToWojiaCloud(formData, clientRes) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'gj.wojiacloud.com',
            port: 443,
            path: '/api/file/uploadFiles',
            method: 'POST',
            headers: formData.getHeaders()
        };

        const request = https.request(options, (cloudRes) => {
            // 设置响应头
            clientRes.status(cloudRes.statusCode);
            Object.keys(cloudRes.headers).forEach(key => {
                clientRes.setHeader(key, cloudRes.headers[key]);
            });

            let data = '';
            cloudRes.on('data', (chunk) => {
                data += chunk;
                clientRes.write(chunk);
            });
            cloudRes.on('end', () => {
                console.log('云端上传响应:', data);
                clientRes.end();
                resolve({ forwarded: true });
            });
        });

        request.on('error', (error) => {
            console.error('请求失败:', error);
            clientRes.status(500).json({
                success: false,
                error: '上传失败',
                message: error.message
            });
            reject(error);
        });

        // 将 FormData 写入请求
        formData.pipe(request);
    });
}

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
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🤖 AI Chat 服务已启动`);
    console.log(`📍 本地地址: http://localhost:${PORT}`);
    console.log(`📍 健康检查: http://localhost:${PORT}/health`);
    console.log(`🔑 腾讯云 AppKey: ${CONFIG.TENCENT_APP_KEY.substring(0, 20)}...`);
});
