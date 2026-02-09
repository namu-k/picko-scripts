# Picko - Content Pipeline

콘텐츠 수집 → 생성 → 발행 파이프라인 자동화 시스템

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

```bash
# 일일 콘텐츠 수집
python -m scripts.daily_collector --date 2026-02-09

# 승인된 콘텐츠 생성
python -m scripts.generate_content --date 2026-02-09

# 생성물 검증
python -m scripts.validate_output --path Content/Longform/

# 상태 점검
python -m scripts.health_check
```

## 설정

`config/config.yml` 파일에서 설정 관리
