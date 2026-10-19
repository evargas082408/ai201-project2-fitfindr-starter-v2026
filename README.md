# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

You type what you're hunting for in plain words — "a vintage graphic tee under
$30, size M" — and FitFindr searches 40 thrift listings from Depop, thredUp and
Poshmark for it, filtering on keywords, size and price. If something matches, it
takes the best match, works out one or two outfits built from pieces already in
your wardrobe, and writes a short caption you could actually post with the find.
If nothing matches, it stops before the outfit step and tells you which part of
your request to change (the budget, the size, or the words).

Data notes from Milestone 1: a listing has `id`, `title`, `description`,
`category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors`
(list), `brand` (usually `None`), and `platform`. Sizes come in four shapes:
letters (`M`, `S/M`, `XL (oversized)`), shoe sizes (`US 8.5`), waist/inseam
(`W30 L30`, `W28`) and `One Size`. A wardrobe is `{"items": [...]}`, each item
with `id`, `name`, `category`, `colors`, `style_tags`, `notes`; an empty
wardrobe is `{"items": []}`.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters the 40 listings by price ceiling and size, then ranks what's left by how many of the query's keywords appear in each listing's title, style tags, description, colors, category and brand. No model call.
- **Inputs:** `description` (str) — keywords, e.g. `"vintage graphic tee"`; `size` (str or None) — e.g. `"M"`, `"8"`, `"W30"`, `None` skips the size filter; `max_price` (float or None) — inclusive ceiling in dollars, `None` skips the price filter.
- **Returns:** A `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) full listing dicts, best match first. Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`. A listing is kept only if it matches at least two-thirds (rounded up) of the query's keywords after filler words are dropped, so both words of `leather bomber` have to match. **Size rule:** the listing's size string is split into size tokens — letter sizes (`S/M` → `S`, `M`), shoe numbers (`US 8.5` → `8.5`), waists (`W30 L30` → `30`/`W30`; the `L30` inseam is *not* read as size L). The requested size matches if it equals one of those tokens exactly, so `M` matches `S/M` and `M/L` but `S` does not match `US 9` and `L` does not match `XL`. `One Size` listings match any requested size. `small`/`medium`/`large` are read as `S`/`M`/`L`.
- **When it has nothing:** An empty list `[]` — never `None`, never an exception. That empty list is what the loop branches on.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, naming specific pieces from the user's wardrobe.
- **Inputs:** `new_item` (dict) — one listing dict, as returned by `search_listings`; `wardrobe` (dict) — `{"items": [wardrobe item dicts]}`, where `items` may be empty.
- **Returns:** A non-empty `str` of plain text: one or two outfits, each a short line naming the new item plus pieces from the wardrobe by their `name`, and a sentence on why they work.
- **When it has nothing:** With an empty wardrobe (`items == []`) it still returns a non-empty `str`: general styling advice for the item (what kinds of pieces to pair it with), and it does not invent pieces the user owns. If `new_item` is empty or `None` it returns the string `"No item to style."` without calling the model.

### `create_fit_card`

- **What it does:** Asks the model for a short, postable caption about the find and the outfit.
- **Inputs:** `outfit` (str) — the string `suggest_outfit` returned; `new_item` (dict) — the same listing dict that went into `suggest_outfit`.
- **Returns:** A `str` caption of 2–4 sentences, written like a social post rather than a product description, that mentions the item, its price (e.g. `$24`) and its platform once each.
- **When it has nothing:** If `outfit` is empty or whitespace-only it returns the string `"Can't write a fit card without an outfit suggestion."` without calling the model. It never raises and never returns `""`.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, the loop does *not* call `suggest_outfit`. Instead it re-runs the search with the price ceiling removed, then with the size removed, to find out which filter emptied it; it writes a message naming that filter ("raise your budget to $38", "try size L", or "try other words") into `session["error"]` and returns the session with `outfit_suggestion` and `fit_card` still `None`. Otherwise it takes the first (best-scoring) result into `session["selected_item"]` and goes on to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

