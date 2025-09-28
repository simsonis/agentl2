# agentl2-llm

LLM-based legal chatbot module for the agentl2 project with **agent-based architecture**.

## Features

- **🤖 Multi-Agent System**: Specialized agents for different conversation stages
- **💬 Conversational Flow**: Natural back-and-forth dialogue with clarification requests
- **🔍 Smart Search**: Multi-source search with keyword enhancement
- **✅ Information Verification**: Fact checking and source validation
- **📚 Expert Responses**: LLM-powered legal advice with proper citations
- **🧠 Context Management**: Maintains conversation context across multiple turns

## Agent Architecture

```
User Query → Facilitator Agent → Search Agent → Response Agent → Final Answer
     ↓              ↓              ↓             ↓              ↓
Intent Analysis → Search Execution → Information → Expert Legal
& Clarification   & Enhancement     Verification   Response
```

### Agents

1. **Facilitator Agent**: 20년차 법률 상담가 역할
   - 사용자 의도 파악 및 키워드 추출
   - 정보 부족 시 추가 질문 생성
   - 자연스러운 대화 진행

2. **Search Agent**: 법률 검색 전문가
   - 키워드 최적화 및 확장
   - 내부/외부 소스 검색 조정
   - 검색 결과 품질 평가

3. **Response Agent**: 시니어 변호사 역할
   - 종합적인 법률 조언 생성
   - 출처 검증 및 인용
   - 실무 가이드 제공

## Quick Start

```python
from agentl2_llm import AgentPipeline, ConversationManager

# Initialize agent pipeline
pipeline = AgentPipeline(
    openai_api_key="your-api-key",
    openai_model="gpt-4"
)

# Create conversation manager
conv_manager = ConversationManager(pipeline)

# Start a conversation
conv_id, response = await conv_manager.start_conversation(
    "개인정보보호법 관련 질문이 있습니다"
)

print(response.answer)  # May request clarification

# Continue conversation
response = await conv_manager.continue_conversation(
    conv_id,
    "가명정보 처리 시 동의 절차가 궁금합니다"
)

print(response.answer)  # Detailed legal advice
print(f"Sources: {len(response.sources)}")
print(f"Confidence: {response.confidence:.2f}")

await pipeline.close()
```

## Architecture

```
User Query → Query Analysis → Search Execution → Information Verification → Response Generation
     ↓             ↓              ↓                    ↓                        ↓
Intent/Keywords → Internal/External → Fact Checking → LLM Response → Final Answer
```

## Agent-Based Components

### Core Agents
- **`FacilitatorAgent`**: 20년차 법률 상담가로서 의도 파악 및 대화 진행
- **`SearchAgent`**: 법률 검색 전문가로서 최적화된 검색 수행
- **`ResponseAgent`**: 시니어 변호사로서 전문적인 법률 조언 생성

### Pipeline & Management
- **`AgentPipeline`**: 에이전트 간 통신 및 상태 관리
- **`ConversationManager`**: 대화 컨텍스트 및 세션 관리

### Support Components
- `SearchCoordinator`: 내부/외부 검색 소스 관리
- `FactChecker`: 정보 신뢰성 검증
- `SourceValidator`: 출처 검증 및 인용 관리

## Configuration

Environment variables:
```bash
LLM_OPENAI_API_KEY=your-openai-api-key
LLM_OPENAI_MODEL=gpt-4
LLM_SEARCH_LIMIT=20
LLM_ENABLE_INTERNAL_SEARCH=true
LLM_ENABLE_EXTERNAL_SEARCH=true
```

## External Search Sources

Currently supported:
- **casenote.kr**: Legal database with laws and precedents
  - Law search: `https://casenote.kr/search_law/?q={keyword}`
  - Precedent search: `https://casenote.kr/search/?q={keyword}`

## Usage Examples

### Conversational Flow
```python
# Vague query → Clarification request
response = await pipeline.process_message("개인정보 관련 질문이 있어요")
# Response: "더 구체적인 상황을 알려주시면..."

# Specific query → Direct answer
response = await pipeline.process_message(
    "개인정보보호법 제15조 수집 동의 절차가 궁금합니다",
    conversation_id
)
# Response: Detailed legal advice with sources
```

### Multi-turn Conversation
```python
conv_manager = ConversationManager(pipeline)

# Start conversation
conv_id, response = await conv_manager.start_conversation(
    "금융상품 불완전판매 관련 문의"
)

# Continue conversation
response = await conv_manager.continue_conversation(
    conv_id,
    "구체적으로 펀드 투자 관련해서 설명의무 위반 시 구제 방법이 궁금합니다"
)

# Get conversation summary
summary = conv_manager.get_conversation_summary(conv_id)
```

### Status Monitoring
```python
status = await pipeline.get_pipeline_status()
conv_status = pipeline.get_conversation_status(conversation_id)
```

## Response Format

```python
class LegalResponse:
    answer: str                    # Main legal advice
    sources: List[SearchSource]    # Referenced sources
    confidence: float              # Response reliability (0-1)
    related_keywords: List[str]    # Related legal terms
    follow_up_questions: List[str] # Suggested next questions
    processing_time: float         # Processing duration
    query: LegalQuery             # Original processed query
```

## Development

Install dependencies:
```bash
cd llm
poetry install
```

Run tests:
```bash
poetry run pytest
```

## Integration with Main Project

Add to docker-compose.yml:
```yaml
llm-service:
  build:
    context: ./llm
  container_name: agentl2-llm
  environment:
    - LLM_OPENAI_API_KEY=${OPENAI_API_KEY}
  ports:
    - "8001:8000"
```

## Roadmap

- [ ] Integration with internal database search
- [ ] Advanced legal reasoning capabilities
- [ ] Multi-language support
- [ ] Legal document analysis
- [ ] Conversation memory persistence