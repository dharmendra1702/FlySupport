"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, next_available_day, record_tool_result,
                     runtime_preamble)

DATA_DIR = Path(__file__).resolve().parent / "data" / "americas"

def fare_rules(topic: str = "") -> Dict[str, Any]:
    """Read Larkspur's Customer Commitment & Fare Rules excerpt (Handbook v14.3, sections 4-7)."""
    text = (DATA_DIR / "fare_rules_excerpt.md").read_text(encoding="utf-8")
    if not topic:
        return {"source": "fare_rules_excerpt.md", "content": text}

    sections = text.split("\n### ")
    needle = topic.strip().lower()
    matched = [
        ("### " + s if not s.startswith("#") else s)
        for s in sections
        if needle in s.lower()
    ]
    if not matched:
        return {
            "source": "fare_rules_excerpt.md",
            "topic": topic,
            "note": "No section matched that specific keyword; returning full handbook excerpt.",
            "content": text,
        }
    return {
        "source": "fare_rules_excerpt.md",
        "topic": topic,
        "matched_sections": "\n\n".join(matched),
    }


def cause_in_plain_words(cause_code: str, language: str = "en") -> Dict[str, Any]:
    """Return the approved customer-facing wording for a disruption cause_code."""
    policy = json.loads((DATA_DIR / "disruption_policy.json").read_text(encoding="utf-8"))
    labels = policy.get("cause_labels_customer", {})
    code = cause_code.strip().upper()
    lang = language.strip().lower() or "en"

    if code not in labels:
        return {
            "found": False,
            "cause_code": code,
            "error": f"Unknown cause_code '{code}'. Valid codes: {', '.join(labels.keys())}",
        }

    entry = labels[code]
    plain_label = entry.get(lang) or entry.get("en")
    within_control = code in {"MX", "CREW"}
    return {
        "found": True,
        "cause_code": code,
        "language": lang if lang in entry else "en",
        "customer_label": plain_label,
        "within_airline_control": within_control,
    }


