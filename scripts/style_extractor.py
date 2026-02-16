"""
스타일 추출기 - 레퍼런스 콘텐츠에서 작성 스타일 프롬프트를 역추출합니다.

Usage:
    python -m scripts.style_extractor --urls URL1 URL2 --name "style_name"
    python -m scripts.style_extractor --file urls.txt --name "style_name"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from picko.llm_client import get_writer_client  # noqa: E402
from picko.logger import get_logger  # noqa: E402

logger = get_logger("style_extractor")

logger = get_logger("style_extractor")

# 스타일 분석용 시스템 프롬프트
STYLE_ANALYSIS_SYSTEM_PROMPT = """당신은 콘텐츠 스타일 분석 전문가입니다.
주어진 텍스트들을 분석하여 작성자의 고유한 스타일 특성을 추출하세요."""

STYLE_ANALYSIS_PROMPT = """다음 콘텐츠 샘플들을 분석하여 작성 스타일을 역추출하세요.

## 콘텐츠 샘플
{samples}

## 분석 요청사항

다음 요소들을 분석하여 JSON 형식으로 출력하세요:

1. **tone**: 어조 특성 배열 (예: ["witty", "authoritative", "casual"])
2. **sentence_style**: 문장 스타일 (short_punchy, medium_balanced, long_descriptive)
3. **structure_patterns**: 글 구조 패턴 배열 (예: ["hook -> story -> insight -> CTA"])
4. **vocabulary**: 단어 선택 특성 배열 (예: ["tech_metaphors", "data_driven", "questions"])
5. **signatures**: 시그니처 표현/패턴 배열 (자주 사용하는 표현, 접두사/접미사 등)
6. **hooks**: 글 시작 방식 배열 (질문, 통계, 스토리, 도발적 발언 등)
7. **closings**: 글 마무리 방식 배열 (CTA, 질문, 요약, 통찰 등)
8. **formatting**: 포맷팅 스타일 (이모지 사용, 리스트, 인용구 등)
9. **content_themes**: 자주 다루는 주제 테마

JSON 형식으로만 응답하세요."""

# 프롬프트 생성용 시스템 프롬프트
PROMPT_GENERATION_SYSTEM_PROMPT = """당신은 프롬프트 엔지니어링 전문가입니다.
분석된 스타일 특성을 바탕으로 콘텐츠 생성용 프롬프트를 작성하세요."""

WRITING_PROMPT_TEMPLATE = """다음 스타일 분석 결과를 바탕으로 글 작성용 프롬프트를 작성하세요.

## 스타일 분석 결과
{style_analysis}

## 요구사항
- 위 스타일 특성을 그대로 흉내낼 수 있는 구체적인 프롬프트 작성
- 프롬프트에는 다음이 포함되어야 함:
  1. 어조/톤 가이드
  2. 문장 구조 가이드
  3. 글 구조 템플릿
  4. 사용할 어휘/표현 스타일
  5. 시작과 끝 패턴
- 마크다운 형식으로 작성
- 실제 콘텐츠 생성에 바로 사용 가능한 형태

프롬프트만 출력하세요 (설명 없이):"""

IMAGE_PROMPT_TEMPLATE = """다음 스타일 분석 결과를 바탕으로 이미지 생성용 프롬프트 템플릿을 작성하세요.

## 스타일 분석 결과
{style_analysis}

## 요구사항
- 이 스타일의 시각적 특성을 이미지로 표현할 수 있는 프롬프트 템플릿
- 포함 요소:
  1. 전반적인 비주얼 스타일 (모던, 미니멀, 복고 등)
  2. 색상 팔레트 가이드
  3. 레이아웃/구성 스타일
  4. 타이포그래피 스타일
  5. 분위기/무드
- Jinja2 템플릿 변수 활용 가능 ({{ topic }}, {{ style_hint }} 등)
- Midjourney/DALL-E 스타일 프롬프트 형식

프롬프트만 출력하세요:"""

VIDEO_PROMPT_TEMPLATE = """다음 스타일 분석 결과를 바탕으로 영상 스크립트용 프롬프트 템플릿을 작성하세요.

## 스타일 분석 결과
{style_analysis}

## 요구사항
- 이 스타일의 영상 콘텐츠용 스크립트 생성 프롬프트
- 포함 요소:
  1. 오프닝 훅 스타일
  2. 본문 구성 패턴
  3. 시각적 요소 가이드 (B-roll, 그래픽 등)
  4. 톤/목소리 가이드
  5. 클로징/CTA 스타일
- YouTube/Shorts/TikTok 등 다양한 길이 대응
- Jinja2 템플릿 변수 활용 가능

