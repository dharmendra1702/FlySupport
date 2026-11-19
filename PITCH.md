# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A support agent for disrupted flights with Larkspur's nine tools, eight tools we wrote in agent.py (cause_in_plain_words, ground_stop_status, care_entitlements, reopen_stats, departures_in_window, seats_left, hold_time_left, what_automation_will_not_do), and next_available_day and fare_rules served over MCP.

Does: Looks up bookings, checks live flight status and policy entitlements, finds open seats and earliest travel days, holds a seat for 15 minutes and tells the customer how long the hold has left, and says plainly what the chat cannot do and hands those cases to a person.

Number: 61,081 to 73,840 tokens in, total across the five tickets (and the tool schemas now cost 5,486 tokens per turn with 19 tools, up from 3,260 with 13, counted by run.py --tool-tax).

Safety check: It places a 15-minute hold on a seat but never finalizes a rebooking without the customer's own Confirm-click token, verified in the trace for K7PQ2M.

Next: Turn on prompt caching to cut repeat input tokens across turns and add a tone guardrail for angry passengers.

Still broken: Every API turn resends the uncached conversation and full tool schemas, and next_available_day checks availability for a single passenger rather than a multi-passenger group.

Lever: <cost | speed | intelligence>

## Priya asked

Costs:
Wrong:
Runs it:
Left out: