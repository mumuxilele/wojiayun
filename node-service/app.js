const http = require('http');
const https = require('https');
const url = require('url');

// 配置
const PORT = 22307;

// 生产环境配置
const PROD_URL = 'https://gj.wojiacloud.com';
const DEV_URL = 'https://gj.wojiacloud.cn';

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
    const fullUrl = `${targetUrl}/h5/users/getUserInfo`;
    const isDevText = (isDev === '1' || isDev === 'true') ? '开发' : '生产';
    console.log(`[${isDevText}环境] 转发到: ${fullUrl}`);
    
    try {
        const result = await httpRequestPromise(fullUrl, { access_token: accessToken });
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

// 获取客户列表 - 转发到第三方服务器
async function getCustomerList(accessToken, isDev, current, rowCount, searchPhrase) {
    if (!accessToken) {
        return { success: false, msg: 'access_token不能为空' };
    }
    
    // 判断环境
    const targetUrl = (isDev === '1' || isDev === 'true') ? DEV_URL : PROD_URL;
    const fullUrl = `${targetUrl}/api/rentCus/list`;
    const isDevText = (isDev === '1' || isDev === 'true') ? '开发' : '生产';
    console.log(`[${isDevText}环境] 转发客户列表到: ${fullUrl}`);
    
    const params = {
        access_token: accessToken,
        current: current || 1,
        rowCount: rowCount || 10,
        time: Date.now()
    };
    if (searchPhrase) {
        params.searchPhrase = searchPhrase;
    }
    
    try {
        const result = await httpRequestPromise(fullUrl, params);
        return result;
    } catch (error) {
        console.error('转发客户列表请求失败:', error.message);
        return {
            success: false,
            msg: '第三方服务调用失败: ' + error.message,
            error: error.message
        };
    }
}

// 设备巡检统计 - 转发到第三方服务器
async function equipmentReport(apiPath, accessToken, isDev, extraParams = {}) {
    if (!accessToken) {
        return { success: false, msg: 'access_token不能为空' };
    }
    
    const targetUrl = (isDev === '1' || isDev === 'true') ? DEV_URL : PROD_URL;
    const fullUrl = `${targetUrl}/h5/equipmentProjectReport/${apiPath}`;
    const isDevText = (isDev === '1' || isDev === 'true') ? '开发' : '生产';
    console.log(`[${isDevText}环境] 转发设备巡检到: ${fullUrl}`);
    
    const params = {
        access_token: accessToken,
        time: Date.now(),
        ...extraParams
    };
    
    try {
        const result = await httpRequestPromise(fullUrl, params);
        return result;
    } catch (error) {
        console.error(`转发设备巡检${apiPath}请求失败:`, error.message);
        return {
            success: false,
            msg: '第三方服务调用失败: ' + error.message,
            error: error.message
        };
    }
}

// 获取组织单元 - 转发到第三方服务器
async function getOrgUnits(accessToken, isDev, searchPhrase) {
    if (!accessToken) {
        return { success: false, msg: 'access_token不能为空' };
    }
    
    const targetUrl = (isDev === '1' || isDev === 'true') ? DEV_URL : PROD_URL;
    const fullUrl = `${targetUrl}/h5/orgUnits/getAllOrgUnitForAuth`;
    const isDevText = (isDev === '1' || isDev === 'true') ? '开发' : '生产';
    console.log(`[${isDevText}环境] 转发组织单元到: ${fullUrl}`);
    
    const params = {
        access_token: accessToken,
        time: Date.now()
    };
    if (searchPhrase) {
        params.searchPhrase = searchPhrase;
    }
    
    try {
        const result = await httpRequestPromise(fullUrl, params);
        return result;
    } catch (error) {
        console.error('转发组织单元请求失败:', error.message);
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
        res.end(JSON.stringify({ msg: 'User Info Service', version: '3.0', description: '转发到第三方服务' }));
        return;
    }
    
    // getUserInfo 接口
    if (pathname === '/api/getUserInfo' || pathname === '/getUserInfo') {
        const accessToken = query.access_token || query.token || '';
        const isDev = query.isdev || query.isDev || '0';
        
        const result = await getUserInfo(accessToken, isDev);
        
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(result));
        return;
    }
    
    // 客户列表接口
    if (pathname === '/api/rentCus/list' || pathname === '/rentCus/list') {
        const accessToken = query.access_token || '';
        const isDev = query.isdev || query.isDev || '0';
        const current = query.current || 1;
        const rowCount = query.rowCount || 10;
        const searchPhrase = query.searchPhrase || '';
        
        const result = await getCustomerList(accessToken, isDev, current, rowCount, searchPhrase);
        
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(result));
        return;
    }
    
    // 设备巡检统计接口
    if (pathname.startsWith('/equipmentProjectReport/')) {
        const accessToken = query.access_token || '';
        const isDev = query.isdev || query.isDev || '0';
        const apiPath = pathname.replace('/equipmentProjectReport/', '');
        
        // 获取其他参数
        const extraParams = { ...query };
        delete extraParams.access_token;
        delete extraParams.isdev;
        
        const result = await equipmentReport(apiPath, accessToken, isDev, extraParams);
        
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(result));
        return;
    }
    
    // 组织单元接口
    if (pathname === '/orgUnits/getAllOrgUnitForAuth' || pathname === '/api/orgUnits/getAllOrgUnitForAuth') {
        const accessToken = query.access_token || '';
        const isDev = query.isdev || query.isDev || '0';
        const searchPhrase = query.searchPhrase || '';
        
        const result = await getOrgUnits(accessToken, isDev, searchPhrase);
        
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
    console.log(`接口:`);
    console.log(`  - /getUserInfo?isdev=0&access_token=xxx (获取用户信息)`);
    console.log(`  - /rentCus/list?isdev=0&access_token=xxx&current=1&rowCount=10&searchPhrase=关键词 (客户列表)`);
    console.log(`生产环境: ${PROD_URL}`);
    console.log(`开发环境: ${DEV_URL}`);
});
