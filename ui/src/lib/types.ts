
// src/lib/types.ts

export interface Citation {
  source_name: string;
  description: string;
  link: string;
}

export interface AssistantMessage {
  summary: string;
  citations: Citation[];
  followUps: string[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string | AssistantMessage;
}
