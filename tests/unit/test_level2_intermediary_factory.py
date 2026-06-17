"""Level 2 intermediary factory tests."""

from trinityguard.level1_framework.a3s.adapter import A3SCodeMAS
from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
from trinityguard.level2_intermediary.factory import create_intermediary


class LocalFactoryMAS(BaseMAS):
    def get_agents(self):
        return []

    def get_agent(self, name):
        raise ValueError(name)

    def run_workflow(self, task: str, **kwargs):
        return WorkflowResult(success=True, output=task, messages=[])

    def get_topology(self):
        return {}


def test_create_intermediary_uses_local_intermediary_for_generic_base_mas():
    intermediary = create_intermediary(LocalFactoryMAS())

    assert intermediary.__class__.__name__ == "LocalMASIntermediary"


def test_create_intermediary_uses_a3s_intermediary_for_a3s_code_mas():
    class Session:
        def send(self, request):
            return {"text": request["prompt"]}

    intermediary = create_intermediary(A3SCodeMAS(session=Session(), workspace="/tmp/project"))

    assert intermediary.__class__.__name__ == "A3SIntermediary"
