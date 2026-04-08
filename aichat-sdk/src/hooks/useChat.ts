import { useState, useCallback, useRef, useEffect } from 'react';
import { ChatService } from '../services/chatService';
import { Message, ChatConfig, SSEEvent } from '../types';

export function useChat(config: ChatConfig) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visitorId, setVisitorId] = useState<string | null>(null);
  const [sessionId] = useState(() => 
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    })
  );

  const chatServiceRef = useRef<ChatService | null>(null);
  const currentMessageRef = useRef<string>('');

  // 初始化服务
  useEffect(() => {
    chatServiceRef.current = new ChatService(config);
    
    // 获取用户信息
    chatServiceRef.current.getUserInfo(config.accessToken)
      .then(userInfo => {
        setVisitorId(userInfo.userId || userInfo.empId || userInfo.id);
      })
      .catch(err => {
        setError(err.message);
      });
  }, [config]);

  // 发送消息
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || !visitorId || isStreaming) return;

    setError(null);
    setIsStreaming(true);

    // 添加用户消息
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // 创建助手消息占位
    const assistantMessageId = `assistant_${Date.now()}`;
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }]);

    currentMessageRef.current = '';

    try {
      const customVariables = config.customVariables || {};
      const generator = chatServiceRef.current!.sendMessage(
        content,
        visitorId,
        sessionId,
        { ...customVariables, access_token: config.accessToken }
      );

      for await (const event of generator) {
        handleSSEEvent(event, assistantMessageId);
      }

      // 标记流式结束
      setMessages(prev => prev.map(m => 
        m.id === assistantMessageId ? { ...m, isStreaming: false } : m
      ));
    } catch (err: any) {
      setError(err.message);
      setMessages(prev => prev.map(m => 
        m.id === assistantMessageId 
          ? { ...m, content: '❌ 请求失败，请重试', isStreaming: false }
          : m
      ));
    } finally {
      setIsStreaming(false);
    }
  }, [visitorId, isStreaming, sessionId, config]);

  // 处理 SSE 事件
  const handleSSEEvent = useCallback((event: SSEEvent, messageId: string) => {
    switch (event.type) {
      case 'reply':
        // 关键修复：检查 is_from_self 字段
        // is_from_self: true 表示用户消息，false 表示机器人消息
        // 我们只需要处理机器人消息，跳过用户消息
        if (event.payload?.is_from_self === true) {
          console.log('跳过用户消息:', event.payload.content);
          break;
        }
        
        if (event.payload?.content) {
          currentMessageRef.current += event.payload.content;
          setMessages(prev => prev.map(m => 
            m.id === messageId 
              ? { ...m, content: currentMessageRef.current }
              : m
          ));
        }
        break;
      case 'error':
        setError(event.error?.message || '发生错误');
        setMessages(prev => prev.map(m => 
          m.id === messageId 
            ? { ...m, content: `❌ ${event.error?.message || '发生错误'}`, isStreaming: false }
            : m
        ));
        break;
    }
  }, []);

  // 清空消息
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isStreaming,
    error,
    visitorId,
    sendMessage,
    clearMessages,
  };
}
