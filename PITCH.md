# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A support agent for disrupted flights with Larkspur's nine tools, our custom tools in agent.py, and next_available_day and fare_rules served over MCP.

Does: Looks up bookings, checks live flight status and policy entitlements, finds open seats and earliest travel days, holds a seat for 15 minutes, and escalates out-of-scope cases.

Number: 61,081 to 73,840 tokens in, total across the five tickets (and 3,260 schema tokens per turn with 13 tools).

Safety check: It places a 15-minute hold on a seat but never finalizes a rebooking without the customer's own Confirm-click token, verified in the trace for K7PQ2M.

Next: Turn on prompt caching to cut repeat input tokens across turns and add a tone guardrail for angry passengers.

Still broken: Every API turn resends the uncached conversation and full tool schemas, and next_available_day checks availability for a single passenger rather than a multi-passenger group.

Lever: <cost | speed | intelligence>

## Priya asked

Costs:
Wrong:
Runs it:
Left out: