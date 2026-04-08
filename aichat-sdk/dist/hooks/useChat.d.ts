import { Message, ChatConfig } from '../types';
export declare function useChat(config: ChatConfig): {
    messages: Message[];
    isStreaming: boolean;
    error: string | null;
    visitorId: string | null;
    sendMessage: (content: string) => Promise<void>;
    clearMessages: () => void;
};
