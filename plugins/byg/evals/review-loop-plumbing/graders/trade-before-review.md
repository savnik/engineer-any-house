---
type: tool_order
before:
  tool: Agent
  input_match: '"subagent_type"\s*:\s*"(?:[\w-]+:)?plumber"'
after:
  tool: Agent
  input_match: '"subagent_type"\s*:\s*"(?:[\w-]+:)?plumbing-review"'
arm: with-only
---
