#!/usr/bin/env python3
"""
문서 목록 자동 생성 스크립트

docs/ 디렉터리의 모든 문서를 스캔하여 README.md에 포함할 목록을 자동으로 생성합니다.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class DocsListGenerator:
    def __init__(self, docs_root: str = "docs"):
        self.docs_root = Path(docs_root)
        self.readme_path = self.docs_root / "README.md"
        self.sections = {
            "PRD": {"path": "", "pattern": r"PRD\.md", "icon": "📋"},
            "계획": {"path": "plans/", "pattern": r"\.md$", "icon": "📅"},
            "UI/UX": {"path": "ui/", "pattern": r"\.md$", "icon": "🎨"},
            "API": {"path": "api/", "pattern": r"README\.md", "icon": "🔌"},
            "명세": {"path": "specs/", "pattern": r"\.yml$", "icon": "📝"},
            "아키텍처": {"path": "architecture/", "pattern": r"\.md$", "icon": "🏗️"},
            "개발": {"path": "development/", "pattern": r"\.md$", "icon": "💻"},
            "운영": {"path": "operations/", "pattern": r"\.md$", "icon": "🚀"},
            "사용자": {"path": "user/", "pattern": r"\.md$", "icon": "👥"},
            "테스트": {"path": "testing/", "pattern": r"\.md$", "icon": "🧪"},
            "보안": {"path": "security/", "pattern": r"\.md$", "icon": "🔒"},
        }

    def scan_directory(self, section: str) -> List[Dict]:
        """특정 섹션의 디렉터리를 스캔하여 파일 목록을 반환"""
        section_info = self.sections.get(section)
        if not section_info:
            return []

        section_path = self.docs_root / section_info["path"]
        if not section_path.exists():
            return []

        files = []
        for file_path in section_path.glob("*"):
            if file_path.is_file():
                # 파일 패턴 매칭
                if re.search(section_info["pattern"], file_path.name):
                    # 파일 정보 수집
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path.relative_to(self.docs_root)),
                        "size": self._format_size(file_path.stat().st_size),
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d"),
                        "status": self._get_file_status(file_path),
                        "description": self._extract_description(file_path),
                    }
                    files.append(file_info)

        # 파일 이름으로 정렬
        files.sort(key=lambda x: x["name"])
        return files

    def _format_size(self, size_bytes: int) -> str:
        """파일 크기를 사람이 읽기 쉬운 형식으로 변환"""
        for unit in ["B", "KB", "MB"]:
            if size_bytes < 1024:
                return f"{size_bytes} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} GB"

    def _get_file_status(self, file_path: Path) -> str:
        """파일 상태 확인 (완료/진행중/계획중)"""
        try:
            content = file_path.read_text(encoding="utf-8")
            # 파일 내용에서 상태 확인
            if "🚧" in content or "진행중" in content:
                return "🚧 진행중"
            elif "⏸️" in content or "계획중" in content:
                return "⏸️ 계획중"
            else:
                return "✅ 완료"
        except Exception:
            return "❓ 미확인"

    def _extract_description(self, file_path: Path) -> str:
        """파일에서 간단한 설명 추출"""
        try:
            content = file_path.read_text(encoding="utf-8")
            # 첫 번째 # 뒤의 텍스트 추출
            match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if match:
                return match.group(1).split("\n")[0].strip()
            return file_path.stem
        except Exception:
            return file_path.stem

    def generate_table_of_contents(self) -> str:
        """문서 목차 생성"""
        toc = []
        toc.append("## 📚 문서 목차")
        toc.append("")

        for section in self.sections:
            files = self.scan_directory(section)
            if files:
                section_info = self.sections[section]
                toc.append(f"### {section_info['icon']} {section}")
                toc.append("")
                toc.append("| 파일 | 크기 | 수정일 | 상태 | 설명 |")
                toc.append("|------|------|--------|------|------|")

                for file_info in files:
                    # 파일 경로를 링크로 변환
                    if file_info["name"].endswith(".md"):
                        link = f"[{file_info['name']}](./{file_info['path']})"
                    else:
                        link = f"`{file_info['name']}`"

                    toc.append(
                        f"| {link} | {file_info['size']} | "
                        f"{file_info['modified']} | {file_info['status']} | "
                        f"{file_info['description']} |"
                    )

                toc.append("")

        return "\n".join(toc)

    def generate_statistics(self) -> str:
        """문서 통계 정보 생성"""
        stats = []
        stats.append("## 📊 문서 통계")
        stats.append("")

        total_files = 0
        completed_files = 0
        in_progress_files = 0
        planned_files = 0

        for section in self.sections:
            files = self.scan_directory(section)
            total_files += len(files)
            for file_info in files:
                if file_info["status"] == "✅ 완료":
                    completed_files += 1
                elif file_info["status"] == "🚧 진행중":
                    in_progress_files += 1
                elif file_info["status"] == "⏸️ 계획중":
                    planned_files += 1

        stats.append("| 구분 | 개수 | 비율 |")
        stats.append("|------|------|------|")
        stats.append(f"| **총 파일 수** | {total_files} | 100% |")
        stats.append(f"| ✅ 완료 | {completed_files} | {completed_files / total_files * 100:.1f}% |")
        stats.append(f"| 🚧 진행중 | {in_progress_files} | {in_progress_files / total_files * 100:.1f}% |")
        stats.append(f"| ⏸️ 계획중 | {planned_files} | {planned_files / total_files * 100:.1f}% |")

        stats.append("")
        stats.append(f"**완료율**: {completed_files / total_files * 100:.1f}%")

        return "\n".join(stats)

    def generate_workflow_section(self) -> str:
        """워크플로우 섹션 생성"""
        workflow = []
        workflow.append("## 🔄 문서 관리 워크플로우")
        workflow.append("")

        workflow.append("### 문서 작성 순서")
        workflow.append("1. **PRD 작성** - 제품 요구사항 정의")
        workflow.append("2. **아키텍처 설계** - 시스템 구조 설계")
        workflow.append("3. **API 명세** - 인터페이스 정의")
        workflow.append("4. **UI/UX 설계** - 사용자 인터페이스 설계")
        workflow.append("5. **개발 가이드** - 개발 환경 및 규칙 정의")
        workflow.append("6. **테스트 전략** - 테스트 계획 수립")
        workflow.append("7. **배포 가이드** - 운영 절차 정의")
        workflow.append("8. **사용자 매뉴얼** - 최종 사용자 가이드")
        workflow.append("")

        workflow.append("### 문서 유지보수")
        workflow.append("- **주기 검사**: 매주 월요일 자동 문서 검사")
        workflow.append("- **링크 검증**: 깨진 링크 자동 체크")
        workflow.append("- **업데이트 트리거**: 코드 변경 시 관련 문자 업데이트")
        workflow.append("- **버전 관리**: 모든 문서 변경은 Git으로 추적")

        return "\n".join(workflow)

    def update_readme(self):
        """README.md 파일 업데이트"""
        print("README.md 업데이트 중...")

        # 기존 README 읽기
        existing_content = ""
        if self.readme_path.exists():
            existing_content = self.readme_path.read_text(encoding="utf-8")

        # 새로운 콘텐츠 생성
        new_content = []

        # 헤더 부분 유지
        lines = existing_content.split("\n")
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith("---") and i > 0:
                header_end = i
                break

        if header_end:
            new_content.extend(lines[: header_end + 1])
        else:
            new_content.append("---")
            new_content.append(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            new_content.append("---")

        # 새 섹션 추가
        new_content.append("")
        new_content.append(self.generate_table_of_contents())
        new_content.append("")
        new_content.append(self.generate_statistics())
        new_content.append("")
        new_content.append(self.generate_workflow_section())
        new_content.append("")
        new_content.append("*마지막 업데이트: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "*")

        # 파일 쓰기
        self.readme_path.write_text("\n".join(new_content), encoding="utf-8")

        print("✅ README.md 업데이트 완료!")


def main():
    """메인 실행 함수"""
    generator = DocsListGenerator()

    print("🔍 문서 목록 생성 시작...")
    print(f"📁 기준 디렉터리: {generator.docs_root}")
    print()

    # 디렉터리 스캔
    for section in generator.sections:
        files = generator.scan_directory(section)
        if files:
            print(f"✅ {section}: {len(files)}개 파일 발견")
            for file_info in files[:3]:  # 각 섹션의 처음 3개만 출력
                print(f"   - {file_info['name']}")
            if len(files) > 3:
                print(f"   ... and {len(files) - 3} more files")

    print()
    # README 업데이트
    generator.update_readme()

    print("\n🎉 작업 완료!")
    print(f"📄 업데이트된 README 위치: {generator.readme_path}")


if __name__ == "__main__":
    main()
