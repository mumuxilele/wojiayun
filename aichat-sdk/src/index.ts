// Components
export { ChatContainer, MessageList, InputArea, VoiceButton } from './components';

// Hooks
export { useChat } from './hooks/useChat';

// Services
export { ChatService } from './services/chatService';
export { VoiceService } from './services/voiceService';

// Types
export type {
  Message,
  Reference,
  ChatConfig,
  VoiceRecognitionResult,
  ChatState,
  SSEEvent,
  VoiceButtonProps,
  MessageListProps,
  InputAreaProps,
  ChatContainerProps,
} from './types';

// Styles
import './styles/index.css';
