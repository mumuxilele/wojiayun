#!/usr/bin/env node

/**
 * Wojiayun MCP Server - Streamable HTTP 模式
 * 
 * 支持通过 HTTP 网络访问的 MCP 服务
 * 使用 Streamable HTTP 传输方式（MCP 2025-03-26 规范）
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import express from "express";
import cors from "cors";
import { z } from "zod";
import { randomUUID } from "crypto";

const app = express();
const PORT = process.env.MCP_PORT || 3001;

// 启用 CORS
app.use(cors({
  origin: "*",
  methods: ["GET", "POST", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Accept", "Mcp-Session-Id"],
  exposedHeaders: ["Mcp-Session-Id"],
}));

// 启用 JSON 解析
app.use(express.json());

// 存储活跃的会话
const sessions = new Map();

// 创建 MCP 服务器实例
function createMcpServer() {
  const server = new McpServer({
    name: "wojiayun-mcp",
    version: "1.0.0",
  });

  // ==================== Tools ====================

  // 示例工具：获取服务器状态
  server.tool(
    "get_server_status",
    "获取服务器运行状态",
    {},
    async () => {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              status: "running",
              uptime: process.uptime(),
              memory: process.memoryUsage(),
              timestamp: new Date().toISOString(),
            }, null, 2),
          },
        ],
      };
    }
  );

  // 示例工具：执行数学计算
  server.tool(
    "calculate",
    "执行数学计算",
    {
      expression: z.string().describe("数学表达式，如 2 + 2"),
    },
    async ({ expression }) => {
      try {
        const result = Function(`"use strict"; return (${expression})`)();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                expression,
                result,
              }, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                error: "计算失败",
                message: error.message,
              }, null, 2),
            },
          ],
          isError: true,
        };
      }
    }
  );

  // 示例工具：文本处理
  server.tool(
    "process_text",
    "处理文本（转换大小写、统计字数等）",
    {
      text: z.string().describe("要处理的文本"),
      operation: z.enum(["uppercase", "lowercase", "count", "reverse"]).describe("操作类型"),
    },
    async ({ text, operation }) => {
      let result;
      switch (operation) {
        case "uppercase":
          result = text.toUpperCase();
          break;
        case "lowercase":
          result = text.toLowerCase();
          break;
        case "count":
          result = {
            characters: text.length,
            words: text.split(/\s+/).filter(Boolean).length,
            lines: text.split("\n").length,
          };
          break;
        case "reverse":
          result = text.split("").reverse().join("");
          break;
        default:
          throw new Error(`未知操作: ${operation}`);
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              operation,
              input: text,
              result,
            }, null, 2),
          },
        ],
      };
    }
  );

  // ==================== Resources ====================

  server.resource(
    "config://server",
    "服务器配置信息",
    async () => ({
      contents: [
        {
          uri: "config://server",
          text: JSON.stringify({
            name: "wojiayun-mcp",
            version: "1.0.0",
            environment: process.env.NODE_ENV || "development",
            platform: process.platform,
            nodeVersion: process.version,
          }, null, 2),
          mimeType: "application/json",
        },
      ],
    })
  );

  server.resource(
    "info://system",
    "系统运行信息",
    async () => ({
      contents: [
        {
          uri: "info://system",
          text: JSON.stringify({
            hostname: process.env.HOSTNAME || "unknown",
            pid: process.pid,
            arch: process.arch,
            memoryUsage: process.memoryUsage(),
          }, null, 2),
          mimeType: "application/json",
        },
      ],
    })
  );

  // ==================== Prompts ====================

  server.prompt(
    "code_review",
    "代码审查提示词",
    {
      code: z.string().describe("要审查的代码"),
      language: z.string().optional().describe("编程语言"),
    },
    ({ code, language }) => ({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `请审查以下${language ? language + " " : ""}代码，指出潜在问题和改进建议：\n\n\`\`\`${language || ""}\n${code}\n\`\`\``,
          },
        },
      ],
    })
  );

  server.prompt(
    "generate_docs",
    "生成文档提示词",
    {
      topic: z.string().describe("文档主题"),
      style: z.enum(["technical", "user-friendly", "api"]).optional().describe("文档风格"),
    },
    ({ topic, style }) => ({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `请为以下主题生成${style || "technical"}风格的文档：\n\n主题：${topic}`,
          },
        },
      ],
    })
  );

  return server;
}

// ==================== HTTP 路由 ====================

// MCP 端点 - 处理所有 MCP 请求
app.all("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"];
  
  try {
    let transport;
    let server;

    if (sessionId && sessions.has(sessionId)) {
      // 已有会话，获取现有的 transport
      const session = sessions.get(sessionId);
      transport = session.transport;
      server = session.server;
    } else if (req.method === "POST") {
      // 新会话
      server = createMcpServer();
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (newSessionId) => {
          console.log(`新会话初始化: ${newSessionId}`);
          sessions.set(newSessionId, { transport, server });
        },
      });

      // 连接服务器和传输
      await server.connect(transport);
    } else {
      // GET 或 DELETE 请求但没有会话 ID
      res.status(400).json({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Bad Request: 缺少 Mcp-Session-Id 头",
        },
        id: null,
      });
      return;
    }

    // 处理请求
    await transport.handleRequest(req, res);
  } catch (error) {
    console.error("MCP 请求处理错误:", error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: "2.0",
        error: {
          code: -32603,
          message: "Internal server error",
        },
        id: null,
      });
    }
  }
});

// 健康检查
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "wojiayun-mcp",
    version: "1.0.0",
    transport: "streamable-http",
    timestamp: new Date().toISOString(),
    activeSessions: sessions.size,
  });
});

// 根路径
app.get("/", (req, res) => {
  res.json({
    name: "Wojiayun MCP Server",
    version: "1.0.0",
    description: "MCP 服务 - Streamable HTTP 模式",
    transport: "streamable-http",
    endpoint: "/mcp",
    healthCheck: "/health",
    protocol: "MCP 2025-03-26",
    usage: {
      description: "使用 MCP 客户端连接到 /mcp 端点",
      example: {
        "mcpServers": {
          "wojiayun": {
            "url": "http://47.98.238.209:3001/mcp"
          }
        }
      }
    },
  });
});

// 定期清理过期会话（30 分钟无活动）
setInterval(() => {
  const now = Date.now();
  for (const [id, session] of sessions.entries()) {
    if (session.lastActivity && now - session.lastActivity > 30 * 60 * 1000) {
      console.log(`清理过期会话: ${id}`);
      sessions.delete(id);
    }
  }
}, 60 * 1000);

// ==================== 启动服务器 ====================

app.listen(PORT, () => {
  console.log(`Wojiayun MCP Server 已启动`);
  console.log(`传输模式: Streamable HTTP`);
  console.log(`监听端口: ${PORT}`);
  console.log(`MCP 端点: http://0.0.0.0:${PORT}/mcp`);
  console.log(`健康检查: http://0.0.0.0:${PORT}/health`);
});
