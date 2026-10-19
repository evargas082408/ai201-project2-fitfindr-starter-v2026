"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import math
import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── search helpers ────────────────────────────────────────────────────────────

# Words that say nothing about the item. Without this, "looking for a tee"
# would need "looking" and "for" to match too.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "in", "of", "with", "to", "some",
    "looking", "want", "need", "find", "me", "my", "i", "something", "piece",
    "item", "size", "under", "over", "below", "less", "than", "max", "cheap",
}

# Same garment, different spelling. Applied after plurals are folded.
_SYNONYMS = {"tshirt": "tee", "jean": "jeans", "pant": "pants",
             "trouser": "trousers", "sneaker": "sneakers"}

_WORD_SIZES = {"SMALL": "S", "MEDIUM": "M", "LARGE": "L",
               "EXTRA SMALL": "XS", "EXTRA LARGE": "XL"}


def _words(text: str) -> list[str]:
    """Lowercase keywords with plurals folded: 'Jackets' -> 'jacket'."""
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower().replace("t-shirt", "tshirt")):
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(_SYNONYMS.get(w, w))
    return out


def normalize_size(size: str) -> str:
    """'medium' -> 'M', 'us 8' -> '8', 'w30' -> 'W30', 'm' -> 'M'."""
    s = size.strip().upper()
    s = _WORD_SIZES.get(s, s)
    return re.sub(r"^US\s*", "", s)


def size_tokens(listing_size: str) -> set[str]:
    """
    The sizes a listing's size string actually offers.

    'S/M' -> {'S','M'}, 'US 8.5' -> {'8.5'}, 'W30 L30' -> {'30','W30'},
    'XL (oversized)' -> {'XL'}, 'One Size' -> {'ONE SIZE'} (matches anything).
    The L30 in 'W30 L30' is an inseam, so it is removed before letter sizes
    are read — otherwise every pair of jeans would count as a size L.
    """
    s = listing_size.upper()
    if "ONE SIZE" in s:
        return {"ONE SIZE"}
    tokens = set()
    for waist in re.findall(r"\bW(\d+)", s):
        tokens |= {waist, "W" + waist}
    s = re.sub(r"\b[WL]\d+", " ", s)
    tokens |= set(re.findall(r"\b(?:XXXL|XXL|XL|XXS|XS|S|M|L)\b", s))
    tokens |= set(re.findall(r"\d+(?:\.\d+)?", s))
    return tokens


def size_matches(requested: str, listing_size: str) -> bool:
    """The size rule from the README's Tool Inventory: exact token match."""
    tokens = size_tokens(listing_size)
    return "ONE SIZE" in tokens or normalize_size(requested) in tokens


def _keyword_score(terms: list[str], listing: dict) -> tuple[int, int]:
    """(weighted score, how many distinct query terms matched)."""
    title = set(_words(listing["title"]))
    tags = set(_words(" ".join(listing["style_tags"])))
    rest = set(_words(" ".join([
        listing["description"], listing["category"],
        " ".join(listing["colors"]), listing.get("brand") or "",
    ])))
    score = matched = 0
    for t in set(terms):
        hit = 3 * (t in title) + 2 * (t in tags) + 1 * (t in rest)
        score += hit
        matched += hit > 0
    return score, matched


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    terms = [w for w in _words(description or "") if w not in _STOPWORDS]
    if not terms:
        return []
    # Two-thirds of the keywords, rounded up: "leather bomber" needs both
    # words, so a leather belt does not count as a bomber.
    needed = max(1, math.ceil(len(terms) * 2 / 3))

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not size_matches(size, listing["size"]):
            continue
        score, matched = _keyword_score(terms, listing)
        if matched >= needed:
            scored.append((score, listing))

    # Stable sort: equal scores keep file order, so the same query always
    # picks the same first result.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    if not new_item:
        return "No item to style."

    item = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item}\n\n"
            "They haven't told us what's in their closet. Suggest one or two "
            "outfits as general advice: name the KINDS of pieces to pair it "
            "with (e.g. 'straight-leg dark jeans', 'white sneakers'), colors "
            "that work, and the vibe. Don't pretend they own anything. "
            "Plain text, under 100 words, no headings."
        )
    else:
        closet = "\n".join(
            f"- {w['name']} ({w['category']}; {', '.join(w['colors'])}"
            + (f"; {w['notes']}" if w.get("notes") else "") + ")"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item}\n\n"
            f"Here is what they already own:\n{closet}\n\n"
            "Suggest one or two complete outfits built around the new piece, "
            "using ONLY pieces from their list, called by the names given. "
            "One line per outfit, then one sentence on why it works. "
            "Plain text, under 100 words, no headings."
        )

    reply = generate(prompt, system=_STYLIST).strip()
    return reply or "Couldn't come up with an outfit for this one — try again."


# ── shared by both model tools ────────────────────────────────────────────────

_STYLIST = (
    "You are a thrift-savvy stylist. You are specific and practical, and you "
    "never invent details about an item that aren't in its listing."
)


def _describe_item(item: dict) -> str:
    """One listing as prompt text. Brand is left out when it's None."""
    price = item.get("price")
    lines = [
        f"Title: {item.get('title')}",
        f"Category: {item.get('category')}",
        f"Size: {item.get('size')}",
        f"Condition: {item.get('condition')}",
        f"Price: ${price:g}" if isinstance(price, (int, float)) else "",
        f"Colors: {', '.join(item.get('colors') or [])}",
        f"Style: {', '.join(item.get('style_tags') or [])}",
        f"Platform: {item.get('platform')}",
        f"Brand: {item['brand']}" if item.get("brand") else "",
        f"Description: {item.get('description')}",
    ]
    return "\n".join(line for line in lines if line)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "Can't write a fit card without an outfit suggestion."

    price = new_item.get("price")
    price_text = f"${price:g}" if isinstance(price, (int, float)) else "the price"
    prompt = (
        f"The find:\n{_describe_item(new_item)}\n\n"
        f"How it'll be styled:\n{outfit}\n\n"
        "Write the caption for an Instagram/TikTok post about this thrift find. "
        "2 to 4 sentences, under 60 words, casual first person, like a real "
        "post — not a product description. Mention the item, the price written "
        f"exactly as {price_text}, and the platform ({new_item.get('platform')}) "
        "once each. Be specific about the vibe. At most two emoji and two "
        "hashtags. Return only the caption."
    )
    reply = generate(prompt, system=_STYLIST).strip()
    return reply or "Couldn't write a fit card this time — try again."
