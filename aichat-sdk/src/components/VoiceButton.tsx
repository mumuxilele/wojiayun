import React, { useState, useRef, useCallback, useEffect } from 'react';
import { VoiceButtonProps } from '../types';

export const VoiceButton: React.FC<VoiceButtonProps> = ({ 
  onResult, 
  disabled = false,
  className = '' 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const recognitionRef = useRef<any>(null);
  const longPressTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isLongPressRef = useRef(false);

  useEffect(() => {
    // 检查浏览器支持
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'zh-CN';

      recognitionRef.current.onresult = (event: any) => {
        const result = event.results[event.results.length - 1];
        if (result.isFinal) {
          const text = result[0].transcript;
          onResult(text);
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('语音识别错误:', event.error);
        setIsRecording(false);
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };

      setIsSupported(true);
    }
  }, [onResult]);

  const startRecording = useCallback(() => {
    if (!isSupported || disabled || isRecording) return;
    
    try {
      recognitionRef.current?.start();
      setIsRecording(true);
    } catch (error) {
      console.error('启动语音识别失败:', error);
    }
  }, [isSupported, disabled, isRecording]);

  const stopRecording = useCallback(() => {
    if (!isRecording) return;
    
    try {
      recognitionRef.current?.stop();
      setIsRecording(false);
    } catch (error) {
      console.error('停止语音识别失败:', error);
    }
  }, [isRecording]);

  // 长按开始
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    isLongPressRef.current = false;
    longPressTimerRef.current = setTimeout(() => {
      isLongPressRef.current = true;
      startRecording();
    }, 300);
  }, [startRecording]);

  // 长按结束
  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
    }
    if (isLongPressRef.current) {
      stopRecording();
    }
  }, [stopRecording]);

  // 鼠标事件（PC端）
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isLongPressRef.current = false;
    longPressTimerRef.current = setTimeout(() => {
      isLongPressRef.current = true;
      startRecording();
    }, 300);
  }, [startRecording]);

  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
    }
    if (isLongPressRef.current) {
      stopRecording();
    }
  }, [stopRecording]);

  const handleMouseLeave = useCallback(() => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
    }
    if (isRecording) {
      stopRecording();
    }
  }, [isRecording, stopRecording]);

  if (!isSupported) {
    return null;
  }

  return (
    <button
      type="button"
      className={`voice-btn ${isRecording ? 'recording' : ''} ${className}`}
      disabled={disabled}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      title="长按说话"
    >
      <svg 
        width="20" 
        height="20" 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2"
      >
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
      </svg>
      {isRecording && <span className="recording-indicator">录音中...</span>}
    </button>
  );
};
