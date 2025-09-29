// IMPORTANT! Set the runtime to edge
export const runtime = 'edge';

// Get LLM service URL from environment
const LLM_SERVICE_URL = process.env.LLM_SERVICE_URL || 'http://localhost:8001';

// Helper function to create a streaming response from Agent Pipeline
function createAgentStream(response: Response): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let buffer = '';

  return new ReadableStream({
    async start(controller) {
      const reader = response.body?.getReader();

      if (!reader) {
        controller.enqueue(
          encoder.encode(
            JSON.stringify({ type: 'error', error: 'LLM 서비스로부터 스트림을 열 수 없습니다.' }) + '\n'
          )
        );
        controller.close();
        return;
      }

      const flushBufferedEvent = (chunk: string) => {
        const dataLines = chunk
          .split('\n')
          .map((line) => line.trim())
          .filter((line) => line.startsWith('data: '));

        if (dataLines.length === 0) {
          return;
        }

        const payload = dataLines.map((line) => line.slice(6)).join('\n');
        if (!payload) {
          return;
        }

        try {
          const parsed = JSON.stringify(JSON.parse(payload)) + '\n';
          controller.enqueue(encoder.encode(parsed));
        } catch (error) {
          console.error('Error parsing SSE payload:', error, payload);
        }
      };

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const segments = buffer.split('\n\n');
          buffer = segments.pop() ?? '';

          for (const segment of segments) {
            flushBufferedEvent(segment);
          }
        }

        if (buffer.trim().length > 0) {
          flushBufferedEvent(buffer);
        }
      } catch (error) {
        console.error('Stream error:', error);
        controller.enqueue(
          encoder.encode(
            JSON.stringify({ type: 'error', error: '스트림 처리 중 오류가 발생했습니다.' }) + '\n'
          )
        );
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
      }),
    });

    if (!response.ok) {
      throw new Error(`LLM service error: ${response.status} ${response.statusText}`);
    }

    // Create streaming response from Agent Pipeline
    const stream = createAgentStream(response);

    // Respond with the stream (JSON Lines)
    return new Response(stream, {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Chat API error:', error);

    // Fallback response as JSON error event
    const encoder = new TextEncoder();
    const fallbackStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            JSON.stringify({
              type: 'error',
              error: `Agent 파이프라인 처리 중 오류가 발생했습니다: ${String(error)}`,
            }) + '\n'
          )
        );
        controller.close();
      },
    });

    return new Response(fallbackStream, {
      status: 500,
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
    });
  }
}
