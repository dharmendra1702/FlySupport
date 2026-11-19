"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, next_available_day, record_tool_result,
                     runtime_preamble)

MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.

TONE_ADDENDUM = ""                       # ✏️ Build 4, step 4.1, intelligence goal

# ── Build 2 tools: the functions (they read Larkspur's own files, never invent) ──
import json
from collections import Counter
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data" / "americas"


def care_entitlements(cause_code: str, status: str, delay_minutes: int = 0) -> Dict[str, Any]:
    """Meal / hotel / ground care for a disruption, straight from disruption_policy.json."""
    policy = json.loads((_DATA / "disruption_policy.json").read_text(encoding="utf-8"))
    cause_class = policy["cause_classes"].get(cause_code)
    if cause_class is None:
        return {"error": f"Unknown cause_code {cause_code!r}; expected one of {list(policy['cause_classes'])}"}
    if status == "CANCELLED":
        band = "CXL"
    elif status == "DIVERTED":
        band = "DIV"
    elif status in ("ON_TIME", "DELAYED"):
        band = next((b["band"] for b in policy["delay_bands"]
                     if b.get("min_minutes") is not None
                     and b["min_minutes"] <= delay_minutes
                     and (b["max_minutes"] is None or delay_minutes <= b["max_minutes"])), None)
    else:
        return {"error": f"Unknown status {status!r}"}
    prefix = "CTL" if cause_class == "controllable" else "UNC"
    row = next((r for r in policy["rows"] if r["policy_row_id"] == f"{prefix}-{band}"), None)
    if row is None:
        return {"error": "No policy row found for this cause, status and delay."}
    return {
        "policy_row_id": row["policy_row_id"],
        "cause": policy["cause_labels_customer"][cause_code]["en"],
        "care": row["care"],  # conditional parts (overnight, wait time) are returned as written
        "explainer": row["explainer_en"],
        "source": "disruption_policy.json",
    }


