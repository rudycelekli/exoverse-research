"""Harbor adapters for the frozen deterministic retrieval policies."""

from harbor.agents.base import BaseAgent


class Direct(BaseAgent):
    policy = "direct"

    @classmethod
    def name(cls):
        return cls.policy

    def version(self):
        return "1"

    async def setup(self, environment):
        pass

    async def run(self, instruction, environment, context):
        result = await environment.exec(command=f"cd /app && python3 policy.py {self.policy}")
        if result.return_code != 0:
            raise RuntimeError("Retrieval policy did not produce answers.")


class Grounded(Direct):
    policy = "grounded"
