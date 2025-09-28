// IMPORTANT! Set the runtime to edge
export const runtime = 'edge';

// Get LLM service URL from environment
const LLM_SERVICE_URL = process.env.LLM_SERVICE_URL || 'http://localhost:8001';

// Helper function to create a streaming response from Agent Pipeline
function createAgentStream(response: Response): ReadableStream<Uint8Array> {
  return new ReadableStream({
    async pull(controller) {
      const encoder = new TextEncoder();
      const reader = response.body?.getReader();

      if (!reader) {
        controller.close();
        return;
      }

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Decode the chunk and parse SSE data
          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split('\n').filter(line => line.trim());

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === 'agent_step') {
                  // Show agent step progress
                  controller.enqueue(encoder.encode(`🔄 ${data.agent}: ${data.step}\n`));
                } else if (data.type === 'content') {
                  // Stream content chunks
                  controller.enqueue(encoder.encode(data.content));
                } else if (data.type === 'complete') {
                  // Add final formatting with sources
                  const final = data.final_response;
                  if (final.sources && final.sources.length > 0) {
                    controller.enqueue(encoder.encode('\n\n📚 참고자료:\n'));
                    final.sources.forEach((source: any, index: number) => {
                      controller.enqueue(encoder.encode(`${index + 1}. ${source.source_name}\n`));
                    });
                  }

                  if (final.followUps && final.followUps.length > 0) {
                    controller.enqueue(encoder.encode('\n💡 추가 질문:\n'));
                    final.followUps.forEach((question: string, index: number) => {
                      controller.enqueue(encoder.encode(`${index + 1}. ${question}\n`));
                    });
                  }
                  break;
                } else if (data.type === 'error') {
                  controller.enqueue(encoder.encode(`❌ 오류: ${data.error}`));
                  break;
                }
              } catch (parseError) {
                console.error('Error parsing SSE data:', parseError);
              }
            }
          }
        }
      } catch (error) {
        console.error('Stream error:', error);
        controller.enqueue(encoder.encode('❌ 스트림 처리 중 오류가 발생했습니다.'));
      } finally {
        controller.close();
      }
    },
  });
}

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    // Call the LLM Agent service instead of OpenAI directly
    const response = await fetch(`${LLM_SERVICE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        conversation_id: null // Could be extracted from request if needed
      }),
    });

    if (!response.ok) {
      throw new Error(`LLM service error: ${response.status} ${response.statusText}`);
    }

    // Create streaming response from Agent Pipeline
    const stream = createAgentStream(response);

    // Respond with the stream
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
      },
    });
  } catch (error) {
    console.error('Chat API error:', error);

    // Fallback response
    return new Response(
      `❌ Agent 체인 처리 중 오류가 발생했습니다: ${error}\n\n💡 다음을 확인해 주세요:\n1. LLM 서비스가 실행 중인지 확인\n2. 네트워크 연결 상태 확인\n3. 잠시 후 다시 시도`,
      {
        status: 500,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' }
      }
    );
  }
}