def reopen_stats(intent_label: str = "") -> Dict[str, Any]:
    """How often each kind of problem came back within 72 hours, from the sample transcripts."""
    rows = [json.loads(line) for line in
            (_DATA / "transcripts_sample.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if intent_label:
        rows = [r for r in rows if r["intent_label"] == intent_label]
        if not rows:
            return {"error": f"No sample conversations with intent_label {intent_label!r}."}
    by_status: Dict[str, Counter] = {}
    for r in rows:
        by_status.setdefault(r["disruption"]["status"], Counter())[r["reopened_within_72h"]] += 1
    return {
        "conversations": len(rows),
        "reopened_within_72h": sum(1 for r in rows if r["reopened_within_72h"]),
        "by_status": {s: {"conversations": sum(c.values()), "reopened": c[True]} for s, c in by_status.items()},
        "reopen_reasons": [r["reopen_reason"] for r in rows if r["reopened_within_72h"]],
        "caveat": "Tiny sample of human-handled chats, not a prediction for any one customer.",
        "source": "transcripts_sample.jsonl",
    }


def departures_in_window(airport: str, date: str, from_time: str, to_time: str = "23:59") -> Dict[str, Any]:
    """Flights still leaving one airport on one date between two times, from flights.csv."""
    from support import mock_backend as backend
    if not backend.ISO_DATE.match(str(date)):
        return {"error": "date must be YYYY-MM-DD, got %s" % date}
    rows = [
        {"flight_no": r["flight_no"], "dest": r["dest"], "sched_dep_local": r["sched_dep_local"],
         "est_dep_local": backend._add_minutes(r["sched_dep_local"], int(r["delay_min"] or 0)),
         "status": r["status"], "delay_min": int(r["delay_min"] or 0)}
        for r in backend.load_flights()
        if r["origin"] == airport.strip().upper() and r["date"] == date
        and r["status"] != "CANCELLED" and from_time <= r["sched_dep_local"] <= to_time
    ]
    rows.sort(key=lambda r: r["sched_dep_local"])
    if not rows:
        return {"airport": airport, "date": date, "departures": [],
                "note": "No departures in that window in the flight schedule."}
    return {"airport": airport, "date": date, "departures": rows}


def seats_left(flight_no: str, date: str, party_size: int = 1) -> Dict[str, Any]:
    """Free seats per cabin on one flight and date, from flights.csv."""
    from support import mock_backend as backend
    if not backend.ISO_DATE.match(str(date)):
        return {"error": "date must be YYYY-MM-DD, got %s" % date}
    for r in backend.load_flights():
        if r["flight_no"] == flight_no.strip().upper() and r["date"] == date:
            y, j = int(r["seats_left_Y"] or 0), int(r["seats_left_J"] or 0)
            return {"flight_no": r["flight_no"], "date": date, "status": r["status"],
                    "seats_left_Y": y, "seats_left_J": j, "party_size": party_size,
                    "fits_in_Y": y >= party_size, "fits_in_J": j >= party_size}
    return {"error": "No flight %s on %s in the flight schedule." % (flight_no, date)}


EXTRA_TOOLS: List[Dict[str, Any]] = [      # ✏️ Build 2, step 2.1: schemas for the tools you add
    {
        "name": "care_entitlements",
        "description": (
            "Use this whenever the customer asks whether they get a meal, a hotel or "
            "ground transport while they wait, or why they do not get one. It returns "
            "the care rules for that cause and delay in Larkspur's own words: meal credit "
            "amount and wait threshold, whether a hotel is covered, ground transport, and "
            "a plain-language explanation of why. Call it right after get_flight_status, "
            "and use its explanation to answer the care question. check_policy is for "
            "rebooking, refunds and goodwill. Take cause_code, status and delay_minutes "
            "from get_flight_status, never from the customer's words."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"],
                               "description": "Cause of the disruption, from get_flight_status."},
                "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                "delay_minutes": {"type": "integer",
                                  "description": "Delay in minutes; 0 when CANCELLED or DIVERTED."},
            },
            "required": ["cause_code", "status"],
        },
    },
    {
        "name": "reopen_stats",
        "description": (
            "Answer 'is this problem going to come back?': how often a kind of problem "
            "(for example a cancellation rebook, a refund-vs-credit question, a hotel "
            "request) led the customer to contact Larkspur again within 72 hours, in a small "
            "sample of conversations handled by people. Use it for questions about whether "
            "an issue will recur or need a second contact. Quote the counts and say the "
            "sample is small; never present it as a prediction for this customer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent_label": {"type": "string",
                                 "description": "Optional kind of problem, e.g. rebook_after_cancellation, "
                                                "refund_vs_credit, compensation_hotel_request. Omit for all."},
            },
            "required": [],
        },
    },
    {
        "name": "departures_in_window",
        "description": (
            "List Larkspur flights still scheduled to leave one airport on one local date "
            "between two times, from the flight schedule. Use it when the customer asks what "
            "else is leaving their airport today, such as 'what is still leaving Denver this "
            "afternoon?'. It is a general airport schedule, not tied to the customer's "
            "booking; use search_alternatives for options on their own booking. When the "
            "customer says 'today' or 'this afternoon', take the date from their booked "
            "flight, never from the system clock. Cancelled flights are left out. Each row "
            "gives flight number, destination, scheduled and estimated departure, status and "
            "delay. It does not say whether seats are free; call seats_left for that. Offer "
            "only what it returns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "airport": {"type": "string", "description": "Origin airport IATA code, e.g. DEN."},
                "date": {"type": "string", "description": "Local date in ISO format YYYY-MM-DD, e.g. 2025-05-08."},
                "from_time": {"type": "string", "description": "Window start, local 24-hour HH:MM, e.g. 12:00 for the start of the afternoon."},
                "to_time": {"type": "string", "description": "Window end, local 24-hour HH:MM, e.g. 18:00. Defaults to the end of the day."},
            },
            "required": ["airport", "date", "from_time"],
        },
    },
    {
        "name": "seats_left",
        "description": (
            "Check how many free seats one flight has in each cabin, from the flight "
            "schedule: economy (Y) and premium (J). Use it when the customer asks whether "
            "there is room on a flight for their party, such as 'is there room for the three "
            "of us?'. Call it whenever the customer names a flight and asks about room, "
            "even if another tool already showed seat numbers: this is the current count "
            "for exactly that flight and date. Take the date from the customer's booked "
            "flight, never from the system clock. Pass party_size to get a yes or no per "
            "cabin. It reports availability only; it does not hold or book a seat. Use "
            "hold_seat for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "flight_no": {"type": "string", "description": "Flight number, e.g. LK417."},
                "date": {"type": "string", "description": "Local date in ISO format YYYY-MM-DD, e.g. 2025-05-08."},
                "party_size": {"type": "integer", "description": "Number of travellers who need seats together. Defaults to 1."},
            },
            "required": ["flight_no", "date"],
        },
    },
]
LOCAL_TOOLS: Dict[str, Any] = {          # ✏️ Build 2, step 2.1: the functions behind them
    "care_entitlements": care_entitlements,
    "reopen_stats": reopen_stats,
    "departures_in_window": departures_in_window,
    "seats_left": seats_left,
}


