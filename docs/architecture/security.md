# 보안 아키텍처

> **최종 수정**: 2026-03-04
> **대상 독자**: 개발자, 보안 담당자, 시스템 아키텍트
> **구현 상태**: 이 문서는 보안 **설계 가이드**입니다.
> `APIKeyManager`, `ServiceAuth`, `OAuthClient`, `JWTValidator`, `DataEncryption` 등의 클래스는 현재 코드에 구현되어 있지 않으며, 프로덕션 배포 시 참고하기 위한 설계 문서입니다.
> 현재 API 키는 `.env` 환경 변수 방식으로 관리됩니다.

---

## 1. 개요

이 문서는 Picko 시스템의 보안 아키텍처를 상세히 설명합니다. 인증 및 인가, 데이터 보안, API 보안 등 주요 보안 요소를 다룹니다.

---

## 2. 보안 원칙

### 2.1 CIA 트리오 적용

#### 2.1.1 기밀성 (Confidentiality)
- 민감 정보 암호화
- 접통 제어
- 데이터 마스킹

#### 2.1.2 무결성 (Integrity)
- 데이터 검증
- 체크섬 검사
- 변경 감지

#### 2.1.3 가용성 (Availability)
- 백업 및 복원
- 재해 복구
- 서비스 중단 관리

### 2.2 보안 설계 원칙

1. **Defense in Depth**: 여러 계층의 보안 방어
2. **Least Privilege**: 최소 권한 원칙
3. **Zero Trust**: 신뢰하지 않고 항상 검증
4. **Security by Design**: 설계 단계부터 보안 고려
5. **Fail-Safe**: 장애 발생 시 안전한 상태로 전환

---

## 3. 인증 및 인가

### 3.1 시스템 내 인증

#### 3.1.1 API 키 인증

```python
# API 키 관리 클래스
class APIKeyManager:
    def __init__(self):
        self.keys = self.load_api_keys()
        self.key_blacklist = set()

    def verify_key(self, key: str, required_scopes: List[str]) -> bool:
        # 키 검증
        if key in self.key_blacklist:
            return False

        key_info = self.keys.get(key)
        if not key_info:
            return False

        # 스코프 검증
        user_scopes = set(key_info.get('scopes', []))
        required_scopes = set(required_scopes)

        return required_scopes.issubset(user_scopes)

    def blacklist_key(self, key: str):
        # 키 블랙리스트 추가
        self.key_blacklist.add(key)
```

#### 3.1.2 내부 서비스 인증

```python
# 서비스 간 인증
class ServiceAuth:
    def __init__(self, service_id: str):
        self.service_id = service_id
        self.service_certs = self.load_service_certs()

    def authenticate_request(self, request: dict) -> bool:
        # 서비스 인증서 검증
        service_cert = request.get('service_cert')
        if not service_cert:
            return False

        # 인증서 유효성 검증
        return self.verify_certificate(service_cert)
```

### 3.2 사용자 인증 (미래)

#### 3.2.1 OAuth 2.0 인증 플로우

```python
# OAuth 2.0 클라이언트
class OAuthClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = "https://picko.app/auth/callback"

    async def get_auth_code(self, user_id: str) -> str:
        # 인증 코드 생성
        auth_code = generate_auth_code(user_id)
        store_auth_code(auth_code, user_id)
        return auth_code

    async def exchange_code_for_token(self, code: str) -> dict:
        # 인증 코드 → 액세스 토큰 교환
        user_id = get_user_id_from_code(code)
        if not user_id:
            raise InvalidAuthCodeError()

        return {
            'access_token': generate_access_token(user_id),
            'refresh_token': generate_refresh_token(user_id),
            'expires_in': 3600
        }
```

#### 3.2.2 JWT 토큰 검증

```python
# JWT 토큰 검증기
class JWTValidator:
    def __init__(self):
        self.secret_key = get_secret_key('jwt')

    def validate_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])

            # 만료 시간 검증
            if payload['exp'] < time.time():
                raise TokenExpiredError()

            return payload
        except jwt.PyJWTError as e:
            raise InvalidTokenError(str(e))
```

---

## 4. 데이터 보안

### 4.1 데이터 암호화

#### 4.1.1 정적 데이터 암호화

```python
# 데이터 암호화 관리
class DataEncryption:
    def __init__(self):
        self.key = self.load_encryption_key()
        self.cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv))
        self.encrypted_data = {}

    def encrypt_sensitive_data(self, data: dict) -> dict:
        # 민감한 API 키 및 설정 암호화
        encrypted = {}
        for key, value in data.items():
            if self.is_sensitive_field(key):
                encrypted[key] = self.encrypt_value(value)
            else:
                encrypted[key] = value
        return encrypted

    def decrypt_sensitive_data(self, encrypted: dict) -> dict:
        # 암호화된 데이터 복호화
        decrypted = {}
        for key, value in encrypted.items():
            if self.is_sensitive_field(key):
                decrypted[key] = self.decrypt_value(value)
            else:
                decrypted[key] = value
        return decrypted
```

#### 4.1.2 전송 중 데이터 암호화

```python
# HTTPS/TLS 설정
class TLSConfig:
    def __init__(self):
        self.cert_path = "/etc/picko/cert.pem"
        self.key_path = "/etc/picko/key.pem"
        self.ca_bundle = "/etc/picko/ca-bundle.crt"

    def setup_https_server(self):
        # HTTPS 서버 설정
        ssl_context = ssl.create_default_context(
            ssl.Purpose.CLIENT_AUTH,
            cafile=self.ca_bundle
        )
        ssl_context.load_cert_chain(
            certfile=self.cert_path,
            keyfile=self.key_path
        )
        return ssl_context
```

### 4.2 API 키 관리

#### 4.2.1 API 키 저장소

```python
# API 키 저장소
class APIKeyStore:
    def __init__(self):
        self.encryption_key = get_encryption_key('api_keys')
        self.key_store = self.load_key_store()

    def store_key(self, provider: str, key_data: dict) -> None:
        # API 키 저장
        encrypted_key = self.encrypt_data(key_data)
        self.key_store[provider] = encrypted_key
        self.save_key_store()

    def get_key(self, provider: str) -> dict:
        # API 키 조회
        encrypted_key = self.key_store.get(provider)
        if not encrypted_key:
            raise KeyError(f"API key for {provider} not found")

        return self.decrypt_data(encrypted_key)

    def revoke_key(self, provider: str) -> None:
        # API 키 폐기
        if provider in self.key_store:
            del self.key_store[provider]
            self.save_key_store()
```

#### 4.2.2 API 키 검증

```python
# API 키 검증
class APIKeyValidator:
    def __init__(self):
        self.key_manager = APIKeyManager()
        self.rate_limiter = RateLimiter()

    async def validate_request(self, request: Request) -> bool:
        # API 키 검증
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return False

        # 키 유효성 검증
        if not self.key_manager.verify_key(api_key):
            return False

        # 레이트 리밋 검증
        client_ip = request.client.host
        if not await self.rate_limiter.check_limit(client_ip):
            return False

        return True
```

### 4.3 로그 보안

#### 4.3.1 민감 정보 마스킹

```python
# 로그 필터링
class LogFilter:
    def __init__(self):
        self.sensitive_patterns = [
            r'api[_-]?key[:=]\s*[a-zA-Z0-9_-]{20,}',
            r'token[:=]\s*[a-zA-Z0-9_-]{20,}',
            r'password[:=]\s*[^\s]+',
            r'Authorization:\s*Bearer\s+[^\s]+'
        ]

    def mask_sensitive_data(self, message: str) -> str:
        # 민감 정보 마스킹
        for pattern in self.sensitive_patterns:
            message = re.sub(pattern, '***MASKED***', message)
        return message

    def filter_request_log(self, request_log: dict) -> dict:
        # 요청 로그 필터링
        filtered_log = request_log.copy()

        # 헤더 필터링
        if 'headers' in filtered_log:
            headers = filtered_log['headers']
            filtered_log['headers'] = {
                k: self.mask_sensitive_data(v)
                for k, v in headers.items()
            }

        # 본문 필터링
        if 'body' in filtered_log:
            filtered_log['body'] = self.mask_sensitive_data(filtered_log['body'])

        return filtered_log
```

#### 4.3.2 안전한 로깅

