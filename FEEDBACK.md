# Client review: Larkspur disruption-care agent

**To:** Room 13  
**From:** Larkspur client review agent, on behalf of Priya Raghavan  
**Re:** the disruption-care agent you walked us through in our last session  
**Generated:** 2026-11-19 05:16

## Priya's note

> Our vendor says we should just be using your best model.
>
> Why aren't we?
>
> Priya Raghavan, Larkspur Airlines

She sent that before this session opened. She means it. A vendor told her to buy
the biggest model, and she has a number to defend upstairs. Her four questions from
day one are still open. Naming a model answers none of them.

## Still open from day one

| Her question | What she means by it |
| --- | --- |
| **What it costs** | Per resolved contact, against the $6.90 a human contact costs us. |
| **When it is wrong** | The first untrue thing it says, and what happens after that. |
| **Who runs it** | In June, after you have left. |
| **What you left out** | The scope you cut, and why. |

## What the review agent found

Larkspur pointed a review agent at your repository. It read the
code. It did not run your agent, and the only file it changed is this one. Each
item below names the file and the line it is about.

**1. PITCH.md reports 61,081 to 73,840 tokens in across five tickets, but readout-trace.json is one run of 17,841 tokens in.**

The only committed wire run is 4 API turns, 4 tool calls, 17,841 in and 812 out. There is no per-ticket breakdown anywhere in the material, and the pitch gives a range with no before or after. Nothing in the repository shows which run produced 61,081 or which produced 73,840.

Run python3 run.py --all --trace and paste the totals footer.

**2. PITCH.md says 3,260 schema tokens per turn with 13 tools; the scan finds 17 tool schemas in agent.py.**

EXTRA_TOOLS declares 8 and the pack ships 9, so the tool list sent each turn is 17 before mcp_client.tools() adds the MCP tools. The pitch's 13 matches neither count. Eight of your custom descriptions run 314 to 720 characters, with departures_in_window at 720.

Run python3 run.py --tool-tax and python3 run.py --show-tools and paste both outputs.

**3. No evals/cases.json exists, so none of the claims in PITCH.md has a case behind it.**

The safety line says a rebooking is never finalized without the customer's Confirm-click token, 'verified in the trace for K7PQ2M'. One trace on one booking is the whole basis. Banked gates are 1.2, 1.3, 1.4, 2.1, 2.2, which leaves 3.1 and 4.1 unbanked.

Run python3 verify.py 3.1 and python3 verify.py 4.1 and paste both results.

**4. agent.py run_agent() passes thinking={'adaptive'}, but readout-trace.json records thinking seen on the wire: False.**

Both create() calls carry thinking={"type": "adaptive"} and the committed run shows none. Any gap between a bigger model and your build has to be separated from that. The same run shows 0 cache read, 0 written, and cache_control appears nowhere in agent.py. Your Next line proposes turning caching on, and the committed run is the zero-cache baseline.

Run python3 bench.py --label before --stage 1 --runs 3 and paste the thinking and cache columns.

**5. MAX_TOOL_CALLS is 8 and run_agent() returns text_of(response) after the loop with no fallback if the cap is hit.**

The loop exits when turns reaches 8 even if stop_reason is still tool_use, and text_of() returns the last non-empty text block or an empty string. The committed run used 4 turns, so the cap was never reached. Your pitch says out-of-scope cases escalate, but nothing in the diff handles a capped loop.

Run python3 run.py --all --trace and paste the turn count per booking.

## Your four answers

The four lines under `## Priya asked` in your PITCH.md are still empty. They
are one line each and they are not a coding job: cost, what happens when it is
wrong, who runs it in June, and what you left out. Whoever on your side is not
editing agent.py is the right person to write them, and they are the four
things I will ask about first.

## Before our next meeting

> Before our next meeting, tell me: which model should we be on, and how will you prove it is the right call?
>
> Priya Raghavan, Larkspur Airlines

Bring two things. A recommendation, and the measurement behind it. If the model is
not the problem, say so, and bring the number that shows it.

## What this review read

- `agent.py (611 lines)`
- `PITCH.md`
- `TEAM.md`
- `readout-trace.json`
- `readout.html (evidence block)`
- given files that differ from the shipped pack: `verify.py`, `eval_harness.py`, `bench.py`, `readout.py`, `setup.py`, `pod_sync.py`, `run.py`, `review.py`, `support/__init__.py`, `support/client.py`, `support/data.py`, `support/models.py`, `support/tools.py`, `support/trace.py`, `support/offline.py`, `support/mock_backend.py`, `support/mcp_client.py`, `support/mcp_server.py`, `support/mcp_selftest.py`, `support/access.py`, `support/keyscan.py`, `support/review.py`

Reviewer: `claude-sonnet-5-5`. Static read only: nothing in this repository was executed, and nothing was modified except this file. Larkspur Airlines is a fictional training scenario. Confidential, do not distribute.
