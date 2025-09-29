// src/components/answer-card.tsx
import AgentEventList from "@/components/agent-event-list";
import { AssistantMessage } from "@/lib/types";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import CitationChip from "./citation-chip";
import FollowUps from "./follow-ups";

interface AnswerCardProps {
  message: AssistantMessage;
  onFollowUpClick: (question: string) => void;
}

const formatProcessingTime = (value?: number) => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return undefined;
  }
  return `${value.toFixed(2)}s`;
};

export default function AnswerCard({ message, onFollowUpClick }: AnswerCardProps) {
  const processingTimeLabel = formatProcessingTime(message.processingTime);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">최종 답변</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary */}
        <div className="prose dark:prose-invert max-w-none">
          <p>{message.summary}</p>
        </div>

        {/* Meta information */}
        {(message.confidence !== undefined || processingTimeLabel || (message.relatedKeywords && message.relatedKeywords.length > 0)) && (
          <div className="space-y-2 text-sm text-muted-foreground">
            <div className="flex flex-wrap items-center gap-3">
              {message.confidence !== undefined && (
                <Badge variant="outline">신뢰도 {message.confidence.toFixed(2)}</Badge>
              )}
              {processingTimeLabel && <Badge variant="outline">처리 {processingTimeLabel}</Badge>}
            </div>
            {message.relatedKeywords && message.relatedKeywords.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {message.relatedKeywords.map((keyword) => (
                  <Badge key={keyword} variant="secondary" className="text-xs">
                    {keyword}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">참고 출처</h4>
            <div className="flex flex-wrap gap-2">
              {message.citations.map((citation, i) => (
                <CitationChip key={`${citation.source_name}-${i}`} citation={citation} />
              ))}
            </div>
          </div>
        )}

        {/* Follow-ups */}
        {message.followUps && message.followUps.length > 0 && (
          <FollowUps questions={message.followUps} onQuestionClick={onFollowUpClick} />
        )}

        {/* Agent reasoning timeline */}
        {message.agentTrail && message.agentTrail.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">에이전트 추론 로그</h4>
            <AgentEventList events={message.agentTrail} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