```python
# 안전한 로거
class SecureLogger:
    def __init__(self):
        self.logger = logging.getLogger('picko')
        self.filter = LogFilter()

        # 민감 정보 로깅 금지 설정
        logging.captureWarnings(True)

    def log_request(self, request: Request, response: Response):
        # 요청 로깅 (필터링 적용)
        log_data = {
            'method': request.method,
            'url': str(request.url),
            'status_code': response.status_code,
            'user_agent': request.headers.get('User-Agent'),
            'ip': request.client.host
        }

        filtered_log = self.filter.filter_request_log(log_data)
        self.logger.info(f"Request: {json.dumps(filtered_log)}")

    def log_error(self, error: Exception, context: dict = None):
        # 에러 로깅 (스택 트레이스 보호)
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        # 민감 정보 제거
        filtered_data = self.filter.filter_request_log(error_data)
        self.logger.error(f"Error: {json.dumps(filtered_data)}")
```

---

## 5. API 보안

### 5.1 입력 검증

#### 5.1.1 요청 유효성 검사

```python
# 요청 검증
class RequestValidator:
    def __init__(self):
        self.schemas = load_schemas()

    def validate_request(self, request: Request, schema_name: str) -> dict:
        # 요청 유효성 검사
        schema = self.schemas.get(schema_name)
        if not schema:
            raise InvalidSchemaError(f"Schema {schema_name} not found")

        try:
            # JSON 유효성 검사
            data = request.json()
            validated_data = schema.validate(data)
            return validated_data
        except ValidationError as e:
            raise InvalidRequestError(str(e))

    def sanitize_input(self, data: dict) -> dict:
        # 입력 데이터 정제
        sanitized = {}
        for key, value in data.items():
            # SQL 인젝션 방지
            value = self.escape_sql(value)
            # XSS 방지
            value = self.escape_html(value)
            sanitized[key] = value
        return sanitized
```

#### 5.1.2 파일 업로드 검증

```python
# 파일 업로드 검증
class FileUploadValidator:
    def __init__(self):
        self.allowed_types = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'text/markdown': '.md'
        }
        self.max_size = 10 * 1024 * 1024  # 10MB

    def validate_file(self, file: UploadFile) -> bool:
        # 파일 타입 검증
        if file.content_type not in self.allowed_types:
            raise InvalidFileTypeError(f"Type {file.content_type} not allowed")

        # 파일 크기 검증
        file.file.seek(0, 2)  # EOF로 이동
        file_size = file.file.tell()
        file.file.seek(0)  # 다시 시작 위치로

        if file_size > self.max_size:
            raise FileSizeError(f"File too large: {file_size} > {self.max_size}")

        return True

    def sanitize_filename(self, filename: str) -> str:
        # 파일 이름 정제
        return re.sub(r'[^\w\-.]', '_', filename)
```

### 5.2 레이트 리밋

#### 5.2.1 슬라이딩 윈도우 레이트 리밋

```python
# 레이트 리미터
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = self.load_rate_limits()

    async def check_limit(self, identifier: str) -> bool:
        # 현재 한도 확인
        now = time.time()
        limit = self.limits.get(identifier, {'count': 100, 'window': 60})

        # 오래된 요청 제거
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < limit['window']
        ]

        # 한도 초과 확인
        if len(self.requests[identifier]) >= limit['count']:
            return False

        # 새 요청 기록
        self.requests[identifier].append(now)
        return True
```

#### 5.2.2 Redis 기분 분산 레이트 리밋

```python
# Redis 레이트 리미터
class RedisRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.limits = self.load_rate_limits()

    async def check_limit(self, identifier: str, key: str) -> bool:
        # Redis를 사용한 분산 레이트 리밋
        now = int(time.time())
        limit = self.limits.get(key, {'count': 100, 'window': 60})

        # Redis 키 생성
        redis_key = f"rate_limit:{identifier}:{key}"

        # 현재 윈도우의 요청 수 확인
        pipe = self.redis.pipeline()
        pipe.zadd(redis_key, {str(now): now})
        pipe.zremrangebyscore(redis_key, 0, now - limit['window'])
        pipe.expire(redis_key, limit['window'])
        pipe.zcard(redis_key)
        results = pipe.execute()

        # 한도 초과 확인
        if results[-1] >= limit['count']:
            return False

        return True
```

### 5.3 CORS 설정

```python
# CORS 미들웨어
class CORSMiddleware:
    def __init__(self, app):
        self.app = app
        self.allowed_origins = self.load_cors_config()

    def add_cors_headers(self, response: Response):
        # CORS 헤더 추가
        origin = request.headers.get('Origin')

        if origin in self.allowed_origins:
            response.headers.update({
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
                'Access-Control-Max-Age': '86400'
            })

        return response

    def handle_preflight(self):
        # Preflight 요청 처리
        if request.method == 'OPTIONS':
            return Response(status_code=200)
        return None
```

