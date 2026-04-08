export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
    references?: Reference[];
    optionCards?: string[];
    isStreaming?: boolean;
}
export interface Reference {
    id: string;
    title: string;
    url?: string;
    snippet?: string;
}
export interface ChatConfig {
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
export interface VoiceRecognitionResult {
    text: string;
    confidence: number;
}
export interface ChatState {
    messages: Message[];
    isLoading: boolean;
    isStreaming: boolean;
    error: string | null;
}
export interface SSEEvent {
    type: 'reply' | 'error' | 'done' | 'references' | 'option_cards';
    payload?: any;
    error?: {
        message: string;
        code?: string;
    };
}
export interface VoiceButtonProps {
    onResult: (text: string) => void;
    disabled?: boolean;
    className?: string;
}
export interface MessageListProps {
    messages: Message[];
    className?: string;
}
export interface InputAreaProps {
    onSend: (message: string) => void;
    disabled?: boolean;
    placeholder?: string;
    enableVoice?: boolean;
    className?: string;
}
export interface ChatContainerProps {
    config: ChatConfig;
    className?: string;
}
