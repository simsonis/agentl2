// src/components/answer-card.tsx
import { AssistantMessage } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import CitationChip from "./citation-chip";
import FollowUps from "./follow-ups";

interface AnswerCardProps {
  message: AssistantMessage;
  onFollowUpClick: (question: string) => void;
}

export default function AnswerCard({ message, onFollowUpClick }: AnswerCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">답변</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary */}
        <div className="prose dark:prose-invert max-w-none">
          <p>{message.summary}</p>
        </div>

        {/* Citations */}
        <div>
          <h4 className="text-sm font-semibold mb-2">근거 자료</h4>
          <div className="flex flex-wrap gap-2">
            {message.citations.map((citation, i) => (
              <CitationChip key={i} citation={citation} />
            ))}
          </div>
        </div>

        {/* Follow-ups */}
        {message.followUps && message.followUps.length > 0 && (
          <FollowUps questions={message.followUps} onQuestionClick={onFollowUpClick} />
        )}
      </CardContent>
    </Card>
  );
}