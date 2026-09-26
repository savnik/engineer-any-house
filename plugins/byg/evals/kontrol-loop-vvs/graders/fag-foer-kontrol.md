---
type: tool_order
before:
  tool: Agent
  input_match: '"subagent_type"\s*:\s*"(?:[\w-]+:)?vvs-mester"'
after:
  tool: Agent
  input_match: '"subagent_type"\s*:\s*"(?:[\w-]+:)?vvs-kontrol"'
arm: with-only
---
