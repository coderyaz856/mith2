"""FollowUpAgent: proposes research questions and directions for deeper exploration."""
from __future__ import annotations

from agents.base_agent import BaseAgent, default_agent_config


class FollowUpAgent(BaseAgent):
    """Proposes follow-up research questions based on previous findings.

    Role: Identifies gaps, proposes deeper questions, suggests new research directions.
    """

    def __init__(self) -> None:
        super().__init__(
            default_agent_config(
                role_name="followup",
                instructions=(
                    "Identify knowledge gaps, propose follow-up research questions, suggest methodologies, "
                    "and highlight connections among findings. Be specific and actionable."
                ),
            )
        )

    def role_prompt(self) -> str:  # noqa: D401
        return self.config.instructions

    def _build_prompt(self, input_text: str) -> str:
        return f"""You are a research strategist analyzing findings to identify knowledge gaps and propose follow-up research questions.

PREVIOUS FINDINGS AND DISCUSSION:
{input_text}

Your task:
1. **Identify Knowledge Gaps**: What important aspects remain unexplored or unclear?
2. **Propose Follow-up Questions**: Generate 3-5 specific, actionable research questions that would deepen understanding
3. **Suggest Research Directions**: Recommend methodologies, datasets, or approaches for addressing these questions
4. **Highlight Connections**: Identify potential relationships between findings that merit further investigation

Format your response as:
### Knowledge Gaps
- Gap 1
- Gap 2
...

### Follow-up Research Questions
1. Question focusing on [specific aspect]
2. Question addressing [particular gap]
...

### Recommended Research Directions
- Direction 1: [methodology/approach]
- Direction 2: [dataset/resource to explore]
...

### Potential Connections to Explore
- Connection between [finding X] and [finding Y]
...

Be specific, actionable, and prioritize questions that would have the most impact on advancing understanding of the topic."""

    def send(self, prompt: str):  # type: ignore[override]
        # Wrap upstream composite prompt with role instructions for clarity.
        full = (
            f"{self.role_prompt()}\n\n"
            f"=== PRIOR ANALYSIS ===\n{prompt}\n\n"
            f"=== TASK ===\nProduce gaps, questions, directions, connections in the specified format."
        )
        return super().send(full)
