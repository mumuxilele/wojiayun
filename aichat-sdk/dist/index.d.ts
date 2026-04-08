import React from 'react';

interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
    references?: Reference[];
    optionCards?: string[];
    isStreaming?: boolean;
}
interface Reference {
    id: string;
    title: string;
    url?: string;
    snippet?: string;
}
interface ChatConfig {
    accessToken: string;
    apiUrl?: string;
    visitorId?: string;
    sessionId?: string;
    customVariables?: Record<string, string>;
    onMessage?: (message: Message) => void;
    onError?: (error: Error) => void;
    placeholder?: string;
    welcomeMessage?: string;
    enableVoice?: boolean;
    theme?: 'light' | 'dark';
}
interface VoiceRecognitionResult {
    text: string;
    confidence: number;
}
interface ChatState {
    messages: Message[];
    isLoading: boolean;
    isStreaming: boolean;
    error: string | null;
}
interface SSEEvent {
    type: 'reply' | 'error' | 'done' | 'references' | 'option_cards';
    payload?: any;
    error?: {
        message: string;
        code?: string;
    };
}
interface VoiceButtonProps {
    onResult: (text: string) => void;
    disabled?: boolean;
    className?: string;
}
interface MessageListProps {
    messages: Message[];
    className?: string;
}
interface InputAreaProps {
    onSend: (message: string) => void;
    disabled?: boolean;
    placeholder?: string;
    enableVoice?: boolean;
    className?: string;
}
interface ChatContainerProps {
    config: ChatConfig;
    className?: string;
}

declare const ChatContainer: React.FC<ChatContainerProps>;

declare const MessageList: React.FC<MessageListProps>;

declare const InputArea: React.FC<InputAreaProps>;

declare const VoiceButton: React.FC<VoiceButtonProps>;

declare function useChat(config: ChatConfig): {
    messages: Message[];
    isStreaming: boolean;
    error: string | null;
    visitorId: string | null;
    sendMessage: (content: string) => Promise<void>;
    clearMessages: () => void;
};

declare class ChatService {
    private config;
    private abortController;
    constructor(config: ChatConfig);
    getUserInfo(): Promise<any>;
    sendMessage(content: string, visitorId: string, sessionId: string, customVariables?: Record<string, string>): AsyncGenerator<{
        type: string;
        payload?: any;
        error?: any;
    }>;
    abort(): void;
}

declare class VoiceService {
    private recognition;
    private isSupported;
    constructor();
    isVoiceSupported(): boolean;
    startRecognition(): Promise<VoiceRecognitionResult>;
    stopRecognition(): void;
}

export { ChatContainer, ChatService, InputArea, MessageList, VoiceButton, VoiceService, useChat };
export type { ChatConfig, ChatContainerProps, ChatState, InputAreaProps, Message, MessageListProps, Reference, SSEEvent, VoiceButtonProps, VoiceRecognitionResult };
