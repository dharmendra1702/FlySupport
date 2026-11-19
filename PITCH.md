# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A support agent for disrupted flights with Larkspur's nine tools, eight tools we wrote in agent.py (cause_in_plain_words, ground_stop_status, care_entitlements, reopen_stats, departures_in_window, seats_left, hold_time_left, what_automation_will_not_do), and next_available_day and fare_rules served over MCP.

Does: Looks up bookings, checks live flight status and policy entitlements, finds open seats and earliest travel days, holds a seat for 15 minutes and tells the customer how long the hold has left, and says plainly what the chat cannot do and hands those cases to a person.

Number: $0.0344 to $0.0322 model cost per contact (-6%), average of 15 conversations (5 ticket types, 3 runs each), from bench.py before and after caching the conversation; an identical first run gave $0.0313 (-9%). Uncached input tokens per contact went from 3,963 to 11 and the cache hit rate from 86% to 93%.

Safety check: It places a 15-minute hold on a seat but never finalizes a rebooking without the customer's own Confirm-click token, verified in the trace for K7PQ2M.

Next: Add a tone guardrail for angry passengers, then trim overlapping tool descriptions to cut the schema tokens sent on every turn.

Still broken: An abusive message with a legal threat (tone-0101) still gets a normal entitlements answer and a voucher instead of an escalation, and next_available_day checks availability for a single passenger rather than a multi-passenger group.

Lever: cost

## Priya asked

Costs: About 3 cents of model cost per contact ($0.0322), against the $6.90 a person costs today. That is measured by bench.py over 15 conversations (5 ticket types, 3 runs each) with the tool schemas, system prompt and conversation all cached: $0.0344 before caching the conversation (a 6 to 9% saving across two runs, short of the 10% we aimed for), and about $0.10 before any caching in our earlier bench. Model cost only, not the loaded cost. Speed did not change (p50 about 10 seconds either way).
Wrong: We find out by reading the wire trace of each run, which is how we caught Claude sending dates in the wrong format and the loop dropping its tool calls. We now have 11 eval cases (9 of them hard gates) and the agent passes 7 to 9 of them across runs; it reliably fails the abusive-message case (it never escalates) and the unclear-booking case (no apology). What protects the customer today: the agent only holds a seat, and nothing is rebooked until the customer clicks Confirm; anything outside its remit goes to a person.
Runs it: Not decided yet, and it needs a named owner before launch. What it says comes from Larkspur's own files (the policy, the Handbook, the flight data), so whoever owns those at Larkspur should own the agent: watch the traces, fix the tool descriptions and update it when the policy changes.
Left out: What Handbook section 7 gives to people: refunds, fare-difference collection, hotel approval, other-airline rebooking, groups of 10 or more, unaccompanied minors, partner-operated flights, pets in cabin, medical requests and baggage tracing. The agent explains and hands over for those. We also did not build Spanish, a tone guardrail for angry passengers or group seat checks; we ran out of time.