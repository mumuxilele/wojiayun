const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 22306;

// 静态文件目录
const VISIT_DIR = path.join(__dirname, 'visit');
const EQUIPMENT_DIR = path.join(__dirname, 'equipment');

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
    let baseDir = VISIT_DIR; // 默认

    // 处理 /equipment/ 前缀
    if (filePath.startsWith('/equipment/') || filePath.startsWith('/equipment')) {
        baseDir = EQUIPMENT_DIR;
        if (filePath.startsWith('/equipment/')) {
            filePath = filePath.substring('/equipment/'.length);
        } else if (filePath === '/equipment') {
            filePath = 'report.html';
        }
    } else if (filePath.startsWith('/visit/') || filePath.startsWith('/visit')) {
        if (filePath.startsWith('/visit/')) {
            filePath = filePath.substring('/visit/'.length);
        } else if (filePath === '/visit') {
            filePath = 'index.html';
        }
    }

    // 去掉前导 /
    if (filePath.startsWith('/')) {
        filePath = filePath.substring(1);
    }

    // 默认文件
    if (filePath === '' || filePath === '/') {
        filePath = 'index.html';
    }

    // 安全检查
    if (filePath.includes('..')) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
    }

    const fullPath = path.join(baseDir, filePath);
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
    console.log(`Unified service running at http://localhost:${PORT}/`);
    console.log(`Visit: http://localhost:${PORT}/visit/`);
    console.log(`Equipment: http://localhost:${PORT}/equipment/`);
});
