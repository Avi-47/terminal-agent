from eval.run_task import run_task


class FakeAgent:
    def __init__(
        self,
        client,
        workspace,
        use_repo_context=True,
        enable_validation=True,
    ):
        self.workspace = workspace
        self.enable_validation = enable_validation
        self.telemetry = None

    def run(self, description):
        return "fake response"


def test_run_task_passes_validation_setting(tmp_path, monkeypatch):
    captured = {}

    class RecordingAgent:
        def __init__(
            self,
            client,
            workspace,
            use_repo_context=True,
            enable_validation=True,
            enable_reviewer=True,
        ):
            captured["enable_validation"] = enable_validation
            self.telemetry = None

        def run(self, description):
            return "fake response"

    task = {
        "task_id": "validation-setting-test",
        "description": "test task",
        "setup": {},
        "success_condition": {
            "type": "response_contains",
            "value": "fake response",
        },
    }

    run_task(
        task,
        client=None,
        agent_factory=RecordingAgent,
        enable_validation=False,
    )

    assert captured["enable_validation"] is False