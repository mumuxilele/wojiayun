import { ChatConfig } from '../types';

export class ChatService {
  private config: ChatConfig;
  private abortController: AbortController | null = null;

  constructor(config: ChatConfig) {
    this.config = {
      apiUrl: '/api',
      ...config,
    };
  }

  async getUserInfo(): Promise<any> {
    const response = await fetch(
      `${this.config.apiUrl}/userinfo?access_token=${encodeURIComponent(this.config.accessToken)}`
    );
    const result = await response.json();
    if (result.success && result.data) {
      return result.data.data || result.data;
    }
    throw new Error(result.error || '获取用户信息失败');
  }

  async *sendMessage(
    content: string,
    visitorId: string,
    sessionId: string,
    customVariables?: Record<string, string>
  ): AsyncGenerator<{ type: string; payload?: any; error?: any }> {
    this.abortController = new AbortController();

    const response = await fetch(`${this.config.apiUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        visitor_biz_id: visitorId,
        content,
        custom_variables: customVariables,
        stream: 'enable',
        incremental: true,
      }),
      signal: this.abortController.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data:')) {
          try {
            const data = JSON.parse(line.substring(5).trim());
            yield data;
          } catch (e) {
            console.error('Parse error:', e);
          }
        }
      }
    }
  }

  abort() {
    this.abortController?.abort();
  }
}
