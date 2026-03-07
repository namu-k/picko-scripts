from picko.video.agents.state import TerminalStatus, assert_shot_key_invariants, create_initial_state


def test_terminal_status_values() -> None:
    assert TerminalStatus.AUTO_APPROVED.value == "auto_approved"
    assert TerminalStatus.NEEDS_HUMAN_REVIEW.value == "needs_human_review"
    assert TerminalStatus.REVISE_REQUIRED.value == "revise_required"
    assert TerminalStatus.BLOCKED.value == "blocked"
    assert TerminalStatus.MAX_ITERATIONS_REACHED.value == "max_iterations_reached"


def test_create_initial_state_preserves_reserved_fields() -> None:
    state = create_initial_state(
        account_id="acct",
        intent="brand",
        services=["sora_app"],
        platforms=["instagram_reel"],
        execution_mode="manual_assisted",
        creative_brief={"account_id": "acct", "intent": "brand"},
        campaign_context={"campaign": "spring"},
        performance_hints=["hook_first_2s"],
        experiment_vars={"variant": "A"},
    )

    assert state["campaign_context"] == {"campaign": "spring"}
    assert state["performance_hints"] == ["hook_first_2s"]
    assert state["experiment_vars"] == {"variant": "A"}


def test_shot_key_invariants_pass_and_fail() -> None:
    state = create_initial_state(
        account_id="acct",
        intent="brand",
        services=["sora_app"],
        platforms=["instagram_reel"],
        execution_mode="manual_assisted",
        creative_brief={"account_id": "acct", "intent": "brand"},
    )

    state["shot_order"] = ["shot_1"]
    state["shots_by_id"] = {
        "shot_1": {
            "shot_id": "shot_1",
            "purpose": "hook",
            "scene_description": "Close up",
            "subject": "Creator",
            "setting": "room",
            "lighting": "soft",
            "camera_intent": "push_in",
            "duration_sec": 5.0,
        }
    }
    assert_shot_key_invariants(state)

    state["production_by_shot_id"] = {"shot_2": {"shot_id": "shot_2"}}
    try:
        assert_shot_key_invariants(state)
    except ValueError as exc:
        assert "production_by_shot_id" in str(exc)
    else:
        raise AssertionError("Expected invariant violation for mismatched shot keys")
