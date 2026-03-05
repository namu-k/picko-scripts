# picko/account_inferrer.py
"""
Account Inferrer Module
AI-powered inference for account scoring and style configuration
"""

from dataclasses import dataclass


@dataclass
class AccountSeed:
    """Minimal account information for onboarding

    This is the input for AccountInferrer to generate
    scoring.yml and style.yml configurations.
    """

    account_id: str
    name: str
    description: str
    target_audience: list[str]
    channels: list[str]
    one_liner: str = ""  # One-sentence summary for the account
    tone_hints: list[str] | None = None
    reference_text: str | None = None
    reference_url: str | None = None