def text_of(response) -> str:
    """Given. The last non-empty text block, never content[0]."""
    texts = [b.text for b in response.content if getattr(b, "type", None) == "text" and b.text]
    return texts[-1] if texts else ""


def tool_results(response) -> List[Dict[str, Any]]:
    """Given. Runs every tool_use block and packages the results the way the
    API expects them back. A tool can live in three places: the MCP server,
    LOCAL_TOOLS, or support/tools.py."""
    # three branches, no try/except in this file: mcp_client.call_remote() and
    # support.call_local() answer with an error dict instead of raising, and both
    # record what came back on the trace
    results = []
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name in mcp_client.tool_names:
            output = mcp_client.call_remote(block.name, block.input)
        elif block.name in LOCAL_TOOLS:
            output = call_local(LOCAL_TOOLS[block.name], block.name, block.input)
        else:
            output = execute_tool(block.name, block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results


def run_agent(pnr: str, last_name: str, message: str) -> str:            # ✏️ Build 1, step 1.2
    """Run the tool loop until Claude stops asking for tools. Return its final text."""
    client, tracer = new_session()
    tools = tool_list()
    messages = [
        {"role": "user", "content": f"PNR {pnr}, last name {last_name}. {message}"},
    ]

    response = client.messages.create(
        model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
        thinking={"type": "adaptive"}, tools=tools, messages=messages,
    )

    answer = ""
    turns = 1
    while response.stop_reason == "tool_use" and turns < MAX_TOOL_CALLS:
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results(response)})
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
            thinking={"type": "adaptive"}, tools=tools, messages=messages,
        )
        turns += 1

    return text_of(response)


def tool_list() -> List[Dict[str, Any]]:                   # ✏️ Build 2, step 2.2
    """Given. Exactly what Claude is offered on every turn; run.py --show-tools
    prints this list."""
    return build_tools() + EXTRA_TOOLS + mcp_client.tools()