The loop is a `while next_step != "done"` loop in which each step sets `next_step` from what it just got back (`parse → search → select → suggest → card`, or `parse → search → explain_empty`). It calls `trace.check_iterations(count)` on every pass, so a branch that never ends hits `config.MAX_ITERATIONS` instead of spinning. The empty-search message is built by `agent.py::explain_empty`.

**How the query is parsed:** Regex, in `agent.py::parse_query`, with no model call. The price comes from `under/below/less than/max/up to $N`, a bare `$N`, or `N dollars/bucks`. The size comes from `size X` / `in size X`, where X is a letter size, `small/medium/large` (read as S/M/L), a shoe number or a `W` waist. Both spans are cut out of the text, and what's left (punctuation stripped) is the description. Anything not stated is `None`. For example, `'chunky cardigan, size medium, max $40'` → `{'description': 'chunky cardigan', 'size': 'M', 'max_price': 40.0}`.

**What moves through the session:** In order: `query` → `parsed` (description, size, max_price) → `search_results` (the full list) → `selected_item` (`search_results[0]`) → `outfit_suggestion` → `fit_card`. Each tool reads its inputs back out of the session, not from a local variable. I added one field, `tool_calls`, a list of `{"tool", "item_id"}` appended right before each tool runs, so criterion 3 can check that the id that reached `suggest_outfit` and `create_fit_card` is the id of `selected_item`. On the empty path, `error` is set and `selected_item`, `outfit_suggestion` and `fit_card` stay `None`.

Printed session from a real run (`run_agent('denim jacket under $50', get_example_wardrobe())`, wardrobe and long fields trimmed):

```
"parsed": {"description": "denim jacket", "size": null, "max_price": 50.0},
"selected_item": {"id": "lst_007", "title": "Denim Jacket — Light Wash, Cropped", "price": 42.0, "platform": "poshmark", ...},
"fit_card": "Scored this vintage Wrangler denim jacket on Poshmark for just $42 and the structured shoulders are so good. I love the light wash for building easy streetwear looks. 💙 #thriftfind",
"error": null,
"tool_calls": [
  {"tool": "search_listings", "item_id": null},
  {"tool": "suggest_outfit", "item_id": "lst_007"},
  {"tool": "create_fit_card", "item_id": "lst_007"}
]
search_results ids: ['lst_007']
state check: True
empty path ('designer ballgown size XXS under $5'): fit_card = None | outfit = None | tool_calls = [{'tool': 'search_listings', 'item_id': None}]
```

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30, size M'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1: Y2K Baby Tee — Butterfly Print paired with Baggy straight-leg jeans, dark wash, Vintage black denim jacket, and Chunky white sneakers.
Outfit 2: Y2K Baby Tee — Butterfly Print paired with Wide-leg khaki trousers, Black cropped zip hoodie, and Black combat boots.
These combinations balance the fitted, cropped silhouette of the baby tee with contrasting proportions in the bottoms and outerwear, while tying the white, black, and denim color elements together cleanly.

  Fit card: Scored this early 2000s butterfly tee on depop for just $18 and I'm obsessed with the fitted crop. It has the cutest vintage Y2K energy. 🦋 #thriftfind

2 model calls this session, 669 prompt + 147 output tokens
```

The size filter did its job: the 2003 tour tee (size L, the top match with no size) was left out, and `S/M` matched `M`.

And the empty branch, which is shorter because it stops after search:

```
$ python app.py ask 'leather bomber under $40'

  Nothing matches 'leather bomber' under $40. The cheapest match is 90s Leather Bomber — Black at $75 — raise your budget to $75 to see it.

0 model calls this session
```

```
$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing in the listings matches 'designer ballgown' in size XXS under $5. No item matches those words at any size or price, so changing the size or budget won't help. Try other words: name the kind of item (tee, jacket, jeans, sneakers, cardigan) or a style (vintage, y2k, grunge, cottagecore, 90s).

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}]

$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Vintage Levi's 501 Jeans paired with the white ribbed tank top, vintage black denim jacket, brown leather belt, and black combat boots.
Vintage Levi's 501 Jeans paired with the oversized grey crewneck sweatshirt, black crossbody bag, and chunky white sneakers.