---

## 6. 네트워크 보안

### 6.1 방화벽 규칙

```python
# 방화벽 규칙
class FirewallRules:
    def __init__(self):
        self.rules = self.load_firewall_rules()

    def check_request(self, request: Request) -> bool:
        # 요청 방화벽 검사
        client_ip = request.client.host

        # IP 허용 목록 확인
        if client_ip not in self.rules['allowed_ips']:
            return False

        # 포트 허용 목록 확인
        if request.url.port not in self.rules['allowed_ports']:
            return False

        # 프로토콜 확인
        if request.url.scheme not in self.rules['allowed_protocols']:
            return False

        return True

    def is_malicious_ip(self, ip: str) -> bool:
        # 악성 IP 확인
        return ip in self.load_malicious_ips()
```

### 6.2 VPN 및 프록시 감지

```python
# VPN 감지
class VPNDetector:
    def __init__(self):
        self.vpn_providers = self.load_vpn_providers()
        self.proxy_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Forwarded-Host',
            'X-Proxy-User-IP'
        ]

    def detect_proxy(self, request: Request) -> bool:
        # 프록시 감지
        for header in self.proxy_headers:
            if header in request.headers:
                return True

        # VPN IP 확인
        client_ip = request.client.host
        return self.check_vpn_ip(client_ip)

    async def verify_geolocation(self, ip: str) -> dict:
        # 지리적 위치 확인
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipapi.co/{ip}/json/") as response:
                data = await response.json()
                return {
                    'country': data.get('country_name'),
                    'city': data.get('city'),
                    'timezone': data.get('timezone')
                }
```

---

## 7. 보안 모니터링

### 7.1 보안 이벤트 로깅

```python
# 보안 이벤트 로거
class SecurityEventLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.event_types = self.load_event_types()

    def log_security_event(self, event_type: str, details: dict):
        # 보안 이벤트 로깅
        if event_type not in self.event_types:
            raise InvalidEventTypeError(f"Event type {event_type} not recognized")

        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'source_ip': request.client.host,
            'user_agent': request.headers.get('User-Agent')
        }

        self.logger.warning(f"Security Event: {json.dumps(event)}")

        # 위협 분석 시스템 전송
        self.send_to_threat_analyzer(event)

    def detect_anomalous_activity(self, user_id: str) -> bool:
        # 비정상 활동 감지
        recent_events = self.get_recent_events(user_id)

        # 로그인 실패 패턴
        failed_logins = sum(1 for e in recent_events if e['type'] == 'login_failed')
        if failed_logins > 5:
            return True

        # API 호출 이상 패턴
        api_calls = sum(1 for e in recent_events if e['type'] == 'api_call')
        if api_calls > 1000:
            return True

        return False
```

### 7.2 침투 테스트

```python
# 침투 테스트 프레임워크
class PenetrationTestFramework:
    def __init__(self):
        self.test_cases = self.load_test_cases()

    async def run_security_tests(self, target_url: str) -> dict:
        # 보안 테스트 실행
        results = {}

        for test_name, test_func in self.test_cases.items():
            try:
                result = await test_func(target_url)
                results[test_name] = {
                    'status': 'passed' if result else 'failed',
                    'details': result
                }
            except Exception as e:
                results[test_name] = {
                    'status': 'error',
                    'details': str(e)
                }

        return results

    def sql_injection_test(self, url: str) -> bool:
        # SQL 인젝션 테스트
        test_payloads = [
            "' OR '1'='1",
            "' UNION SELECT NULL--",
            "'; DROP TABLE users--"
        ]

        for payload in test_payloads:
            response = requests.get(f"{url}?id={payload}")
            if "error" in response.text.lower() and "sql" in response.text.lower():
                return False

        return True

    def xss_test(self, url: str) -> bool:
        # XSS 테스트
        test_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>"
        ]

        for payload in test_payloads:
            response = requests.post(url, json={"input": payload})
            if payload in response.text:
                return False

        return True
```

---

## 8. 보안 구성

### 8.1 환경 변수 보안

