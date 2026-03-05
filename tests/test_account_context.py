from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

import pytest

import picko.account_context as account_context_module
from picko.account_context import AccountContextLoader


def _mock_config(profiles: Mapping[str, Mapping[str, object]]) -> SimpleNamespace:
    def get_account(account_id: str) -> Mapping[str, object]:
        return profiles.get(account_id, {})

    return SimpleNamespace(
        vault=SimpleNamespace(root="unused"),
        accounts_dir="config/accounts",
        get_account=get_account,
    )


class TestAccountContextLoaderYaml:
    def test_load_identity_reads_identity_block_from_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        profiles = {
            "test_account": {
                "identity": {
                    "one_liner": "Test one liner",
                    "target_audience": ["audience1", "audience2"],
                    "value_proposition": "Test value",
                    "pillars": ["P1: Test"],
                    "tone_voice": {"tone": "friendly"},
                    "boundaries": ["No spam"],
                    "bio": "Bio",
                    "bio_secondary": "Bio 2",
                    "link_purpose": "CTA",
                }
            }
        }
        monkeypatch.setattr(account_context_module, "get_config", lambda: _mock_config(profiles))

        loader = AccountContextLoader(tmp_path)
        identity = loader.load_identity("test_account")

        assert identity is not None
        assert identity.account_id == "test_account"
        assert identity.one_liner == "Test one liner"
        assert identity.target_audience == ["audience1", "audience2"]
        assert identity.value_proposition == "Test value"
        assert identity.pillars == ["P1: Test"]
        assert identity.tone_voice == {"tone": "friendly"}
        assert identity.boundaries == ["No spam"]
        assert identity.bio == "Bio"
        assert identity.bio_secondary == "Bio 2"
        assert identity.link_purpose == "CTA"

    def test_load_identity_falls_back_to_legacy_top_level_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        profiles = {
            "legacy_account": {
                "one_liner": "Legacy one liner",
                "target_audience": ["legacy target"],
                "value_proposition": "Legacy value",
                "pillars": ["P1: Legacy"],
                "tone_voice": {"tone": "direct"},
                "boundaries": ["No hype"],
                "bio": "Legacy bio",
                "bio_secondary": "Legacy bio 2",
                "link_purpose": "Legacy link",
            }
        }
        monkeypatch.setattr(account_context_module, "get_config", lambda: _mock_config(profiles))

        loader = AccountContextLoader(tmp_path)
        identity = loader.load_identity("legacy_account")

        assert identity is not None
        assert identity.account_id == "legacy_account"
        assert identity.one_liner == "Legacy one liner"
        assert identity.target_audience == ["legacy target"]
        assert identity.tone_voice == {"tone": "direct"}

    def test_load_weekly_slot_reads_weekly_slot_block(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        profiles = {
            "test_account": {
                "identity": {
                    "one_liner": "Test one liner",
                    "target_audience": [],
                    "value_proposition": "",
                    "pillars": [],
                    "tone_voice": {},
                    "boundaries": [],
                },
                "weekly_slot": {
                    "customer_outcome": "Test outcome",
                    "operator_kpi": "Test KPI",
                    "cta": "Test CTA",
                    "pillar_distribution": {"P1": 2, "P2": 2, "P3": 2, "P4": 1},
                },
            }
        }
        monkeypatch.setattr(account_context_module, "get_config", lambda: _mock_config(profiles))

        loader = AccountContextLoader(tmp_path)
        _ = loader.load_identity("test_account")
        weekly_slot = loader.load_weekly_slot("2026-03-02")

        assert weekly_slot is not None
        assert weekly_slot.week_of == "2026-03-02"
        assert weekly_slot.account_id == "test_account"
        assert weekly_slot.customer_outcome == "Test outcome"
        assert weekly_slot.operator_kpi == "Test KPI"
        assert weekly_slot.cta == "Test CTA"
        assert weekly_slot.pillar_distribution == {"P1": 2, "P2": 2, "P3": 2, "P4": 1}

    def test_load_weekly_slot_returns_none_when_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        profiles = {
            "test_account": {
                "identity": {
                    "one_liner": "Test one liner",
                    "target_audience": [],
                    "value_proposition": "",
                    "pillars": [],
                    "tone_voice": {},
                    "boundaries": [],
                }
            }
        }
        monkeypatch.setattr(account_context_module, "get_config", lambda: _mock_config(profiles))

        loader = AccountContextLoader(tmp_path)
        _ = loader.load_identity("test_account")
        weekly_slot = loader.load_weekly_slot("2026-03-02")

        assert weekly_slot is None

    def test_load_style_profile_unchanged(self, temp_vault_dir: Path):
        style_dir = temp_vault_dir / "config" / "reference_styles" / "test_style"
        style_dir.mkdir(parents=True)
        profile_file = style_dir / "profile.yml"
        profile_file.write_text(
            """
name: test_style
source_urls:
  - https://example.com
analyzed_at: '2026-02-16T00:00:00'
sample_count: 5
characteristics:
  tone:
    - casual
    - friendly
  sentence_style: short
""",
            encoding="utf-8",
        )

        loader = AccountContextLoader(temp_vault_dir)
        style = loader.load_style_profile("test_style")

        assert style is not None
        assert style.name == "test_style"
        assert style.sample_count == 5
        assert style.characteristics["tone"] == ["casual", "friendly"]
