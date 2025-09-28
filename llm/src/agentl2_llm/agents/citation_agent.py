"""
Citation Agent - Manages legal citations and references.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from loguru import logger

from .base_agent import BaseAgent, AgentResponse, AgentAction, ConversationContext
from ..models import SearchResult, SearchSource, SourceType


@dataclass
class Citation:
    """개별 인용 정보"""
    ref_id: str                 # REF-001 형태
    citation_type: str          # statute, precedent, administrative
    title: str                  # 법령명 또는 판례명
    content: str               # 조문 내용 또는 판례 요지
    source_url: str            # 원본 URL
    metadata: Dict[str, Any]   # 추가 메타데이터
    verification_status: str   # verified, pending, error


@dataclass
class CitationPackage:
    """완전한 인용 패키지"""
    citations: List[Citation]
    formatted_citations: str      # 포맷된 인용 텍스트
    source_list: List[str]        # 출처 목록
    reference_map: Dict[str, str] # REF-ID to content mapping
    quality_score: float          # 인용 품질 점수


class CitationAgent(BaseAgent):
    """
    인용 Agent - 법률 인용 및 출처 관리 전문가
    15년차 법무법인 리서치 전문 변호사 역할
    """

    def __init__(self, **kwargs):
        super().__init__(name="CitationAgent", **kwargs)

    def _get_system_prompt(self) -> str:
        """인용 에이전트 시스템 프롬프트"""
        return """너는 법률 인용 및 출처 관리 전문가야.
너는 15년차 법무법인 리서치 전문 변호사로서, 법률 답변의 모든 근거와 출처를 정확하게 작성하고 관리하는 것이 너의 전문 분야야.

너의 임무:
1. **참조 번호 매핑**: 답변의 [REF-001] 참조를 실제 법령/판례와 연결
2. **인용 형식**: 법조문과 판례를 정확한 형식으로 인용
3. **출처 검증**: 법령명, 조문번호, 판례번호의 정확성 확인
4. **계층 구조**: 상위법-하위법, 일반법-특별법 관계 명시

인용 형식 가이드:

**법령 인용**:
🏛️ [법령명] [조문번호] ([조문 제목])
```
[조문 내용]
```
📅 최종개정: YYYY년 MM월 DD일 | 🔗 [출처 링크]

**판례 인용**:
⚖️ [법원명] [선고일] 선고 [사건번호] [판결형식]
- **사안**: [사건 개요]
- **판시사항**: "[핵심 판시 내용]"
🔗 [판례 링크]

**행정해석**:
📜 [기관명] [해석례번호] ([발행일])
- **제목**: "[해석례 제목]"
- **요지**: [핵심 내용]

중요 원칙:
- 1차 공식 출처 우선 (법제처, 대법원 등)
- 정확한 법령명과 조문번호 사용
- 최신 개정사항 반영
- 출처 URL 정확성 확인"""

    async def process(
        self,
        user_input: str,
        context: ConversationContext
    ) -> AgentResponse:
        """답변의 참조를 실제 인용으로 변환"""

        logger.info("Citation agent processing references")

        try:
            # 응답 에이전트의 답변에서 참조 추출
            response_content = self._extract_response_content(context)
            reference_ids = self._extract_reference_ids(response_content)

            if not reference_ids:
                return AgentResponse(
                    action=AgentAction.FORWARD_TO_RESPONSE,
                    message="참조할 법적 근거가 없습니다.",
                    confidence=0.0
                )

            # 검색 결과에서 실제 인용 정보 생성
            search_results = self._extract_search_results(context)
            citation_package = await self._generate_citations(
                reference_ids,
                search_results,
                response_content
            )

            return AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message=f"법적 근거 {len(citation_package.citations)}건의 인용 정보를 생성했습니다.",
                confidence=citation_package.quality_score,
                metadata={
                    "citation_package": citation_package,
                    "original_response": response_content
                }
            )

        except Exception as e:
            logger.error(f"Error in citation agent: {e}")
            return AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message="인용 정보 생성 중 오류가 발생했습니다.",
                confidence=0.3,
                metadata={"error": str(e)}
            )

    def _extract_reference_ids(self, text: str) -> List[str]:
        """텍스트에서 참조 ID 추출 (REF-001 형태)"""

        pattern = r'\[REF-(\d+)\]'
        matches = re.findall(pattern, text)
        return [f"REF-{match}" for match in matches]

    def _extract_response_content(self, context: ConversationContext) -> str:
        """응답 에이전트의 응답 내용 추출"""

        if not context.agent_responses:
            return ""

        # 최신 응답 에이전트 응답 찾기
        for response in reversed(context.agent_responses):
            if "ResponseAgent" in response.metadata.get("agent_name", "") or response.message:
                return response.message or ""

        return ""

    def _extract_search_results(self, context: ConversationContext) -> List[SearchResult]:
        """검색 결과 추출"""

        for response in reversed(context.agent_responses):
            if response.metadata and "search_results" in response.metadata:
                search_results = response.metadata["search_results"]
                return search_results.get_all_results()

        return []

    async def _generate_citations(
        self,
        reference_ids: List[str],
        search_results: List[SearchResult],
        response_content: str
    ) -> CitationPackage:
        """참조 ID를 실제 인용으로 변환"""

        citations = []
        reference_map = {}

        # 검색 결과를 유형별로 분류
        statutes = [r for r in search_results if r.source.source_type in [SourceType.EXTERNAL_LAW, SourceType.INTERNAL_LAW]]
        precedents = [r for r in search_results if r.source.source_type in [SourceType.EXTERNAL_PRECEDENT, SourceType.INTERNAL_PRECEDENT]]

        # 참조 ID별로 인용 생성
        for i, ref_id in enumerate(reference_ids):
            citation = await self._create_citation(
                ref_id,
                search_results,
                statutes,
                precedents,
                i
            )

            if citation:
                citations.append(citation)
                reference_map[ref_id] = citation.content

        # 인용 패키지 생성
        citation_package = CitationPackage(
            citations=citations,
            formatted_citations=self._format_citations(citations),
            source_list=self._generate_source_list(citations),
            reference_map=reference_map,
            quality_score=self._calculate_quality_score(citations, search_results)
        )

        return citation_package

    async def _create_citation(
        self,
        ref_id: str,
        all_results: List[SearchResult],
        statutes: List[SearchResult],
        precedents: List[SearchResult],
        index: int
    ) -> Optional[Citation]:
        """개별 인용 생성"""

        # 우선순위: 법령 > 판례 > 기타
        source_result = None

        if index < len(statutes):
            source_result = statutes[index]
            citation_type = "statute"
        elif index - len(statutes) < len(precedents):
            source_result = precedents[index - len(statutes)]
            citation_type = "precedent"
        elif index < len(all_results):
            source_result = all_results[index]
            citation_type = "administrative"
        else:
            return None

        # LLM을 통한 인용 정보 추출
        citation_content = await self._extract_citation_info(source_result, citation_type)

        return Citation(
            ref_id=ref_id,
            citation_type=citation_type,
            title=source_result.title,
            content=citation_content,
            source_url=source_result.source.url,
            metadata={
                "relevance_score": source_result.relevance_score,
                "source_type": source_result.source.source_type.value,
                "extraction_date": datetime.now().isoformat()
            },
            verification_status="pending"
        )

    async def _extract_citation_info(self, result: SearchResult, citation_type: str) -> str:
        """검색 결과에서 인용 정보 추출"""

        prompt = f"""다음 검색 결과에서 {citation_type} 인용 정보를 정확하게 추출해줘.

