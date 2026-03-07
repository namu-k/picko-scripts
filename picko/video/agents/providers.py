from dataclasses import dataclass


@dataclass
class ProviderCapability:
    provider_id: str
    display_name: str
    execution_modes: list[str]
    supported_ratios: list[str]
    supported_durations: list[float]
    max_duration_per_clip: float
    supports_start_image: bool
    supports_end_image: bool
    supports_reference_image: bool
    supports_first_last_frame: bool
    native_audio: bool
    post_audio_api: bool


PROVIDER_CAPABILITIES: dict[str, ProviderCapability] = {
    "sora_app": ProviderCapability(
        provider_id="sora_app",
        display_name="Sora (App)",
        execution_modes=["manual_assisted"],
        supported_ratios=["9:16", "16:9", "1:1"],
        supported_durations=[5, 10, 15, 20],
        max_duration_per_clip=20.0,
        supports_start_image=True,
        supports_end_image=False,
        supports_reference_image=False,
        supports_first_last_frame=False,
        native_audio=False,
        post_audio_api=False,
    ),
    "sora_api": ProviderCapability(
        provider_id="sora_api",
        display_name="Sora (API)",
        execution_modes=["api"],
        supported_ratios=["9:16", "16:9", "1:1"],
        supported_durations=[4, 6, 8],
        max_duration_per_clip=12.0,
        supports_start_image=True,
        supports_end_image=False,
        supports_reference_image=False,
        supports_first_last_frame=True,
        native_audio=True,
        post_audio_api=True,
    ),
}


def get_providers_for_mode(execution_mode: str) -> dict[str, ProviderCapability]:
    return {
        provider_id: capability
        for provider_id, capability in PROVIDER_CAPABILITIES.items()
        if execution_mode in capability.execution_modes
    }


def get_providers_for_mode_and_services(
    execution_mode: str,
    requested_services: list[str],
) -> dict[str, ProviderCapability]:
    mode_providers = get_providers_for_mode(execution_mode)
    if not requested_services:
        return mode_providers
    requested = set(requested_services)
    return {provider_id: capability for provider_id, capability in mode_providers.items() if provider_id in requested}