```python
# 환경 변수 보안 검사
class EnvironmentSecurity:
    def __init__(self):
        self.required_secrets = [
            'DATABASE_PASSWORD',
            'ENCRYPTION_KEY',
            'JWT_SECRET'
        ]

    def validate_environment(self) -> dict:
        # 환경 변수 보안 검사
        checks = {
            'secrets_present': self.check_secrets(),
            'secrets_encrypted': self.check_secrets_encrypted(),
            'weak_passwords': self.check_weak_passwords(),
            'default_credentials': self.check_default_credentials()
        }

        return checks

    def encrypt_environment_variables(self):
        # 환경 변수 암호화
        env_file = os.environ.get('ENV_FILE', '.env')
        encrypted_vars = {}

        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key in self.required_secrets:
                        encrypted_vars[key] = self.encrypt(value)
                    else:
                        encrypted_vars[key] = value

        # 암호화된 파일 저장
        with open(env_file, 'w') as f:
            for key, value in encrypted_vars.items():
                f.write(f"{key}={value}\n")
```

### 8.2 보안 구성 파일

```yaml
# security.yml - 보안 설정 예시
security:
  encryption:
    algorithm: "AES-256-GCM"
    key_rotation_days: 90
    key_store_path: "/etc/picko/keys/"

  api:
    rate_limit:
      default:
        count: 100
        window: 60
      auth:
        count: 10
        window: 60

    cors:
      allowed_origins:
        - "https://picko.app"
        - "https://api.picko.app"

  monitoring:
    enable_ssl_cert_monitoring: true
    enable_intrusion_detection: true
    log_retention_days: 90

  backup:
    encryption: true
    offsite_backup: true
    retention_days: 365
```

---

## 9. 보안 점검리스트

### 9.1 배포 전 보안 점검

```python
# 배포 전 보안 점검리스트
class SecurityChecklist:
    def __init__(self):
        self.checks = [
            self.check_environment_variables,
            self.check_api_keys,
            self.check_permissions,
            self.check_dependencies,
            self.check_configuration
        ]

    def run_pre_deployment_checks(self) -> dict:
        # 배포 전 보안 점검 실행
        results = {}

        for check in self.checks:
            try:
                results[check.__name__] = check()
            except Exception as e:
                results[check.__name__] = {'status': 'error', 'message': str(e)}

        return results

    def check_environment_variables(self) -> dict:
        # 환경 변수 검사
        env_vars = dict(os.environ)

        issues = []
        if 'PASSWORD' in env_vars and len(env_vars['PASSWORD']) < 8:
            issues.append("Password too short")

        if 'DEBUG' in env_vars and env_vars['DEBUG'].lower() == 'true':
            issues.append("Debug mode enabled in production")

        return {
            'status': 'passed' if not issues else 'failed',
            'issues': issues
        }

    def check_api_keys(self) -> dict:
        # API 키 검사
        key_issues = []

        # 하드코딩된 키 확인
        source_files = ['.env', 'config.yml']
        for file in source_files:
            if os.path.exists(file):
                content = open(file).read()
                if 'sk-' in content or 'pk-' in content:
                    key_issues.append(f"Potential hardcoded key in {file}")

        return {
            'status': 'passed' if not key_issues else 'failed',
            'issues': key_issues
        }
```

### 9.2 정기 보안 감사

```python
# 정기 보안 감사
class SecurityAuditor:
    def __init__(self):
        self.audit_trails = self.load_audit_trails()

    def run_security_audit(self) -> dict:
        # 보안 감사 실행
        audit_results = {
            'vulnerabilities': self.scan_vulnerabilities(),
            'compliance': self.check_compliance(),
            'monitoring': self.check_monitoring(),
            'backup': self.verify_backups()
        }

        # 감사 보고서 생성
        self.generate_audit_report(audit_results)

        return audit_results

    def scan_vulnerabilities(self) -> List[dict]:
        # 취약성 스캔
        vulnerabilities = []

        # 종속성 취약성 검사
        vulnerabilities.extend(self.scan_dependency_vulnerabilities())

        # 코드 취약성 검사
        vulnerabilities.extend(self.scan_code_vulnerabilities())

        # 인프라 취약성 검사
        vulnerabilities.extend(self.scan_infrastructure_vulnerabilities())

        return vulnerabilities
```

---

*이 문서는 Picko 시스템의 보안 아키텍처를 상세히 설명하며, 개발자와 보안 담당자가 시스템을 안전하게 구축하고 유지 관리할 수 있도록 돕습니다.*
