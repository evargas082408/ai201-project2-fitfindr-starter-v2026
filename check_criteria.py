#!/usr/bin/env python3
"""
Score a run_eval.py run against criteria.md. ← UNIT 4, MILESTONES 3-5

    python check_criteria.py results/run_<stamp>_before.json

run_eval.py leaves the PASS/FAIL cells blank on purpose, because what counts
as a pass is written in criteria.md and deciding it is my job. This is that
decision written down as code, so the exact same rule is applied to every try
and to both the before and after runs. Each check quotes the line of the
criterion it scores.

It prints the run-log table ready to paste, then why every FAIL failed.
"""

import json
import re
import sys
from collections import Counter, defaultdict

import config  # noqa: F401 — fixes the Windows console encoding, like every entry point

# The five queries criterion 5 names, and what each one states.
PARSE_EXPECTED = {
    "vintage graphic tee under $30": {"size": None, "max_price": 30.0},
    "90s track jacket in size M": {"size": "M", "max_price": None},
    "platform sneakers size 8": {"size": "8", "max_price": None},
    "denim jacket for less than 50 dollars": {"size": None, "max_price": 50.0},
    "chunky cardigan, size medium, max $40": {"size": "M", "max_price": 40.0},
}

TARGETS = {1: (4, "4 of 5"), 2: (5, "5 of 5"), 3: (5, "5 of 5"),
           4: (4, "4 of 5 + 4 different first sentences"), 5: (4, "4 of 5 queries")}

NAMES = {
    1: "Matching query completes all three tools",
    2: "Impossible query stops before tool 2",
    3: "Searched item is the item every later tool gets",
    4: "Fit card is postable and not a template",
    5: "Query's price and size parsed and respected",
}

_FALLBACKS = ("Can't write a fit card", "Couldn't write a fit card")


# ── one check per criterion: (passed, why) ────────────────────────────────────

def _tools(s):
    return [c["tool"] for c in s.get("tool_calls") or []]


def check_1(s):
    """completes all three tool calls and returns a fit card"""
    if s.get("error"):
        return False, f"stopped early: {s['error'][:70]}"
    card = s.get("fit_card") or ""
    if not card.strip() or card.startswith(_FALLBACKS):
        return False, f"no real fit card: {card!r}"
    if _tools(s) != ["search_listings", "suggest_outfit", "create_fit_card"]:
        return False, f"tools called: {_tools(s)}"
    return True, "3 tools, fit card returned"


def check_2(s):
    """stops before calling suggest_outfit and returns a message naming what to change"""
    if "suggest_outfit" in _tools(s) or s.get("fit_card") is not None:
        return False, f"went past search: {_tools(s)}"
    msg = (s.get("error") or "").lower()
    names_change = (re.search(r"budget to \$\d", msg) or re.search(r"try size \S", msg)
                    or "try other words" in msg)
    if not names_change:
        return False, f"message doesn't name a change: {msg[:70]!r}"
    return True, "stopped after search, names a change"


def check_3(s):
    """selected_item id == search_results[0] id == the id both later tools recorded"""
    ids = {
        "selected_item": (s.get("selected_item") or {}).get("id"),
        "search_results[0]": ((s.get("search_results") or [{}])[0]).get("id"),
    }
    for call in s.get("tool_calls") or []:
        if call["tool"] in ("suggest_outfit", "create_fit_card"):
            ids[call["tool"]] = call["item_id"]
    if len(ids) < 4 or None in ids.values() or len(set(ids.values())) != 1:
        return False, f"ids: {ids}"
    return True, f"all four are {ids['selected_item']}"


def _price_written(card, price):
    whole = float(price).is_integer()
    pattern = rf"\${int(price)}(?:\.00?)?(?!\d)" if whole else rf"\${price:.2f}"
    return re.search(pattern, card) is not None


def check_4(s):
    """(a) price as $ + number, (b) platform name, (c) 80 words or fewer"""
    card, item = s.get("fit_card") or "", s.get("selected_item") or {}
    if not card or not item:
        return False, "no fit card"
    misses = []
    if not _price_written(card, item["price"]):
        misses.append(f"no ${item['price']:g}")
    if item["platform"].lower() not in card.lower():
        misses.append(f"no '{item['platform']}'")
    words = len(card.split())
    if words > 80:
        misses.append(f"{words} words")
    return (not misses), ", ".join(misses) or f"${item['price']:g}, {item['platform']}, {words} words"


