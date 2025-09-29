
'use client';

import { FC, useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
// import { useToast } from '@/hooks/use-toast';

// 6개 에이전트의 초기 설정
const initialAgentConfigs = {
  facilitator: {
    name: '전달자 (Facilitator)',
    role: '의도파악/키워드추출',
    model: 'gpt-4',
    systemPrompt: `당신은 사용자의 법률 질문을 분석하여 핵심 키워드를 추출하고 법적 의도를 파악하는 전문가입니다.

주요 역할:
1. 사용자 질문에서 핵심 법률 용어와 키워드 추출
2. 질문의 법적 의도 분류 (법령 검색, 판례 분석, 해석 등)
3. 다음 단계 에이전트가 활용할 수 있는 구조화된 정보 생성

응답 형식은 간결하고 명확하게 작성하세요.`,
    temperature: 0.3,
    maxTokens: 1000,
    topP: 1.0,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0
  },
  search: {
    name: '검색자 (Search)',
    role: '다중라운드검색',
    model: 'gpt-4',
    systemPrompt: `당신은 법령 및 판례 검색을 수행하는 전문가입니다.

주요 역할:
1. 키워드를 바탕으로 관련 법령 검색
2. 유사 판례 및 해석례 검색
3. 내부 DB와 외부 소스를 활용한 다중 검색
4. 검색 결과의 관련성 평가 및 우선순위 결정

정확하고 포괄적인 검색 결과를 제공하세요.`,
    temperature: 0.2,
    maxTokens: 1200,
    topP: 1.0,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0
  },
  analyst: {
    name: '분석가 (Analyst)',
    role: '법적분석/쟁점식별',
    model: 'gpt-4',
    systemPrompt: `당신은 법적 쟁점을 식별하고 분석하는 전문가입니다.

주요 역할:
1. 검색된 법령과 판례를 바탕으로 법적 쟁점 식별
2. 적용 가능한 법리와 원칙 분석
3. 사안의 복잡성과 중요도 평가
4. 잠재적 법적 위험 요소 파악

논리적이고 체계적인 분석을 제공하세요.`,
    temperature: 0.4,
    maxTokens: 1500,
    topP: 1.0,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0
  },
  response: {
    name: '응답자 (Response)',
    role: '답변내용생성',
    model: 'gpt-4',
    systemPrompt: `당신은 법적 분석을 바탕으로 사용자에게 명확한 답변을 제공하는 전문가입니다.

주요 역할:
1. 분석 결과를 바탕으로 구체적이고 실용적인 답변 생성
2. 법적 근거를 명시하며 이해하기 쉽게 설명
3. 사용자의 상황에 맞는 조치 사항 제안
4. 추가 고려사항이나 주의점 안내

명확하고 이해하기 쉬운 언어로 답변하세요.`,
    temperature: 0.5,
    maxTokens: 2000,
    topP: 1.0,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0
  },
  citation: {
    name: '인용자 (Citation)',
    role: '인용/출처관리',
    model: 'gpt-4',
    systemPrompt: `당신은 법률 답변의 인용과 출처를 정리하는 전문가입니다.

주요 역할:
1. 참조된 법령의 정확한 조문 및 출처 정리
2. 인용된 판례의 사건번호 및 요지 정리
3. 외부 자료의 신뢰성 검증
4. 법적 근거의 계층적 구조화

정확하고 체계적인 인용 형식을 유지하세요.`,
    temperature: 0.1,
    maxTokens: 800,
    topP: 1.0,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0
  },
  validator: {
    name: '검증자 (Validator)',
    role: '종합검증/품질관리',
    model: 'gpt-4',
    systemPrompt: `당신은 최종 답변의 정확성과 품질을 검증하는 전문가입니다.

주요 역할:
1. 답변 내용의 법적 정확성 검증
2. 논리적 일관성 및 완성도 평가
3. 인용 출처의 정확성 확인
4. 사용자에게 도움이 되는지 최종 평가

높은 품질 기준을 유지하며 객관적으로 검증하세요.`,
    temperature: 0.2,
    maxTokens: 1000,
    topP: 1.0,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0
  }
};

const LlmAdminPage: FC = () => {
  // const { toast } = useToast();
  const [agentConfigs, setAgentConfigs] = useState(initialAgentConfigs);
  const [activeAgent, setActiveAgent] = useState<keyof typeof initialAgentConfigs>('facilitator');
  const [globalSettings, setGlobalSettings] = useState({
    defaultModel: 'gpt-4',
    maxRetries: 3,
    timeout: 30,
    enableLogging: true
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const availableModels = [
    { value: 'gpt-4', label: 'GPT-4' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    { value: 'claude-3-opus', label: 'Claude 3 Opus' },
    { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
    { value: 'claude-3-haiku', label: 'Claude 3 Haiku' }
  ];

  const updateAgentConfig = (agentKey: keyof typeof agentConfigs, field: string, value: unknown) => {
    setAgentConfigs(prev => ({
      ...prev,
      [agentKey]: {
        ...prev[agentKey],
        [field]: value
      }
    }));
  };

  // Load configurations from backend
  const loadConfigurations = async () => {
    setIsLoading(true);
    try {
      const [agentConfigsResponse, globalSettingsResponse] = await Promise.all([
        fetch('http://localhost:8001/admin/agent-configs'),
        fetch('http://localhost:8001/admin/global-settings')
      ]);

      if (agentConfigsResponse.ok && globalSettingsResponse.ok) {
        const agentConfigsData = await agentConfigsResponse.json();
        const globalSettingsData = await globalSettingsResponse.json();

        if (agentConfigsData.success) {
          setAgentConfigs(agentConfigsData.data);
        }
        if (globalSettingsData.success) {
          setGlobalSettings(globalSettingsData.data);
        }
      }
    } catch (error) {
      console.error('Failed to load configurations:', error);
      alert('서버에서 설정을 불러오는데 실패했습니다. 기본 설정을 사용합니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // Load configurations on mount
  useEffect(() => {
    loadConfigurations();
  }, []);

  const resetToDefaults = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8001/admin/reset-to-defaults', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setAgentConfigs(data.data.agentConfigs);
          setGlobalSettings(data.data.globalSettings);
          alert('초기화 완료: ' + data.message);
        }
      }
    } catch (error) {
      console.error('Failed to reset to defaults:', error);
      alert('설정을 초기화하는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const saveConfigurations = async () => {
    setIsSaving(true);
    try {
      const [agentConfigsResponse, globalSettingsResponse] = await Promise.all([
        fetch('http://localhost:8001/admin/agent-configs', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(agentConfigs)
        }),
        fetch('http://localhost:8001/admin/global-settings', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(globalSettings)
        })
      ]);

      if (agentConfigsResponse.ok && globalSettingsResponse.ok) {
        const agentConfigsData = await agentConfigsResponse.json();
        const globalSettingsData = await globalSettingsResponse.json();

        if (agentConfigsData.success && globalSettingsData.success) {
          alert('설정이 성공적으로 저장되었습니다.');
        }
      } else {
        throw new Error('Failed to save configurations');
      }
    } catch (error) {
      console.error('Failed to save configurations:', error);
      alert('설정을 저장하는데 실패했습니다.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen space-y-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">LLM 에이전트 관리</h1>
          <p className="text-muted-foreground mt-2">6단계 법률 AI 에이전트의 시스템 프롬프트와 설정을 관리합니다.</p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={resetToDefaults}
            disabled={isLoading}
          >
            {isLoading ? '처리 중...' : '기본값 복원'}
          </Button>
          <Button
            onClick={saveConfigurations}
            disabled={isSaving || isLoading}
          >
            {isSaving ? '저장 중...' : '설정 저장'}
          </Button>
        </div>
      </div>

      {/* 에이전트 선택 탭 */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {Object.entries(agentConfigs).map(([key, config]) => (
          <Button
            key={key}
            variant={activeAgent === key ? "default" : "outline"}
            onClick={() => setActiveAgent(key as keyof typeof agentConfigs)}
            className="min-w-fit flex-shrink-0"
          >
            <Badge variant="secondary" className="mr-2 text-xs">
              {key.charAt(0).toUpperCase()}
            </Badge>
            {config.name}
          </Button>
        ))}
      </div>

      {/* 선택된 에이전트 설정 */}
      <div className="grid gap-8 lg:grid-cols-2">
        {/* 시스템 프롬프트 편집 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-3">
              <Badge variant="outline" className="text-sm">
                {activeAgent.charAt(0).toUpperCase()}
              </Badge>
              {agentConfigs[activeAgent].name} - 시스템 프롬프트
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">역할</label>
              <div className="mt-1">
                <Badge variant="secondary">{agentConfigs[activeAgent].role}</Badge>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">시스템 프롬프트</label>
              <Textarea
                value={agentConfigs[activeAgent].systemPrompt}
                onChange={(e) => updateAgentConfig(activeAgent, 'systemPrompt', e.target.value)}
                className="mt-2 min-h-[200px] font-mono text-sm"
                placeholder="시스템 프롬프트를 입력하세요..."
              />
            </div>
          </CardContent>
        </Card>

        {/* 모델 설정 */}
        <Card>
          <CardHeader>
            <CardTitle>모델 설정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">사용 모델</label>
              <Select
                value={agentConfigs[activeAgent].model}
                onValueChange={(value) => updateAgentConfig(activeAgent, 'model', value)}
              >
                <SelectTrigger className="mt-2">
                  <SelectValue placeholder="모델을 선택하세요" />
                </SelectTrigger>
                <SelectContent>
                  {availableModels.map((model) => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Temperature: {agentConfigs[activeAgent].temperature}
              </label>
              <Slider
                value={[agentConfigs[activeAgent].temperature]}
                onValueChange={(value) => updateAgentConfig(activeAgent, 'temperature', value[0])}
                max={1}
                min={0}
                step={0.1}
                className="mt-2"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>보수적 (0)</span>
                <span>창의적 (1)</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">최대 토큰 수</label>
              <Input
                type="number"
                value={agentConfigs[activeAgent].maxTokens}
                onChange={(e) => updateAgentConfig(activeAgent, 'maxTokens', parseInt(e.target.value))}
                className="mt-2"
                min={100}
                max={4000}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Top P: {agentConfigs[activeAgent].topP}
              </label>
              <Slider
                value={[agentConfigs[activeAgent].topP]}
                onValueChange={(value) => updateAgentConfig(activeAgent, 'topP', value[0])}
                max={1}
                min={0}
                step={0.1}
                className="mt-2"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>결정적 (0)</span>
                <span>다양한 (1)</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Frequency Penalty: {agentConfigs[activeAgent].frequencyPenalty}
              </label>
              <Slider
                value={[agentConfigs[activeAgent].frequencyPenalty]}
                onValueChange={(value) => updateAgentConfig(activeAgent, 'frequencyPenalty', value[0])}
                max={2}
                min={-2}
                step={0.1}
                className="mt-2"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>반복 증가 (-2)</span>
                <span>반복 억제 (2)</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Presence Penalty: {agentConfigs[activeAgent].presencePenalty}
              </label>
              <Slider
                value={[agentConfigs[activeAgent].presencePenalty]}
                onValueChange={(value) => updateAgentConfig(activeAgent, 'presencePenalty', value[0])}
                max={2}
                min={-2}
                step={0.1}
                className="mt-2"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>주제 재반복 (-2)</span>
                <span>새 주제 탐색 (2)</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 글로벌 설정 */}
        <Card>
          <CardHeader>
            <CardTitle>글로벌 설정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">기본 모델</label>
              <Select
                value={globalSettings.defaultModel}
                onValueChange={(value) => setGlobalSettings(prev => ({ ...prev, defaultModel: value }))}
                disabled={isLoading}
              >
                <SelectTrigger className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {availableModels.map((model) => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">최대 재시도 횟수</label>
              <Input
                type="number"
                value={globalSettings.maxRetries}
                onChange={(e) => setGlobalSettings(prev => ({ ...prev, maxRetries: parseInt(e.target.value) }))}
                className="mt-2"
                min={1}
                max={10}
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">타임아웃 (초)</label>
              <Input
                type="number"
                value={globalSettings.timeout}
                onChange={(e) => setGlobalSettings(prev => ({ ...prev, timeout: parseInt(e.target.value) }))}
                className="mt-2"
                min={10}
                max={120}
                disabled={isLoading}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 에이전트 파이프라인 상태 */}
      <Card>
        <CardHeader>
          <CardTitle>에이전트 파이프라인 상태</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Object.entries(agentConfigs).map(([key, config]) => (
              <div
                key={key}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent transition-colors cursor-pointer"
                onClick={() => setActiveAgent(key as keyof typeof agentConfigs)}
              >
                <div className="flex items-center gap-3">
                  <Badge variant={activeAgent === key ? "default" : "secondary"}>
                    {key.charAt(0).toUpperCase()}
                  </Badge>
                  <div>
                    <div className="font-medium text-sm">{config.name}</div>
                    <div className="text-xs text-muted-foreground">{config.role}</div>
                  </div>
                </div>
                <div className="text-right">
                  <Badge variant="outline" className="text-xs">{config.model}</Badge>
                  <div className="text-xs text-muted-foreground mt-1">
                    T: {config.temperature} | P: {config.topP}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LlmAdminPage;
