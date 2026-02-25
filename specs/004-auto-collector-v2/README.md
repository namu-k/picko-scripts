# 004-auto-collector-v2

자동 수집기 V2 - 계정별 맞춤 소스 발견 및 다양한 입력 채널 자동화

## 개요

기존 daily_collector.py를 확장하여:
1. **소스 자동 발견**: 계정의 관심사/키워드 기반으로 새로운 RSS, 뉴스레터, 팟캐스트 등을 찾아냄
2. **다중 입력 채널**: RSS, Perplexity 이메일, 뉴스레터, 웹 스크래핑
3. **반복 실행**: 주기적으로 소스 품질 평가 및 업데이트
4. **계정별 큐레이션**: 각 계정에 맞는 소스만 수집

## 정본 문서

- `canonical/auto_source_discovery.md` - 소스 자동 발견 알고리즘
- `canonical/perplexity_collector.md` - Perplexity 이메일 수집
- `canonical/multi_channel_collector.md` - 다중 채널 수집기

## 작업 계획

`plans/` 폴더 참조
