const http = require('http');
const url = require('url');

// 配置
const PORT = 22307;
const DEV_TOKEN = 'dev_token_123456'; // 开发环境token
const PROD_TOKEN = 'visit_token_2024'; // 生产环境token

// 用户信息映射 (生产环境从数据库读取)
const users = {
    'admin': { id: 1, name: '管理员', role: 'admin' },
    'user1': { id: 2, name: '张三', role: 'user' },
    'user2': { id: 3, name: '李四', role: 'user' }
};

// 模拟数据库查询
function getUserInfo(accessToken, isDev) {
    // 开发环境
    if (isDev === '1' || isDev === 'true') {
        if (accessToken === DEV_TOKEN) {
            return { 
                success: true, 
                data: { 
                    id: 999, 
                    name: '开发用户', 
                    role: 'dev',
                    isDev: true 
                } 
            };
        }
        return { success: false, msg: '开发环境Token无效' };
    }
    
    // 生产环境
    if (accessToken === PROD_TOKEN) {
        // 返回默认管理员信息
        return { 
            success: true, 
            data: users['admin'] 
        };
    }
    
    return { success: false, msg: 'Token无效' };
}

const server = http.createServer((req, res) => {
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
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(JSON.stringify({ msg: 'User Info Service', version: '1.0' }));
        return;
    }
    
    // getUserInfo 接口
    if (pathname === '/api/getUserInfo' || pathname === '/getUserInfo') {
        const accessToken = query.access_token || query.token || '';
        const isDev = query.isdev || query.isDev || '';
        
        if (!accessToken) {
            res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(JSON.stringify({ success: false, msg: 'access_token不能为空' }));
            return;
        }
        
        const result = getUserInfo(accessToken, isDev);
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
    console.log(`接口: /getUserInfo?isdev=1&access_token=xxx`);
});
