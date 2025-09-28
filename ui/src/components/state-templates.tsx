// src/components/state-templates.tsx
import { Card, CardContent } from '@/components/ui/card';

export const LoadingComponent = () => (
  <div className="flex items-center space-x-2">
    <div className="h-2 w-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
    <div className="h-2 w-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
    <div className="h-2 w-2 bg-primary rounded-full animate-bounce"></div>
    <span className="text-sm text-muted-foreground">답변을 생성하는 중입니다...</span>
  </div>
);

export const WelcomeComponent = () => (
  <Card className="w-full">
    <CardContent className="p-6">
      <h2 className="text-lg font-semibold">법률 AI 에이전트 AgentL2 입니다.</h2>
      <p className="mt-2 text-muted-foreground">
        개인정보보호법, 신용정보보호법 등 법률에 대해 무엇이든 물어보세요.
        <br />
        소스코드를 입력하여 법규 준수 여부를 확인할 수도 있습니다.
      </p>
    </CardContent>
  </Card>
);