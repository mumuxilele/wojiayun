import React, { useEffect, useRef } from 'react';
import { MessageListProps, Message } from '../types';
import './MessageList.css';

export const MessageList: React.FC<MessageListProps> = ({ 
  messages, 
  className = '' 
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 渲染 Markdown 内容（简化版，实际可使用 marked.js）
  const renderContent = (content: string) => {
    // 代码块处理
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    let processed = content;
    
    // 先处理代码块
    processed = processed.replace(codeBlockRegex, (match, lang, code) => {
      return `<pre class="code-block"><code class="language-${lang || 'plaintext'}">${escapeHtml(code.trim())}</code></pre>`;
    });
    
    // 行内代码
    processed = processed.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    // 粗体
    processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // 斜体
    processed = processed.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // 换行
    processed = processed.replace(/\n/g, '<br>');
    
    return processed;
  };

  const escapeHtml = (text: string) => {
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
  };

  const renderMessage = (message: Message) => {
    const isUser = message.role === 'user';
    
    return (
      <div
        key={message.id}
        ref={(el) => {
          if (el) messageRefs.current.set(message.id, el);
        }}
        className={`message ${isUser ? 'user-message' : 'assistant-message'} ${message.isStreaming ? 'streaming' : ''}`}
      >
        <div className="message-avatar">
          {isUser ? '👤' : '🤖'}
        </div>
        <div className="message-content">
          <div 
            className="message-text"
            dangerouslySetInnerHTML={{ __html: renderContent(message.content) }}
          />
          {message.references && message.references.length > 0 && (
            <div className="message-references">
              <div className="references-title">📚 参考资料</div>
              {message.references.map((ref, idx) => (
                <div key={ref.id || idx} className="reference-item">
                  <a href={ref.url} target="_blank" rel="noopener noreferrer">
                    {ref.title}
                  </a>
                  {ref.snippet && <p className="reference-snippet">{ref.snippet}</p>}
                </div>
              ))}
            </div>
          )}
          {message.optionCards && message.optionCards.length > 0 && (
            <div className="option-cards">
              {message.optionCards.map((card, idx) => (
                <div key={idx} className="option-card">
                  {card}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`message-list ${className}`}>
      {messages.map(renderMessage)}
      <div ref={messagesEndRef} className="messages-end" />
    </div>
  );
};
