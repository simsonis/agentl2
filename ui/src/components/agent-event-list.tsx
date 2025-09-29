import { AgentEvent } from "@/lib/types";
import { Badge } from "./ui/badge";

const agentLabels: Record<string, string> = {
  facilitator: "전달자",
  search: "검색",
  analyst: "분석가",
  response: "응답",
  citation: "인용",
  validator: "검증",
  pipeline: "파이프라인",
};

const formatAgentName = (agent: string) => agentLabels[agent] ?? agent;

const formatTimestamp = (timestamp?: string) => {
  if (!timestamp) return undefined;
  try {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return undefined;
    return date.toLocaleTimeString();
  } catch {
    return undefined;
  }
};

interface AgentEventListProps {
  events: AgentEvent[];
  title?: string;
}

const renderJson = (value: unknown) => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

export default function AgentEventList({ events, title }: AgentEventListProps) {
  if (!events || events.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {title && <h4 className="text-sm font-semibold text-muted-foreground">{title}</h4>}
      {events.map((event, index) => {
        const key = `${event.agent}-${event.timestamp ?? index}-${event.type}-${index}`;
        const displayTime = formatTimestamp(event.timestamp);
        const stage = typeof event.payload?.stage === "string" ? event.payload.stage : undefined;
        const message =
          typeof event.payload?.output === "object" && event.payload?.output &&
          typeof (event.payload.output as Record<string, unknown>).message === "string"
            ? ((event.payload.output as Record<string, unknown>).message as string)
            : undefined;
        const confidence =
          typeof event.payload?.output === "object" && event.payload?.output &&
          typeof (event.payload.output as Record<string, unknown>).confidence === "number"
            ? ((event.payload.output as Record<string, unknown>).confidence as number)
            : undefined;

        return (
          <div
            key={key}
            className="rounded-lg border border-border bg-muted/30 p-3 text-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{formatAgentName(event.agent)}</Badge>
                {stage && <Badge variant="outline">{stage}</Badge>}
                <Badge variant="outline" className="text-xs uppercase">{event.type}</Badge>
              </div>
              {displayTime && (
                <span className="text-xs text-muted-foreground">{displayTime}</span>
              )}
            </div>

            {message && (
              <p className="mt-2 whitespace-pre-wrap text-foreground">{message}</p>
            )}

            {confidence !== undefined && (
              <p className="mt-1 text-xs text-muted-foreground">신뢰도: {confidence.toFixed(2)}</p>
            )}

            <details className="mt-2 text-xs text-muted-foreground">
              <summary className="cursor-pointer select-none">입력 및 출력 상세 보기</summary>
              <div className="mt-2 space-y-2">
                {event.payload?.input && (
                  <div>
                    <div className="font-semibold">입력</div>
                    <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-background p-2 text-xs text-foreground/80">
                      {renderJson(event.payload.input)}
                    </pre>
                  </div>
                )}
                {event.payload?.output && (
                  <div>
                    <div className="font-semibold">출력</div>
                    <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-background p-2 text-xs text-foreground/80">
                      {renderJson(event.payload.output)}
                    </pre>
                  </div>
                )}
                {event.payload?.context && (
                  <div>
                    <div className="font-semibold">컨텍스트</div>
                    <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-background p-2 text-xs text-foreground/80">
                      {renderJson(event.payload.context)}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          </div>
        );
      })}
    </div>
  );
}
