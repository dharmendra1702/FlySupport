# PITCH.md

Built: Fixed the `run_agent` loop so tool calls don't crash or return blank text, switched `get_flight_status` to `YYYY-MM-DD`, and gave `search_alternatives` a clear description.

Does: Handles all 5 disruption ticket types end-to-end—checks bookings, live flight status, and policy rules, finds rebooking options, holds seats, and escalates edge cases.

Number: 5/5 tickets solved in 19 turns total (~12.2k input tokens and ~13s per chat) vs. $6.90 per human agent across 530,000 disrupted chats a year.

Safety check: Gated actions work—`confirm_rebooking` cannot fire without a customer's `confirmation_token`, and flight facts come strictly from live tools.

Next: Enable prompt caching to cut repeat input tokens, add extra tools/MCP data, and add a tone guardrail for angry passengers.

Still broken: Caching is off so every turn resends the full chat history (61,081 input tokens across 5 tickets), `TONE_ADDENDUM` is still empty (0 chars), and 0 custom tools are added yet.

Lever: cost

## Priya asked

Costs: About 12.2k input + 1k output tokens per chat (~$0.04–$0.05/chat, or ~$25k/year for 530k chats) compared to ~$3.66M/year for human agents at $6.90 each.

Wrong: Catch mistakes before customers see them using wire traces (`--trace`), automated `verify.py` checks, and a 5-ticket regression suite.

Runs it: Larkspur Ops and Engineering own it jointly—the agent clears routine disruptions and hands tricky cases straight to human queues.

Left out: Group bookings (like G2HL9V), partner flights, unaccompanied minors, refunds, and final booking commits (customer-click only).

## Most expensive turn

**Turn 4 (4,102 tokens in)** cost the most because every API call is stateless and resends the entire 7-message history, system prompt, and 9 tool schemas from scratch—to make the final turn cheaper than Turn 3, we need prompt caching on the repeated prefix.