import { VoiceRecognitionResult } from '../types';

export class VoiceService {
  private recognition: SpeechRecognition | null = null;
  private isSupported: boolean;

  constructor() {
    this.isSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    
    if (this.isSupported) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      this.recognition = new SpeechRecognition();
      this.recognition.lang = 'zh-CN';
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.maxAlternatives = 1;
    }
  }

  isVoiceSupported(): boolean {
    return this.isSupported;
  }

  startRecognition(): Promise<VoiceRecognitionResult> {
    return new Promise((resolve, reject) => {
      if (!this.recognition) {
        reject(new Error('语音识别不支持'));
        return;
      }

      this.recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        const confidence = event.results[0][0].confidence;
        resolve({ text, confidence });
      };

      this.recognition.onerror = (event) => {
        let errorMsg = '语音识别失败';
        switch (event.error) {
          case 'no-speech':
            errorMsg = '未检测到语音';
            break;
          case 'audio-capture':
            errorMsg = '无法访问麦克风';
            break;
          case 'not-allowed':
            errorMsg = '麦克风权限被拒绝';
            break;
          case 'network':
            errorMsg = '网络错误';
            break;
        }
        reject(new Error(errorMsg));
      };

      this.recognition.start();
    });
  }

  stopRecognition() {
    this.recognition?.stop();
  }
}
