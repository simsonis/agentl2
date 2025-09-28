'use client';

import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Message, AssistantMessage } from '@/lib/types';
import SearchBar from '@/components/search-bar';
import AnswerCard from '@/components/answer-card';
import { LoadingComponent, WelcomeComponent } from '@/components/state-templates';
import { Card, CardContent } from '@/components/ui/card';

// Mock Assistant Response
const createMockResponse = (query: string): AssistantMessage => ({
  summary: `'${query}'에 대한 답변입니다. 개인정보보호법 제15조(개인정보의 수집·이용)에 따르면, 정보주체의 동의를 받은 경우에만 개인정보를 수집할 수 있으며, 그 수집 목적의 범위에서 이용할 수 있습니다. 이는 정보주체의 권리를 보장하기 위한 핵심적인 조항입니다.`,
  citations: [
    {
      source_name: '개인정보보호법 제15조',
      description: '개인정보의 수집·이용에 관한 조항입니다.',
      link: 'https://www.law.go.kr/LSW/lsInfoP.do?lsId=008032&chrClsCd=010202&urlMode=lsInfoP&efYd=20230915#0000',
    },
    {
      source_name: '관련 판례 2022다12345',
      description: '개인정보 수집 동의의 유효 요건에 대한 대법원 판례입니다.',
      link: '#',
    },
  ],
  followUps: [
    '개인정보의 제3자 제공 요건은?',
    '마케팅 목적으로 개인정보를 사용하려면?',
    '주민등록번호 처리 기준에 대해 알려줘',
  ],
});

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasProcessedInitialQuery = useRef(false);
  const searchParams = useSearchParams();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle initial query from URL parameters
  useEffect(() => {
    const initialQuery = searchParams.get('query');
    if (initialQuery && !hasProcessedInitialQuery.current) {
      hasProcessedInitialQuery.current = true;
      setQuery(initialQuery);

      // Auto-submit the query
      setTimeout(() => {
        const userMessage: Message = {
          id: Date.now().toString(),
          role: 'user',
          content: initialQuery.trim(),
        };

        setMessages([userMessage]);
        setQuery('');
        setIsLoading(true);
        handleAPICall(initialQuery.trim());
      }, 100);
    }
  }, [searchParams]);

  const handleAPICall = async (queryText: string) => {
    try {
      // Build conversation history for API
      const conversationMessages = [
        {
          role: 'system',
          content: '당신은 한국의 법률 전문가입니다. 사용자의 법률 관련 질문에 정확하고 도움이 되는 답변을 제공해주세요. 관련 법령이나 판례가 있다면 인용해주세요.',
        },
        // Include previous conversation history
        ...messages.map(msg => ({
          role: msg.role,
          content: typeof msg.content === 'string' ? msg.content : msg.content.summary || ''
        })),
        {
          role: 'user',
          content: queryText,
        },
      ];

      // Call actual API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: conversationMessages,
        }),
      });

      if (!response.ok) {
        throw new Error('API 호출 실패');
      }

      // Read the streaming response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('응답을 읽을 수 없습니다');
      }

      let accumulatedContent = '';
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
      };

      // Add empty assistant message first
      setMessages((prev) => [...prev, assistantMessage]);

      // Read the stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        accumulatedContent += chunk;

        // Update the assistant message with accumulated content
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessage.id
              ? { ...msg, content: accumulatedContent }
              : msg
          )
        );
      }

      setIsLoading(false);
    } catch (error) {
      console.error('API 호출 에러:', error);
      setIsLoading(false);

      // Fallback to mock response on error
      const assistantResponse = createMockResponse(queryText);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: assistantResponse,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }
  };

  const handleSearchSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentQuery = query.trim();
    setQuery('');
    setIsLoading(true);

    await handleAPICall(currentQuery);
  };

  const handleFollowUpClick = (question: string) => {
    // This will trigger a new search
    setQuery(question);
    // We can't submit a form from here, so we'll just set the query
    // and let the user press enter. A more advanced implementation
    // would trigger the submission flow directly.
    document.getElementById('main-search-bar')?.focus();
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Chat Messages Area */}
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
                        <p className="text-sm font-medium">{msg.content as string}</p>
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

        {isLoading && (
          <div className="mt-8">
            <LoadingComponent />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Fixed Search Bar at Bottom (only when there are messages) */}
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