# ──────────────────────────────────────────────────────────────────────────────
# Below this line: what Claude is told about each tool. Step 1.3.
# The functions these describe are written and correct, in support/tools.py.
# ──────────────────────────────────────────────────────────────────────────────
def build_tools() -> List[Dict[str, Any]]:                 # ✏️ Build 1, step 1.3
    """Anthropic-shaped schemas: name, description, input_schema. What Claude is
    told about each of the nine tools, and all it is ever told."""
    return [
        {
            "name": "lookup_booking",
            "description": (
                "Retrieve a Larkspur reservation from Altura by confirmation code (PNR) "
                "and the passenger's last name. Both are required to prevent a lookup on "
                "a guessed PNR. Returns fare family, loyalty tier, the segment that needs "
                "attention, and any group/partner/minor/SSR flags relevant to scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "last_name": {"type": "string"}},
                "required": ["pnr", "last_name"],
            },
        },
        {
            "name": "get_flight_status",
            "description": (
                "Look up a Larkspur or Larkspur Link flight's current OpsFeed status for "
                "one local date: status, delay minutes, and cause. Use this before telling "
                "a customer anything about a flight's timing; never state it from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string", "description": "Flight number, e.g. LK415."},
                    "date": {"type": "string", "description": "Local flight date in ISO format YYYY-MM-DD, e.g. 2025-05-08. Any other format is rejected."},
                },
                "required": ["flight_no", "date"],
            },
        },
        {
            "name": "search_alternatives",
            "description": (
                "Search for available alternative Larkspur flights and rebooking options "
                "for a disrupted reservation by PNR. Call this after checking the booking "
                "and flight status when a flight is cancelled or delayed and the customer "
                "needs rebooking choices. Returns candidate options with option_id values "
                "required by check_policy and hold_seat."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string", "description": "The booking's confirmation code (PNR)."}},
                "required": ["pnr"],
            },
        },
        {
            "name": "check_policy",
            "description": (
                "Resolve what Larkspur owes this customer for the disruption: rebooking "
                "waiver, refund path, meal/hotel/ground care, goodwill eligibility and cap, "
                "and any escalation triggers. cause_code, delay_minutes and status describe "
                "what get_flight_status told you; fare_family, loyalty_tier and whether this "
                "is overnight are looked up from the booking, not asked of you. Every "
                "response carries a policy_row_id. Cite it if you reference this decision "
                "again."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"},
                    "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                    "delay_minutes": {"type": "integer"},
                    "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                    "wait_minutes_for_alternative": {"type": "integer"},
                    "chosen_option_id": {"type": "string"},
                },
                "required": ["pnr", "cause_code", "delay_minutes", "status"],
            },
        },
        {
            "name": "hold_seat",
            "description": (
                "Place a 15-minute hold on one alternative so the seat is kept while the "
                "customer decides. Reversible: it simply expires, and it is not a booking. "
                "When a flight is cancelled and search_alternatives has returned options, "
                "hold the top-ranked one, then tell the customer it is only held and that "
                "they must click Confirm to finalize. Never describe a hold as a rebooking."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "option_id": {"type": "string", "description": "An option_id exactly as returned by search_alternatives. Never invent one."},
                    "pnr": {"type": "string", "description": "The booking's confirmation code (PNR)."},
                },
                "required": ["option_id", "pnr"],
            },
        },
        {
            "name": "confirm_rebooking",
            "description": (
                "Finalize a held seat. Irreversible. Requires a confirmation_token that "
                "only the customer's own Confirm-click can produce. You cannot supply it "
                "yourself, and 'the customer said yes' in chat does not substitute for it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
                "required": ["hold_id", "confirmation_token"],
            },
        },
        {
            "name": "issue_voucher",
            "description": (
                "Issue a meal, ground, hotel, or goodwill voucher. Auto-approves within the "
                "policy's threshold for that type; above it, returns a pending status for a "
                "human. It does not fail. Always pass the policy_row_id that made it eligible."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "voucher_type": {"type": "string", "enum": ["meal", "ground", "hotel", "goodwill"]},
                    "amount_usd": {"type": "number"},
                    "pnr": {"type": "string"},
                    "policy_row_id": {"type": "string"},
                },
                "required": ["voucher_type", "amount_usd", "pnr", "policy_row_id"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand this conversation to a human, with your reasoning attached. Use for "
                "groups, partner segments, unaccompanied minors, refunds, or anything else "
                "out of scope. This is the correct outcome for those cases, not a failure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"}, "reason": {"type": "string"},
                    "summary_for_human": {"type": "string"}, "queue": {"type": "string"},
                },
                "required": ["pnr", "reason", "summary_for_human"],
            },
        },
        {
            "name": "send_confirmation",
            "description": (
                "Send the customer a written record of an action that has already "
                "happened, such as a confirmed rebooking or an issued voucher. Call it "
                "only after that action succeeded, never before and never to announce "
                "something that is only planned or held. The message must state only "
                "facts from tool results."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