def ground_stop_status(airport: str = "DEN") -> Dict[str, Any]:
    """Check current ground stop status and remarks for an airport using bookings.json clock and flights.csv."""
    code = (airport or "DEN").strip().upper()
    bookings_data = json.loads((DATA_DIR / "bookings.json").read_text(encoding="utf-8"))
    now_str = bookings_data.get("fixture_clock", "")
    clock_note = bookings_data.get("fixture_clock_note", "")
    current_date = now_str.split("T")[0] if "T" in now_str else ""

    ground_stop_flights = []
    airport_flights_today = []
    with (DATA_DIR / "flights.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            remarks = (row.get("remarks") or "").strip()
            is_airport = row.get("origin") == code or row.get("dest") == code
            if is_airport and (not current_date or row.get("date") == current_date):
                airport_flights_today.append(row)
            if "ground stop" in remarks.lower() and (is_airport or code in remarks.upper()):
                ground_stop_flights.append({
                    "flight_no": row["flight_no"],
                    "route": f"{row['origin']}-{row['dest']}",
                    "date": row["date"],
                    "sched_dep_local": row["sched_dep_local"],
                    "status": row["status"],
                    "delay_min": row["delay_min"],
                    "remarks": remarks,
                })

    active = bool(ground_stop_flights) or (f"{code} ground stop" in clock_note)
    return {
        "airport": code,
        "current_time": now_str,
        "ground_stop_active": active,
        "estimated_end_time": None,
        "end_time_note": (
            "No end or lift time is listed in Larkspur's operational feed or flight remarks."
            if active else "No active ground stop recorded for this airport."
        ),
        "operational_note": clock_note if code in clock_note else "",
        "affected_flights_with_ground_stop_remarks": ground_stop_flights,
        "total_flights_checked_today": len(airport_flights_today),
    }


MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.

TONE_ADDENDUM = ""                       # ✏️ Build 4, step 4.1, intelligence goal
#EXTRA_TOOLS: List[Dict[str, Any]] = []   # ✏️ Build 2, step 2.1: schemas for the tools you add
#LOCAL_TOOLS: Dict[str, Any] = {}         # ✏️ Build 2, step 2.1: the functions behind them

EXTRA_TOOLS: List[Dict[str, Any]] = [
    # {
    #     "name": "next_available_day",
    #     "description": (
    #         "Find the earliest calendar date with at least one open seat on a Larkspur "
    #         "flight between an origin and destination airport starting from a given date. "
    #         "Use this when a customer asks 'when is the first day I can fly?' or asks for "
    #         "the earliest available travel date. Unlike search_alternatives (which only "
    #         "checks immediate rebooking options for a specific disrupted PNR), this searches "
    #         "across dates by city pair and cabin."
    #     ),
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {
    #             "origin": {"type": "string", "description": "3-letter IATA origin airport code, e.g. DEN"},
    #             "dest": {"type": "string", "description": "3-letter IATA destination airport code, e.g. AUS"},
    #             "date": {"type": "string", "description": "Earliest date to search from in YYYY-MM-DD format"},
    #             "cabin": {"type": "string", "enum": ["Y", "J"], "description": "Cabin code: Y for Main/Economy, J for First"},
    #         },
    #         "required": ["origin", "dest", "date"],
    #     },
    # },
    # {
    #     "name": "fare_rules",
    #     "description": (
    #         "Look up Larkspur Airlines' official Customer Commitment & Fare Rules Handbook "
    #         "(v14.3, sections 4 to 7) to explain the policy reasoning behind rules—such as "
    #         "why a hotel is or isn't covered, differences between Basic, Main, Main Plus, and "
    #         "First fares, meal/goodwill rules, or what chat automation cannot do. Unlike "
    #         "check_policy (which computes entitlements for one disrupted flight), use this "
    #         "when a customer asks 'why' a rule applies."
    #     ),
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {
    #             "topic": {
    #                 "type": "string",
    #                 "description": "Optional keyword or section topic to look up (e.g. 'hotel', 'Basic', 'Main', 'refund', 'goodwill')",
    #             }
    #         },
    #         "required": [],
    #     },
    # },
    {
        "name": "cause_in_plain_words",
        "description": (
            "Translate a flight disruption cause_code (WX, ATC, MX, CREW, SEC) into Larkspur's "
            "approved plain-language customer explanation from disruption_policy.json. Use this "
            "when a customer asks why their flight was delayed or cancelled in plain words they "
            "can understand or repeat. Distinct from get_flight_status, which returns raw codes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cause_code": {"type": "string", "description": "Disruption cause code such as WX, ATC, MX, CREW, or SEC"},
                "language": {"type": "string", "description": "Language code ('en' or 'es'), defaults to 'en'"},
            },
            "required": ["cause_code"],
        },
    },
    {
        "name": "ground_stop_status",
        "description": (
            "Check whether an airport (such as DEN) currently has an active ground stop and "
            "whether an end time is known, using Larkspur's operational clock and live flight "
            "remarks. Use this when a customer asks if an airport is still stopped or until when. "
            "Distinct from get_flight_status, which checks a single flight number."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "airport": {"type": "string", "description": "3-letter IATA airport code, e.g. DEN"},
            },
            "required": ["airport"],
        },
    },
]

LOCAL_TOOLS: Dict[str, Any] = {
    # "next_available_day": next_available_day,
    # "fare_rules": fare_rules,
    "cause_in_plain_words": cause_in_plain_words,
    "ground_stop_status": ground_stop_status,
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
                    "flight_no": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
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
                "properties": {"pnr": {"type": "string"}},
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
            "description": "Place a 15-minute hold on one alternative. Reversible. It simply expires.",
            "input_schema": {
                "type": "object",
                "properties": {"option_id": {"type": "string"}, "pnr": {"type": "string"}},
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
            "description": "Send the customer a written confirmation of what was just done. Benign.",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
