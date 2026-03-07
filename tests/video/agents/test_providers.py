from picko.video.agents.providers import get_providers_for_mode, get_providers_for_mode_and_services


def test_get_providers_for_mode_filters_execution_mode() -> None:
    manual = get_providers_for_mode("manual_assisted")
    api = get_providers_for_mode("api")

    assert "sora_app" in manual
    assert "sora_api" not in manual
    assert "sora_api" in api
    assert "sora_app" not in api


def test_get_providers_for_mode_and_services_intersection() -> None:
    providers = get_providers_for_mode_and_services("manual_assisted", ["sora_app"])
    assert set(providers.keys()) == {"sora_app"}

    empty = get_providers_for_mode_and_services("manual_assisted", ["sora_api"])
    assert empty == {}


def test_get_providers_for_mode_and_services_empty_requested_services() -> None:
    providers = get_providers_for_mode_and_services("manual_assisted", [])
    mode_only = get_providers_for_mode("manual_assisted")
    assert providers == mode_only
