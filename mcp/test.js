#!/usr/bin/env node

/**
 * MCP Server 测试脚本
 * 用于验证 MCP 服务是否正常工作
 */

import { spawn } from "child_process";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// 启动 MCP 服务
const server = spawn("node", [join(__dirname, "index.js")], {
  stdio: ["pipe", "pipe", "pipe"],
});

let responseBuffer = "";
let requestId = 0;

// 发送 JSON-RPC 请求
function sendRequest(method, params = {}) {
  const request = {
    jsonrpc: "2.0",
    id: ++requestId,
    method,
    params,
  };
  const message = JSON.stringify(request);
  const header = `Content-Length: ${Buffer.byteLength(message)}\r\n\r\n`;
  server.stdin.write(header + message);
}

// 处理响应
server.stdout.on("data", (data) => {
  responseBuffer += data.toString();
  
  // 尝试解析响应
  const lines = responseBuffer.split("\r\n");
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith("Content-Length:")) {
      const length = parseInt(lines[i].split(":")[1].trim());
      const contentStart = responseBuffer.indexOf("\r\n\r\n") + 4;
      if (responseBuffer.length >= contentStart + length) {
        const content = responseBuffer.substring(contentStart, contentStart + length);
        try {
          const response = JSON.parse(content);
          console.log("\n收到响应:", JSON.stringify(response, null, 2));
        } catch (e) {
          console.error("解析响应失败:", e.message);
        }
        responseBuffer = responseBuffer.substring(contentStart + length);
      }
    }
  }
});

server.stderr.on("data", (data) => {
  console.log("服务日志:", data.toString().trim());
});

// 测试序列
async function runTests() {
  console.log("=== MCP Server 测试开始 ===\n");

  // 1. 初始化
  console.log("1. 发送初始化请求...");
  sendRequest("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: {
      name: "test-client",
      version: "1.0.0",
    },
  });

  // 等待初始化完成
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // 2. 发送 initialized 通知
  console.log("\n2. 发送 initialized 通知...");
  const notification = {
    jsonrpc: "2.0",
    method: "notifications/initialized",
  };
  const message = JSON.stringify(notification);
  const header = `Content-Length: ${Buffer.byteLength(message)}\r\n\r\n`;
  server.stdin.write(header + message);

  await new Promise((resolve) => setTimeout(resolve, 500));

  // 3. 列出可用工具
  console.log("\n3. 请求工具列表...");
  sendRequest("tools/list", {});

  await new Promise((resolve) => setTimeout(resolve, 500));

  // 4. 调用计算工具
  console.log("\n4. 调用计算工具...");
  sendRequest("tools/call", {
    name: "calculate",
    arguments: {
      expression: "2 + 2 * 3",
    },
  });

  await new Promise((resolve) => setTimeout(resolve, 500));

  // 5. 调用文本处理工具
  console.log("\n5. 调用文本处理工具...");
  sendRequest("tools/call", {
    name: "process_text",
    arguments: {
      text: "Hello MCP World",
      operation: "uppercase",
    },
  });

  await new Promise((resolve) => setTimeout(resolve, 500));

  // 6. 列出资源
  console.log("\n6. 请求资源列表...");
  sendRequest("resources/list", {});

  await new Promise((resolve) => setTimeout(resolve, 500));

  // 7. 读取资源
  console.log("\n7. 读取服务器配置资源...");
  sendRequest("resources/read", {
    uri: "config://server",
  });

  await new Promise((resolve) => setTimeout(resolve, 500));

  // 8. 列出提示词
  console.log("\n8. 请求提示词列表...");
  sendRequest("prompts/list", {});

  await new Promise((resolve) => setTimeout(resolve, 1000));

  console.log("\n=== 测试完成 ===");
  server.kill();
  process.exit(0);
}

// 运行测试
runTests().catch((error) => {
  console.error("测试失败:", error);
  server.kill();
  process.exit(1);
});
