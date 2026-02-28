from unittest.mock import MagicMock

from scripts import style_extractor as se


def test_fetch_web_content_success(monkeypatch):
    response = MagicMock()
    response.text = "<html><head><title>T</title></head><body><p>Hello</p><script>x</script></body></html>"
    response.raise_for_status.return_value = None

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: response)

    result = se.fetch_web_content("https://example.com")
    assert result["success"] is True
    assert result["title"] == "T"
    assert "Hello" in result["content"]


def test_fetch_multiple_urls_keeps_only_success(monkeypatch):
    monkeypatch.setattr(
        "scripts.style_extractor.fetch_web_content",
        lambda url: {"url": url, "content": "x", "success": url.endswith("ok")},
    )
    results = se.fetch_multiple_urls(["https://a-ok", "https://b-fail"])
    assert len(results) == 1


def test_analyze_style_parses_json_block():
    client = MagicMock()
    client.generate.return_value = '```json\n{"tone":["casual"]}\n```'

    result = se.analyze_style(client, ["sample"])
    assert result["tone"] == ["casual"]


def test_analyze_style_returns_parse_error_on_invalid_json():
    client = MagicMock()
    client.generate.return_value = "not-json"

    result = se.analyze_style(client, ["sample"])
    assert "parse_error" in result
    assert "raw_response" in result


def test_generate_prompts_calls_client_three_times():
    client = MagicMock()
    client.generate.side_effect = ["w", "i", "v"]

    prompts = se.generate_prompts(client, {"tone": ["plain"]})

    assert prompts == {"writing": "w", "image": "i", "video": "v"}
    assert client.generate.call_count == 3


def test_save_style_profile_writes_profile_and_prompt_files(tmp_path):
    style_dir = se.save_style_profile(
        output_dir=tmp_path,
        name="founder_style",
        source_urls=["https://x"],
        sample_count=1,
        style_analysis={"tone": ["direct"]},
        prompts={"writing": "W", "image": "I", "video": "V"},
    )

    assert style_dir == tmp_path / "founder_style"
    assert (style_dir / "profile.yml").exists()
    assert (style_dir / "writing_prompt.md").read_text(encoding="utf-8") == "W"
    assert (style_dir / "image_prompt.md").read_text(encoding="utf-8") == "I"
    assert (style_dir / "video_prompt.md").read_text(encoding="utf-8") == "V"
