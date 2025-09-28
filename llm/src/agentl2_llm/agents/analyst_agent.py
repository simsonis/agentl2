"""
Analyst Agent - Analyzes search results and identifies legal issues.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent, AgentResponse, AgentAction, ConversationContext
from ..models import SearchResults, SearchResult


class AnalysisResult:
    """결과 데이터 구조"""
    def __init__(self):
        self.core_issues: List[str] = []
        self.applicable_laws: List[Dict[str, str]] = []
        self.precedent_analysis: str = ""
        self.conflicts: List[str] = []
        self.confidence_score: float = 0.0
        self.analysis_summary: str = ""
        self.priority_ranking: List[str] = []


class AnalystAgent(BaseAgent):
    """
    분석가 Agent - 검색 결과를 심층 분석하고 법적 쟁점을 식별
    15년차 대형로펌 리서치 전문 변호사 역할
    """

    def __init__(self, **kwargs):
        super().__init__(name="AnalystAgent", **kwargs)

    def _get_system_prompt(self) -> str:
        """분석가 에이전트 시스템 프롬프트"""
        return """너는 법률 데이터 분석 및 패턴 인식 전문가야.
너는 15년차 대형로펌의 리서치 전문 변호사로서, 복잡한 법적 사안을 체계적으로 분석하는 것이 전문 분야야.

너의 임무:
1. **검색 결과 심층 분석**: 수집된 법령과 판례 간의 관계, 위계, 적용 우선순위 분석
2. **모순 및 충돌 탐지**: 상충되는 법령이나 판례, 개정으로 인한 불일치 발견
3. **법적 쟁점 식별**: 사용자 사안에서 핵심이 되는 법적 쟁점과 부차적 쟁점 구분
4. **선례 패턴 분석**: 유사 사건의 판결 경향과 법원의 해석 변화 추이 분석

분석 관점:
- **시간적 관점**: 법령 제정→개정 연혁, 판례 변화 추이
- **체계적 관점**: 상위법-하위법 관계, 일반법-특별법 관계
- **실무적 관점**: 이론과 실제 적용의 차이, 법원의 실제 판단 기준

너의 분석 결과 포맷:
1. **핵심 쟁점**: 이 사안의 법적 쟁점 3가지 이내
2. **적용 법령**: 우선순위별 적용 법령과 조문
3. **판례 분석**: 관련 판례의 법리와 사실관계 비교
4. **모순 지점**: 발견된 법령/판례 간 충돌이나 불명확한 부분
5. **분석 신뢰도**: 수집된 정보의 충분성과 신뢰성 평가 (1-10점)

중요: 법적 결론을 내리지 말고, 객관적 분석만 제공해. 불확실한 부분은 명확히 "불명확함" 또는 "추가 검토 필요"라고 표시해."""

    async def process(
        self,
        user_input: str,
        context: ConversationContext
    ) -> AgentResponse:
        """검색 결과를 분석하고 법적 쟁점을 식별"""

        logger.info("Analyst agent processing search results")

        try:
            # 검색 결과 추출
            search_results = self._extract_search_results(context)

            if not search_results or search_results.total_count == 0:
                return AgentResponse(
                    action=AgentAction.FORWARD_TO_RESPONSE,
                    message="검색 결과가 없어 분석을 수행할 수 없습니다.",
                    confidence=0.0
                )

            # 법적 분석 수행
            analysis_result = await self._perform_legal_analysis(
                search_results,
                context.extracted_intent,
                context.extracted_keywords,
                user_input
            )

            return AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message=f"법적 분석 완료: {len(analysis_result.core_issues)}개 핵심 쟁점 식별",
                intent=context.extracted_intent,
                keywords=context.extracted_keywords,
                confidence=analysis_result.confidence_score,
                metadata={
                    "analysis_result": analysis_result,
                    "search_results": search_results
                }
            )

        except Exception as e:
            logger.error(f"Error in analyst agent: {e}")
            return AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message="분석 중 오류가 발생했지만 가능한 정보로 답변을 생성하겠습니다.",
                confidence=0.3,
                metadata={"error": str(e)}
            )

    async def _perform_legal_analysis(
        self,
        search_results: SearchResults,
        intent: str,
        keywords: List[str],
        user_query: str
    ) -> AnalysisResult:
        """법적 분석 수행"""

        # 검색 결과 요약 생성
        results_summary = self._summarize_search_results(search_results)

        # LLM을 통한 분석 수행
        analysis_text = await self._generate_analysis(
            user_query, intent, keywords, results_summary
        )

        # 분석 결과 파싱
        analysis_result = self._parse_analysis_result(analysis_text)

        return analysis_result

    def _summarize_search_results(self, search_results: SearchResults) -> str:
        """검색 결과 요약"""

        summary_parts = []

        # 결과 개수 정보
        summary_parts.append(f"총 검색 결과: {search_results.total_count}건")
        summary_parts.append(f"내부 결과: {len(search_results.internal_results)}건")
        summary_parts.append(f"외부 결과: {len(search_results.external_results)}건")
        summary_parts.append("")

        # 주요 결과 요약
        all_results = search_results.get_all_results()

        for i, result in enumerate(all_results[:10], 1):  # 상위 10개 결과
            summary_parts.append(f"{i}. {result.title}")
            summary_parts.append(f"   출처: {result.source.source_type.value}")
            summary_parts.append(f"   관련도: {result.relevance_score:.2f}")
            summary_parts.append(f"   내용: {result.content[:200]}...")
            summary_parts.append("")

        return "\n".join(summary_parts)

    async def _generate_analysis(
        self,
        user_query: str,
        intent: str,
        keywords: List[str],
        results_summary: str
    ) -> str:
        """LLM을 통한 분석 생성"""

        prompt = f"""다음 법률 사안에 대해 체계적 분석을 수행해줘.

