"""
Validate Output 스크립트
생성된 콘텐츠 검증 (템플릿 규격, 필수 필드, 링크 유효성)
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from picko.config import get_config
from picko.vault_io import VaultIO
from picko.logger import setup_logger

logger = setup_logger("validate_output")


@dataclass
class ValidationResult:
    """검증 결과"""
    path: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """검증 리포트"""
    total_files: int = 0
    valid_files: int = 0
    invalid_files: int = 0
    results: list[ValidationResult] = field(default_factory=list)
    
    def add_result(self, result: ValidationResult):
        self.results.append(result)
        self.total_files += 1
        if result.valid:
            self.valid_files += 1
        else:
            self.invalid_files += 1


class OutputValidator:
    """출력물 검증기"""
    
    # 콘텐츠 타입별 필수 frontmatter 필드
    REQUIRED_FIELDS = {
        "input": ["id", "title", "source", "source_url", "status"],
        "digest": ["type", "date"],
        "longform": ["id", "title", "type", "status", "source_input"],
        "pack": ["id", "type", "channel", "status"],
        "image_prompt": ["id", "type", "source_content", "status"]
    }
    
    # 콘텐츠 타입별 필수 섹션
    REQUIRED_SECTIONS = {
        "input": ["요약"],
        "longform": ["핵심 내용"],
        "image_prompt": ["메인 프롬프트"]
    }
    
    def __init__(self):
        self.config = get_config()
        self.vault = VaultIO()
        logger.info("OutputValidator initialized")
    
    def validate_path(self, path: str, recursive: bool = False) -> ValidationReport:
        """
        경로 검증
        
        Args:
            path: 검증할 경로 (파일 또는 디렉토리)
            recursive: 하위 디렉토리 포함
        
        Returns:
            ValidationReport
        """
        report = ValidationReport()
        full_path = self.vault.get_path(path)
        
        if full_path.is_file():
            result = self._validate_file(full_path)
            report.add_result(result)
        elif full_path.is_dir():
            notes = self.vault.list_notes(path, recursive=recursive)
            for note_path in notes:
                result = self._validate_file(note_path)
                report.add_result(result)
        else:
            logger.warning(f"Path not found: {path}")
        
        return report
    
    def _validate_file(self, path: Path) -> ValidationResult:
        """개별 파일 검증"""
        result = ValidationResult(path=str(path), valid=True)
        
        try:
            meta, content = self.vault.read_note(path)
            
            # 콘텐츠 타입 감지
            content_type = self._detect_content_type(meta, path)
            
            # 1. Frontmatter 필수 필드 검증
            self._validate_required_fields(meta, content_type, result)
            
            # 2. 필수 섹션 검증
            self._validate_required_sections(content, content_type, result)
            
            # 3. 내부 링크 유효성 검증
            self._validate_wikilinks(content, result)
            
            # 4. 추가 검증
            self._validate_content_quality(meta, content, content_type, result)
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to read file: {e}")
        
        return result
    
    def _detect_content_type(self, meta: dict, path: Path) -> str:
        """콘텐츠 타입 감지"""
        # frontmatter의 type 필드 확인
        if "type" in meta:
            type_val = meta["type"]
            if type_val in ["digest", "longform", "pack", "image_prompt"]:
                return type_val
        
        # 경로 기반 추론
        path_str = str(path).replace("\\", "/")
        
        if "/_digests/" in path_str or "/digests/" in path_str:
            return "digest"
        elif "/Longform/" in path_str:
            return "longform"
        elif "/Packs/" in path_str:
            return "pack"
        elif "/_prompts/" in path_str:
            return "image_prompt"
        elif "/Inputs/" in path_str:
            return "input"
        
        return "unknown"
    
    def _validate_required_fields(
        self,
        meta: dict,
        content_type: str,
        result: ValidationResult
    ):
        """필수 필드 검증"""
        required = self.REQUIRED_FIELDS.get(content_type, [])
        
        for field in required:
            if field not in meta:
                result.valid = False
                result.errors.append(f"Missing required field: {field}")
            elif not meta[field]:
                result.warnings.append(f"Empty required field: {field}")
    
    def _validate_required_sections(
        self,
        content: str,
        content_type: str,
        result: ValidationResult
    ):
        """필수 섹션 검증"""
        required = self.REQUIRED_SECTIONS.get(content_type, [])
        
        for section in required:
            # ## 섹션명 패턴 확인
            if f"## {section}" not in content and f"# {section}" not in content:
                result.valid = False
                result.errors.append(f"Missing required section: {section}")
    
    def _validate_wikilinks(self, content: str, result: ValidationResult):
        """내부 링크 유효성 검증"""
        links = self.vault.extract_wikilinks(content)
        
        for link in links:
            resolved = self.vault.resolve_wikilink(link)
            if resolved is None:
                result.warnings.append(f"Broken wikilink: [[{link}]]")
    
    def _validate_content_quality(
        self,
        meta: dict,
        content: str,
        content_type: str,
        result: ValidationResult
    ):
        """콘텐츠 품질 검증"""
        # 제목 길이
        title = meta.get("title", "")
        if title and len(title) > 200:
            result.warnings.append(f"Title too long: {len(title)} chars")
        
        # 본문 최소 길이
        if content_type in ["longform", "input"]:
            if len(content) < 100:
                result.warnings.append(f"Content too short: {len(content)} chars")
        
        # 상태 값 검증
        status = meta.get("status")
        valid_statuses = ["inbox", "draft", "review", "published", "archived", "pending", "generated"]
        if status and status not in valid_statuses:
            result.warnings.append(f"Unknown status: {status}")
        
        # 날짜 형식 검증
        for date_field in ["created_at", "publish_date", "collected_at"]:
            if date_field in meta:
                try:
                    datetime.fromisoformat(str(meta[date_field]).replace("Z", "+00:00"))
                except ValueError:
                    result.warnings.append(f"Invalid date format for {date_field}")


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description="Validate Output - 생성된 콘텐츠 검증"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="Content/",
        help="검증할 경로 (기본: Content/)"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="하위 디렉토리 포함"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 출력"
    )
    
    args = parser.parse_args()
    
    validator = OutputValidator()
    report = validator.validate_path(args.path, recursive=args.recursive)
    
    # 결과 출력
    print(f"\n{'='*60}")
    print(f"Validation Report")
    print(f"{'='*60}")
    print(f"Total Files:   {report.total_files}")
    print(f"Valid:         {report.valid_files}")
    print(f"Invalid:       {report.invalid_files}")
    print(f"{'='*60}")
    
    if args.verbose or report.invalid_files > 0:
        for result in report.results:
            if not result.valid or args.verbose:
                status = "✓" if result.valid else "✗"
                print(f"\n{status} {result.path}")
                
                for error in result.errors:
                    print(f"  ❌ {error}")
                
                if args.verbose:
                    for warning in result.warnings:
                        print(f"  ⚠️ {warning}")
    
    # 종료 코드
    if report.invalid_files > 0:
        exit(1)


if __name__ == "__main__":
    main()
