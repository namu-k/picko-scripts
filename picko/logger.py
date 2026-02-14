"""
로깅 유틸리티 모듈
모든 스크립트에서 통일된 로깅 형식 사용
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger as LoggerType

# 기본 로그 디렉토리
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "logs"


def setup_logger(
    script_name: str,
    log_dir: str | Path | None = None,
    level: str = "INFO",
    retention_days: int = 30,
) -> "LoggerType":
    """
    스크립트별 로거 설정

    Args:
        script_name: 스크립트 이름 (로그 파일명에 사용)
        log_dir: 로그 디렉토리 경로
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        retention_days: 로그 보관 일수

    Returns:
        설정된 loguru logger 인스턴스
    """
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR

    log_dir = Path(log_dir)

    # 날짜별 디렉토리 생성
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log_dir = log_dir / today
    daily_log_dir.mkdir(parents=True, exist_ok=True)

    # 기본 핸들러 제거
    logger.remove()

    # 콘솔 출력
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[script]}</cyan> | {message}",
        level=level,
        colorize=True,
    )

    # 파일 출력 (스크립트별)
    log_file = daily_log_dir / f"{script_name}.log"
    logger.add(
        sink=str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[script]} | {message}",
        level=level,
        rotation="00:00",  # 자정에 로테이션
        retention=f"{retention_days} days",
        encoding="utf-8",
    )

    # 에러 전용 파일
    error_file = daily_log_dir / "errors.log"
    logger.add(
        sink=str(error_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[script]} | {message}\n{exception}",
        level="ERROR",
        rotation="00:00",
        retention=f"{retention_days} days",
        encoding="utf-8",
    )

    # 스크립트명 바인딩
    return logger.bind(script=script_name)


def get_logger(script_name: str) -> "LoggerType":
    """
    간단한 로거 획득 (기본 설정 사용)

    Args:
        script_name: 스크립트 이름

    Returns:
        loguru logger 인스턴스
    """
    return setup_logger(script_name)
