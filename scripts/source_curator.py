"""
소스 품질 관리 스크립트
수집된 소스의 품질을 지속적으로 모니터링하고 관리
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from picko.config import get_config
from picko.logger import setup_logger
from picko.source_manager import SourceManager, SourceMeta

logger = setup_logger("source_curator")


@dataclass
class CurationReport:
    """품질 관리 리포트"""

    timestamp: str
    total_sources: int = 0
    active_sources: int = 0
    pending_sources: int = 0
    trusted_sources: int = 0
    low_quality_sources: list[str] = field(default_factory=list)
    inactive_sources: list[str] = field(default_factory=list)
    review_needed: list[str] = field(default_factory=list)


class SourceCurator:
    """
    소스 품질 평가 및 관리.
    기존 ContentScorer를 소스 수준으로 집계.
    """

    def __init__(
        self,
        source_manager: SourceManager | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.config = get_config()

        # 소스 매니저 초기화
        if source_manager is None:
            sources_path = Path(self.config.sources_file)
            source_manager = SourceManager(sources_path)
        self.sm = source_manager

        # 품질 규칙 로드
        if config is None:
            collectors_path = Path("config/collectors.yml")
            if collectors_path.exists():
                with open(collectors_path, "r", encoding="utf-8") as f:
                    collectors_config = yaml.safe_load(f) or {}
                config = collectors_config.get("quality_rules", {})
            else:
                config = {}
        self.rules = self._get_default_rules(config)

        logger.info(f"SourceCurator initialized with {len(self.rules)} rules")

    def _get_default_rules(self, config: dict[str, Any]) -> dict[str, Any]:
        """기본 규칙 (설정 파일에서 덮어쓰기)"""
        defaults = {
            "min_relevance_score": 0.6,
            "min_quality_score": 0.5,
            "max_inactive_days": 30,
            "min_signal_noise_ratio": 0.2,
            "trusted_threshold_quality": 0.9,
            "trusted_threshold_count": 50,
        }
        defaults.update(config)
        return defaults

    def evaluate_all(self) -> CurationReport:
        """모든 활성 소스의 품질 메트릭 계산"""
        report = CurationReport(timestamp=datetime.now().isoformat())

        sources = self.sm.load()
        report.total_sources = len(sources)

        for source in sources:
            if source.status == "pending":
                report.pending_sources += 1
                continue

            if not source.enabled:
                continue

            report.active_sources += 1

            # 규칙 적용
            action = self.apply_rules(source)

            if action == "trusted":
                report.trusted_sources += 1
            elif action == "disable":
                report.low_quality_sources.append(source.id)
            elif action == "review":
                report.review_needed.append(source.id)

            # 비활성 체크
            if source.last_collected:
                try:
                    last_collected = datetime.strptime(source.last_collected, "%Y-%m-%d")
                    days_inactive = (datetime.now() - last_collected).days
                    if days_inactive > self.rules["max_inactive_days"]:
                        report.inactive_sources.append(source.id)
                except Exception:
                    pass

        logger.info(f"Evaluation complete: {report.active_sources} active sources")
        return report

    def apply_rules(self, source: SourceMeta) -> str | None:
        """
        규칙 적용 결과 반환

        Returns:
            "disable" | "review" | "trusted" | None
        """
        # 신뢰 소스 체크
        if (
            source.quality_score
            and source.quality_score >= self.rules["trusted_threshold_quality"]
            and source.collected_count >= self.rules["trusted_threshold_count"]
        ):
            return "trusted"

        # 저품질 체크
        if source.quality_score is not None and source.quality_score < self.rules["min_quality_score"]:
            return "disable"

        # 신호/잡음 비율 체크
        if source.signal_noise_ratio is not None and source.signal_noise_ratio < self.rules["min_signal_noise_ratio"]:
            return "disable"

        # 관련성 체크
        if source.quality_score is not None and source.quality_score < self.rules["min_relevance_score"]:
            return "review"

        return None

    def report(self) -> str:
        """소스별 품질 리포트 텍스트 생성"""
        sources = self.sm.load()

        lines = ["# Source Quality Report", "", f"Generated: {datetime.now().isoformat()}", ""]

        # 활성 소스
        active = [s for s in sources if s.enabled and s.status == "active"]
        lines.append(f"## Active Sources ({len(active)})")
        lines.append("")

        for source in sorted(active, key=lambda x: x.quality_score or 0, reverse=True):
            score_str = f"{source.quality_score:.2f}" if source.quality_score else "N/A"
            snr_str = f"{source.signal_noise_ratio:.2f}" if source.signal_noise_ratio else "N/A"
            lines.append(f"- **{source.id}**")
            lines.append(f"  - URL: {source.url}")
            lines.append(f"  - Quality Score: {score_str}")
            lines.append(f"  - Signal/Noise Ratio: {snr_str}")
            lines.append(f"  - Collected Count: {source.collected_count}")
            lines.append("")

        # Pending 소스
        pending = [s for s in sources if s.status == "pending"]
        if pending:
            lines.append(f"## Pending Sources ({len(pending)})")
            lines.append("")
            for source in pending:
                lines.append(f"- {source.id}: {source.url}")
            lines.append("")

        # 비활성 소스
        inactive = [s for s in sources if not s.enabled]
        if inactive:
            lines.append(f"## Inactive Sources ({len(inactive)})")
            lines.append("")
            for source in inactive:
                lines.append(f"- {source.id}: {source.url}")
            lines.append("")

        return "\n".join(lines)

    def cleanup(self, dry_run: bool = False) -> list[str]:
        """규칙에 따라 저품질 소스 비활성화"""
        disabled = []

        sources = self.sm.load()

        for source in sources:
            if not source.enabled:
                continue

            action = self.apply_rules(source)

            if action == "disable":
                disabled.append(source.id)
                if not dry_run:
                    self.sm.disable(source.id)
                    logger.info(f"Disabled low-quality source: {source.id}")

        if dry_run:
            logger.info(f"[DRY RUN] Would disable {len(disabled)} sources")
        else:
            logger.info(f"Disabled {len(disabled)} sources")

        return disabled

    def get_status(self) -> dict[str, Any]:
        """소스 상태 요약"""
        sources = self.sm.load()

        status = {
            "total": len(sources),
            "active": len([s for s in sources if s.enabled and s.status == "active"]),
            "pending": len([s for s in sources if s.status == "pending"]),
            "disabled": len([s for s in sources if not s.enabled]),
            "rejected": len([s for s in sources if s.status == "rejected"]),
        }

        return status

    def approve(self, source_id: str) -> bool:
        """소스 승인"""
        return self.sm.approve(source_id)

    def reject(self, source_id: str) -> bool:
        """소스 거부"""
        return self.sm.reject(source_id)


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(description="소스 품질 관리")
    parser.add_argument("--report", action="store_true", help="품질 리포트 출력")
    parser.add_argument("--cleanup", action="store_true", help="저품질 소스 정리")
    parser.add_argument("--dry-run", action="store_true", help="실제 변경 없이 시뮬레이션")
    parser.add_argument("--status", action="store_true", help="소스 상태 요약")
    parser.add_argument("--approve", metavar="SOURCE_ID", help="소스 승인")
    parser.add_argument("--reject", metavar="SOURCE_ID", help="소스 거부")

    args = parser.parse_args()

    curator = SourceCurator()

    # 승인/거부 처리
    if args.approve:
        if curator.approve(args.approve):
            print(f"Approved: {args.approve}")
        else:
            print(f"Failed to approve: {args.approve}")
        return

    if args.reject:
        if curator.reject(args.reject):
            print(f"Rejected: {args.reject}")
        else:
            print(f"Failed to reject: {args.reject}")
        return

    # 상태 조회
    if args.status:
        status = curator.get_status()
        print("\nSource Status Summary:")
        print("-" * 30)
        for key, value in status.items():
            print(f"  {key}: {value}")
        return

    # 리포트 생성
    if args.report:
        report_text = curator.report()
        print(report_text)
        return

    # 정리 실행
    if args.cleanup:
        disabled = curator.cleanup(dry_run=args.dry_run)
        if disabled:
            print(f"\nDisabled sources: {disabled}")
        else:
            print("\nNo sources to disable")
        return

    # 기본: 상태 출력
    status = curator.get_status()
    print("\nSource Status Summary:")
    print("-" * 30)
    for key, value in status.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
