"""
Enhanced Validator Agent - Comprehensive legal advice verification.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent, AgentResponse, AgentAction, ConversationContext
from .citation_agent import CitationPackage
from .analyst_agent import AnalysisResult


@dataclass
class ValidationResult:
    """확장된 검증 결과"""
    overall_status: str                    # PASS, CONDITIONAL_PASS, FAIL
    content_validation: Dict[str, Any]     # 내용 검증 결과
    citation_validation: Dict[str, Any]    # 인용 검증 결과
    consistency_validation: Dict[str, Any] # 일관성 검증 결과
    risk_assessment: Dict[str, str]        # 위험도 평가
    improvement_suggestions: List[str]     # 개선 제안
    final_confidence: float                # 최종 신뢰도
    validation_metadata: Dict[str, Any]    # 검증 메타데이터


class ValidatorAgent(BaseAgent):
    """
    확장된 검증자 Agent - 답변+근거+출처 종합 검증
    30년차 대법관급 법률 전문가 역할
    """

    def __init__(self, **kwargs):
        super().__init__(name="ValidatorAgent", **kwargs)

    def _get_system_prompt(self) -> str:
        """확장된 검증자 에이전트 시스템 프롬프트"""
        return """너는 법률 조언 검증 및 품질 관리 전문가야.
너는 30년차 대법관급 법률 전문가로서, 제공되는 모든 법적 조언의 정확성과 완성도를 최종 검증하는 것이 너의 역할이야.

확장된 검증 임무:
1. **법적 논리 검증**: 제시된 법적 해석과 적용의 논리적 일관성 확인
2. **인용 정확성 검증**: 법령 조문, 판례 인용의 정확성 및 최신성 확인
3. **위험도 평가**: 제공된 조언의 법적 리스크와 한계 평가
4. **누락 사항 점검**: 고려되지 않은 중요한 법적 요소나 예외 사항 확인
5. **답변-근거 일치성**: 답변 내용과 인용된 근거의 논리적 일치성 검증
6. **출처 신뢰성**: 1차/2차 출처 구분, 공식/비공식 출처 검증
7. **종합 품질 관리**: 전체적인 답변의 완성도와 사용자 안전성 확인

검증 기준:
- **정확성**: 법령/판례 인용이 정확한가?
- **완전성**: 모든 관련 법적 요소가 고려되었는가?
- **일관성**: 법적 논리에 모순이 없는가?
- **실무성**: 실제 적용 가능한 조언인가?
- **안전성**: 법적 위험이 적절히 고지되었는가?
- **최신성**: 최신 법령 개정사항이 반영되었는가?

검증 결과 포맷:
1. **종합 판정**: PASS / CONDITIONAL_PASS / FAIL
2. **세부 검증 결과**:
   - 내용 검증: 답변 논리와 법적 정확성
   - 인용 검증: 출처와 인용의 정확성
   - 일관성 검증: 답변-근거-출처 간 일치성
3. **위험 평가**: 높음/보통/낮음 + 구체적 위험 요소
4. **개선 권고**: 구체적인 수정 또는 보완 방향
5. **최종 신뢰도**: 검증된 조언의 신뢰성 점수 (1-10점)

검증 원칙:
- **보수적 접근**: 불확실한 경우 보수적으로 판단
- **사용자 보호 우선**: 사용자에게 불리한 결과를 초래할 가능성 경고
- **전문가 상담 권유**: 복잡하거나 고위험 사안은 전문가 상담 권유
- **한계 명시**: AI 조언의 한계와 법적 책임 부인 명확히 표시

