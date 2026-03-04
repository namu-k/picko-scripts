#!/usr/bin/env python3
"""
문서 상태 점검 스크립트

docs/ 디렉터리의 모든 문서를 점검하여 다음 사항을 확인합니다:
1. 깨진 링크
2. 누락된 문서
3. 필요한 섹션
4. 포맷 문제
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class DocsStatusChecker:
    def __init__(self, docs_root: str = "docs"):
        self.docs_root = Path(docs_root)
        self.readme_path = self.docs_root / "README.md"
        self.required_sections = {
            "PRD": "제품 요구사항",
            "아키텍처": "시스템 아키텍처",
            "API": "API 명세",
            "개발": "개발 가이드",
            "운영": "운영 가이드",
            "사용자": "사용자 매뉴얼",
        }

    def check_broken_links(self) -> List[Dict]:
        """깨진 링크 확인"""
        broken_links = []

        for md_file in self.docs_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # 링크 패턴 찾기
                links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

                for text, link in links:
                    # 상대 링크인 경우
                    if link.startswith("./") or link.startswith("../"):
                        link_path = md_file.parent / link
                        if not link_path.exists():
                            broken_links.append(
                                {
                                    "file": str(md_file.relative_to(self.docs_root)),
                                    "link": link,
                                    "text": text,
                                    "type": "relative",
                                }
                            )
                    # 절대 링크인 경우
                    elif link.startswith("/"):
                        absolute_path = self.docs_root / link[1:]
                        if not absolute_path.exists():
                            broken_links.append(
                                {
                                    "file": str(md_file.relative_to(self.docs_root)),
                                    "link": link,
                                    "text": text,
                                    "type": "absolute",
                                }
                            )

            except Exception as e:
                print(f"오류 발생 ({md_file}): {e}")

        return broken_links

    def check_missing_sections(self) -> Dict[str, List[str]]:
        """누락된 섹션 확인"""
        missing = {}

        for section_name, description in self.required_sections.items():
            section_path = self.docs_root / section_name.lower()
            if section_name == "PRD":
                prd_path = self.docs_root / "PRD.md"
                if not prd_path.exists():
                    missing[section_name] = ["PRD.md"]
            else:
                if not section_path.exists():
                    missing[section_name] = ["디렉터리 생성 필요"]
                else:
                    # 디렉터리가 비어있는지 확인
                    if not any(section_path.iterdir()):
                        missing[section_name] = ["파일 생성 필요"]

        return missing

    def check_document_format(self) -> List[Dict]:
        """문서 포맷 점검"""
        format_issues = []

        for md_file in self.docs_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")

                # 1. UTF-8 BOM 확인
                if content.startswith("\ufeff"):
                    format_issues.append(
                        {
                            "file": str(md_file.relative_to(self.docs_root)),
                            "issue": "UTF-8 BOM 포함",
                            "severity": "warning",
                        }
                    )

                # 2. 빈 줄로 시작하는지 확인
                if content and content[0] != "\n":
                    format_issues.append(
                        {
                            "file": str(md_file.relative_to(self.docs_root)),
                            "issue": "파일 시작에 빈 줄이 없음",
                            "severity": "info",
                        }
                    )

                # 3. 첫 번째 헤딩 확인
                first_heading = re.search(r"^# ", content)
                if not first_heading:
                    format_issues.append(
                        {
                            "file": str(md_file.relative_to(self.docs_root)),
                            "issue": "첫 번째 헤딩(제목) 없음",
                            "severity": "warning",
                        }
                    )

                # 4. 마지막 줄 확인
                lines = content.split("\n")
                if lines and lines[-1].strip():
                    format_issues.append(
                        {
                            "file": str(md_file.relative_to(self.docs_root)),
                            "issue": "파일 끝에 빈 줄이 없음",
                            "severity": "info",
                        }
                    )

            except Exception as e:
                format_issues.append(
                    {
                        "file": str(md_file.relative_to(self.docs_root)),
                        "issue": f"파일 읽기 오류: {e}",
                        "severity": "error",
                    }
                )

        return format_issues

    def check_consistency(self) -> List[Dict]:
        """문서 일관성 점검"""
        consistency_issues = []

        # 1. 용어 일관성
        terms = {
            "파이프라인": ["pipeline", "파이프라인"],
            "워크플로우": ["workflow", "워크플로우"],
            "API": ["API", "애피"],
            "컴포넌트": ["component", "컴포넌트"],
        }

        for md_file in self.docs_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")

                for term, variations in terms.items():
                    # 여러 용어가 혼용되어 있는지 확인
                    found_terms = []
                    for variation in variations:
                        if variation.lower() in content.lower():
                            found_terms.append(variation)

                    if len(found_terms) > 1:
                        consistency_issues.append(
                            {
                                "file": str(md_file.relative_to(self.docs_root)),
                                "issue": f"'{term}' 용어가 여러 형태로 사용됨: {found_terms}",
                                "severity": "warning",
                            }
                        )

            except Exception:
                pass

        return consistency_issues

    def generate_report(self) -> str:
        """점검 보고서 생성"""
        report = []

        # 보고서 헤더
        report.append("# 문서 상태 점검 보고서")
        report.append(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 1. 깨진 링크
        report.append("## 🔗 깨진 링크")
        broken_links = self.check_broken_links()

        if broken_links:
            report.append("⚠️ 다음과 같은 깨진 링크를 발견했습니다:")
            report.append("")
            report.append("| 파일 | 링크 | 텍스트 | 유형 |")
            report.append("|------|------|--------|------|")

            for link in broken_links:
                report.append(f"| {link['file']} | {link['link']} | {link['text']} | {link['type']} |")
        else:
            report.append("✅ 깨진 링크 없음")

        report.append("")

        # 2. 누락된 섹션
        report.append("## 📁 누락된 섹션")
        missing_sections = self.check_missing_sections()

        if missing_sections:
            report.append("⚠️ 다음 섹션이 누락되었습니다:")
            report.append("")
            report.append("| 섹션 | 상태 |")
            report.append("|------|------|")

            for section, issues in missing_sections.items():
                report.append(f"| {section} | {'❌ ' + ', '.join(issues)} |")
        else:
            report.append("✅ 모든 필수 섹션 존재")

        report.append("")

        # 3. 포맷 문제
        report.append("## 📝 문서 포맷 점검")
        format_issues = self.check_document_format()

        if format_issues:
            report.append("⚠️ 포맷 문제를 발견했습니다:")
            report.append("")
            report.append("| 파일 | 문제 | 심각도 |")
            report.append("|------|------|--------|")

            for issue in format_issues:
                severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}
                report.append(f"| {issue['file']} | {issue['issue']} | {severity_icon.get(issue['severity'], '⚪')} |")
        else:
            report.append("✅ 모든 문서 포맷 정상")

        report.append("")

        # 4. 일관성 점검
        report.append("## 🔄 용어 일관성")
        consistency_issues = self.check_consistency()

        if consistency_issues:
            report.append("⚠️ 일관성 문제를 발견했습니다:")
            report.append("")
            report.append("| 파일 | 문제 |")
            report.append("|------|------|")

            for issue in consistency_issues:
                report.append(f"| {issue['file']} | {issue['issue']} |")
        else:
            report.append("✅ 용어 일관성 유지")

        report.append("")

        # 5. 요약
        report.append("## 📊 요약")
        report.append("")

        total_issues = len(broken_links) + len(missing_sections) + len(format_issues) + len(consistency_issues)
        report.append("| 항목 | 개수 |")
        report.append("|------|------|")
        report.append(f"| 깨진 링크 | {len(broken_links)}개 |")
        report.append(f"| 누락 섹션 | {len(missing_sections)}개 |")
        report.append(f"| 포맷 문제 | {len(format_issues)}개 |")
        report.append(f"| 일관성 문제 | {len(consistency_issues)}개 |")
        report.append(f"| **총계** | {total_issues}개 |")

        if total_issues == 0:
            report.append("")
            report.append("🎉 모든 점검 항목을 통과했습니다!")
        else:
            report.append("")
            report.append("📋 권장 사항:")
            report.append("1. 깨진 링크는 즉시 수정하세요")
            report.append("2. 누락된 섹션을 생성하세요")
            report.append("3. 포맷 문제를 수정하세요")
            report.append("4. 용어 일관성을 유지하세요")

        return "\n".join(report)

    def run_check(self):
        """점검 실행"""
        print("🔍 문서 상태 점검을 시작합니다...")

        # 보고서 생성
        report = self.generate_report()

        # 보고서 저장
        report_path = self.docs_root / "docs_status_report.md"
        report_path.write_text(report, encoding="utf-8")

        print(f"✅ 점검 완료! 보고서 저장 위치: {report_path}")
        print("\n📋 주요 결과:")

        # 주요 결과 출력
        broken_links = self.check_broken_links()
        if broken_links:
            print(f"⚠️ 깨진 링크: {len(broken_links)}개")

        missing = self.check_missing_sections()
        if missing:
            print(f"⚠️ 누락 섹션: {len(missing)}개")

        format_issues = self.check_document_format()
        if format_issues:
            print(f"⚠️ 포맷 문제: {len(format_issues)}개")

        consistency_issues = self.check_consistency()
        if consistency_issues:
            print(f"⚠️ 일관성 문제: {len(consistency_issues)}개")


if __name__ == "__main__":
    checker = DocsStatusChecker()
    checker.run_check()