프롬프트만 출력하세요:"""


def fetch_web_content(url: str) -> dict[str, Any]:
    """웹 URL에서 콘텐츠 수집"""
    import requests
    from bs4 import BeautifulSoup

    try:

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()

        # 주요 콘텐츠 추출
        text = soup.get_text(separator="\n", strip=True)

        # 줄바꿈 정리
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n".join(lines)

        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "content": content[:10000],  # 길이 제한
            "success": True,
        }
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {"url": url, "error": str(e), "success": False}


def fetch_multiple_urls(urls: list[str]) -> list[dict[str, Any]]:
    """여러 URL에서 콘텐츠 수집"""
    results = []
    for url in urls:
        logger.info(f"Fetching: {url}")
        result = fetch_web_content(url)
        if result.get("success"):
            results.append(result)
    return results


def analyze_style(client: Any, samples: list[str]) -> dict[str, Any]:
    """LLM으로 스타일 분석"""

    # 샘플 텍스트 결합
    combined_samples = "\n\n---\n\n".join([f"### 샘플 {i + 1}\n{s}" for i, s in enumerate(samples)])

    prompt = STYLE_ANALYSIS_PROMPT.format(samples=combined_samples)

    logger.info("Analyzing style patterns...")
    response = client.generate(
        prompt=prompt,
        system_prompt=STYLE_ANALYSIS_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=2000,
    )

    # JSON 추출
    try:
        # ```json 블록에서 추출 시도
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Response: {response}")
        return {"raw_response": response, "parse_error": str(e)}


def generate_prompts(client: Any, style_analysis: dict[str, Any]) -> dict[str, str]:
    """각 목적별 프롬프트 생성"""

    style_json = json.dumps(style_analysis, ensure_ascii=False, indent=2)

    prompts = {}

    # 글 작성용 프롬프트
    logger.info("Generating writing prompt...")
    prompts["writing"] = client.generate(
        prompt=WRITING_PROMPT_TEMPLATE.format(style_analysis=style_json),
        system_prompt=PROMPT_GENERATION_SYSTEM_PROMPT,
        temperature=0.5,
        max_tokens=2000,
    )

    # 이미지용 프롬프트
    logger.info("Generating image prompt...")
    prompts["image"] = client.generate(
        prompt=IMAGE_PROMPT_TEMPLATE.format(style_analysis=style_json),
        system_prompt=PROMPT_GENERATION_SYSTEM_PROMPT,
        temperature=0.5,
        max_tokens=1500,
    )

    # 영상용 프롬프트
    logger.info("Generating video prompt...")
    prompts["video"] = client.generate(
        prompt=VIDEO_PROMPT_TEMPLATE.format(style_analysis=style_json),
        system_prompt=PROMPT_GENERATION_SYSTEM_PROMPT,
        temperature=0.5,
        max_tokens=1500,
    )

    return prompts


def save_style_profile(
    output_dir: Path,
    name: str,
    source_urls: list[str],
    sample_count: int,
    style_analysis: dict[str, Any],
    prompts: dict[str, str],
) -> Path:
    """스타일 프로필 저장"""

    # 출력 디렉토리 생성
    style_dir = output_dir / name
    style_dir.mkdir(parents=True, exist_ok=True)

    # YAML 프로필 저장
    profile = {
        "name": name,
        "source_urls": source_urls,
        "analyzed_at": datetime.now().isoformat(),
        "sample_count": sample_count,
        "characteristics": style_analysis,
    }

    profile_path = style_dir / "profile.yml"
    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(profile, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    logger.info(f"Saved profile: {profile_path}")

    # 각 프롬프트 저장
    prompt_files = {
        "writing_prompt.md": prompts["writing"],
        "image_prompt.md": prompts["image"],
        "video_prompt.md": prompts["video"],
    }

    for filename, content in prompt_files.items():
        filepath = style_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved prompt: {filepath}")

    return style_dir


def main():
    parser = argparse.ArgumentParser(description="레퍼런스 콘텐츠에서 스타일 프롬프트 추출")
    parser.add_argument(
        "--urls",
        nargs="+",
        help="분석할 URL 목록",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="URL 목록이 담긴 파일 (한 줄에 하나씩)",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="스타일 이름 (예: tech_influencer, startup_founder)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="config/reference_styles",
        help="출력 디렉토리 (기본: config/reference_styles)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=10,
        help="분석할 최대 샘플 수 (기본: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장 없이 분석만 수행",
    )

    args = parser.parse_args()

    # URL 수집
    urls = []
    if args.urls:
        urls.extend(args.urls)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    if not urls:
        parser.error("URL을 제공해주세요 (--urls 또는 --file)")

    logger.info(f"Analyzing {len(urls)} URLs for style: {args.name}")

    # 콘텐츠 수집
    contents = fetch_multiple_urls(urls)
    if not contents:
        logger.error("수집된 콘텐츠가 없습니다.")
        sys.exit(1)

    # 샘플 제한
    samples = [c["content"] for c in contents[: args.max_samples]]

    # LLM 클라이언트 가져오기
    client = get_writer_client()

    # 스타일 분석
    style_analysis = analyze_style(client, samples)

    # 프롬프트 생성
    prompts = generate_prompts(client, style_analysis)

    # 결과 출력
    print("\n" + "=" * 60)
    print(f"스타일 분석 결과: {args.name}")
    print("=" * 60)
    print(f"\n분석된 샘플 수: {len(samples)}")
    print("\n## 스타일 특성:")
    print(yaml.dump(style_analysis, allow_unicode=True, default_flow_style=False))

    if not args.dry_run:
        # 저장
        output_dir = Path(args.output)
        style_dir = save_style_profile(
            output_dir=output_dir,
            name=args.name,
            source_urls=urls,
            sample_count=len(samples),
            style_analysis=style_analysis,
            prompts=prompts,
        )
        print(f"\n저장 완료: {style_dir}")
    else:
        print("\n[Dry-run] 저장하지 않음")

    print("\n## 글 작성 프롬프트 미리보기:")
    print("-" * 40)
    print(prompts["writing"][:500] + "...")


if __name__ == "__main__":
    main()