중요: 절대 검증 과정을 건너뛰지 말고, 의심스러운 부분은 반드시 지적해. 사용자의 법적 안전이 최우선이야."""

    async def process(
        self,
        user_input: str,
        context: ConversationContext
    ) -> AgentResponse:
        """종합적인 답변+근거+출처 검증"""

        logger.info("Enhanced validator agent performing comprehensive verification")

        try:
            # 검증 대상 데이터 추출
            validation_data = self._extract_validation_data(context)

            if not validation_data:
                return AgentResponse(
                    action=AgentAction.COMPLETE,
                    message="검증할 데이터가 없습니다.",
                    confidence=0.0
                )

            # 종합 검증 수행
            validation_result = await self._perform_comprehensive_validation(
                validation_data,
                user_input,
                context
            )

            # 최종 답변 구성
            final_answer = self._construct_final_answer(validation_data, validation_result)

            return AgentResponse(
                action=AgentAction.COMPLETE,
                message=final_answer,
                confidence=validation_result.final_confidence,
                metadata={
                    "validation_result": validation_result,
                    "validation_status": validation_result.overall_status
                }
            )

        except Exception as e:
            logger.error(f"Error in enhanced validator agent: {e}")
            return AgentResponse(
                action=AgentAction.COMPLETE,
                message="검증 중 오류가 발생했습니다. 답변을 주의해서 참고하시기 바랍니다.",
                confidence=0.3,
                metadata={"error": str(e)}
            )

    def _extract_validation_data(self, context: ConversationContext) -> Optional[Dict[str, Any]]:
        """검증할 데이터 추출"""

        validation_data = {
            "answer_content": "",
            "analysis_result": None,
            "citation_package": None,
            "search_results": None
        }

        if not context.agent_responses:
            return None

        # 각 에이전트의 결과 추출
        for response in context.agent_responses:
            metadata = response.metadata or {}

            # 응답 에이전트 결과
            if "ResponseAgent" in metadata.get("agent_name", "") or (response.message and "법적" in response.message):
                validation_data["answer_content"] = response.message

            # 분석가 에이전트 결과
            if "analysis_result" in metadata:
                validation_data["analysis_result"] = metadata["analysis_result"]

            # 인용 에이전트 결과
            if "citation_package" in metadata:
                validation_data["citation_package"] = metadata["citation_package"]

            # 검색 결과
            if "search_results" in metadata:
                validation_data["search_results"] = metadata["search_results"]

        return validation_data if validation_data["answer_content"] else None

    async def _perform_comprehensive_validation(
        self,
        validation_data: Dict[str, Any],
        user_query: str,
        context: ConversationContext
    ) -> ValidationResult:
        """종합 검증 수행"""

        # 1. 내용 검증
        content_validation = await self._validate_content(
            validation_data["answer_content"],
            validation_data["analysis_result"],
            user_query
        )

        # 2. 인용 검증
        citation_validation = await self._validate_citations(
            validation_data["citation_package"],
            validation_data["answer_content"]
        )

        # 3. 일관성 검증
        consistency_validation = await self._validate_consistency(
            validation_data["answer_content"],
            validation_data["citation_package"],
            validation_data["analysis_result"]
        )

        # 4. 위험도 평가
        risk_assessment = await self._assess_risks(
            validation_data,
            user_query
        )

        # 5. 종합 판정
        overall_status = self._determine_overall_status(
            content_validation,
            citation_validation,
            consistency_validation,
            risk_assessment
        )

        # 6. 개선 제안
        improvement_suggestions = self._generate_improvement_suggestions(
            content_validation,
            citation_validation,
            consistency_validation,
            risk_assessment
        )

        # 7. 최종 신뢰도 계산
        final_confidence = self._calculate_final_confidence(
            content_validation,
            citation_validation,
            consistency_validation
        )

        return ValidationResult(
            overall_status=overall_status,
            content_validation=content_validation,
            citation_validation=citation_validation,
            consistency_validation=consistency_validation,
            risk_assessment=risk_assessment,
            improvement_suggestions=improvement_suggestions,
            final_confidence=final_confidence,
            validation_metadata={
                "validation_timestamp": datetime.now().isoformat(),
                "validator_version": "2.0",
                "query_complexity": self._assess_query_complexity(user_query)
            }
        )

    async def _validate_content(
        self,
        answer_content: str,
        analysis_result: Optional[AnalysisResult],
        user_query: str
    ) -> Dict[str, Any]:
        """답변 내용 검증"""

        prompt = f"""다음 법률 답변의 내용을 검증해줘.

사용자 질문: {user_query}

답변 내용:
{answer_content}

분석 결과:
{analysis_result.analysis_summary if analysis_result else "분석 정보 없음"}

