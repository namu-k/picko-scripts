"""
Health Check 스크립트
파이프라인 상태 점검 (소스 접근성, API 연결, Vault 권한 등)
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from picko.config import get_config
from picko.logger import setup_logger
from picko.vault_io import VaultIO

# Windows UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logger = setup_logger("health_check")


@dataclass
class CheckResult:
    """체크 결과"""

    name: str
    passed: bool
    message: str
    details: str = ""


class HealthChecker:
    """파이프라인 상태 점검기"""

    def __init__(self):
        self.config = get_config()
        self.results: list[CheckResult] = []

    def run_all(self) -> list[CheckResult]:
        """모든 체크 실행"""
        self.results = []

        self.check_vault_access()
        self.check_api_keys()
        self.check_sources()
        self.check_directories()
        self.check_disk_space()

        return self.results

    def check_vault_access(self):
        """Vault 읽기/쓰기 권한 확인"""
        try:
            VaultIO()
            vault_root = Path(self.config.vault.root)

            # 읽기 테스트
            if not vault_root.exists():
                self.results.append(
                    CheckResult(
                        name="Vault Access", passed=False, message="Vault root not found", details=str(vault_root)
                    )
                )
                return

            # 쓰기 테스트
            test_file = vault_root / ".health_check_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                self.results.append(
                    CheckResult(name="Vault Access", passed=True, message="Read/Write OK", details=str(vault_root))
                )
            except Exception as e:
                self.results.append(
                    CheckResult(
                        name="Vault Access",
                        passed=False,
                        message=f"Write permission denied: {e}",
                        details=str(vault_root),
                    )
                )
        except Exception as e:
            self.results.append(CheckResult(name="Vault Access", passed=False, message=str(e)))

    def check_api_keys(self):
        """API 키 설정 확인"""
        # OpenAI
        openai_key = os.environ.get(self.config.llm.api_key_env, "")
        if openai_key:
            # 마스킹하여 표시
            masked = f"{openai_key[:8]}...{openai_key[-4:]}" if len(openai_key) > 12 else "***"
            self.results.append(CheckResult(name="OpenAI API Key", passed=True, message="Configured", details=masked))
        else:
            self.results.append(
                CheckResult(
                    name="OpenAI API Key",
                    passed=False,
                    message=f"Not set ({self.config.llm.api_key_env})",
                    details="Set environment variable",
                )
            )

    def check_sources(self):
        """RSS 소스 접근성 확인"""
        sources = self.config.sources.get("sources", [])
        enabled_sources = [s for s in sources if s.get("enabled", True)]

        if not enabled_sources:
            self.results.append(
                CheckResult(
                    name="RSS Sources", passed=False, message="No enabled sources", details="Check config/sources.yml"
                )
            )
            return

        accessible = 0
        failed = []

        with httpx.Client(timeout=10) as client:
            for source in enabled_sources[:5]:  # 최대 5개만 테스트
                try:
                    response = client.head(source["url"], follow_redirects=True)
                    if response.status_code < 400:
                        accessible += 1
                    else:
                        failed.append(f"{source['id']}: HTTP {response.status_code}")
                except Exception as e:
                    failed.append(f"{source['id']}: {str(e)[:30]}")

        if accessible == len(enabled_sources[:5]):
            self.results.append(
                CheckResult(name="RSS Sources", passed=True, message=f"All {accessible} sources accessible")
            )
        else:
            self.results.append(
                CheckResult(
                    name="RSS Sources",
                    passed=False,
                    message=f"{accessible}/{len(enabled_sources[:5])} accessible",
                    details="; ".join(failed),
                )
            )

    def check_directories(self):
        """필수 디렉토리 확인"""
        vault_root = Path(self.config.vault.root)
        required_dirs = [
            self.config.vault.inbox,
            self.config.vault.digests,
            self.config.vault.longform,
            self.config.vault.packs,
            self.config.vault.images_prompts,
        ]

        missing = []
        for dir_path in required_dirs:
            full_path = vault_root / dir_path
            if not full_path.exists():
                missing.append(dir_path)

        if not missing:
            self.results.append(
                CheckResult(name="Directories", passed=True, message=f"All {len(required_dirs)} directories exist")
            )
        else:
            self.results.append(
                CheckResult(
                    name="Directories",
                    passed=False,
                    message=f"{len(missing)} directories missing",
                    details=", ".join(missing),
                )
            )

    def check_disk_space(self):
        """디스크 공간 확인"""
        import shutil

        vault_root = Path(self.config.vault.root)

        try:
            total, used, free = shutil.disk_usage(vault_root)
            free_gb = free / (1024**3)

            if free_gb >= 1.0:
                self.results.append(CheckResult(name="Disk Space", passed=True, message=f"{free_gb:.1f} GB available"))
            else:
                self.results.append(
                    CheckResult(
                        name="Disk Space",
                        passed=False,
                        message=f"Low disk space: {free_gb:.1f} GB",
                        details="Recommend at least 1 GB free",
                    )
                )
        except Exception as e:
            self.results.append(CheckResult(name="Disk Space", passed=False, message=str(e)))


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(description="Health Check - 파이프라인 상태 점검")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")

    args = parser.parse_args()

    checker = HealthChecker()
    results = checker.run_all()

    if args.json:
        import json

        output = [{"name": r.name, "passed": r.passed, "message": r.message, "details": r.details} for r in results]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'=' * 60}")
        print(f"Health Check Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        for result in results:
            status = "✅" if result.passed else "❌"
            print(f"{status} {result.name}: {result.message}")
            if result.details:
                print(f"   └─ {result.details}")

        print(f"\n{'=' * 60}")
        print(f"Summary: {passed} passed, {failed} failed")
        print(f"{'=' * 60}")

        if failed > 0:
            exit(1)


if __name__ == "__main__":
    main()
