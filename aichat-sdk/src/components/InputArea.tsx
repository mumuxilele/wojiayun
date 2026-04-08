import React, { useState, useRef, useCallback } from 'react';
import { InputAreaProps } from '../types';
import { VoiceButton } from './VoiceButton';
import './InputArea.css';

export const InputArea: React.FC<InputAreaProps> = ({
  onSend,
  disabled = false,
  placeholder = '输入消息...',
  enableVoice = true,
  className = ''
}) => {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmedValue = inputValue.trim();
    if (trimmedValue && !disabled) {
      onSend(trimmedValue);
      setInputValue('');
      inputRef.current?.focus();
    }
  }, [inputValue, disabled, onSend]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleVoiceResult = useCallback((text: string) => {
    setInputValue(prev => prev + text);
    inputRef.current?.focus();
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  }, []);

  // 自动调整输入框高度
  const adjustTextareaHeight = useCallback(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  return (
    <div className={`input-area ${className}`}>
      <div className="input-container">
        <textarea
          ref={inputRef}
          className="message-input"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onInput={adjustTextareaHeight}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
        />
        <div className="input-actions">
          {enableVoice && (
            <VoiceButton 
              onResult={handleVoiceResult} 
              disabled={disabled}
              className="action-btn"
            />
          )}
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={disabled || !inputValue.trim()}
            type="button"
          >
            <svg 
              width="20" 
              height="20" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};
