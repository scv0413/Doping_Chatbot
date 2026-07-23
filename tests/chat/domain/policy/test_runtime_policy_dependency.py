import subprocess
import sys


def test_runtime_policy_import_does_not_load_graph_module() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import app.chat.domain.policy.runtime_policy; "
                "print('app.chat.orchestration.graph.graph' in sys.modules or "
                "'app.chat.orchestration.graph.graph' in sys.modules)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "False"
