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

Costs: About 6 cents per ticket, against the $6.90 a person costs today. That is modelled, not measured: 73,840 tokens in across the five tickets is about 14,770 per ticket, plus about 1,300 tokens out in our runs, at Sonnet list prices from bench.py. A proper per-customer figure comes from bench.py in the next session. The 19 tool schemas alone add 5,486 tokens to every turn.
Wrong: We find out by reading the wire trace of each run, which is how we caught Claude sending dates in the wrong format and the loop dropping its tool calls. We have no eval cases yet, so nothing catches a wrong answer automatically. What protects the customer today: the agent only holds a seat, and nothing is rebooked until the customer clicks Confirm; anything outside its remit goes to a person.
Runs it: Not decided yet, and it needs a named owner before launch. What it says comes from Larkspur's own files (the policy, the Handbook, the flight data), so whoever owns those at Larkspur should own the agent: watch the traces, fix the tool descriptions and update it when the policy changes.
Left out: What Handbook section 7 gives to people: refunds, fare-difference collection, hotel approval, other-airline rebooking, groups of 10 or more, unaccompanied minors, partner-operated flights, pets in cabin, medical requests and baggage tracing. The agent explains and hands over for those. We also did not build Spanish, a tone guardrail for angry passengers, group seat checks or prompt caching; we ran out of time.