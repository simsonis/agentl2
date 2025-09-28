"""
Test script for the enhanced 6-agent pipeline
"""

import asyncio
import os
from src.agentl2_llm.pipeline.enhanced_agent_pipeline import EnhancedAgentPipeline, EnhancedConversationManager

async def test_enhanced_pipeline():
    """Test the enhanced 6-agent pipeline"""

    # Initialize pipeline (you'll need to set your OpenAI API key)
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")

    pipeline = EnhancedAgentPipeline(
        openai_api_key=api_key,
        openai_model="gpt-4",
        temperature=0.3
    )

    try:
        # Test pipeline status
        print("🔧 Pipeline Status:")
        status = await pipeline.get_pipeline_status()
        print(f"Pipeline Type: {status['pipeline']['type']}")
        print(f"Active Conversations: {status['pipeline']['active_conversations']}")

        for agent_name, agent_info in status['agents'].items():
            print(f"  - {agent_name}: {agent_info['status']} ({agent_info['role']})")

        print("\n" + "="*50)

        # Test conversation manager
        conversation_manager = EnhancedConversationManager(pipeline)

        # Test legal query
        test_query = "개인정보보호법에서 가명정보 처리 조건은 무엇인가요?"

        print(f"🤖 Processing Query: {test_query}")
        print("\n📋 Agent Pipeline Execution:")

        conversation_id, response = await conversation_manager.start_conversation(test_query)

        print(f"✅ Pipeline Complete!")
        print(f"Conversation ID: {conversation_id}")
        print(f"Processing Time: {response.processing_time:.2f}s")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Sources Found: {len(response.sources)}")

        print("\n📝 Final Answer:")
        print(response.answer[:200] + "..." if len(response.answer) > 200 else response.answer)

        # Test conversation analysis
        analysis = conversation_manager.get_conversation_analysis(conversation_id)
        if analysis:
            print(f"\n📊 Conversation Analysis:")
            print(f"Pipeline Completion Rate: {analysis['pipeline_performance']['completion_rate']:.1%}")
            print(f"Agents Executed: {analysis['pipeline_performance']['agents_executed']}/6")

            if analysis['detailed_analysis']['legal_analysis']:
                legal_analysis = analysis['detailed_analysis']['legal_analysis']
                print(f"Core Issues: {len(legal_analysis.core_issues)}")
                print(f"Applicable Laws: {len(legal_analysis.applicable_laws)}")

        print("\n🎯 Test completed successfully!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")

    finally:
        await pipeline.close()

if __name__ == "__main__":
    asyncio.run(test_enhanced_pipeline())