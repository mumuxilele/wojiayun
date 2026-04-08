import React, { useEffect, useState } from 'react';
import { ChatContainerProps, Message, ChatConfig } from '../types';
import { useChat } from '../hooks/useChat';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import './ChatContainer.css';

export const ChatContainer: React.FC<ChatContainerProps> = ({
  config,
  className = ''
}) => {
  const { 
    messages, 
    isStreaming, 
    error, 
    visitorId, 
    sendMessage, 
    clearMessages 
  } = useChat(config);

  const [showWelcome, setShowWelcome] = useState(true);

  // 添加欢迎消息
  useEffect(() => {
    if (config.welcomeMessage && messages.length === 0) {
      const welcomeMsg: Message = {
        id: 'welcome',
        role: 'assistant',
        content: config.welcomeMessage,
        timestamp: new Date().toISOString(),
      };
      // 这里需要通过 useChat 的初始化逻辑添加欢迎消息
      // 暂时通过本地状态处理
    }
  }, [config.welcomeMessage, messages.length]);

  const handleSend = (content: string) => {
    setShowWelcome(false);
    sendMessage(content);
  };

  const handleClear = () => {
    clearMessages();
    setShowWelcome(true);
  };

  return (
    <div className={`chat-container ${config.theme === 'dark' ? 'dark-theme' : ''} ${className}`}>
      <div className="chat-header">
        <div className="header-title">
          <span className="header-icon">🤖</span>
          <span>AI 助手</span>
        </div>
        <button 
          className="clear-btn" 
          onClick={handleClear}
          title="清空对话"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>

      <div className="chat-body">
        {showWelcome && config.welcomeMessage && messages.length === 0 ? (
          <div className="welcome-message">
            <div className="welcome-icon">👋</div>
            <div className="welcome-text">{config.welcomeMessage}</div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
        
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}
      </div>

      <InputArea
        onSend={handleSend}
        disabled={isStreaming || !visitorId}
        placeholder={config.placeholder || '输入消息...'}
        enableVoice={config.enableVoice !== false}
      />

      {isStreaming && (
        <div className="streaming-indicator">
          <span className="dot"></span>
          <span className="dot"></span>
          <span className="dot"></span>
        </div>
      )}
    </div>
  );
};
