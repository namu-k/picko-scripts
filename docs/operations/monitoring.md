# 모니터링 가이드 (Monitoring Guide)

이 문서는 Picko 스크립트 시스템의 모니터링 구성 및 운영 절차를 설명합니다.
> **구현 상태**: 이 문서는 모니터링 **설계 가이드**입니다.
> `picko/monitoring.py`, Prometheus/Grafana 통합 코드 등은 현재 구현되어 있지 않습니다.
> 프로덕션 운영 시 참고하기 위한 설계 문서입니다.

## 목차
- [모니터링 개요](#모니터링-개요)
- [시스템 모니터링](#시스템-모니터링)
- [로그 수집 및 분석](#로그-수집-및-분석)
- [알림 설정](#알림-설정)
- [성능 지표](#성능-지표)
- [대시보드 구성](#대시보드-구성)
- [문제 해결](#문제-해결)

## 모니터링 개요

### 모니터링 목표

1. **시스템 가용성**: 99.9% 이상 유지
2. **성능 저하 조기 발견**: 평소 대비 20% 이상 저하 시 경고
3. **오류 즉시 감지**: 1분 이내 발견 및 알림
4. **자원 사용량 최적화**: 예산 내에서 운영

### 모니터링 범위

- **인프라**: 서버, 컨테이너, 네트워크, 스토리지
- **애플리케이션**: Python 프로세스, 스크립트 실행 상태
- **비즈니스**: RSS 수집 상태, 콘텐츠 생성량, API 응답
- **사용자**: 접근 패턴, 오류 발생 현황

## 시스템 모니터링

### Prometheus + Grafana 설정

#### Prometheus 설정

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - "alerts.yml"

scrape_configs:
  # 애플리케이션 메트릭
  - job_name: 'picko-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  # Node Exporter (시스템 메트릭)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 30s

  # Redis Exporter
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['localhost:9121']
    scrape_interval: 30s

  # Docker 컨테이너
  - job_name: 'docker'
    static_configs:
      - targets: ['localhost:9323']
    scrape_interval: 30s
```

#### 커스텀 메트립 등록

```python
# picko/monitoring.py
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

# 커스텀 메트릭 정의
RSS_COLLECTOR_ATTEMPTS = Counter('rss_collector_attempts_total', 'RSS 수집 시도 횟수')
RSS_COLLECTOR_SUCCESS = Counter('rss_collector_success_total', 'RSS 수집 성공 횟수')
RSS_COLLECTOR_FAILURE = Counter('rss_collector_failure_total', 'RSS 수집 실패 횟수')
CONTENT_GENERATION_DURATION = Histogram('content_generation_seconds', '콘텐츠 생성 시간', ['content_type'])
ERROR_RATE = Counter('errors_total', '오류 발생 횟수', ['error_type', 'component'])
ACTIVE_JOBS = Gauge('active_jobs', '실행 중인 작업 수')
CACHE_HIT_RATIO = Gauge('cache_hit_ratio', '캐시 적중률')

def record_collector_attempt():
    RSS_COLLECTOR_ATTEMPTS.inc()

def record_collector_success():
    RSS_COLLECTOR_SUCCESS.inc()

def record_collector_failure():
    RSS_COLLECTOR_FAILURE.inc()

def record_error(error_type, component):
    ERROR_RATE.labels(error_type=error_type, component=component).inc()

def measure_generation_time(content_type):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            CONTENT_GENERATION_DURATION.labels(content_type=content_type).observe(duration)
            return result
        return wrapper
    return decorator

# 메트릭 서버 시작
start_http_server(8000)
```

#### 메트립 수집 코드

```python
# scripts/daily_collector.py (수정)
from picko.monitoring import (
    record_collector_attempt,
    record_collector_success,
    record_collector_failure,
    record_error,
    ACTIVE_JOBS,
    measure_generation_time,
)

def collect_rss_feeds():
    ACTIVE_JOBS.inc()
    try:
        record_collector_attempt()
        # RSS 수집 로직...
        record_collector_success()
    except Exception as e:
        record_collector_failure()
        record_error('rss_collection', 'daily_collector')
        raise
    finally:
        ACTIVE_JOBS.dec()
```

### Grafana 대시보드 설정

#### 시스템 상태 대시보드

```json
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": "-- Grafana --",
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "gnetId": null,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "panels": [
    {
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
      "id": 1,
      "panels": [],
      "title": "Picko 시스템 모니터링",
      "type": "row"
    },
    {
      "aliasColors": {},
      "bars": false,
      "dashLength": 10,
      "dashes": false,
      "fill": 1,
      "fillGradient": 0,
      "gridPos": {"h": 8, "w": 8, "x": 0, "y": 1},
      "hiddenSeries": false,
      "id": 2,
      "legend": {
        "avg": false,
        "current": false,
        "max": false,
        "min": false,
        "show": true,
        "total": false,
        "values": false
      },
      "lines": true,
      "linewidth": 1,
      "nullPointMode": "null",
      "options": {
        "data": [
          {
            "id": "default",
            "name": "Line Style"
          }
        ],
        "orientation": "auto"
      },
      "percentage": false,
      "pointradius": 2,
      "points": false,
      "renderer": "flot",
      "series": [],
      "spaceLength": 10,
      "stack": false,
      "steppedLine": false,
      "targets": [
        {
          "expr": "rate(cpu_usage_total[5m])",
          "legendFormat": "CPU 사용률",
          "refId": "A"
        }
      ],
      "thresholds": [],
      "timeFrom": null,
      "timeRegions": [],
      "timeShift": null,
      "title": "CPU 사용률",
      "tooltip": {
        "shared": true,
        "sort": 0,
        "value_type": "individual"
      },
      "type": "graph",
      "xaxis": {
        "buckets": null,
        "mode": "time",
        "name": null,
        "show": true,
        "values": []
      },
      "yaxes": [
        {
          "format": "percentunit",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": 0,
          "show": true
        },
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        }
      ],
      "yaxis": {
        "align": false,
        "alignLevel": null
      }
    },
    {
      "cacheTimeout": null,
      "colorBackground": false,
      "colorValue": false,
      "colors": [
        "rgba(245, 54, 54, 0.9)",
        "rgba(237, 129, 40, 0.89)",
        "rgba(50, 172, 45, 0.89)"
      ],
      "datasource": "Prometheus",
      "description": "실행 중인 작업 수",
      "fieldConfig": {
        "defaults": {
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "red",
                "value": null
              },
              {
                "color": "yellow",
                "value": 5
              },
              {
                "color": "green",
                "value": 10
              }
            ]
          },
          "unit": "none"
        }
      },
      "gridPos": {"h": 8, "w": 4, "x": 8, "y": 1},
      "id": 3,
      "interval": null,
      "links": [],
      "maxDataPoints": 100,
      "options": {
        "colorMode": "value",
        "graphMode": "none",
        "justifyMode": "auto",
        "orientation": "horizontal",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "textMode": "auto"
      },
      "pluginVersion": "7.1.3",
      "targets": [
        {
          "expr": "active_jobs",
          "instant": true,
          "interval": "",
          "legendFormat": "",
          "refId": "A"
        }
      ],
      "timeFrom": null,
      "timeShift": null,
      "title": "실행 중인 작업",
      "type": "stat"
    },
    {
      "datasource": "Prometheus",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 1},
      "id": 4,
      "options": {
        "description": "",
        "displayMode": "gradient",
        "orientation": "horizontal",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "showUnfilled": true,
        "text": {
          "valueSize": 14
        },
        "thresholds": {
          "mode": "absolute",
          "steps": [
            {
              "color": "green",
              "value": 0
            },
            {
              "color": "yellow",
              "value": 5
            },
            {
              "color": "red",
              "value": 10
            }
          ]
        }
      },
      "pluginVersion": "7.1.3",
      "targets": [
        {
          "expr": "cache_hit_ratio",
          "instant": true,
          "legendFormat": "캐시 적중률",
          "refId": "A"
        }
      ],
      "title": "캐시 적중률",
      "type": "gauge"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 27,
  "style": "dark",
  "tags": [],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-15m",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "Picko 시스템 상태",
  "uid": "picko-system-status",
  "version": 1
}
```

## 로그 수집 및 분석

### ELK Stack 구성

#### Logstash 설정

```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [log][file][path] =~ "/var/log/picko" {
    grok {
      match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:logger} - %{GREEDYDATA:message}" }
      overwrite => [ "message" ]
    }

    date {
      match => [ "timestamp", "ISO8601" ]
      locale => "en"
    }

    if [level] == "ERROR" {
      mutate {
        add_tag => ["error"]
      }
    }

    if [message] =~ "RSS.*" {
      mutate {
        add_field => { "category" => "rss_collection" }
      }
    }

    if [message] =~ "LLM.*" {
      mutate {
        add_field => { "category" => "llm_api" }
      }
    }

    if [message] =~ "Content.*" {
      mutate {
        add_field => { "category" => "content_generation" }
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "picko-logs-%{+YYYY.MM.dd}"
  }

  # 중요 로그별로 별도 저장
  if [tags] and [tags][0] == "error" {
    elasticsearch {
      hosts => ["elasticsearch:9200"]
      index => "picko-errors-%{+YYYY.MM.dd}"
    }
  }

  stdout {
    codec => rubydebug
  }
}
```

#### Filebeat 설정

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/picko/*.log
  fields:
    app: picko
  fields_under_root: true
  json.keys_under_root: true
  json.add_error_key: true

  multiline.pattern: '^\d{4}-\d{2}-\d{2}'
  multiline.negate: true
  multiline.match: after

processors:
- add_docker_metadata:
    host: "unix:///var/run/docker.sock"
    match: ["container.*"]

output:
  logstash:
    hosts: ["logstash:5044"]

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
```

### Python 로깅 설정

```python
# picko/logger.py
import sys
from pathlib import Path
from loguru import logger

# 로그 레벨 설정
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 파일 로깅
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "app.log",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    level="INFO",
)

logger.add(
    log_dir / "error.log",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    level="ERROR",
    filter=lambda record: record["level"].name == "ERROR",
)

# 구조화된 로깅
logger.add(
    log_dir / "{time:YYYY-MM-DD}/structured.jsonl",
    format="{message}",
    serialize=True,
    level="INFO",
    rotation="1 day",
    retention="7 days",
)
```

### 로그 분석 쿼리 예시

```sql
-- Elasticsearch 쿼리: 오류 추세 분석
GET /picko-errors-*/_search
{
  "size": 0,
  "aggs": {
    "error_trend": {
      "date_histogram": {
        "field": "@timestamp",
        "calendar_interval": "1h"
      },
      "aggs": {
        "error_type": {
          "terms": {
            "field": "log.level",
            "size": 10
          }
        }
      }
    }
  },
  "query": {
    "range": {
      "@timestamp": {
        "gte": "now-24h"
      }
    }
  }
}

-- 최근 오류 10개
GET /picko-errors-*/_search
{
  "size": 10,
  "sort": [
    {
      "@timestamp": {
        "order": "desc"
      }
    }
  ]
}

-- RSS 수집 실패율
GET /picko-logs-*/_search
{
  "size": 0,
  "query": {
    "match": {
      "category": "rss_collection"
    }
  },
  "aggs": {
    "success_rate": {
      "filters": {
        "filters": {
          "success": {
            "term": {
              "message.keyword": "RSS collection completed"
            }
          },
          "failure": {
            "term": {
              "message.keyword": "RSS collection failed"
            }
          }
        }
      }
    }
  }
}
```

## 알림 설정

### Alertmanager 설정

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_auth_username: 'alerts@picko.com'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'admin@picko.com'
    subject: 'Picko 시스템 알림: {{ .GroupLabels.alertname }}'
    body: |
      시스템에서 문제가 감지되었습니다.

      요약: {{ .GroupLabels.alertname }}

      그룹: {{ .GroupLabels.service }}

      시작 시간: {{ .StartsAt }}

      상세 정보: {{ .CommonAnnotations.description }}

      레이블:
        {{ range $k, $v := .GroupLabels }}{{ $k }}={{ $v }} {{ end }}

      ---
      {{ range .Alerts }}
        경고: {{ .Annotations.summary }}
        설명: {{ .Annotations.description }}
        라벨: {{ range $k, $v := .Labels }}{{ $k }}={{ $v }} {{ end }}
      {{ end }}

  slack_configs:
  - api_url: 'https://hooks.slack.com/services/xxxx'
    channel: '#picko-alerts'
    title: 'Picko 시스템 알림'
    text: '{{ .CommonAnnotations.summary }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
```

### Prometheus 경고 규칙

```yaml
# alerts.yml
groups:
- name: picko-system
  rules:
  - alert: HighErrorRate
    expr: rate(errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "오류율이 높습니다"
      description: "5분간 오류율이 0.1을 초과했습니다: {{ $value }}"

  - alert: RSSCollectionFailure
    expr: rate(rss_collector_failure_total[5m]) / rate(rss_collector_attempts_total[5m]) > 0.3
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "RSS 수집 실패율이 높습니다"
      description: "RSS 수집 실패율이 30%를 초과했습니다: {{ $value }}"

  - alert: HighCPUUsage
    expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "CPU 사용량이 높습니다"
      description: "CPU 사용량이 80%를 초과했습니다: {{ $value }}%"

  - alert: LowDiskSpace
    expr: (node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"} < 20
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "디스크 공간이 부족합니다"
      description: "남은 디스크 공간이 20% 미만입니다: {{ $value }}%"
```

### 알림 상세 정보

| 경고 이름 | 트리거 조건 | 심각도 | 조치 항목 |
|---------|-----------|--------|----------|
| HighErrorRate | 5분간 오류율 > 0.1 | 경고 | 로그 확인, 애플리케이션 재시작 |
| RSSCollectionFailure | RSS 실패율 > 30% | 심각 | 수동 개입 필요, 외부 서비스 점검 |
| HighCPUUsage | CPU > 80% (10분 지속) | 경고 | 부하 분석, 서버 확장 고려 |
| LowDiskSpace | 디스크 > 80% 사용 | 심각 | 정리, 공간 확보 |
| ContentGenerationSlow | 생성 시간 > 5분 | 경고 | LLM API 점검, 타임아웃 조정 |

## 성능 지표

### 애플리케이션 지표

1. **RSS 수집 지표**
   - 수집 시도 횟수
   - 성공률 (%)
   - 평균 수집 시간 (초)
   - 수집된 아이템 수
   - 외부 API 응답 시간

2. **콘텐츠 생성 지표**
   - 생성 시작 시간
   - 콘텐츠 타별별 생성 시간 (longform, packs, image)
   - LLM API 호출 성공률
   - 토큰 사용량
   - 생성 성공률 (%)

3. **시스템 지표**
   - 메모리 사용량 (GB)
   - CPU 사용률 (%)
   - 디스크 사용량 (%)
   - 네트워크 입출력
   - 활성 프로세스 수

### 지표 계산 쿼리

```sql
-- RSS 수집 성공률
SELECT
  count_if(status = 'success') / count(*) * 100 AS success_rate
FROM rss_collection
WHERE timestamp > now() - 1 hour

-- 평균 생성 시간
SELECT
  AVG(duration_seconds) as avg_generation_time,
  content_type
FROM content_generation
WHERE timestamp > now() - 24 hours
GROUP BY content_type

-- LLM API 호출 성공률
SELECT
  count_if(status = 'success') / count(*) * 100 AS success_rate,
  provider
FROM llm_api_calls
WHERE timestamp > now() - 1 hour
GROUP BY provider

-- 시스템 자원 사용율 (Node Exporter 메트릭)
SELECT
  100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) AS cpu_usage,
  (1 - avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes)) * 100 AS memory_usage
FROM system_metrics
WHERE timestamp > now() - 5m
```

## 대시보드 구성

### 주요 대시보드

1. **시스템 상태 대시보드**
   - CPU/Memory 사용률
   - 디스크 공간
   - 네트워크 통계
   - 활성 프로세스

2. **애플리케이션 성능 대시보드**
   - RSS 수집 실적
   - 콘텐츠 생성 속도
   - 에러율 추세
   - API 응답 시간

3. **비즈니스 대시보드**
   - 생성된 콘텐츠 수 (일/주/월)
   - 콘텐츠 타별 분포
   - 처리 지연 시간
   - 자원 사용 효율성

### 대시보드 레이아웃

```
┌─────────────────┬─────────────────┬─────────────────┐
│ 시스템 상태     │ CPU 사용률     │ 디스크 공간     │
│ (7개 패널)      │ (선형 그래프)   │ (게이지)        │
├─────────────────┼─────────────────┼─────────────────┤
│ RSS 수집        │ 성공률         │                 │
│ 선형 그래프     │ 스택 영역 그래프│                 │
├─────────────────┼─────────────────┼─────────────────┤
│ 콘텐츠 생성     │ 생성 시간      │                 │
│ 타별 분포       │ 분포 히스토그램 │                 │
├─────────────────┼─────────────────┼─────────────────┤
│ 에러 추세       │ 알림 현황      │ 시계열 선택기   │
│ 막대 그래프     │ 표              │                 │
└─────────────────┴─────────────────┴─────────────────┘
```

## 문제 해결

### 일반적인 문제 및 해결 방법

#### 1. RSS 수집 실패

**증상**: RSS 수집 스크립트가 계속 실패

**진단 절차**:
```bash
# 로그 확인
tail -f logs/YYYY-MM-DD/daily_collector.log

# RSS 피드 상태 확인
curl -I https://example.com/feed.xml

# 네트워크 연결 테스트
telnet rss.example.com 443
```

**해결 방법**:
1. 외부 RSS 서비스 접속 가능 여부 확인
2. API 키 유효성 검사
3. 피드 URL 변경 또는 필터링 규칙 수정
4. RSS 수집 시간 조정 (피드 업데이트 타이밍 고려)

#### 2. LLM API 호출 실패

**증상**: 콘텐츠 생성 중 API 오류 발생

**진단 절차**:
```bash
# LLM 로그 확인
grep "LLM.*ERROR" logs/error.log

# API 사용량 확인
curl -H "Authorization: Bearer $API_KEY" https://api.openai.com/v1/usage

# 대기 시간 테스트
curl -o /dev/null -s -w "%{time_total}\n" https://api.openai.com/v1/models
```

**해결 방법**:
1. API 키 재발급 또는 회원가입
2. 사용량 제한 확인 및 조정
3. 시간 초과 값 조정 (config.yml)
4. Fallback 모델 설정

#### 3. 디스크 공간 부족

**증상**: 로그 디렉토리가 꽉 참

**진단 절차**:
```bash
# 디스크 사용량 확인
df -h

# 로그 파일 크기 확인
du -sh logs/
find logs/ -name "*.log" -exec ls -lh {} \;

# 캐시 크기 확인
du -sh cache/
```

**해결 방법**:
1. 로그 자동 정리 설정 확인
2. 오래된 로그 압축
3. 캐시 정책 조정
4. 자동 확장 스토리지 설정

#### 4. 메모리 부족

**증상**: Python 프로세스 종료

**진단 절차**:
```bash
# 메모리 사용량 확인
free -h
top | grep python

# 프로세스 메모리 덤프
gcore <pid>

# GC 활동 확인
python -c "import gc; print(gc.get_count())"
```

**해결 방법**:
1. 메모리 사용량 모니터링 강화
2. 배치 작업 사이즈 조정
3. 메모리 누수 코드 수정
4. 서버 메모리 업그레이드

### 성능 최적화

1. **캐시 전략**
   - Redis 도입
   - 캐시 히트 레이트 모니터링
   - TTL 설정 최적화

2. ** 데이터베이스 튜닝**
   - 인덱스 분석
   - 쿼리 최적화
   - 커넥션 풀링

3. **병렬 처리**
   - 작업 큐 도입
   - 워커 수 조정
   - 리소스 제한 설정

4. **네트워크 최적화**
   - API 호출 배치화
   - 커넥션 재사용
   - 지연 시간 최적화

### 모니터링 데이터 관리

```bash
# 로그 정리 스크립트
#!/bin/bash
# cleanup-logs.sh

# 30일 이전 로그 압축
find logs/ -name "*.log" -mtime +30 -exec gzip {} \;

# 60일 이전 로그 삭제
find logs/ -name "*.log.gz" -mtime +60 -exec rm {} \;

# 캐시 정리
find cache/ -name "*.cache" -mtime +7 -delete

# 메트릭 데이터 보관 정책
# Prometheus 설정
 retention: "15d"

# Grafana 데이터 보관
 retention_rules:
   - metric: '*'
     value: '1w'

# Elasticsearch 인덱스 롤링
 logs/picko-logs-*
 retention: "7d"

 errors/picko-errors-*
 retention: "30d"
```

### 모니터링 스크립트

```python
# scripts/health_check.py
import asyncio
import aiohttp
from datetime import datetime
import json

async def check_rss_feeds():
    """RSS 피드 상태 확인"""
    status = {}
    sources = load_rss_sources()

    async with aiohttp.ClientSession() as session:
        for source in sources:
            try:
                async with session.get(source['url'], timeout=10) as response:
                    status[source['id']] = {
                        'status': 'ok' if response.status == 200 else 'error',
                        'response_time': response.elapsed.total_seconds(),
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                status[source['id']] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

    return status

async def check_llm_services():
    """LLM 서비스 상태 확인"""
    services = {
        'openai': 'https://api.openai.com/v1/models',
        'anthropic': 'https://api.anthropic.com/v1/models',
    }

    results = {}

    async with aiohttp.ClientSession() as session:
        for name, url in services.items():
            try:
                async with session.get(url, timeout=10) as response:
                    results[name] = {
                        'status': 'ok' if response.status == 200 else 'error',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

    return results

def monitor_system_resources():
    """시스템 리소스 모니터링"""
    import psutil

    return {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'timestamp': datetime.now().isoformat()
    }

if __name__ == "__main__":
    async def main():
        rss_status = await check_rss_feeds()
        llm_status = await check_llm_services()
        resources = monitor_system_resources()

        health_report = {
            'timestamp': datetime.now().isoformat(),
            'rss_feeds': rss_status,
            'llm_services': llm_status,
            'system_resources': resources
        }

        # 결과 저장
        with open('logs/health_check.jsonl', 'a') as f:
            f.write(json.dumps(health_report) + '\n')

        # 결과 출력
        print(json.dumps(health_report, indent=2))

    asyncio.run(main())
```
