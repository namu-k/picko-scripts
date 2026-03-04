# 파이프라인 종합 분석 결과

> 최종 업데이트: 2026-02-17
> 브랜치: `feature/pipeline-reliability`

---

## ✅ 완료된 기능들

| 단계 | 상태 | 비고 |
|------|------|------|
| daily_collector.py | ✅ 완료 | 수집 → 중복제거 → NLP → 임베딩 → 스코어 → 다이제스트 |
| explore_topic.py | ✅ 완료 | 주제 탐색 스크립트 |
| generate_content.py | ✅ 완료 | 롱폼, 팩, 이미지 프롬프트 생성 |
| validate_output.py | ✅ 완료 | 콘텐츠 검증 |
| prompt_loader.py | ✅ 완료 | 외부 프롬프트 로더 |

---

## ✅ 완료된 BCP 이슈들

| Issue | 작업 | 상태 | 산출물 |
|-------|------|------|--------|
| #3 | 프롬프트 외부화 (BCP-001) | ✅ 완료 | `config/prompts/` (longform, packs, image, exploration, reference) |
| #4 | 주제 탐색 단계 (BCP-002) | ✅ 완료 | `scripts/explore_topic.py` + `config/prompts/exploration/` |
| #6 | 레퍼런스 기반 문체 (BCP-004) | ✅ 완료 | `config/reference_styles/founder_tech_brief/` |
| #7 | 채널별 이미지/레이아웃 (BCP-005) | ✅ 완료 | `config/prompts/image/` (twitter, linkedin, newsletter) |

---

## ❌ 남은 작업

### 🔴 High Priority (Critical Path)

| 항목 | 설명 | 난이도 | 산출물 |
|------|------|--------|--------|
| **daily_collector.py 테스트** | 핵심 파이프라인 테스트 (RSS fetch, dedup, NLP, scoring) | High | `tests/test_daily_collector.py` |
| **generate_content.py 테스트** | 생성 로직 테스트 (prompt loading, longform, packs) | High | `tests/test_generate_content.py` |
| **engagement_sync.py API 연동** | Twitter API 연동으로 engagement 메트릭 수집 | High | `_fetch_twitter_metrics()` 구현 |
| **Account Profiles** | `config/accounts/socialbuilders.yml` 생성 | Low | 계정 프로필 파일 |

### 🟡 Medium Priority

| 항목 | 설명 | 난이도 | 산출물 |
|------|------|--------|--------|
| validate_output.py 테스트 | 검증 로직 테스트 | Mid | `tests/test_validate_output.py` |
| 채널 선택 UI | 채널별 생성 선택 메커니즘 | Mid | frontmatter 필드 확장 |
| score_calibrator 연동 | 실제 engagement 데이터로 calibration 검증 | Mid | 연동 테스트 |

---

## 📊 테스트 커버리지 현황

| 모듈 | 커버리지 | 상태 |
|------|----------|------|
| picko/ | 32.82% | ⚠️ 개선 필요 |
| scripts/ | 0% | 🔴 Critical |
| - daily_collector.py | 0% | 🔴 |
| - generate_content.py | 0% | 🔴 |
| - validate_output.py | 0% | 🔴 |
| - engagement_sync.py | 0% | 🔴 |
| - score_calibrator.py | 0% | 🔴 |

---

## 📋 권장 조치 (우선순위 순)

### Phase 1: 안정성 확보 (Week 1-2)

1. **`tests/test_daily_collector.py` 생성**
   - RSS fetch 테스트
   - 중복 제거 테스트
   - NLP processing 테스트
   - Score calculation 테스트

2. **`tests/test_generate_content.py` 생성**
   - Prompt loading 테스트
   - Longform generation 테스트
   - Pack generation 테스트
   - Error handling 테스트

3. **`tests/test_validate_output.py` 생성**
   - Required frontmatter 검증 테스트
   - Section validation 테스트

### Phase 2: 피드백 루프 복구 (Week 2-3)

4. **Twitter API 연동 (`engagement_sync.py`)**
   - Tweepy 라이브러리 사용
   - `_fetch_twitter_metrics()` 구현
   - views, likes, retweets, replies 수집

5. **`config/accounts/socialbuilders.yml` 생성**
   - target_audience, interests, tone_voice
   - channel별 설정
   - keyword 가중치

### Phase 3: 검증 (Week 3-4)

6. **score_calibrator 실제 데이터 검증**
   - 수집된 engagement 데이터로 calibration
   - 가중치 조정 제안 검증

---

## 🎯 KPI 목표

| KPI | 현재 | 목표 | 달성 조건 |
|-----|------|------|-----------|
| Time-to-Production | 6주 예상 | ≤ 4주 | 고우선순위 항목 완료 |
| System Reliability | 3/10 | ≥ 8/10 | scripts/ 테스트 커버리지 ≥ 60% |
| Feedback Loop Integrity | 0/10 | ≥ 6/10 | 최소 1개 플랫폼 engagement 수집 |

---

## 🔗 관련 문서

- [advisory_report.md](./advisory_report.md) - Team PIPELINE 분석 보고서
- [개선_논의_콘텐츠_파이프라인.md](./개선_논의_콘텐츠_파이프라인.md) - 개선 논의 배경
- [TEAM_BETTER_CONTENT_PIPELINE.md](./TEAM_BETTER_CONTENT_PIPELINE.md) - 팀 구성 및 역할