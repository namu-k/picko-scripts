# Feature Specification: OpenRouter LLM Provider

**Feature Branch**: `001-openrouter-provider`
**Created**: 2026-02-16
**Status**: Approved
**Input**: Add OpenRouter as an LLM provider to picko-scripts for flexible model routing and cost optimization.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure OpenRouter as Writer LLM (Priority: P1)

개발자는 config.yml에서 writer_llm을 OpenRouter로 설정하고, OPENROUTER_API_KEY만 설정하면 글쓰기 파이프라인을 OpenRouter 모델로 실행할 수 있어야 한다.

**Why this priority**: 핵심 기능. OpenRouter 없이는 목표 달성 불가.

**Independent Test**: config.yml에 provider: "openrouter" 설정 후 generate_content 실행 시 OpenRouter API로 호출되는지 확인.

**Acceptance Scenarios**:

1. **Given** config에 writer_llm.provider: "openrouter", model: "openai/gpt-4o-mini", **When** generate_content 실행, **Then** OpenRouter API가 호출되어 longform 콘텐츠가 생성된다.
2. **Given** OPENROUTER_API_KEY 미설정, **When** OpenRouter 클라이언트 초기화, **Then** 누락된 API 키를 식별하는 경고 로그가 기록되고 빠르게 실패(fail-fast)한다.

---

### User Story 2 - Use OpenRouter for Summary/Tagging (Priority: P2)

개발자는 summary_llm을 OpenRouter로 설정해 요약·태깅 작업을 OpenRouter로 수행할 수 있어야 한다.

**Why this priority**: 요약·태깅도 OpenRouter로 통일 가능. 로컬 Ollama가 없는 환경에서 유용.

**Independent Test**: daily_collector 실행 시 OpenRouter 모델로 요약·태깅이 수행되는지 확인.

**Acceptance Scenarios**:

1. **Given** summary_llm.provider: "openrouter", model: "openai/gpt-4o-mini", **When** daily_collector 실행, **Then** RSS 수집 후 요약·태깅이 OpenRouter로 처리된다.
2. **Given** summary_llm.provider: "openrouter" with invalid model ID, **When** API 호출, **Then** 적절한 에러 메시지가 로깅된다.

---

### User Story 3 - Stream Generation Support (Priority: P2)

OpenRouterClient는 generate_stream()을 지원해 스트리밍 응답을 받을 수 있어야 한다.

**Why this priority**: 기존 클라이언트와 동일한 인터페이스 제공. BaseLLMClient 계약 충족 필수.

**Independent Test**: generate_stream() 호출 시 청크가 순차적으로 반환되는지 확인.

**Acceptance Scenarios**:

1. **Given** OpenRouterClient 초기화 완료, **When** generate_stream(prompt) 호출, **Then** 텍스트 청크가 Generator로 순차 반환된다.
2. **Given** 스트리밍 중 네트워크 오류 발생, **When** 청크 수신 중단, **Then** 예외가 적절히 전파된다.

---

### Edge Cases

- OPENROUTER_API_KEY가 빈 문자열일 때: 초기화 시 명확한 경고 로그 출력, API 호출 시 인증 에러 반환.
- 잘못된 모델 ID(예: openai/invalid-model) 사용 시: OpenRouter API의 에러 응답이 LLMClient 재시도 로직을 통해 처리되고, 최종적으로 사용자에게 모델 ID 확인 메시지 전달.
- OpenRouter API가 5xx를 반환할 때: 기존 LLMClient의 지수 백오프 재시도 로직(max_retries 설정)이 적용됨.
- config.yml에 provider: "openrouter"이지만 api_key_env가 누락된 경우: 기본값 "OPENROUTER_API_KEY" 사용.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: OpenRouterClient는 OpenAI 호환 API를 사용하며 base_url="https://openrouter.ai/api/v1"를 사용한다.
- **FR-002**: 모델 ID는 provider/model 형식(예: openai/gpt-4o-mini, anthropic/claude-3.5-sonnet)을 지원한다.
- **FR-003**: OpenRouter 사용 시, API 키는 `api_key_env`로 지정된 환경변수에서 로드한다. OpenRouter 미지정 시 기본값은 `OPENROUTER_API_KEY`이며, 이는 `LLMConfig` 전역 기본값(`OPENAI_API_KEY`)과 별개이다.
- **FR-004**: generate()와 generate_stream()을 BaseLLMClient 인터페이스에 맞게 구현한다.
- **FR-005**: 기존 LLMClient 래퍼의 캐싱·재시도 로직을 그대로 활용한다 (추가 구현 불필요).
- **FR-006**: config.yml의 llm, summary_llm, writer_llm에 provider: "openrouter"를 설정할 수 있다.
- **FR-007**: 기존 OpenAI, Anthropic, Ollama 프로바이더 동작에 영향이 없다 (무변경).

### Key Entities

- **OpenRouterClient**: BaseLLMClient를 상속하는 구체 클라이언트 클래스. OpenAI Python SDK를 custom base_url로 초기화하여 OpenRouter API에 연결.
- **LLMConfig**: 기존 dataclass는 변경 없음. `provider="openrouter"` 설정 시 `api_key_env`를 `"OPENROUTER_API_KEY"`로 명시해야 한다. `LLMConfig` 전역 기본값(`OPENAI_API_KEY`)은 유지된다.
- **SummaryLLMConfig**: `api_key_env: str = ""` 필드 추가. OpenRouter 사용 시 `"OPENROUTER_API_KEY"` 로 설정.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: provider="openrouter"로 설정 시 LLMClient가 정상 초기화되고 generate()가 텍스트를 반환한다.
- **SC-002**: OPENROUTER_API_KEY 설정 시 실제 API 호출로 유효한 응답을 받을 수 있다.
- **SC-003**: pytest 단위 테스트(모킹)가 모두 통과한다.
- **SC-004**: writer_llm을 openrouter로 설정한 뒤 generate_content 스크립트로 콘텐츠가 생성된다.
- **SC-005**: 기존 테스트 스위트가 regression 없이 통과한다.
