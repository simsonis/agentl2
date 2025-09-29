// src/lib/types.ts

export interface Citation {
  source_name: string;
  description: string;
  link: string;
  confidence?: number;
}

export interface AgentEventPayload {
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  context?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AgentEvent {
  type: string;
  agent: string;
  payload: AgentEventPayload;
  timestamp?: string;
}

export interface AssistantMessage {
  summary: string;
  citations: Citation[];
  followUps: string[];
  confidence?: number;
  processingTime?: number;
  relatedKeywords?: string[];
  agentTrail?: AgentEvent[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string | AssistantMessage;
}