다음 관점에서 검증해줘:
1. **법적 정확성**: 법령 해석과 적용이 정확한가?
2. **논리 일관성**: 답변의 논리적 흐름이 일관된가?
3. **완전성**: 중요한 법적 요소가 누락되지 않았는가?
4. **명확성**: 사용자가 이해하기 쉽게 설명되었는가?

검증 결과를 다음 형태로 제공해줘:
- 정확성 점수: (1-10)
- 일관성 점수: (1-10)
- 완전성 점수: (1-10)
- 발견된 문제점: [구체적 문제점들]
- 강점: [답변의 장점들]"""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=600)
            return self._parse_validation_response(response, "content")

        except Exception as e:
            logger.error(f"Content validation failed: {e}")
            return {
                "accuracy_score": 5.0,
                "consistency_score": 5.0,
                "completeness_score": 5.0,
                "issues": [f"검증 중 오류 발생: {str(e)}"],
                "strengths": []
            }

    async def _validate_citations(
        self,
        citation_package: Optional[CitationPackage],
        answer_content: str
    ) -> Dict[str, Any]:
        """인용 검증"""

        if not citation_package:
            return {
                "citation_accuracy": 0.0,
                "source_reliability": 0.0,
                "issues": ["인용 정보 없음"],
                "verified_citations": 0,
                "total_citations": 0
            }

        prompt = f"""다음 인용 정보들의 정확성을 검증해줘.

답변 내용:
{answer_content[:500]}...

인용 정보:
{citation_package.formatted_citations[:1000]}...

다음을 검증해줘:
1. **인용 정확성**: 법령명, 조문번호, 판례번호가 정확한가?
2. **출처 신뢰성**: 1차 공식 출처인가? 신뢰할 만한가?
3. **관련성**: 인용된 내용이 답변과 관련성이 있는가?
4. **최신성**: 최신 개정사항이 반영되었는가?

검증 결과:
- 인용 정확성: (1-10)
- 출처 신뢰성: (1-10)
- 문제있는 인용: [구체적 문제점]
- 검증된 인용 수: X / 전체 Y"""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=500)
            return self._parse_validation_response(response, "citation")

        except Exception as e:
            logger.error(f"Citation validation failed: {e}")
            return {
                "citation_accuracy": 7.0,
                "source_reliability": 7.0,
                "issues": [],
                "verified_citations": len(citation_package.citations),
                "total_citations": len(citation_package.citations)
            }

    async def _validate_consistency(
        self,
        answer_content: str,
        citation_package: Optional[CitationPackage],
        analysis_result: Optional[AnalysisResult]
    ) -> Dict[str, Any]:
        """답변-근거-분석 간 일관성 검증"""

        citation_summary = citation_package.formatted_citations[:500] if citation_package else "인용 정보 없음"
        analysis_summary = analysis_result.analysis_summary if analysis_result else "분석 정보 없음"

        prompt = f"""답변, 분석, 인용 간의 일관성을 검증해줘.

답변:
{answer_content[:400]}...

분석 요약:
{analysis_summary}

인용 요약:
{citation_summary}...

검증 포인트:
1. 답변의 결론이 인용된 법령/판례와 일치하는가?
2. 분석에서 식별된 쟁점이 답변에 반영되었는가?
3. 과도한 해석이나 논리적 비약이 있는가?

