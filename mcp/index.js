#!/usr/bin/env node

/**
 * Wojiayun MCP Server
 * 
 * 一个标准的 MCP (Model Context Protocol) 服务实现
 * 支持 tools、resources、prompts 三大核心能力
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// 创建 MCP 服务器实例
const server = new McpServer({
  name: "wojiayun-mcp",
  version: "1.0.0",
  capabilities: {
    tools: {},
    resources: {},
    prompts: {},
  },
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
      // 安全的数学表达式求值
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

// 示例资源：服务器配置
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

// 示例资源：系统信息
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
          cpuUsage: process.cpuUsage(),
        }, null, 2),
        mimeType: "application/json",
      },
    ],
  })
);

// ==================== Prompts ====================

// 示例提示词：代码审查
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

// 示例提示词：文档生成
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

// ==================== 启动服务器 ====================

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Wojiayun MCP Server 已启动");
}

main().catch((error) => {
  console.error("服务器启动失败:", error);
  process.exit(1);
});