def first_sentence(card):
    return re.split(r"(?<=[.!?])\s+", card.strip())[0].strip().lower()


def _offers(listing_size, wanted):
    """The README's size rule, re-written here so the check isn't the filter checking itself."""
    s = listing_size.upper()
    if "ONE SIZE" in s:
        return True
    s = re.sub(r"\bL\d+", " ", s)  # 'L30' in 'W30 L30' is an inseam
    tokens = re.split(r"[^A-Z0-9.]+", s.replace("US", " "))
    return wanted in tokens or "W" + wanted in tokens


def check_5(s):
    """parsed holds exactly the stated max_price and size, and no result breaks either"""
    want = PARSE_EXPECTED.get(s.get("query"))
    got = s.get("parsed") or {}
    if want is None:
        return False, "not one of criterion 5's queries"
    if got.get("size") != want["size"] or got.get("max_price") != want["max_price"]:
        return False, f"parsed size={got.get('size')!r} max_price={got.get('max_price')!r}, wanted {want}"
    for r in s.get("search_results") or []:
        if want["max_price"] is not None and r["price"] > want["max_price"]:
            return False, f"{r['id']} costs ${r['price']:g}"
        if want["size"] and not _offers(r["size"], want["size"]):
            return False, f"{r['id']} is size {r['size']}"
    n = len(s.get("search_results") or [])
    return True, f"parsed right, {n} results all inside the limits"


CHECKS = {1: check_1, 2: check_2, 3: check_3, 4: check_4, 5: check_5}


# ── reading a run and printing the table ──────────────────────────────────────

def score(path):
    rows = json.loads(open(path, encoding="utf-8").read())
    by_criterion = defaultdict(list)
    for row in rows:
        number = row["scenario"].get("criterion")
        if number:
            by_criterion[number].append(row)

    table, notes = [], []
    for number in sorted(CHECKS):
        needed, target = TARGETS[number]
        results, extra = [], ""

        if number == 5:
            # One column per query. A query passes only if all five of its
            # runs pass — the filtering has no randomness, so one bad run is a bug.
            for row in by_criterion[number]:
                runs = [_run(CHECKS[5], t) for t in row["tries"]]
                ok = all(p for p, _ in runs)
                results.append((ok, f"{row['scenario']['query']!r}: "
                                    f"{sum(p for p, _ in runs)}/{len(runs)} runs — {runs[0][1]}"))
        else:
            for t in by_criterion[number][0]["tries"]:
                results.append(_run(CHECKS[number], t))

        passes = sum(p for p, _ in results)
        met = passes >= needed
        if number == 4:
            cards = [(t["session"] or {}).get("fit_card") or "" for t in by_criterion[4][0]["tries"]]
            firsts = [first_sentence(c) for c in cards if c]
            openers = [" ".join(f.split()[:2]) for f in firsts]
            distinct = len(set(firsts))
            met = met and distinct >= 4
            extra = (f"{distinct} different first sentences; opening words: "
                     + ", ".join(f"'{o}'" for o in openers))
            # Revised in unit 4 (see criteria.md): "different first sentences"
            # passed cards that differed by one word, so the template check is
            # now on the opening two words.
            top, top_count = Counter(openers).most_common(1)[0]
            revised = passes >= needed and top_count <= 2
            extra += (f"\n  revised criterion 4: {top_count} of {len(openers)} open with "
                      f"'{top}' (allowed: 2) — {'MET' if revised else 'MISSED'}")

        cells = " | ".join("PASS" if p else "FAIL" for p, _ in results)
        verdict = f"{'MET' if met else 'MISSED'} ({passes}/{len(results)})"
        table.append(f"| {number}. {NAMES[number]} | {target} | {cells} | {verdict} |")

        notes.append(f"\nCriterion {number}: {verdict}")
        for i, (p, why) in enumerate(results, 1):
            notes.append(f"  try {i}: {'PASS' if p else 'FAIL'} — {why}")
        if extra:
            notes.append(f"  {extra}")

    print("| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |")
    print("|---|---|---|---|---|---|---|---|")
    print("\n".join(table))
    print("\n".join(notes))


def _run(check, attempt):
    if attempt["crashed"]:
        return False, f"crashed: {attempt['crashed'][:70]}"
    return check(attempt["session"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python check_criteria.py results/run_<stamp>_<label>.json")
    score(sys.argv[1])
