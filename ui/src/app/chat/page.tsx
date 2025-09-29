'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import AgentEventList from '@/components/agent-event-list';
import AnswerCard from '@/components/answer-card';
import SearchBar from '@/components/search-bar';
import { LoadingComponent, WelcomeComponent } from '@/components/state-templates';
import { Card, CardContent } from '@/components/ui/card';
import { AgentEvent, AssistantMessage, Message } from '@/lib/types';

const createMockResponse = (query: string): AssistantMessage => ({
  summary: `'${query}'에 대한 정식 답변을 생성하는 중 문제가 발생했습니다. 이 예시는 서비스 복구 전까지 임시로 제공되는 기본 응답입니다.`,
  citations: [
    {
      source_name: '개인정보보호법 제5조',
      description: '개인정보 보호 기본 원칙을 규정한 조문입니다.',
      link: 'https://www.law.go.kr/LSW/lsInfoP.do?lsId=008032',
    },
  ],
  followUps: [
    '조금 더 구체적인 사실관계를 알려주실 수 있나요?',
    '관련된 판례나 사건 번호를 알고 계시면 함께 알려주세요.',
  ],
  confidence: 0,
  agentTrail: [],
});

const mapFinalResponseToAssistantMessage = (
  finalResponse: Record<string, unknown>,
  agentTrail: AgentEvent[],
): AssistantMessage => {
  const sources = Array.isArray(finalResponse.sources) ? finalResponse.sources : [];
  const followUps = Array.isArray(finalResponse.followUps) ? finalResponse.followUps : [];
  const relatedKeywords = Array.isArray(finalResponse.related_keywords)
    ? (finalResponse.related_keywords as string[])
    : undefined;

  return {
    summary: String(finalResponse.answer ?? ''),
    citations: sources.map((source: Record<string, unknown>) => ({
      source_name: String(source?.source_name ?? source?.title ?? '출처 미상'),
      description: String(source?.description ?? source?.excerpt ?? ''),
      link: String(source?.link ?? source?.url ?? '#'),
      confidence: typeof source?.confidence === 'number' ? source.confidence : undefined,
    })),
    followUps: followUps.map((item: unknown) => String(item)),
    confidence: typeof finalResponse.confidence === 'number' ? finalResponse.confidence : undefined,
    processingTime:
      typeof finalResponse.processing_time === 'number' ? finalResponse.processing_time : undefined,
    relatedKeywords,
    agentTrail,
  };
};

const normalizeAgentEvent = (event: Record<string, unknown>): AgentEvent => {
  const payload = (event?.payload ?? {}) as Record<string, unknown>;
  const timestamp = typeof payload.timestamp === 'string' ? payload.timestamp : undefined;

  return {
    type: String(event?.type ?? 'agent_step'),
    agent: String(event?.agent ?? 'unknown'),
    payload,
    timestamp,
  };
};

function ChatPageContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgentTrail, setCurrentAgentTrail] = useState<AgentEvent[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasProcessedInitialQuery = useRef(false);
  const searchParams = useSearchParams();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (currentAgentTrail.length > 0) {
      scrollToBottom();
    }
  }, [currentAgentTrail]);

  useEffect(() => {
    const initialQuery = searchParams.get('query');
    if (initialQuery && !hasProcessedInitialQuery.current) {
      hasProcessedInitialQuery.current = true;

      setTimeout(() => {
        const cleanedQuery = initialQuery.trim();
        if (!cleanedQuery) return;

        const userMessage: Message = {
          id: Date.now().toString(),
          role: 'user',
          content: cleanedQuery,
        };

        const history = [userMessage];
        setMessages(history);
        setQuery('');
        setIsLoading(true);
        void handleAPICall(cleanedQuery, history);
      }, 120);
    }
  }, [searchParams]);

  const handleAPICall = async (queryText: string, history: Message[]) => {
    setCurrentAgentTrail([]);
    let assistantMessageId: string | null = null;

    try {
      const conversationMessages = [
        {
          role: 'system',
          content:
            '당신은 한국 법률 질의를 지원하는 전문 LLM입니다. 질문의 맥락과 의도를 정확히 파악하고, 필요한 근거와 함께 신뢰도 있는 답변을 제공합니다.',
        },
        ...history.map((msg) => ({
          role: msg.role,
          content: typeof msg.content === 'string' ? msg.content : msg.content.summary,
        })),
      ];

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: conversationMessages }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`API 호출 실패: ${response.status} ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      assistantMessageId = (Date.now() + 1).toString();

      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
      };
      setMessages((prev) => [...prev, assistantMessage]);

      let buffer = '';
      let partialAnswer = '';
      const localTrail: AgentEvent[] = [];
      let streamCompleted = false;

      const flushLine = (line: string) => {
        if (!line.trim() || streamCompleted) return;

        try {
          const parsed = JSON.parse(line);
          const eventType = parsed.type;

          if (eventType === 'agent_step' || eventType === 'pipeline') {
            const normalized = normalizeAgentEvent(parsed);
            localTrail.push(normalized);
            setCurrentAgentTrail([...localTrail]);
            return;
          }

          if (eventType === 'content') {
            if (typeof parsed.content === 'string') {
              partialAnswer += parsed.content;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: partialAnswer }
                    : msg
                )
              );
            }
            return;
          }

          if (eventType === 'complete') {
            const finalResponse = parsed.final_response ?? {};
            const assistantPayload = mapFinalResponseToAssistantMessage(finalResponse, [...localTrail]);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: assistantPayload }
                  : msg
              )
            );
            setCurrentAgentTrail([]);
            streamCompleted = true;
            return;
          }

          if (eventType === 'error') {
            const errorMessage = String(parsed.error ?? 'Agent 파이프라인 처리 중 오류가 발생했습니다.');
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: errorMessage }
                  : msg
              )
            );
            setCurrentAgentTrail([]);
            streamCompleted = true;
            return;
          }
        } catch (error) {
          console.error('Streaming chunk parsing failed:', error, line);
        }
      };

      while (!streamCompleted) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          flushLine(line);
        }
      }

      if (!streamCompleted && buffer.trim().length > 0) {
        flushLine(buffer);
      }
    } catch (error) {
      console.error('API 스트림 처리 오류:', error);
      const assistantResponse = createMockResponse(queryText);

      if (assistantMessageId) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: assistantResponse }
              : msg
          )
        );
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: assistantResponse,
          },
        ]);
      }
    } finally {
      setIsLoading(false);
      setCurrentAgentTrail([]);
    }
  };

  const handleSearchSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const cleanedQuery = query.trim();
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: cleanedQuery,
    };

    const history = [...messages, userMessage];
    setMessages(history);
    setQuery('');
    setIsLoading(true);

    await handleAPICall(cleanedQuery, history);
  };

  const handleFollowUpClick = (question: string) => {
    setQuery(question);
    document.getElementById('main-search-bar')?.focus();
  };

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-16">
            <WelcomeComponent />
            <div className="mt-8">
              <SearchBar
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onSubmit={handleSearchSubmit}
              />
            </div>
          </div>
        )}

        <div className="space-y-8">
          {messages.map((msg) => (
            <div key={msg.id} className="w-full">
              {msg.role === 'user' ? (
                <div className="flex justify-end mb-4">
                  <div className="max-w-3xl">
                    <Card className="bg-primary text-primary-foreground border-0">
                      <CardContent className="p-4">
                        <p className="text-sm font-medium whitespace-pre-wrap">{msg.content as string}</p>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              ) : (
                <div className="w-full">
                  {typeof msg.content === 'string' ? (
                    <Card className="bg-card border border-border">
                      <CardContent className="p-6">
                        <div className="prose prose-sm max-w-none dark:prose-invert">
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </CardContent>
                    </Card>
                  ) : (
                    <AnswerCard
                      message={msg.content as AssistantMessage}
                      onFollowUpClick={handleFollowUpClick}
                    />
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {isLoading && currentAgentTrail.length > 0 && (
          <div className="mt-8">
            <AgentEventList events={currentAgentTrail} title="실시간 에이전트 진행 상황" />
          </div>
        )}

        {isLoading && (
          <div className="mt-8">
            <LoadingComponent />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length > 0 && (
        <div className="sticky bottom-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-t border-border p-4">
          <div className="max-w-3xl mx-auto">
            <SearchBar
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onSubmit={handleSearchSubmit}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ChatPageContent />
    </Suspense>
  );
}
