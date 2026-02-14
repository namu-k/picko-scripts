"""
Score Calibrator 스크립트
실제 성과와 예측 점수를 비교 분석하여 가중치 조정 제안
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from picko.config import get_config
from picko.vault_io import VaultIO
from picko.scoring import calculate_score
from picko.logger import setup_logger

logger = setup_logger("score_calibrator")


@dataclass
class PerformanceRecord:
    """성과 기록"""
    content_id: str
    content_path: str
    predicted_score: float
    novelty: float
    relevance: float
    quality: float
    actual_performance: float
    platform: str
    published_at: str


@dataclass
class CalibrationReport:
    """보정 리포트"""
    total_analyzed: int
    correlation: dict[str, float]  # 각 점수 요소와 성과의 상관관계
    suggested_weights: dict[str, float]
    current_weights: dict[str, float]
    improvement_estimate: float
    top_performers: list[PerformanceRecord]
    underperformers: list[PerformanceRecord]


class ScoreCalibrator:
    """점수 보정 분석기"""

    def __init__(self):
        self.config = get_config()
        self.vault = VaultIO()
        self.logs_path = "Logs/Publish"
        logger.info("ScoreCalibrator initialized")

    def analyze(
        self,
        days: int = 30,
        min_engagement: int = 10
    ) -> CalibrationReport:
        """
        점수 예측력 분석

        Args:
            days: 분석할 기간 (일)
            min_engagement: 최소 참여 수 (미만은 제외)

        Returns:
            보정 리포트
        """
        logger.info(f"Analyzing score performance (last {days} days)")

        # 성과 데이터 수집
        records = self._collect_performance_data(days, min_engagement)

        if not records:
            logger.warning("No performance data found")
            return self._empty_report()

        # 상관관계 분석
        correlations = self._calculate_correlations(records)

        # 가중치 제안
        suggested_weights = self._suggest_weights(correlations)

        # 개선 추정
        improvement = self._estimate_improvement(records, suggested_weights)

        # 상위/저성과 항목
        sorted_records = sorted(records, key=lambda r: r.actual_performance, reverse=True)
        top_performers = sorted_records[:5]
        underperformers = sorted_records[-5:]

        return CalibrationReport(
            total_analyzed=len(records),
            correlation=correlations,
            suggested_weights=suggested_weights,
            current_weights=self.config.scoring.weights.copy(),
            improvement_estimate=improvement,
            top_performers=top_performers,
            underperformers=underperformers
        )

    def _collect_performance_data(
        self,
        days: int,
        min_engagement: int
    ) -> list[PerformanceRecord]:
        """성과 데이터 수집"""
        records = []
        notes = self.vault.list_notes(self.logs_path)

        for note_path in notes:
            try:
                meta = self.vault.read_frontmatter(note_path)

                # 발행 완료된 항목만
                if meta.get("status") != "published":
                    continue

                # 메트릭 확인
                metrics = meta.get("metrics", {})
                if not metrics:
                    continue

                total_engagement = (
                    metrics.get("views", 0) * 0.1 +
                    metrics.get("likes", 0) * 1.0 +
                    metrics.get("comments", 0) * 2.0 +
                    metrics.get("shares", 0) * 3.0
                )

                if total_engagement < min_engagement:
                    continue

                # 원본 콘텐츠의 점수 조회
                content_id = meta.get("content_id")
                if not content_id:
                    continue

                input_path = f"Inbox/Inputs/{content_id}.md"
                input_meta = self.vault.read_frontmatter(input_path)
                score_data = input_meta.get("score", {})

                records.append(PerformanceRecord(
                    content_id=content_id,
                    content_path=input_path,
                    predicted_score=score_data.get("total", 0),
                    novelty=score_data.get("novelty", 0),
                    relevance=score_data.get("relevance", 0),
                    quality=score_data.get("quality", 0),
                    actual_performance=total_engagement,
                    platform=meta.get("platform", "unknown"),
                    published_at=meta.get("published_at", "")
                ))

            except Exception as e:
                logger.debug(f"Error processing {note_path}: {e}")

        logger.info(f"Collected {len(records)} performance records")
        return records

    def _calculate_correlations(
        self,
        records: list[PerformanceRecord]
    ) -> dict[str, float]:
        """점수 요소별 성과 상관관계 계산"""
        if len(records) < 3:
            return {"novelty": 0, "relevance": 0, "quality": 0}

        actual = [r.actual_performance for r in records]

        correlations = {}
        for factor in ["novelty", "relevance", "quality"]:
            predicted = [getattr(r, factor) for r in records]
            corr = np.corrcoef(predicted, actual)[0, 1]
            correlations[factor] = float(corr) if not np.isnan(corr) else 0.0

        logger.debug(f"Correlations: {correlations}")
        return correlations

    def _suggest_weights(
        self,
        correlations: dict[str, float]
    ) -> dict[str, float]:
        """상관관계 기반 가중치 제안"""
        # 음수 상관관계를 0으로 처리
        adjusted = {k: max(0, v) for k, v in correlations.items()}

        # 합이 0이면 균등 배분
        total = sum(adjusted.values())
        if total == 0:
            return {"novelty": 0.33, "relevance": 0.34, "quality": 0.33}

        # 정규화하여 합이 1이 되도록
        suggested = {k: v / total for k, v in adjusted.items()}

        return suggested

    def _estimate_improvement(
        self,
        records: list[PerformanceRecord],
        new_weights: dict[str, float]
    ) -> float:
        """새 가중치 적용 시 개선 추정"""
        # 현재 가중치로 예상 순위와 실제 성과 순위의 상관관계
        current_ranks = [r.predicted_score for r in records]
        actual_ranks = [r.actual_performance for r in records]
        current_corr = np.corrcoef(current_ranks, actual_ranks)[0, 1]

        # 새 가중치로 재계산
        new_scores = []
        for r in records:
            new_score = (
                r.novelty * new_weights["novelty"] +
                r.relevance * new_weights["relevance"] +
                r.quality * new_weights["quality"]
            )
            new_scores.append(new_score)

        new_corr = np.corrcoef(new_scores, actual_ranks)[0, 1]

        improvement = float((new_corr - current_corr) * 100) if not np.isnan(new_corr - current_corr) else 0.0
        return improvement

    def _empty_report(self) -> CalibrationReport:
        """데이터 없는 빈 리포트"""
        return CalibrationReport(
            total_analyzed=0,
            correlation={"novelty": 0, "relevance": 0, "quality": 0},
            suggested_weights=self.config.scoring.weights.copy(),
            current_weights=self.config.scoring.weights.copy(),
            improvement_estimate=0,
            top_performers=[],
            underperformers=[]
        )

    def apply_weights(self, new_weights: dict[str, bool] = True) -> bool:
        """
        제안된 가중치를 config.yml에 적용

        Args:
            new_weights: 새 가중치 (True면 자동 계산된 가중치 사용)

        Returns:
            적용 성공 여부
        """
        # TODO: config.yml 자동 업데이트 기능
        logger.warning("Auto-config update not implemented - please update config.yml manually")
        return False


def print_report(report: CalibrationReport):
    """리포트 출력"""
    print(f"\n{'='*60}")
    print(f"Score Calibration Report")
    print(f"{'='*60}\n")

    print(f"📊 Analyzed: {report.total_analyzed} published items\n")

    print("🔗 Correlation with Actual Performance:")
    for factor, corr in report.correlation.items():
        bar = "█" * int(abs(corr) * 20)
        sign = "+" if corr > 0 else ""
        print(f"   {factor:12} {sign}{corr:.3f}  {bar}")

    print(f"\n⚖️  Weight Comparison:")
    print(f"{'':12} {'Current':>10} {'Suggested':>10}")
    for factor in ["novelty", "relevance", "quality"]:
        current = report.current_weights.get(factor, 0)
        suggested = report.suggested_weights.get(factor, 0)
        diff = suggested - current
        diff_str = f"({diff:+.2f})" if diff != 0 else ""
        print(f"   {factor:12} {current:>10.2f} {suggested:>10.2f} {diff_str}")

    print(f"\n📈 Estimated Improvement: {report.improvement_estimate:+.1f}%")

    if report.top_performers:
        print(f"\n🏆 Top Performers:")
        for i, r in enumerate(report.top_performers[:3], 1):
            print(f"   {i}. {r.content_id[:20]}... (score: {r.predicted_score:.2f}, engagement: {r.actual_performance:.0f})")

    if report.underperformers:
        print(f"\n📉 Underperformers:")
        for i, r in enumerate(reversed(report.underperformers[-3:]), 1):
            print(f"   {i}. {r.content_id[:20]}... (score: {r.predicted_score:.2f}, engagement: {r.actual_performance:.0f})")

    print(f"\n{'='*60}")


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description="Score Calibrator - 점수 가중치 분석 및 조정 제안"
    )

    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="분석할 기간 (일, 기본: 30)"
    )
    parser.add_argument(
        "--min-engagement", "-m",
        type=int,
        default=10,
        help="최소 참여 수 (기본: 10)"
    )
    parser.add_argument(
        "--apply", "-a",
        action="store_true",
        help="제안된 가중치를 config.yml에 적용"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 형식으로 출력"
    )

    args = parser.parse_args()

    calibrator = ScoreCalibrator()
    report = calibrator.analyze(days=args.days, min_engagement=args.min_engagement)

    if args.json:
        import json
        output = {
            "total_analyzed": report.total_analyzed,
            "correlation": report.correlation,
            "current_weights": report.current_weights,
            "suggested_weights": report.suggested_weights,
            "improvement_estimate": report.improvement_estimate,
            "top_performers": [
                {
                    "content_id": r.content_id,
                    "predicted_score": r.predicted_score,
                    "actual_performance": r.actual_performance
                }
                for r in report.top_performers
            ]
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    else:
        print_report(report)

        if args.apply:
            if report.total_analyzed == 0:
                print("\n⚠️  Cannot apply: No data to base recommendations on")
            else:
                success = calibrator.apply_weights(report.suggested_weights)
                if success:
                    print("\n✅ Weights applied to config.yml")
                else:
                    print("\n⚠️  Please update config.yml manually with suggested weights")


if __name__ == "__main__":
    main()
