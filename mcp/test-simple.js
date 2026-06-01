#!/usr/bin/env node

/**
 * 简单的 MCP Server 测试
 */

import { spawn } from "child_process";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// 启动 MCP 服务
const server = spawn("node", [join(__dirname, "index.js")], {
  stdio: ["pipe", "pipe", "pipe"],
});

let buffer = "";

server.stdout.on("data", (data) => {
  buffer += data.toString();
  
  // 检查是否有完整的响应
  const headerEnd = buffer.indexOf("\r\n\r\n");
  if (headerEnd !== -1) {
    const header = buffer.substring(0, headerEnd);
    const lengthMatch = header.match(/Content-Length: (\d+)/);
    if (lengthMatch) {
      const length = parseInt(lengthMatch[1]);
      const contentStart = headerEnd + 4;
      if (buffer.length >= contentStart + length) {
        const content = buffer.substring(contentStart, contentStart + length);
        try {
          const response = JSON.parse(content);
          console.log("响应:", JSON.stringify(response, null, 2));
        } catch (e) {
          console.log("原始内容:", content);
        }
        buffer = buffer.substring(contentStart + length);
      }
    }
  }
});

server.stderr.on("data", (data) => {
  console.log("日志:", data.toString().trim());
});

// 发送请求函数
function send(method, params = {}) {
  const request = JSON.stringify({
    jsonrpc: "2.0",
    id: Date.now(),
    method,
    params,
  });
  const message = `Content-Length: ${Buffer.byteLength(request)}\r\n\r\n${request}`;
  server.stdin.write(message);
}

// 测试
setTimeout(() => {
  console.log("发送初始化请求...");
  send("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "test", version: "1.0.0" },
  });
}, 100);

setTimeout(() => {
  console.log("\n发送 initialized 通知...");
  const notification = JSON.stringify({
    jsonrpc: "2.0",
    method: "notifications/initialized",
  });
  server.stdin.write(`Content-Length: ${Buffer.byteLength(notification)}\r\n\r\n${notification}`);
}, 500);

setTimeout(() => {
  console.log("\n请求工具列表...");
  send("tools/list");
}, 1000);

setTimeout(() => {
  console.log("\n调用计算工具...");
  send("tools/call", {
    name: "calculate",
    arguments: { expression: "1 + 1" },
  });
}, 1500);

setTimeout(() => {
  console.log("\n测试完成，关闭服务");
  server.kill();
  process.exit(0);
}, 3000);
