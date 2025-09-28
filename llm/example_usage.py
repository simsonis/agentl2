"""
Example usage of the Enhanced 6-Agent Legal Pipeline

This demonstrates how to use the enhanced pipeline for legal consultations
with comprehensive analysis, citations, and validation.
"""

import asyncio
import os
from src.agentl2_llm.pipeline.enhanced_agent_pipeline import EnhancedAgentPipeline, EnhancedConversationManager

class LegalConsultationDemo:
    """Demo class for legal consultation using enhanced pipeline"""

    def __init__(self, openai_api_key: str):
        self.pipeline = EnhancedAgentPipeline(
            openai_api_key=openai_api_key,
            openai_model="gpt-4",
            temperature=0.3,
            max_conversation_turns=5
        )
        self.conversation_manager = EnhancedConversationManager(self.pipeline)

    async def demonstrate_legal_consultation(self):
        """Demonstrate complete legal consultation flow"""

        print("🏛️  Enhanced Legal AI Assistant - 6-Agent Pipeline Demo")
        print("="*60)

        # Example legal queries
        test_queries = [
            "개인정보보호법상 가명정보 처리가 가능한 경우는?",
            "금융소비자보호법에서 설명의무 위반 시 책임은?",
            "근로기준법상 연장근로 한도와 예외사항을 알려주세요."
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"\n📋 Query {i}: {query}")
            print("-" * 50)

            try:
                # Start new conversation
                conversation_id, response = await self.conversation_manager.start_conversation(query)

                # Display results
                self._display_response(response)

                # Show detailed analysis
                analysis = self.conversation_manager.get_conversation_analysis(conversation_id)
                if analysis:
                    self._display_analysis(analysis)

                print("\n" + "="*60)

            except Exception as e:
                print(f"❌ Error processing query: {e}")

    def _display_response(self, response):
        """Display formatted response"""

        print(f"⏱️  Processing Time: {response.processing_time:.2f}s")
        print(f"🎯 Confidence: {response.confidence:.1%}")

        print(f"\n📝 Answer:")
        # Display first 300 characters
        answer_preview = response.answer[:300] + "..." if len(response.answer) > 300 else response.answer
        print(answer_preview)

        if response.sources:
            print(f"\n📚 Sources ({len(response.sources)}):")
            for i, source in enumerate(response.sources[:3], 1):  # Show top 3
                print(f"  {i}. {source.title}")
                print(f"     Type: {source.source_type.value}")
                print(f"     Confidence: {source.confidence:.1%}")

        if response.related_keywords:
            print(f"\n🔍 Related Keywords: {', '.join(response.related_keywords[:5])}")

        if response.follow_up_questions:
            print(f"\n❓ Follow-up Questions:")
            for question in response.follow_up_questions[:2]:
                print(f"  • {question}")

    def _display_analysis(self, analysis):
        """Display conversation analysis"""

        print(f"\n📊 Pipeline Analysis:")
        performance = analysis['pipeline_performance']
        print(f"  Completion Rate: {performance['completion_rate']:.1%}")
        print(f"  Agents Executed: {performance['agents_executed']}/{performance['total_agents']}")

        # Show legal analysis if available
        legal_analysis = analysis['detailed_analysis'].get('legal_analysis')
        if legal_analysis:
            print(f"  Core Issues: {len(legal_analysis.core_issues)}")
            print(f"  Applicable Laws: {len(legal_analysis.applicable_laws)}")
            print(f"  Analysis Confidence: {legal_analysis.confidence_score:.1f}/1.0")

    async def close(self):
        """Close the pipeline"""
        await self.pipeline.close()

async def main():
    """Main demo function"""

    # Get API key from environment or replace with your key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        return

    # Create and run demo
    demo = LegalConsultationDemo(api_key)

    try:
        await demo.demonstrate_legal_consultation()
    finally:
        await demo.close()

if __name__ == "__main__":
    # Example of how to run the demo
    print("Starting Enhanced Legal Pipeline Demo...")
    asyncio.run(main())