사용자 질의: {user_query}
파악된 의도: {intent}
핵심 키워드: {', '.join(keywords)}

검색 결과:
{results_summary}

다음 구조로 분석해줘:

1. **핵심 쟁점**: 이 사안의 법적 쟁점 3가지 이내 (구체적으로)
2. **적용 법령**: 우선순위별 적용 법령과 조문 (상위법부터)
3. **판례 분석**: 관련 판례의 법리와 사실관계 비교
4. **모순 지점**: 발견된 법령/판례 간 충돌이나 불명확한 부분
5. **분석 신뢰도**: 수집된 정보의 충분성과 신뢰성 평가 (1-10점)

분석 관점:
- 시간적 관점: 법령 제정→개정 연혁, 판례 변화 추이
- 체계적 관점: 상위법-하위법 관계, 일반법-특별법 관계
- 실무적 관점: 이론과 실제 적용의 차이

객관적 분석만 하고, 법적 결론은 내리지 말아줘."""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=1200)
            return response

        except Exception as e:
            logger.error(f"Analysis generation failed: {e}")
            return self._generate_fallback_analysis(user_query, intent, keywords)

    def _parse_analysis_result(self, analysis_text: str) -> AnalysisResult:
        """분석 결과 파싱"""

        result = AnalysisResult()

        lines = analysis_text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 섹션 구분
            if '핵심 쟁점' in line:
                current_section = 'issues'
            elif '적용 법령' in line:
                current_section = 'laws'
            elif '판례 분석' in line:
                current_section = 'precedents'
            elif '모순 지점' in line:
                current_section = 'conflicts'
            elif '분석 신뢰도' in line:
                current_section = 'confidence'
                # 신뢰도 점수 추출
                import re
                score_match = re.search(r'(\d+(?:\.\d+)?)', line)
                if score_match:
                    result.confidence_score = float(score_match.group(1)) / 10.0

            # 내용 파싱
            elif current_section == 'issues' and (line.startswith('-') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                issue = line.lstrip('- 123.').strip()
                if issue:
                    result.core_issues.append(issue)

            elif current_section == 'laws' and (line.startswith('-') or '법' in line):
                law_info = line.lstrip('- ').strip()
                if law_info:
                    result.applicable_laws.append({"law": law_info, "priority": len(result.applicable_laws) + 1})

            elif current_section == 'precedents':
                if line.startswith('-') or '판례' in line or '법원' in line:
                    result.precedent_analysis += line + "\n"

            elif current_section == 'conflicts' and line.startswith('-'):
                conflict = line.lstrip('- ').strip()
                if conflict:
                    result.conflicts.append(conflict)

        # 분석 요약 생성
        result.analysis_summary = self._generate_analysis_summary(result)

        # 우선순위 순서 설정
        result.priority_ranking = [issue[:50] + "..." if len(issue) > 50 else issue for issue in result.core_issues]

        return result

    def _generate_analysis_summary(self, result: AnalysisResult) -> str:
        """분석 요약 생성"""

        summary_parts = []

        if result.core_issues:
            summary_parts.append(f"핵심 쟁점 {len(result.core_issues)}개 식별")

        if result.applicable_laws:
            summary_parts.append(f"적용 법령 {len(result.applicable_laws)}개 확인")

        if result.conflicts:
            summary_parts.append(f"법령 간 충돌 {len(result.conflicts)}건 발견")

        summary_parts.append(f"분석 신뢰도 {result.confidence_score:.1f}/1.0")

        return ", ".join(summary_parts)

    def _generate_fallback_analysis(self, user_query: str, intent: str, keywords: List[str]) -> str:
        """분석 실패 시 대체 분석"""

        return f"""1. **핵심 쟁점**:
- {intent}에 관한 법적 요건 검토
- 관련 키워드({', '.join(keywords[:3])})의 법적 정의와 적용범위
- 예외 상황 및 특수 조건 존재 여부

2. **적용 법령**:
- 관련 기본법령 확인 필요
- 시행령 및 시행규칙 검토 필요

3. **판례 분석**:
- 관련 판례 추가 검색 필요

4. **모순 지점**:
- 검색 결과 부족으로 분석 제한

5. **분석 신뢰도**: 3/10 (정보 부족)"""

    def _extract_search_results(self, context: ConversationContext) -> Optional[SearchResults]:
        """컨텍스트에서 검색 결과 추출"""

        if not context.agent_responses:
            return None

        # 최신 검색 에이전트 응답 찾기
        for response in reversed(context.agent_responses):
            if response.metadata and "search_results" in response.metadata:
                return response.metadata["search_results"]

        return None