The straight fit of the new medium-wash jeans anchors both looks, easily pairing with cropped layers or oversized classics while working seamlessly with your existing footwear and accessories.

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_empty_wardrobe()))"
Pair these medium wash Levi's 501s with a boxy, cropped black graphic tee and worn-in canvas low-top sneakers for an effortless, casual streetwear vibe. Alternatively, dress them up slightly by adding a crisp white cotton button-down shirt tucked in loosely, layered under an oversized beige knit cardigan, and finished with brown leather loafers. The indigo blue and light knee fading work seamlessly with neutral tones like black, white, and beige, as well as muted earth tones, keeping the classic vintage aesthetic grounded and versatile.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these vintage Levi's 501 jeans on depop for just $38 with the best lived-in fading at the knees. I'm styling them the classic way with crisp white sneakers for that effortless streetwear look. 👖✨ #thrifted #levis

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(repr(create_fit_card('', load_listings()[0])))"
"Can't write a fit card without an outfit suggestion."
```

`create_fit_card` run three times on the same item and outfit with the cache off (`AI201_CACHE=0`), to check the words actually change:

```
Scored this bootleg graphic tee on Depop for just $24 and the vintage grunge vibe is unmatched. Tucking it into dark baggy jeans with chunky white sneakers and a black denim jacket makes the ultimate effortless streetwear fit. 🖤 #thrifted
---
Scored this perfectly faded graphic tee on depop for just $24. Tucked it into dark wash baggy jeans and threw on my denim jacket for the ultimate grunge street style. #thriftfind #streetwear
---
Scored this faded graphic tee on depop for just $24 and the worn-in 2003 tour bootleg vibe is unmatched. Tucked it into some dark wash baggy straight-leg jeans with chunky white sneakers and my favorite denim jacket for the ultimate grunge streetwear fit. 🖤 #thriftedstyle #streetwear
```

Different words every time, and all three have the price and platform, but all three open with "Scored this…". That's worth watching against criterion 4 next unit.

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

The course allowed full AI use on this project. I used Claude Code as a coding agent: it read the starter and the data, wrote the specs, criteria and code with me, and ran every test above. I also used the project's own model (Gemini, through `generate()`) as the "attacker" the brief describes. Three specific moments:

**Moment 1: attacking the criteria**

- *What I asked for:* I sent all five criteria to the model with the brief's prompt: *"For each one, tell me exactly how you would test it using only what the sentence says. Don't suggest improvements."*
- *What came back:* It turned all five into tests, but for criteria 1–3 its test setup was just "run a query that matches at least one listing", so it had to pick a query itself. For criterion 5 it listed query 2's expected parse as only "size M" and said nothing about the price.
- *What I changed:* I named the exact test query under criteria 1, 2 and 3 (the ones in `scenarios.py`). I also added "with `None` for whichever one the query doesn't state" to criterion 5, because without it a parser that made up a price for `90s track jacket in size M` would still pass.

**Moment 2: a search that returned the wrong kind of item**

- *What I asked for:* Claude Code built `search_listings` to my first spec, which kept a listing if it matched at least half of the query's keywords, then ran a batch of queries through it, each printed with its parse and results.
- *What came back:* `leather bomber under $40` returned 2 results: a braided leather belt and a leather shoulder bag. With two keywords, "half" meant one, so "leather" alone counted as a match. The only bomber is $75, so the honest answer was "nothing".
- *What I changed:* I raised the cutoff to two-thirds of the keywords (rounded up) in `tools.py` and in the Tool Inventory. Now that query comes back empty, and the empty branch says *"raise your budget to $75 to see it"* instead of offering a belt.

**Moment 3: checking the empty-search message**

- *What I asked for:* I pasted the ballgown message into the model with the brief's prompt: *"I know nothing about how the app works. Tell me what I would try next after reading it."*
- *What came back:* Its first suggestion was right (change the words), but it also said I'd "likely need to change your size (XXS) or price (< $5)". My message had said the words matched nothing "at any size or price", and the model still didn't take from that that size and price weren't the problem.
- *What I changed:* I rewrote that sentence in `agent.py::explain_empty` to say it outright: *"No item matches those words at any size or price, so changing the size or budget won't help."*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
