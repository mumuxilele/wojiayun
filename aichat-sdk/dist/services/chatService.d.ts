import { ChatConfig } from '../types';
export declare class ChatService {
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
