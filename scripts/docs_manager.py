#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
문서 관리 메인 스크립트

문서 목록 생성, 상태 점검, 포맷 검사 등 문서 관리 관련 작업을 수행합니다.
"""

import argparse

from docs_list_generator import DocsListGenerator
from docs_status_checker import DocsStatusChecker


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="문서 관리 도구")
    parser.add_argument("command", choices=["generate", "check", "list", "help"], help="실행할 명령어")
    parser.add_argument("--docs-dir", default="docs", help="문서 루트 디렉터리 (기값: docs)")
    parser.add_argument("--output", help="출력 파일 경로 (생성 시만 사용)")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력")

    args = parser.parse_args()

    # 명령어 실행
    if args.command == "help":
        print_help()
        return

    elif args.command == "generate":
        generator = DocsListGenerator(args.docs_dir)
        print(f"문서 목록 생성 중... ({args.docs_dir})")
        generator.update_readme()
        if args.verbose:
            print_generated_stats(generator)

    elif args.command == "check":
        checker = DocsStatusChecker(args.docs_dir)
        print(f"문서 상태 점검 중... ({args.docs_dir})")
        checker.run_check()

    elif args.command == "list":
        generator = DocsListGenerator(args.docs_dir)
        print(f"문서 목록 ({args.docs_dir}):")
        print_section_stats(generator)


def print_help():
    """도움말 출력"""
    help_text = """
문서 관리 도구 - 사용법

기본 사용법:
  python scripts/docs_manager.py [명령어] [옵션]

명령어:
  generate     문서 목록을 자동으로 생성하고 README.md 업데이트
  check        문서 상태 점검 (깨진 링크, 누락 섹션 등)
  list         문서 목록 간단히 출력
  help         이 도움말 출력

옵션:
  --docs DIR   문서 루트 디렉터리 (기값: docs)
  --output FILE 출력 파일 경로 (생성 시만 사용)
  --verbose, -v 상세 출력

예시:
  # 기본 문서 목록 생성
  python scripts/docs_manager.py generate

  # 다른 디렉터리에서 문서 점검
  python scripts/docs_manager.py check --docs-dir ./my-docs

  # 상세 모드로 문서 목록 생성
  python scripts/docs_manager.py generate --verbose

  # 결과를 파일로 저장
  python scripts/docs_manager.py generate --output ./docs_list.md
"""
    print(help_text)


def print_generated_stats(generator):
    """상세 통계 출력"""
    print("\n생성된 문서 통계:")

    total_count = 0
    section_counts = {}

    for section_name in generator.sections:
        files = generator.scan_directory(section_name)
        if files:
            count = len(files)
            section_counts[section_name] = count
            total_count += count
            icon = generator.sections[section_name]["icon"]
            print(f"  {icon} {section_name}: {count}개 파일")

    print(f"\n총 계: {total_count}개 파일")


def print_section_stats(generator):
    """섹션별 통계 출력"""
    print("\n문서 섹션별 통계:")

    for section_name in generator.sections:
        files = generator.scan_directory(section_name)
        if files:
            icon = generator.sections[section_name]["icon"]
            print(f"  {icon} {section_name}: {len(files)}개")
        else:
            icon = generator.sections[section_name]["icon"]
            print(f"  {icon} {section_name}: 없음")


if __name__ == "__main__":
    main()
