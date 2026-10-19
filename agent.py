"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card, normalize_size
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "tool_calls": [],            # {"tool", "item_id"} per call, in order
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # The loop picks its next step from what the last one returned. The only
    # fork is after search: results → select, nothing → explain and stop.
    next_step = "parse"
    count = 0
    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = parse_query(query)
            next_step = "search"

        elif next_step == "search":
            p = session["parsed"]
            _log_call(session, "search_listings", None)
            session["search_results"] = search_listings(
                p["description"], p["size"], p["max_price"]
            )
            # THE BRANCH: an empty list never reaches suggest_outfit.
            next_step = "select" if session["search_results"] else "explain_empty"

        elif next_step == "explain_empty":
            session["error"] = explain_empty(session["parsed"])
            next_step = "done"

        elif next_step == "select":
            session["selected_item"] = session["search_results"][0]
            next_step = "suggest"

        elif next_step == "suggest":
            item = session["selected_item"]
            _log_call(session, "suggest_outfit", item)
            session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            next_step = "card"

        elif next_step == "card":
            item = session["selected_item"]
            _log_call(session, "create_fit_card", item)
            session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
            next_step = "done"

    return session


def _log_call(session: dict, tool: str, item: dict | None) -> None:
    """Record which listing each tool was handed — criterion 3 checks this."""
    session["tool_calls"].append(
        {"tool": tool, "item_id": item.get("id") if item else None}
    )


# ── parsing the query ─────────────────────────────────────────────────────────

_NUM = r"(\d+(?:\.\d+)?)"
_PRICE_PATTERNS = [
    rf"(?:under|below|less than|max(?:imum)?|up to|at most|<)\s*\$?\s*{_NUM}(?:\s*(?:dollars|bucks))?",
    rf"\${_NUM}",
    rf"{_NUM}\s*(?:dollars|bucks)",
]
_SIZE_PATTERN = (
    r"\b(?:in\s+)?size\s*:?\s*"
    r"(extra small|extra large|small|medium|large|xxxl|xxl|xl|xxs|xs|s|m|l"
    r"|(?:us\s*)?\d+(?:\.\d+)?|w\d+)\b"
)


def parse_query(query: str) -> dict:
    """
    Pull description / size / max_price out of plain text, with regex.

    'vintage graphic tee under $30, size M'
        → {'description': 'vintage graphic tee', 'size': 'M', 'max_price': 30.0}

    Anything not stated comes back as None. What's left after the price and
    size are cut out is the description.
    """
    text = query.strip()

    max_price = None
    for pattern in _PRICE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            max_price = float(m.group(1))
            text = text[: m.start()] + " " + text[m.end():]
            break

    size = None
    m = re.search(_SIZE_PATTERN, text, re.IGNORECASE)
    if m:
        size = normalize_size(m.group(1))
        text = text[: m.start()] + " " + text[m.end():]

    description = re.sub(r"[^\w\s'-]", " ", text)
    description = re.sub(r"\s+", " ", description).strip()
    return {"description": description, "size": size, "max_price": max_price}


# ── the empty branch's message ────────────────────────────────────────────────

def explain_empty(parsed: dict) -> str:
    """
    Work out WHICH part of the request emptied the search, and say what to
    change. Re-runs search_listings with each filter dropped — still no model
    call, so this path stays deterministic.
    """
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]
    asked = f"'{desc}'" + (f" in size {size}" if size else "") + (
        f" under ${price:g}" if price is not None else "")

    any_size_any_price = search_listings(desc)
    if not any_size_any_price:
        return (
            f"Nothing in the listings matches {asked}. No item matches those "
            f"words at any size or price, so changing the size or budget won't "
            f"help. Try other words: name "
            f"the kind of item (tee, jacket, jeans, sneakers, cardigan) or a "
            f"style (vintage, y2k, grunge, cottagecore, 90s)."
        )

    # Is it the budget? Keep the size, drop the price.
    if price is not None:
        right_size = search_listings(desc, size) if size else any_size_any_price
        if right_size:
            cheapest = min(right_size, key=lambda l: l["price"])
            return (
                f"Nothing matches {asked}. The cheapest match"
                + (f" in size {size}" if size else "")
                + f" is {cheapest['title']} at ${cheapest['price']:g} — raise "
                f"your budget to ${cheapest['price']:g} to see it."
            )

    # Is it the size? Keep the price, drop the size.
    if size:
        in_budget = search_listings(desc, None, price) if price is not None else any_size_any_price
        if in_budget:
            sizes = sorted({l["size"] for l in in_budget})[:4]
            return (
                f"Nothing matches {asked}. The matches"
                + (f" under ${price:g}" if price is not None else "")
                + f" come in {', '.join(sizes)} — try size "
                f"{sizes[0]}, or leave the size out."
            )

    # Both at once.
    closest = min(any_size_any_price, key=lambda l: l["price"])
    return (
        f"Nothing matches {asked}, and changing just the size or just the budget "
        f"isn't enough. The closest is {closest['title']} in size "
        f"{closest['size']} at ${closest['price']:g} — try size "
        f"{closest['size']} with a budget of ${closest['price']:g}."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