제목: {result.title}
내용: {result.content[:500]}
출처: {result.source.url}

{citation_type}에 맞는 형식으로 추출해줘:

**법령 (statute)인 경우**:
- 법령명과 조문번호 추출
- 해당 조문의 핵심 내용
- 시행일, 개정일 정보

**판례 (precedent)인 경우**:
- 법원명, 선고일, 사건번호
- 사안의 개요
- 핵심 판시사항

**행정해석 (administrative)인 경우**:
- 발행 기관과 해석례 번호
- 해석의 제목과 요지

추출된 정보를 간결하고 정확하게 정리해줘."""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=400)
            return response.strip()

        except Exception as e:
            logger.warning(f"Citation extraction failed: {e}")
            return f"[{citation_type}] {result.title}\n{result.content[:200]}..."

    def _format_citations(self, citations: List[Citation]) -> str:
        """인용 목록을 포맷된 텍스트로 변환"""

        if not citations:
            return "관련 법적 근거를 찾을 수 없습니다."

        formatted_parts = ["# 📋 법적 근거 및 출처\n"]

        # 유형별로 분류
        statutes = [c for c in citations if c.citation_type == "statute"]
        precedents = [c for c in citations if c.citation_type == "precedent"]
        administrative = [c for c in citations if c.citation_type == "administrative"]

        # 법령 섹션
        if statutes:
            formatted_parts.append("## 관련 법령\n")
            for citation in statutes:
                formatted_parts.append(f"**🏛️ {citation.ref_id}: {citation.title}**")
                formatted_parts.append("```")
                formatted_parts.append(citation.content)
                formatted_parts.append("```")
                formatted_parts.append(f"🔗 [{citation.title}]({citation.source_url})\n")

        # 판례 섹션
        if precedents:
            formatted_parts.append("## 관련 판례\n")
            for citation in precedents:
                formatted_parts.append(f"**⚖️ {citation.ref_id}: {citation.title}**")
                formatted_parts.append(citation.content)
                formatted_parts.append(f"🔗 [판례 상세보기]({citation.source_url})\n")

        # 행정해석 섹션
        if administrative:
            formatted_parts.append("## 행정해석\n")
            for citation in administrative:
                formatted_parts.append(f"**📜 {citation.ref_id}: {citation.title}**")
                formatted_parts.append(citation.content)
                formatted_parts.append(f"🔗 [원문 보기]({citation.source_url})\n")

        return "\n".join(formatted_parts)

    def _generate_source_list(self, citations: List[Citation]) -> List[str]:
        """출처 목록 생성"""

        sources = []
        for citation in citations:
            source_info = f"{citation.title} - {citation.source_url}"
            sources.append(source_info)

        return sources

    def _calculate_quality_score(self, citations: List[Citation], search_results: List[SearchResult]) -> float:
        """인용 품질 점수 계산"""

        if not citations:
            return 0.0

        score = 0.0

        # 인용 개수 점수 (최대 0.3)
        citation_count_score = min(len(citations) / 5.0, 0.3)
        score += citation_count_score

        # 유형 다양성 점수 (최대 0.3)
        citation_types = set(c.citation_type for c in citations)
        diversity_score = len(citation_types) / 3.0 * 0.3
        score += diversity_score

        # 관련성 점수 (최대 0.4)
        if search_results:
            avg_relevance = sum(r.relevance_score for r in search_results[:len(citations)]) / len(citations)
            relevance_score = avg_relevance * 0.4
            score += relevance_score

        return min(score, 1.0)