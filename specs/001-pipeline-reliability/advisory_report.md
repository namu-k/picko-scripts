# Pipeline Reliability Advisory Report

> 브랜치: `feature/pipeline-reliability`
> 분석일: 2026-02-17
> 분석팀: Team PIPELINE

---

## 1. Executive Summary

본 보고서는 Picko 콘텐츠 파이프라인의 현재 상태를 분석하고, 프로덕션 배포를 위한 우선순위가 지정된 액션 플랜을 제안합니다.

### 핵심 발견

| 항목 | 상태 | 위험도 |
|------|------|--------|
| 핵심 파이프라인 기능 | ✅ 완료 | - |
| 프롬프트 외부화 (BCP-001) | ✅ 완료 | - |
| 주제 탐색 단계 (BCP-002) | ✅ 완료 | - |
| 레퍼런스 기반 문체 (BCP-004) | ✅ 완료 | - |
| 채널별 이미지/레이아웃 (BCP-005) | ✅ 완료 | - |
| **테스트 커버리지** | ❌ 0% (scripts/) | 🔴 Critical |
| **Account Profiles** | ❌ 미생성 | 🔴 High |
| **Engagement Sync API** | ❌ Placeholder | 🔴 Critical |

---

## 2. Team PIPELINE 분석 결과

### 2.1 전문가 패널 구성

| 전문가 | 역할 | 핵심 관점 |
|--------|------|-----------|
| Maya Chen (CPO) | 성장 옹호자 | "출시가 완벽보다 낫다" |
| Viktor Petrov (QA) | 품질 수호자 | "테스트 없는 코드는 깨진 코드다" |
| Dr. Sarah Kim (Architect) | 실무 조율자 | "어떤 모서리를 깎고 어떤 것을 보강할지 아는 것" |

### 2.2 핵심 분쟁점

**분쟁**: 프로덕션 배포를 위한 최소 요구사항이 무엇인가?

- **Maya**: 핵심 파이프라인이 작동하면 충분. Account Profiles는 수동 YAML 편집으로 해결.
- **Viktor**: scripts/ 디렉토리 0% 테스트 커버리지는 용납 불가. 무음 실패 위험.
- **Dr. Kim**: 진짜 위험은 **끊어진 피드백 루프**. engagement 데이터 없이는 ROI 증명 불가.

### 2.3 거절된 대안들

| 대안 | 거절 사유 |
|------|-----------|
| 즉시 배포 후 테스트 추가 | 무음 실패 시 데이터 손상 복구 불가 |
| Twitter + LinkedIn API 동시 구현 | 4주+ 소요, 오버엔지니어링 |
| 수동 CSV export에 의존 | 자동화 가치 훼손, 사용자 이탈 |

---

## 3. KPI 평가

| KPI | 측정 기준 | 현재 점수 | 목표 |
|-----|-----------|-----------|------|
| **KPI-1: Time-to-Production** | 고우선순위 항목 완료까지 주 수 | 6주 예상 | ≤ 4주 |
| **KPI-2: System Reliability** | 무음 오류 없는 파이프라인 실행 비율 | 3/10 | ≥ 8/10 |
| **KPI-3: Feedback Loop Integrity** | engagement 메트릭 → score calibration 연결 | 0/10 | ≥ 6/10 |

**현재 종합 점수: 2.3/10**

---

## 4. Final Action Plan

### Phase 1: 안정성 확보 (Week 1-2)

| 순위 | 작업 | 채택 관점 | 난이도 | 산출물 |
|------|------|-----------|--------|--------|
| 1 | `daily_collector.py` 테스트 추가 | Viktor (QA) | High | `tests/test_daily_collector.py` |
| 2 | `generate_content.py` 테스트 추가 | Viktor (QA) | High | `tests/test_generate_content.py` |
| 3 | `validate_output.py` 테스트 추가 | Viktor (QA) | Mid | `tests/test_validate_output.py` |

**테스트 범위**:
- RSS fetch, deduplication, NLP processing, score calculation
- Prompt loading, longform/pack generation, error handling
- Required frontmatter, section validation

### Phase 2: 피드백 루프 복구 (Week 2-3)

| 순위 | 작업 | 채택 관점 | 난이도 | 산출물 |
|------|------|-----------|--------|--------|
| 4 | Twitter API 연동 (`engagement_sync.py`) | Dr. Kim (Architect) | High | `_fetch_twitter_metrics()` |
| 5 | score_calibrator 연동 테스트 | Dr. Kim | Mid | 실제 engagement 데이터로 calibration 검증 |

**최소 구현 범위**:
- Twitter API (Tweepy) 사용
- views, likes, retweets, replies 메트릭 수집
- publish_log와 연동

### Phase 3: 페르소나 활성화 (Week 3-4)

| 순위 | 작업 | 채택 관점 | 난이도 | 산출물 |
|------|------|-----------|--------|--------|
| 6 | `config/accounts/socialbuilders.yml` 생성 | Maya (CPO) | Low | 계정 프로필 파일 |

**계정 프로필 구성**:
- target_audience, interests, tone_voice
- channel별 설정 (twitter, linkedin, newsletter)
- keyword 가중치 (relevance scoring용)

---

## 5. 위험 분석

### 5.1 Critical Risk (치명적 위험)

> **피드백 루프가 완전히 끊겨 있음**
>
> engagement 데이터 없이는:
> - scoring 시스템 calibration 불가
> - ROI 증명 불가
> - 사용자 이탈 inevitable

**완화 전략**: 2주 내 최소 1개 플랫폼(Twitter) API 연동 완료

### 5.2 High Risks

| 위험 | 확률 | 영향 | 완화 방안 |
|------|------|------|-----------|
| 무음 실패로 인한 데이터 손상 | High | High | scripts/ 테스트 커버리지 확보 |
| Account Profile 없이 relevance scoring 제한 | Medium | Medium | 기본 프로필 템플릿 제공 |

---

## 6. 예상 결과

### Action Plan 완료 후

| KPI | 현재 | 예상 | 개선점 |
|-----|------|------|--------|
| KPI-1: Time-to-Production | 4/10 | 7/10 | 범위 축소로 4주 달성 가능 |
| KPI-2: System Reliability | 3/10 | 8/10 | scripts/ 커버리지 0% → ~60% |
| KPI-3: Feedback Loop Integrity | 0/10 | 6/10 | 최소 1개 플랫폼 실제 데이터 |
| **종합** | **2.3/10** | **7/10** | |

---

## 7. 다음 단계

### 즉시 실행 (Today)

- [ ] `tests/test_daily_collector.py` 생성
- [ ] `tests/test_generate_content.py` 생성
- [ ] `tests/test_validate_output.py` 생성

### 단기 (Week 1-2)

- [ ] Twitter API 연동 구현
- [ ] `config/accounts/socialbuilders.yml` 생성

### 중기 (Week 3-4)

- [ ] score_calibrator 실제 데이터 검증
- [ ] 통합 테스트 추가

---

## 8. 참조 문서

- [jobs_to_do.md](./jobs_to_do.md) - 작업 현황 매트릭스
- [개선_논의_콘텐츠_파이프라인.md](./개선_논의_콘텐츠_파이프라인.md) - 개선 논의 배경
- [TEAM_BETTER_CONTENT_PIPELINE.md](./TEAM_BETTER_CONTENT_PIPELINE.md) - 팀 구성 및 역할

---

*This report was produced by **Team PIPELINE**.*
