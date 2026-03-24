const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 22306;
const STATIC_DIR = __dirname;

const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    let filePath = req.url;

    // 处理 /equipment/ 前缀
    if (filePath.startsWith('/equipment/')) {
        filePath = filePath.substring('/equipment/'.length);
    } else if (filePath.startsWith('/equipment')) {
        filePath = filePath.substring('/equipment'.length);
        if (filePath === '' || filePath === '/') {
            filePath = 'report.html';
        }
    }

    // 去掉前导 /
    if (filePath.startsWith('/')) {
        filePath = filePath.substring(1);
    }

    // 默认文件
    if (filePath === '' || filePath === '/') {
        filePath = 'report.html';
    }

    // 安全检查：防止目录遍历
    if (filePath.includes('..')) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
    }

    const fullPath = path.join(STATIC_DIR, filePath);
    const ext = path.extname(fullPath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(fullPath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404);
                res.end('Not Found: ' + filePath);
            } else {
                res.writeHead(500);
                res.end('Server Error');
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content);
        }
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Equipment service running at http://localhost:${PORT}/`);
});
