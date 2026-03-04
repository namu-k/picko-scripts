# 배포 가이드 (Deployment Guide)

이 문서는 Picko 스크립트 시스템의 배포 절차를 설명합니다.
> **구현 상태**: 이 문서는 배포 **참고 아키텍처**입니다.
> Dockerfile, docker-compose.yml, Kubernetes 매니페스트 등은 현재 리포지토리에 포함되어 있지 않습니다.
> 프로덕션 컨테이너화 시 이 문서를 기반으로 구축할 예정입니다.

## 목차
- [배포 개요](#배포-개요)
- [Docker 컨테이너 배포](#docker-컨테이너-배포)
- [Kubernetes 배포](#kubernetes-배포)
- [CI/CD 파이프라인](#cicd-파이프라인)
- [환경별 배포 전략](#환경별-배포-전략)
- [배포 절차 체크리스트](#배포-절차-체크리스트)

## 배포 개요

Picko 스크립트는 다음과 같은 구성 요소들로 배포됩니다:

- **애플리케이션**: Python 스크립트 모음
- **의존성**: Python 패키지 및 시스템 라이브러리
- **구성 파일**: YAML 설정 파일, 환경 변수
- **데이터**: 캐시, 로그, 콘텐츠 저장소
- **외부 의존성**: API 키, 데이터베이스, 외부 서비스

### 시스템 요구사항

- **OS**: Linux (Ubuntu 20.04+ 또는 CentOS 8+)
- **Python**: 3.13+
- **메모리**: 최소 4GB, 권장 8GB
- **스토리지**: 최소 50GB SSD
- **네트워크**: 인터넷 연결 (RSS 수집 및 API 호출 필요)

## Docker 컨테이너 배포

### Dockerfile 작성

```dockerfile
# Dockerfile
FROM python:3.13-slim

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p logs cache multimedia/renders

# 데이터 볼륨 마운트 지점 정의
VOLUME ["/app/data", "/app/logs", "/app/cache"]

# 실행 명령어 (예: 일일 수집기 실행)
CMD ["python", "-m", "scripts.daily_collector", "--date", "$(date +%Y-%m-%d)"]
```

### docker-compose.yml 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  picko-app:
    build: .
    container_name: picko-app
    environment:
      - PYTHONPATH=/app
      - TZ=Asia/Seoul
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./cache:/app/cache
      - ./config:/app/config
      - ./mock_vault:/app/mock_vault
    restart: unless-stopped
    depends_on:
      - redis
    networks:
      - picko-network

  redis:
    image: redis:7-alpine
    container_name: picko-redis
    restart: unless-stopped
    networks:
      - picko-network

  nginx:
    image: nginx:alpine
    container_name: picko-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - picko-app
    restart: unless-stopped
    networks:
      - picko-network

volumes:
  picko-data:
  picko-logs:
  picko-cache:
  picko-config:
  picko-vault:

networks:
  picko-network:
    driver: bridge
```

### 배포 스크립트

```bash
#!/bin/bash
# deploy.sh

# 환경 변수 설정
ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"

# 서비스 중지
docker-compose -f ${COMPOSE_FILE} down

# 이미지 빌드
docker-compose -f ${COMPOSE_FILE} build --no-cache

# 서비스 시작
docker-compose -f ${COMPOSE_FILE} up -d

# 로그 확인
docker-compose -f ${COMPOSE_FILE} logs -f --tail=100

# 상태 확인
docker-compose -f ${COMPOSE_FILE} ps
```

## Kubernetes 배포

### Kubernetes 매니페스트

```yaml
# k8s/picko-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: picko-deployment
  namespace: picko
  labels:
    app: picko
spec:
  replicas: 3
  selector:
    matchLabels:
      app: picko
  template:
    metadata:
      labels:
        app: picko
    spec:
      containers:
      - name: picko-app
        image: picko/picko:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: PYTHONPATH
          value: "/app"
        - name: TZ
          value: "Asia/Seoul"
        - name: ENVIRONMENT
          value: "production"
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
        - name: data-volume
          mountPath: /app/data
        - name: logs-volume
          mountPath: /app/logs
        - name: cache-volume
          mountPath: /app/cache
        - name: vault-volume
          mountPath: /app/mock_vault
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: picko-config
      - name: data-volume
        persistentVolumeClaim:
          claimName: picko-data-pvc
      - name: logs-volume
        persistentVolumeClaim:
          claimName: picko-logs-pvc
      - name: cache-volume
        persistentVolumeClaim:
          claimName: picko-cache-pvc
      - name: vault-volume
        persistentVolumeClaim:
          claimName: picko-vault-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: picko-service
  namespace: picko
spec:
  selector:
    app: picko
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: picko-ingress
  namespace: picko
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.picko.com
    secretName: picko-tls
  rules:
  - host: api.picko.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: picko-service
            port:
              number: 80
```

### ConfigMap 설정

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: picko-config
  namespace: picko
data:
  config.yml: |
    vault:
      root: /app/mock_vault
    llm:
      summary_llm:
        provider: openai
        model: gpt-4o-mini
        api_key_env: OPENAI_API_KEY
      embedding:
        provider: local
        model: BAAI/bge-m3
    cache:
      embedding_dir: /app/cache/embeddings
      max_size: 1000000  # 1MB
    log_level: INFO
    log_dir: /app/logs
  # 다른 설정 파일들...
```

### PersistentVolumeClaim

```yaml
# k8s/pvcs.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: picko-data-pvc
  namespace: picko
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: picko-logs-pvc
  namespace: picko
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: picko-cache-pvc
  namespace: picko
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: picko-vault-pvc
  namespace: picko
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
```

## CI/CD 파이프라인

### GitHub Actions 워크플로우

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov black isort flake8 mypy

    - name: Run linting
      run: |
        black --check picko/ scripts/
        isort --check-only picko/ scripts/
        flake8 picko/ scripts/
        mypy picko/

    - name: Run tests
      run: |
        pytest --cov=picko --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -t picko/picko:latest .
        docker tag picko/picko:latest picko/picko:${GITHUB_SHA:0:7}

    - name: Push to Docker Hub
      env:
        DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
        DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
      run: |
        echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
        docker push picko/picko:latest
        docker push picko/picko:${GITHUB_SHA:0:7}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to Kubernetes
      env:
        KUBE_CONFIG_DATA: ${{ secrets.KUBE_CONFIG }}
      run: |
        echo "$KUBE_CONFIG_DATA" > /tmp/kubeconfig
        export KUBECONFIG=/tmp/kubeconfig

        # 배포 스크립트 실행
        kubectl config use-context picko-production
        kubectl apply -f k8s/

        # 롤아웃 모니터링
        kubectl rollout status deployment/picko-deployment
```

### GitLab CI/CD 예시

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"

cache:
  paths:
    - .venv/
    - node_modules/

unit_test:
  stage: test
  image: python:3.13
  before_script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
  script:
    - pytest --cov=picko
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

lint:
  stage: test
  image: python:3.13
  before_script:
    - pip install black isort flake8 mypy
  script:
    - black --check picko/ scripts/
    - isort --check-only picko/ scripts/
    - flake8 picko/ scripts/
    - mypy picko/

build_docker:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t picko/picko:latest .
    - docker tag picko/picko:latest $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
    - master

deploy_staging:
  stage: deploy
  image: alpine/k8s
  script:
    - kubectl config set-cluster staging-cluster --server=$KUBE_STAGING_URL
    - kubectl config set-credentials staging-user --token=$KUBE_STAGING_TOKEN
    - kubectl config set-context staging --cluster=staging-cluster --user=staging-user
    - kubectl config use-context staging

    - sed -i "s/latest/$CI_COMMIT_SHA/" k8s/deployment.yaml
    - kubectl apply -f k8s/

    - kubectl rollout status deployment/picko-staging --timeout=5m
  only:
    - main
    - master
  environment:
    name: staging
    url: https://api.staging.picko.com

deploy_production:
  stage: deploy
  image: alpine/k8s
  script:
    - kubectl config set-cluster prod-cluster --server=$KUBE_PROD_URL
    - kubectl config set-credentials prod-user --token=$KUBE_PROD_TOKEN
    - kubectl config set-context prod --cluster=prod-cluster --user=prod-user
    - kubectl config use-context prod

    - sed -i "s/latest/$CI_COMMIT_SHA/" k8s/deployment.yaml
    - kubectl apply -f k8s/

    - kubectl rollout status deployment/picko-production --timeout=5m
  only:
    - main
    - master
  when: manual
  environment:
    name: production
    url: https://api.picko.com
```

## 환경별 배포 전략

### 개발 환경 (Development)

- **배포 방식**: 로컬 Docker 개발 서버
- **구성**: 단일 컨테이너, 모든 서비스 내장
- **데이터**: 로컬 볼륨 마운트
- **접근**: 개발자 IP만 허용

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  picko-app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - /app/data
      - /app/logs
      - /app/cache
    environment:
      - DEBUG=1
      - LOG_LEVEL=DEBUG
    ports:
      - "8080:8080"
    command: >
      sh -c "
        python -m pip install -r requirements.txt --no-cache-dir &&
        python -m scripts.daily_collector --dry-run
      "
```

### 테스트 환경 (Staging)

- **배포 방식**: Kubernetes 클러스터
- **구성**: Production과 동일한 아키텍처, 가상 데이터 사용
- **데이터**: 테스트 전용 데이터베이스
- **접근**: QA 팀 접근 권한 부여

### 프로덕션 환경 (Production)

- **배포 방식**: Kubernetes 클러스터 with 자동 스케일링
- **구성**: 고가용성, 다중 AZ 배포
- **데이터**: 영구 스토리지, 백업 자동화
- **접근**: VPN/인증 필수

### 배포 전략

#### 1. 블루-그린 배포

```yaml
# k8s/blue-green-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: picko-blue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: picko
      version: blue
---
apiVersion: v1
kind: Service
metadata:
  name: picko-service
spec:
  selector:
    app: picko
    version: blue
---
# 배포 시점에 Service selector를 green으로 변경
```

#### 2. 카나리 배포

```bash
#!/bin/bash
# canary-deploy.sh

# 카나리 버전 배포
kubectl set image deployment/picko-deployment picko-app=picko/picko:canary-v1

# 로깅 확인
kubectl logs -l app=picko --tail=100

# 트래픽 점진적 전환
kubectl rollout pause deployment picko-deployment
kubectl scale deployment picko-deployment --replicas=4
kubectl rollout resume deployment picko-deployment

# 모니터링
kubectl get pods -l app=picko

# 안정성 확인
kubectl rollout status deployment picko-deployment

# 모든 트래픽 전환 확인 후 기존 버전 스케일 다운
kubectl scale deployment picko-deployment --replicas=0 --selector=version=stable
```

#### 3. 롤링 업데이트

```bash
# 롤링 업데이트 실행
kubectl set image deployment/picko-deployment picko-app=picko/picko:latest

# 업데이트 상태 확인
kubectl rollout status deployment/picko-deployment

# 롤백 필요 시
kubectl rollout undo deployment picko-deployment
```

## 배포 절차 체크리스트

### 배포 전

- [ ] 백업 스냅샷 생성
- [ ] 데이터 백업 수행
- [ ] 변경된 설정 파일 검토
- [ ] 테스트 실행 (단위, 통합, E2E)
- [ ] 배포 스크립트 검증
- [ ] 알림 채널 활성화
- [ ] 롤백 계획 수립

### 배포 중

- [ ] 배포 대상 서비스 정지
- [ ] 신규 아티팩트 업로드
- [ ] 인프라 업데이트 적용
- [ ] 애플리케이션 업데이트
- [ ] 상태 확인
- [ ] 기능 검증
- [ ] 로그 모니터링

### 배포 후

- [ ] 애플리케이션 정상 동작 확인
- [ ] 성능 모니터링
- [ ] 로그 분석
- [ ] 사용자 피드백 확인
- [ ] 롤아웃 완료 보고
- [ ] 배포 문서화
- [ ] 다음 배포 일정 계획

### 배포 모니터링 항목

- [ ] CPU/Memory 사용량
- [ ] 응답 시간
- [ ] 에러율
- [ ] 데이터베이스 연결
- [ ] 외부 API 호출 상태
- [ ] 디스크 공간
- [ ] 네트워크 지연

### 롤백 절차

1. **문제 감지**: 모니터링 알림 수신
2. **평가**: 문제 심각도 판단
3. **결정**: 롤백 필요성 결정
4. **실행**: 롤백 스크립트 실행
   ```bash
   # 롤백 예시
   kubectl rollout undo deployment/picko-deployment
   ```
5. **확인**: 롤백 후 상태 확인
6. **통보**: 팀 알림 발송
7. **조사**: 원인 분석 시작

### 배포 성공 기준

- 모든 서비스가 정상 상태
- 평소보다 10% 이상 성능 저하 없음
- 에러율 < 0.1%
- 응답 시간 95% 백분위수 < 2초
- 배포 후 1시간 안에 안정화
