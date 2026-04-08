import { VoiceRecognitionResult } from '../types';
export declare class VoiceService {
    private recognition;
    private isSupported;
    constructor();
    isVoiceSupported(): boolean;
    startRecognition(): Promise<VoiceRecognitionResult>;
    stopRecognition(): void;
}
