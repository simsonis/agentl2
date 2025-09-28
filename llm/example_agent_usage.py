"""
Example usage of the agent-based legal chatbot.
"""

import asyncio
import os
from agentl2_llm import AgentPipeline, ConversationManager


async def example_conversation():
    """Example conversation flow."""

    # Initialize pipeline
    pipeline = AgentPipeline(
        openai_api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        openai_model="gpt-4"
    )

    # Create conversation manager
    conv_manager = ConversationManager(pipeline)

    print("=== 법률 AI 어시스턴트 예제 ===\n")

    try:
        # Example 1: Vague query (should request clarification)
        print("1. 모호한 질의 예제:")
        print("사용자: 개인정보 관련해서 궁금한 게 있어요")

        conv_id, response = await conv_manager.start_conversation(
            "개인정보 관련해서 궁금한 게 있어요"
        )

        print(f"AI: {response.answer}")
        print(f"신뢰도: {response.confidence:.2f}")
        print(f"후속 질문: {response.follow_up_questions}")
        print("\n" + "="*50 + "\n")

        # Example 2: Specific query (should proceed to search)
        print("2. 구체적인 질의 예제:")
        print("사용자: 개인정보보호법 제15조 수집 동의 절차가 궁금합니다")

        response = await conv_manager.continue_conversation(
            conv_id,
            "개인정보보호법 제15조 수집 동의 절차가 궁금합니다"
        )

        print(f"AI: {response.answer[:300]}...")
        print(f"신뢰도: {response.confidence:.2f}")
        print(f"참조 출처: {len(response.sources)}건")
        print("\n" + "="*50 + "\n")

        # Example 3: New conversation with different topic
        print("3. 새로운 주제 대화:")
        print("사용자: 금융소비자보호법에서 불완전판매란 무엇인가요?")

        conv_id2, response = await conv_manager.start_conversation(
            "금융소비자보호법에서 불완전판매란 무엇인가요?"
        )

        print(f"AI: {response.answer[:300]}...")
        print(f"신뢰도: {response.confidence:.2f}")
        print("\n" + "="*50 + "\n")

        # Get conversation status
        print("4. 대화 상태 확인:")
        status = conv_manager.get_conversation_summary(conv_id)
        if status:
            print(f"대화 턴 수: {status['turn_count']}")
            print(f"추출된 의도: {status['extracted_intent']}")
            print(f"키워드: {status['extracted_keywords']}")

    except Exception as e:
        print(f"오류 발생: {e}")

    finally:
        await pipeline.close()


async def test_agent_responses():
    """Test different types of agent responses."""

    pipeline = AgentPipeline(
        openai_api_key=os.getenv("OPENAI_API_KEY", "test-key")
    )

    test_queries = [
        # Should request clarification
        "법률 문의가 있습니다",

        # Should be specific enough
        "가명정보 처리 시 개인정보보호법 적용 기준이 궁금합니다",

        # Should trigger precedent search
        "개인정보 유출 사고 관련 대법원 판례를 찾고 있습니다",

        # Should trigger procedure guidance
        "개인정보 처리 신고 절차가 어떻게 되나요?"
    ]

    print("=== 에이전트 응답 테스트 ===\n")

    try:
        for i, query in enumerate(test_queries, 1):
            print(f"{i}. 질의: {query}")

            response = await pipeline.process_message(query)

            print(f"   응답: {response.answer[:200]}...")
            print(f"   신뢰도: {response.confidence:.2f}")
            print(f"   후속 질문 수: {len(response.follow_up_questions)}")
            print(f"   참조 출처: {len(response.sources)}건")
            print()

    except Exception as e:
        print(f"테스트 중 오류: {e}")

    finally:
        await pipeline.close()


if __name__ == "__main__":
    print("에이전트 기반 법률 챗봇 예제를 실행합니다...\n")

    # Run example conversation
    asyncio.run(example_conversation())

    print("\n" + "="*60 + "\n")

    # Run agent response tests
    asyncio.run(test_agent_responses())