const http = require('http');
const https = require('https');
const url = require('url');

// 配置
const PORT = 22307;

// 生产环境配置
const PROD_URL = 'https://gj.wojiacloud.com/h5/users/getUserInfo';
const DEV_URL = 'https://gj.wojiacloud.cn/h5/users/getUserInfo';

// 发起HTTP/HTTPS请求
function httpRequest(targetUrl, params, callback) {
    const parsedUrl = new URL(targetUrl);
    const isHttps = parsedUrl.protocol === 'https:';
    const client = isHttps ? https : http;
    
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = `${targetUrl}?${queryString}`;
    
    console.log(`转发请求到: ${fullUrl}`);
    
    const req = client.get(fullUrl, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
            try {
                const json = JSON.parse(data);
                callback(null, json);
            } catch(e) {
                callback(e, null);
            }
        });
    });
    
    req.on('error', callback);
    req.setTimeout(10000, () => {
        req.destroy();
        callback(new Error('请求超时'), null);
    });
}

// 封装Promise版本的请求
function httpRequestPromise(targetUrl, params) {
    return new Promise((resolve, reject) => {
        httpRequest(targetUrl, params, (err, data) => {
            if (err) reject(err);
            else resolve(data);
        });
    });
}

// 获取用户信息 - 转发到第三方服务器
async function getUserInfo(accessToken, isDev) {
    if (!accessToken) {
        return { success: false, msg: 'access_token不能为空' };
    }
    
    // 判断环境
    const targetUrl = (isDev === '1' || isDev === 'true') ? DEV_URL : PROD_URL;
    const isDevText = (isDev === '1' || isDev === 'true') ? '开发' : '生产';
    console.log(`[${isDevText}环境] 转发到: ${targetUrl}`);
    
    try {
        const result = await httpRequestPromise(targetUrl, { access_token: accessToken });
        
        // 直接返回第三方服务器的原始响应
        // success: true = 正常, success: false = 不正常
        return result;
        
    } catch (error) {
        console.error('转发请求失败:', error.message);
        return {
            success: false,
            msg: '第三方服务调用失败: ' + error.message,
            error: error.message
        };
    }
}

const server = http.createServer(async (req, res) => {
    // CORS头
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Token');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    const parsedUrl = url.parse(req.url, true);
    const pathname = parsedUrl.pathname;
    const query = parsedUrl.query;
    
    console.log(`${new Date().toISOString()} - ${pathname}`);
    
    // 根路径
    if (pathname === '/' || pathname === '/index.html') {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ msg: 'User Info Service', version: '2.0', description: '转发到第三方服务' }));
        return;
    }
    
    // getUserInfo 接口
    if (pathname === '/api/getUserInfo' || pathname === '/getUserInfo') {
        const accessToken = query.access_token || query.token || '';
        const isDev = query.isdev || query.isDev || '0';  // 默认生产环境
        
        // 转发请求到第三方服务器
        const result = await getUserInfo(accessToken, isDev);
        
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(result));
        return;
    }
    
    // 健康检查
    if (pathname === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ status: 'ok', timestamp: Date.now() }));
        return;
    }
    
    // 404
    res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ success: false, msg: 'Not Found' }));
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`用户信息服务已启动: http://0.0.0.0:${PORT}`);
    console.log(`接口: /getUserInfo?isdev=0&access_token=xxx (生产) 或 /getUserInfo?isdev=1&access_token=xxx (开发)`);
    console.log(`生产环境: ${PROD_URL}`);
    console.log(`开发环境: ${DEV_URL}`);
});
