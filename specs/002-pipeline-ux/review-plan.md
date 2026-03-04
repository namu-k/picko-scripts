 Plan Review: 002-pipeline-ux/plan.md — 다각도 비판

  ---
  1. 구조/형식 (Structure)

  양호한 점: Summary → Technical Context → Constitution Check → Project    
  Structure → Implementation Details → Traceability → Dependencies 순서가  
  체계적이다. Traceability Matrix로 FR↔파일↔테스트를 연결한 것은 좋은      
  습관.

  문제점:

  - Traceability Matrix의 "Validating Tests" 컬럼이 구체성 부족. 프롬프트  
  렌더 테스트, 초안 N개 생성 테스트 같은 서술은 tasks.md의 T004, T010 등과 
  1:1 매핑이 안 된다. test_prompt_render_variables 같이 예상 테스트        
  함수명이나 T-ID를 직접 참조해야 추적 가능하다.
  - plan.md와 tasks.md 간 중복이 심하다. Implementation Details 영역 1~4의 
  내용이 tasks.md Phase 1~4와 거의 동일하다. plan은 "왜, 어떤 설계 결정"에 
  집중하고, tasks는 "무엇을, 어떤 순서로"에 집중해야 하는데, 현재는 둘 다  
  "무엇을" 수준에 머문다.

  ---
  2. 설계 결정의 부재 (Missing Design Decisions)

  plan.md의 가장 큰 약점: 핵심 설계 결정이 미결인 채 "구현 시 정의"로      
  넘기고 있다.

  결정 사항: 초안 저장 형식: 1파일 N블록 vs N파일
  현재 상태: "프론트매터 필드 또는 별도 파일" (미결)
  왜 문제인가: 다운스트림(T008) 수정 범위가 완전히 달라진다. 파일 경로     
  규칙,
    이미지 프롬프트 매핑, vault_io 변경 범위 모두 이것에 달려 있다.        
  ────────────────────────────────────────
  결정 사항: selected_draft 표현: 프론트매터 플래그 vs *_selected.md 파일  
  현재 상태: 양쪽 모두 나열 (미결)
  왜 문제인가: vault_io의 읽기 로직, generate_content의 쓰기 로직,
    이미지/발행의 읽기 로직이 전부 이 결정에 종속된다.
  ────────────────────────────────────────
  결정 사항: 알림 모듈 의존성: requests vs python-telegram-bot
  현재 상태: "가능" (미결)
  왜 문제인가: requirements.txt 변경, optional dependency 처리
    방식(extras_require?), CI 환경 모두 영향.
  ────────────────────────────────────────
  결정 사항: config.yml 스키마 변경 내용
  현재 상태: 언급 없음
  왜 문제인가: draft_count, 알림 설정, 완료 신호 설정의 YAML 키
    이름·위치·기본값이 전혀 정의되지 않았다.

  이것은 plan이 아니라 spec의 재서술에 가깝다. plan은 spec의 "무엇을"에    
  대해 "어떻게"를 결정하는 문서여야 한다.

  ---
  3. 범위 관리 (Scope)

  4개 영역을 하나의 feature branch에 넣은 것이 적절한가?

  - 영역 1(프롬프트 변수)과 영역 2(초안 선택)는 서로 독립적이지만, 둘 다   
  generate_content.py를 대폭 수정한다.
  - 영역 3(알림)은 새 모듈(notify.py) + 외부 의존성 도입이라 별도 branch가 
  자연스럽다.
  - 영역 4(다음 명령)는 사소한 변경이므로 영역 1이나 2에 포함시켜도        
  무방하다.

  권장: 영역 1+4를 한 PR, 영역 2를 한 PR, 영역 3을 한 PR로 분리하면        
  리뷰·롤백이 쉽다. 현재 plan은 "Phase별 병렬 가능"이라 적었지만, 실제로   
  단일 브랜치에서 병렬 구현하면 merge conflict가 불가피하다
  (generate_content.py가 영역 1·2·3·4 모두에서 수정됨).

  ---
  4. 기존 코드와의 정합성 (Codebase Alignment)

  prompt_composer.py를 읽어보면 이미 PromptComposer가 base → style →       
  identity → context 레이어를 합성한다. 그러면:

  - 영역 1의 실제 작업량이 과소 또는 과대 평가될 수 있다. "누락 변수       
  처리·기본값 정리"라고 했는데, 실제로 어떤 변수가 누락인지 조사(audit)가  
  선행되어야 한다. 현재 plan에는 그 audit 태스크가 없다.
  - **prompt_loader.py에 "변수 치환 로깅 추가"(T003)**라고 했지만, 기존에  
  Jinja2 undefined 처리가 어떻게 되어 있는지(StrictUndefined? Undefined?)  
  확인 없이 태스크가 작성됨.

  ---
  5. 테스트 전략 (Test Strategy)

  - 단위 테스트만 언급되고, 통합/E2E 시나리오가 부족하다. "수동 시나리오   
  검증"이 T020에 한 줄 있지만, 어떤 시나리오를 수동으로 돌릴지 정의되지    
  않았다.
  - 초안 선택 플로우의 테스트가 어렵다. 사람이 프론트매터를 편집하는 것이  
  "선택"인데, 이걸 자동 테스트하려면 fixture로 "선택된 상태의 파일"을      
  만들어야 한다. 이 fixture 설계가 plan에 없다.
  - 알림 테스트: 텔레그램 API를 mock할 것인지, integration test로 실제     
  발송할 것인지 전략이 없다.

  ---
  6. 하위 호환 (Backward Compatibility)

  Constitution Check에서 "PASS"라 적었지만:

  - generate_content.py가 N개 초안을 저장하면, 기존 vault 구조를 읽는 모든 
  downstream 스크립트(publish_log.py, validate_output.py, 이미지 생성 등)가
   영향을 받는다. plan에는 이미지 생성/발행 스크립트만 언급했지만,
  validate_output.py의 수정 필요성은 누락.
  - N=1일 때 기존과 동일하다고 했지만, 파일명 규칙이 바뀌면 (예:
  longform_input_xxx.md → longform_input_xxx_draft1.md) N=1이어도 기존     
  파일명을 기대하는 코드가 깨진다.

  ---
  7. 리스크 & 미언급 사항

  리스크: LLM 비용: N개 초안 = N배 API 호출
  영향: 운영 비용 증가
  plan에서의 언급: 없음
  ────────────────────────────────────────
  리스크: 초안 선택 없이 방치된 항목 처리
  영향: 파이프라인 정체
  plan에서의 언급: spec AC-2.3에서 "스킵"이라 했지만 장기 방치 정책 없음   
  ────────────────────────────────────────
  리스크: 알림 실패 시 재시도 정책
  영향: 알림 누락
  plan에서의 언급: "재시도 정책으로 처리"라 했지만 구체적 전략 없음        
  ────────────────────────────────────────
  리스크: --auto-proceed 자동 진행
  영향: 의도치 않은 대량 생성
  plan에서의 언급: spec에 "(선택)"이라 적었지만 plan에서 아예 다루지 않음  

  ---
  요약: 핵심 개선 제안

  1. 설계 결정을 확정하라 — 초안 저장 형식(N파일 vs 1파일), 선택 표시 방식,
   config 스키마를 plan에서 결정해야 한다. "구현 시 정의"는 plan의 존재    
  이유를 부정한다.
  2. 범위를 쪼개라 — 4개 영역을 단일 branch에서 구현하는 것은
  generate_content.py 충돌 리스크가 크다. 최소 알림(영역 3)은 분리 권장.   
  3. Audit 태스크를 추가하라 — 영역 1 착수 전에 "현재 프롬프트에서 실제로  
  누락된 변수 목록" 조사가 필요하다.
  4. config 스키마를 명시하라 — draft_count, notification,
  completion_signal 등의 YAML 구조·기본값·위치를 plan에서 정의해야
  downstream 태스크 추정이 가능하다.
  5. 비용 영향을 문서화하라 — N개 초안 생성은 LLM 비용 N배를 의미한다.     
  운영자가 인지해야 할 사항.