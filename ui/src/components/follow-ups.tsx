// src/components/follow-ups.tsx
import { Button } from "./ui/button";

interface FollowUpsProps {
  questions: string[];
  onQuestionClick: (question: string) => void;
}

export default function FollowUps({ questions, onQuestionClick }: FollowUpsProps) {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2">추가 질문 제안</h4>
      <div className="flex flex-wrap gap-2">
        {questions.map((q, i) => (
          <Button
            key={i}
            variant="outline"
            size="sm"
            onClick={() => onQuestionClick(q)}
          >
            {q}
          </Button>
        ))}
      </div>
    </div>
  );
}