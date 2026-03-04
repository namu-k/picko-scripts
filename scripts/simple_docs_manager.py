#!/usr/bin/env python3
"""
간단한 문서 관리 스크립트 (Windows 호환 버전)
"""
import re
from datetime import datetime
from pathlib import Path


def generate_docs_list():
    """문서 목록 생성"""
    docs_root = Path("docs")
    readme_path = docs_root / "README.md"

    # 섹션 정의
    sections = {
        "PRD": {"path": "", "pattern": r"PRD\.md"},
        "계획": {"path": "plans/", "pattern": r"\.md$"},
        "UI/UX": {"path": "ui/", "pattern": r"\.md$"},
        "API": {"path": "api/", "pattern": r"README\.md"},
        "명세": {"path": "specs/", "pattern": r"\.yml$"},
        "아키텍처": {"path": "architecture/", "pattern": r"\.md$"},
        "개발": {"path": "development/", "pattern": r"\.md$"},
        "운영": {"path": "operations/", "pattern": r"\.md$"},
        "사용자": {"path": "user/", "pattern": r"\.md$"},
        "테스트": {"path": "testing/", "pattern": r"\.md$"},
    }

    # 새 README 내용 생성
    content = []
    content.append("---")
    content.append("문서 목록 자동 생성")
    content.append(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    content.append("---")
    content.append("")
    content.append("## 문서 목차")
    content.append("")

    total_files = 0
    completed_files = 0

    # 각 섹션 처리
    for section_name, section_info in sections.items():
        section_path = docs_root / section_info["path"]
        if section_path.exists():
            files = list(section_path.glob("*"))
            md_files = [f for f in files if re.search(section_info["pattern"], f.name)]

            if md_files:
                content.append(f"### {section_name}")
                content.append("")
                content.append("| 파일 | 크기 | 수정일 | 상태 | 설명 |")
                content.append("|------|------|--------|------|------|")

                for file_path in sorted(md_files):
                    size_kb = file_path.stat().st_size / 1024
                    modified = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d")

                    # 상태 확인
                try:
                    content_str = file_path.read_text(encoding="utf-8", errors="ignore")
                    if "진행중" in content_str or "in_progress" in content_str.lower():
                        status = "진행중"
                    elif "계획중" in content_str or "planned" in content_str.lower():
                        status = "계획중"
                    else:
                        status = "완료"
                        completed_files += 1
                except Exception:
                    status = "미확인"

                    total_files += 1

                    # 링크 생성
                    if file_path.name.endswith(".md"):
                        link = f"[{file_path.name}](./{section_path.name}/{file_path.name})"
                    else:
                        link = f"`{file_path.name}`"

                    # 설명 추출
                    description = file_path.stem
                    try:
                        first_line = content_str.split("\n")[0]
                        if first_line.startswith("# "):
                            description = first_line[2:].split("\n")[0].strip()
                    except Exception:
                        pass

                    content.append(f"| {link} | {size_kb:.1f} KB | {modified} | {status} | {description} |")

                content.append("")

    # 통계 추가
    content.append("## 문서 통계")
    content.append("")
    content.append("| 구분 | 개수 | 비율 |")
    content.append("|------|------|------|")
    content.append(f"| **총 파일 수** | {total_files} | 100% |")
    content.append(f"| **완료** | {completed_files} | {completed_files / total_files * 100:.1f}% |")
    if total_files > completed_files:
        in_progress = total_files - completed_files
        content.append(f"| **진행중/계획중** | {in_progress} | {in_progress / total_files * 100:.1f}% |")
    content.append("")
    content.append(f"**완료율**: {completed_files / total_files * 100:.1f}%")

    # 작성 순서
    content.append("")
    content.append("## 문서 작성 순서")
    content.append("1. PRD 작성 - 제품 요구사항 정의")
    content.append("2. 아키텍처 설계 - 시스템 구조 설계")
    content.append("3. API 명세 - 인터페이스 정의")
    content.append("4. UI/UX 설계 - 사용자 인터페이스 설계")
    content.append("5. 개발 가이드 - 개발 환경 및 규칙 정의")
    content.append("6. 테스트 전략 - 테스트 계획 수립")
    content.append("7. 배포 가이드 - 운영 절차 정의")
    content.append("8. 사용자 매뉴얼 - 최종 사용자 가이드")
    content.append("")
    content.append(f"*마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    # 파일 쓰기
    readme_path.write_text("\n".join(content), encoding="utf-8")
    print(f"README.md 업데이트 완료! ({total_files}개 문서)")


def check_docs_status():
    """문서 상태 점검"""
    docs_root = Path("docs")
    broken_links = []

    print("문서 상태 점검 시작...")

    # 모든 markdown 파일 스캔
    for md_file in docs_root.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")

            # 링크 확인
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
            for text, link in links:
                if link.startswith("./") or link.startswith("../"):
                    link_path = md_file.parent / link
                    if not link_path.exists():
                        broken_links.append(f"{md_file}: {link}")
        except Exception:
            pass

    # 결과 출력
    if broken_links:
        print(f"\n깨진 링크 발견 ({len(broken_links)}개):")
        for link in broken_links[:5]:  # 처음 5개만 출력
            print(f"  - {link}")
        if len(broken_links) > 5:
            print(f"  ... 및 {len(broken_links) - 5}개 더")
    else:
        print("깨진 링크 없음")

    # 파일 통계
    total_md = len(list(docs_root.rglob("*.md")))
    total_yml = len(list(docs_root.rglob("*.yml")))
    print("\n파일 통계:")
    print(f"  - Markdown 파일: {total_md}개")
    print(f"  - YAML 파일: {total_yml}개")
    print(f"  - 총 파일: {total_md + total_yml}개")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "generate":
            generate_docs_list()
        elif sys.argv[1] == "check":
            check_docs_status()
        else:
            print("사용법: python simple_docs_manager.py [generate|check]")
    else:
        print("기본 작업: 문서 목록 생성")
        generate_docs_list()