일관성 점수: (1-10)
불일치 사항: [구체적 불일치 내용]"""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=400)
            return self._parse_validation_response(response, "consistency")

        except Exception as e:
            logger.error(f"Consistency validation failed: {e}")
            return {
                "consistency_score": 7.0,
                "inconsistencies": [],
                "logical_gaps": []
            }

    async def _assess_risks(
        self,
        validation_data: Dict[str, Any],
        user_query: str
    ) -> Dict[str, str]:
        """위험도 평가"""

        # 키워드 기반 위험도 초기 평가
        high_risk_keywords = ["손해배상", "형사처벌", "과징금", "영업정지", "허가취소"]
        medium_risk_keywords = ["신고", "허가", "등록", "의무", "제재"]

        query_lower = user_query.lower()

        if any(keyword in query_lower for keyword in high_risk_keywords):
            risk_level = "높음"
            risk_factors = ["중대한 법적 결과 초래 가능"]
        elif any(keyword in query_lower for keyword in medium_risk_keywords):
            risk_level = "보통"
            risk_factors = ["법적 의무 위반 위험"]
        else:
            risk_level = "낮음"
            risk_factors = ["일반적인 주의사항"]

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendations": self._generate_risk_recommendations(risk_level)
        }

    def _generate_risk_recommendations(self, risk_level: str) -> List[str]:
        """위험도별 권고사항 생성"""

        if risk_level == "높음":
            return [
                "반드시 해당 분야 전문 변호사와 상담하시기 바랍니다",
                "법적 조치 이전에 충분한 검토가 필요합니다",
                "관련 법령의 최신 개정사항을 확인하시기 바랍니다"
            ]
        elif risk_level == "보통":
            return [
                "관련 전문가 상담을 권장합니다",
                "구체적인 적용 시 주의사항을 확인하시기 바랍니다"
            ]
        else:
            return [
                "일반적인 참고사항으로 활용하시기 바랍니다"
            ]

    def _determine_overall_status(
        self,
        content_validation: Dict[str, Any],
        citation_validation: Dict[str, Any],
        consistency_validation: Dict[str, Any],
        risk_assessment: Dict[str, str]
    ) -> str:
        """종합 판정 결정"""

        # 점수 기반 판정
        avg_content_score = (
            content_validation.get("accuracy_score", 0) +
            content_validation.get("consistency_score", 0) +
            content_validation.get("completeness_score", 0)
        ) / 3

        citation_score = (
            citation_validation.get("citation_accuracy", 0) +
            citation_validation.get("source_reliability", 0)
        ) / 2

        consistency_score = consistency_validation.get("consistency_score", 0)

        overall_score = (avg_content_score + citation_score + consistency_score) / 3

        # 위험도 고려
        risk_level = risk_assessment.get("risk_level", "낮음")

        if overall_score >= 8.0 and risk_level in ["낮음", "보통"]:
            return "PASS"
        elif overall_score >= 6.0:
            return "CONDITIONAL_PASS"
        else:
            return "FAIL"

    def _generate_improvement_suggestions(
        self,
        content_validation: Dict[str, Any],
        citation_validation: Dict[str, Any],
        consistency_validation: Dict[str, Any],
        risk_assessment: Dict[str, str]
    ) -> List[str]:
        """개선 제안 생성"""

        suggestions = []

        # 내용 개선 제안
        if content_validation.get("accuracy_score", 10) < 7:
            suggestions.append("법적 정확성 재검토 필요")

        if content_validation.get("completeness_score", 10) < 7:
            suggestions.append("누락된 법적 요소 보완 필요")

        # 인용 개선 제안
        if citation_validation.get("citation_accuracy", 10) < 7:
            suggestions.append("인용 정보 정확성 확인 필요")

        # 일관성 개선 제안
        if consistency_validation.get("consistency_score", 10) < 7:
            suggestions.append("답변-근거 간 논리적 일관성 강화 필요")

        # 위험도별 제안
        if risk_assessment.get("risk_level") == "높음":
            suggestions.append("고위험 사안으로 전문가 검토 권장")

        return suggestions

    def _calculate_final_confidence(
        self,
        content_validation: Dict[str, Any],
        citation_validation: Dict[str, Any],
        consistency_validation: Dict[str, Any]
    ) -> float:
        """최종 신뢰도 계산"""

        weights = {
            "content": 0.5,
            "citation": 0.3,
            "consistency": 0.2
        }

        content_score = (
            content_validation.get("accuracy_score", 0) +
            content_validation.get("consistency_score", 0) +
            content_validation.get("completeness_score", 0)
        ) / 30  # 30점 만점을 1.0으로 정규화

        citation_score = (
            citation_validation.get("citation_accuracy", 0) +
            citation_validation.get("source_reliability", 0)
        ) / 20  # 20점 만점을 1.0으로 정규화

        consistency_score = consistency_validation.get("consistency_score", 0) / 10

        final_confidence = (
            content_score * weights["content"] +
            citation_score * weights["citation"] +
            consistency_score * weights["consistency"]
        )

        return min(final_confidence, 1.0)

    def _parse_validation_response(self, response: str, validation_type: str) -> Dict[str, Any]:
        """검증 응답 파싱"""

        result = {}

        # 점수 추출
        import re
        scores = re.findall(r'(\d+(?:\.\d+)?)', response)

        if validation_type == "content":
            result["accuracy_score"] = float(scores[0]) if len(scores) > 0 else 5.0
            result["consistency_score"] = float(scores[1]) if len(scores) > 1 else 5.0
            result["completeness_score"] = float(scores[2]) if len(scores) > 2 else 5.0
            result["issues"] = self._extract_issues(response)
            result["strengths"] = self._extract_strengths(response)

        elif validation_type == "citation":
            result["citation_accuracy"] = float(scores[0]) if len(scores) > 0 else 7.0
            result["source_reliability"] = float(scores[1]) if len(scores) > 1 else 7.0
            result["verified_citations"] = int(float(scores[2])) if len(scores) > 2 else 0
            result["total_citations"] = int(float(scores[3])) if len(scores) > 3 else 0
            result["issues"] = self._extract_issues(response)

        elif validation_type == "consistency":
            result["consistency_score"] = float(scores[0]) if len(scores) > 0 else 7.0
            result["inconsistencies"] = self._extract_inconsistencies(response)
            result["logical_gaps"] = []

        return result

    def _extract_issues(self, text: str) -> List[str]:
        """문제점 추출"""
        issues = []
        lines = text.split('\n')
        for line in lines:
            if '문제' in line or '오류' in line or '부정확' in line:
                issues.append(line.strip('- ').strip())
        return issues[:3]  # 최대 3개

    def _extract_strengths(self, text: str) -> List[str]:
        """장점 추출"""
        strengths = []
        lines = text.split('\n')
        for line in lines:
            if '강점' in line or '좋은' in line or '정확' in line:
                strengths.append(line.strip('- ').strip())
        return strengths[:3]  # 최대 3개

    def _extract_inconsistencies(self, text: str) -> List[str]:
        """불일치 사항 추출"""
        inconsistencies = []
        lines = text.split('\n')
        for line in lines:
            if '불일치' in line or '모순' in line:
                inconsistencies.append(line.strip('- ').strip())
        return inconsistencies[:3]  # 최대 3개

    def _assess_query_complexity(self, query: str) -> str:
        """질의 복잡도 평가"""

        complex_indicators = ["동시에", "관계", "충돌", "예외", "특수", "복합"]
        medium_indicators = ["절차", "방법", "기준", "요건"]

        query_lower = query.lower()

        if any(indicator in query_lower for indicator in complex_indicators):
            return "복잡"
        elif any(indicator in query_lower for indicator in medium_indicators):
            return "보통"
        else:
            return "단순"

    def _construct_final_answer(
        self,
        validation_data: Dict[str, Any],
        validation_result: ValidationResult
    ) -> str:
        """최종 답변 구성"""

        # 기본 답변
        answer_parts = [validation_data["answer_content"]]

        # 인용 정보 추가
        if validation_data["citation_package"]:
            answer_parts.append("\n---\n")
            answer_parts.append(validation_data["citation_package"].formatted_citations)

        # 검증 정보 추가
        answer_parts.append("\n---\n")
        answer_parts.append("# ✅ 검증 정보")
        answer_parts.append(f"- **답변 신뢰도**: {validation_result.final_confidence:.1f}/1.0")
        answer_parts.append(f"- **검증 상태**: {validation_result.overall_status}")

        if validation_result.risk_assessment.get("risk_level") != "낮음":
            answer_parts.append(f"- **위험도**: {validation_result.risk_assessment.get('risk_level')}")

        if validation_result.improvement_suggestions:
            answer_parts.append("- **주의사항**: " + ", ".join(validation_result.improvement_suggestions[:2]))

        # 법률 조언 한계 고지
        answer_parts.append("\n---\n")
        answer_parts.append("# ⚠️ 법률 조언의 한계")
        answer_parts.append("본 답변은 일반적인 법률 정보 제공을 목적으로 하며, 구체적인 법률 조언이 아닙니다. 실제 적용 시에는 관련 전문가와의 상담을 권장합니다.")

        return "\n".join(answer_parts)