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

The course allowed full AI use on this project. I used Claude Code as a coding agent: it read the starter and the data, wrote the specs, criteria and code with me, and ran every test in this README. I also used the project's own model (Gemini, through `generate()`) as the "attacker" the brief describes. Three specific moments:

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

**Unit 4.** Same setup: Claude Code did the MCP registration, the handlers, the trace calls, the scenarios, both eval runs, and `check_criteria.py`, which is my criteria written as code so every try gets scored the same way. Gemini, through `generate()`, played the outside reader again. Two moments from this unit:

**Moment 4: the three failure messages, read cold**

- *What I asked for:* the brief's prompt, with all three messages pasted in: *"Here are three error messages from an app I'm using. For each one, tell me what I would try next as a user who can't see the code. If a message leaves me with nothing to try, say so. Don't rewrite them for me."*
- *What came back:* Message 1 (empty search) it got right. For the empty wardrobe it said *"This message leaves you with nothing to try, because it successfully completed the task … and reported no errors."* So a user would never find out the outfit was generic. For the bad key it read *"the search part still works without it"* as "you can try searching again", which would just fail the same way.
- *What I changed:* I added `session["notice"]`, which `app.py` prints under the fit card when the wardrobe is empty, telling the user to add pieces they own. I also changed the bad-key message to end with *"Once that's fixed, ask again to get the outfit and fit card."*

**Moment 5: a criterion that passed when it shouldn't have**

- *What I asked for:* after `check_criteria.py` marked all five criteria MET, I had Claude Code count the opening words of every fit card in the run, not just the five criterion 4 looks at.
- *What came back:* 36 of 45 opened with a "scored" variant, and all 45 with "scored / just scored / found / snagged". Criterion 4 passed anyway, because it asked for "different first sentences" and these differed by a word or two after the same opener. Claude pointed out that this is the exact example the brief gives of a broken criterion.
- *What I changed:* I revised criterion 4 in `criteria.md` under the original (stricter: no more than 2 of 5 cards with the same first two words), called it MISSED instead of taking the pass, and made the fit card opener my one improvement. Then the after-run showed the template had moved to "Channeling…" and "I grabbed this…". I reported that too, rather than re-measuring it until it looked good.

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

`python run_eval.py --label before`, cache off, 10 scenarios × 5 tries, 90 model calls (29,082 prompt + 7,026 output tokens). Files: [results/run_2026-11-01_2344_before.md](results/run_2026-11-01_2344_before.md) (the log run_eval writes) and `.json` (every session, which I added to run_eval so I could check fields instead of reading markdown).

I scored the tries with `check_criteria.py`, which is my reading of `criteria.md` written as code, one check per criterion, so the same rule hits every try in both runs. Its full output is in [results/run_2026-11-01_2344_before_scored.txt](results/run_2026-11-01_2344_before_scored.txt).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before tool 2 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Searched item is the item every later tool gets | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card is postable and not a template | 4 of 5 + 4 different first sentences | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Query's price and size parsed and respected | 4 of 5 queries | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

For criterion 5 the columns are the five queries, because the criterion is written as "4 of the 5 queries". Each query ran five times, so that's 25 runs, and a query only gets PASS if all five of its runs passed. All 25 came back identical, which is what you'd expect from regex and a filter.

**Real output from one try**, per criterion:

Criterion 1, try 1. The loop is `agent.py::run_agent`, the card is `tools.py::create_fit_card`:

```
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 6 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Vintage Graphic Hoodie — Faded Black … +3 more
      →    branch: 6 results → select
...
[5] create_fit_card
      in:  outfit (482 chars), new_item=lst_006
      out: Scored this 2003 tour bootleg style graphic tee for just $24 on depop and it has the absolute best worn-in gru…
      →    done

tool_calls: [{'tool': 'search_listings', 'item_id': None}, {'tool': 'suggest_outfit', 'item_id': 'lst_006'}, {'tool': 'create_fit_card', 'item_id': 'lst_006'}]
fit_card:   Scored this 2003 tour bootleg style graphic tee for just $24 on depop and it has the absolute best worn-in grunge vibe. I've been styling it tucked into dark baggy denim with combat boots, but it looks just as good layered under a black jacket. 🖤 #streetwear
```

Criterion 2, try 1. The message is `agent.py::explain_empty`:

```
error:      Nothing in the listings matches 'designer ballgown' in size XXS under $5. No item matches those words at any size or price, so changing the size or budget won't help. Try other words: name the kind of item (tee, jacket, jeans, sneakers, cardigan) or a style (vintage, y2k, grunge, cottagecore, 90s).
tool_calls: [{'tool': 'search_listings', 'item_id': None}]
outfit_suggestion: None   fit_card: None
```

Criterion 3, try 1. The session from `agent.py::run_agent`, with `tool_calls` written by `agent.py::_log_call`:

```
selected_item["id"]:      lst_007
search_results[0]["id"]:  lst_007
tool_calls: [{'tool': 'search_listings', 'item_id': None}, {'tool': 'suggest_outfit', 'item_id': 'lst_007'}, {'tool': 'create_fit_card', 'item_id': 'lst_007'}]
```

Criterion 4, all five cards, since the criterion is about the set. From `tools.py::create_fit_card`:

```
1. Found this soft, worn-in 2003 tour bootleg tee on depop for $24 and it has the absolute best faded grunge look. I love the slightly boxy fit for throwing on with dark denim or relaxed trousers.   #thriftstyle #streetwear
2. Scored this faded 2003 tour tee on depop for $24 and it's already my favorite piece. The boxy fit and worn-in cotton give it the ultimate grunge streetwear vibe. 🎸 #thriftfind
3. Just scored this 2003 tour bootleg style graphic tee on Depop for $24 and the worn-in black cotton gives off the ultimate grunge vibe. I’m styling it tucked into dark baggy jeans with combat boots, then swapping to khaki trousers and a denim jacket for easy streetwear looks. 🖤 #thrifted
4. Scored this faded graphic tee on depop for just $24. It has that perfectly worn-in, boxy grunge fit I live for. Pair it with baggy denim or crisp khakis for an effortless streetwear vibe. 🖤  #thriftedstyle #streetwear
5. Scored this vintage-style 2003 tour tee on depop for just $24 and the worn-in black cotton has the ultimate grunge look. I’m living for the slightly boxy fit tucked into dark wash denim. 🖤 #thrifted

check_criteria.py: $24 / depop / 38, 31, 50, 37, 35 words — all five PASS
5 different first sentences; opening words: 'found this', 'scored this', 'just scored', 'scored this', 'scored this'
```

Criterion 5, try 1 of each query. `parsed` is `agent.py::parse_query`, results are `search_listings` through MCP (`mcp_server.py::search_listings`), shown as (id, price, size):

```
'vintage graphic tee under $30'         {'size': None, 'max_price': 30.0}  [('lst_006', 24.0, 'L'), ('lst_033', 19.0, 'L'), ('lst_015', 26.0, 'L'), ('lst_002', 18.0, 'S/M'), ('lst_012', 20.0, 'XL (fits oversized)'), ('lst_017', 15.0, 'S/M')]
'90s track jacket in size M'            {'size': 'M', 'max_price': None}   [('lst_004', 45.0, 'M'), ('lst_022', 75.0, 'M')]
'platform sneakers size 8'              {'size': '8', 'max_price': None}   [('lst_019', 48.0, 'US 8')]
'denim jacket for less than 50 dollars' {'size': None, 'max_price': 50.0}  [('lst_007', 42.0, 'S')]
'chunky cardigan, size medium, max $40' {'size': 'M', 'max_price': 40.0}   [('lst_008', 35.0, 'One Size / Oversized')]
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
| 1 | A matching query completes all three tools | 4 of 5 | **MET (5/5)** | All five tries called `search_listings` → `suggest_outfit` → `create_fit_card` in that order and came back with a real caption, not one of the fallback strings. 5 ≥ 4. |
| 2 | An impossible query stops before the second tool | 5 of 5 | **MET (5/5)** | Every try's `tool_calls` held only `search_listings`, `outfit_suggestion` and `fit_card` stayed `None`, and the message said "Try other words" with example keywords, one of the three things the criterion counts as naming a change. |
| 3 | The searched item is the item every later tool receives | 5 of 5 | **MET (5/5)** | In all five tries `selected_item`, `search_results[0]` and the ids `tool_calls` recorded for both model tools were all `lst_007`. |
| 4 | The fit card is postable and not a template | 4 of 5 with $ price, platform, ≤ 80 words, + 4 different first sentences | **MET as written (5/5, 5 different first sentences). MISSED under the unit 4 revision: 3 of 5 open "Scored this"** | Every card had `$24`, `depop` and 31–50 words, so (a)–(c) passed 5 of 5. The first sentences were all technically different, so the original line passes. But the original line was broken (see the revision in [criteria.md](criteria.md)): it can't catch the template it was written to catch. Read plainly, three cards opening with the same two words is a template, so I'm treating 4 as a miss and diagnosing it. |
| 5 | The query's price and size are parsed and respected | 4 of 5 queries | **MET (5/5)** | All five queries parsed to exactly the stated `max_price`/`size` with `None` for the other, and no result broke a limit, in 25 of 25 runs. |

**Diagnoses**

**Criterion 4 (revised): the fit card is a template.** 3 of the 5 cards opened "Scored this". It isn't just those five: across all 45 fit cards in the whole before run, 36 opened with a "scored" variant ("scored this" 23, "just scored" 10, "scored these" 3) and the other 9 with "found this/these" or "snagged this". Not one of 45 opened any other way, on five different items.

- **Where:** the model's output, from `tools.py::create_fit_card`, step [5] in the trace. The tool did what its spec says and the loop handed it the right thing. The trace shows `new_item=lst_006` going in, the same id `select` picked.
- **Mechanism:** my prompt. It asks for *"the item, the price written exactly as $24, and the platform (depop) once each"*. The shortest way to tick all three is one stock sentence, "Scored this [item] on [platform] for $[price]", which is how thrift captions open everywhere the model has read them. Every one of the 45 first sentences has the item, the platform *and* the price packed into it. So the checklist I wrote to pass (a) and (b) is the same thing that produces the template. Temperature 0.9 changes the words after the opener, not the opener.

**The pattern:** this is one problem, not several. Every scenario that reached step 5 shows it, on `lst_006`, `lst_007`, `lst_004`, `lst_019` and `lst_008`, so it's the prompt, not the item.

**Were my other targets too low?** Honestly, partly. Criteria 2, 3 and 5 test code with no randomness in it (a branch, my own bookkeeping, and a regex + filter), so once the code was right, 5 of 5 was the expected result. They're worth keeping because they'd catch a regression, but they were never going to tell me much about the model. The one I'd tighten is **criterion 1**: I allowed one miss in five for a model failure, and 45 of 45 model-backed runs in this test finished. It should be 5 of 5. And **criterion 5 only checks the limits, not relevance**: `90s track jacket in size M` also returned the 90s Leather Bomber, and `vintage graphic tee under $30` returned a crewneck sweatshirt and a mesh top. All inside the limits, so it passes. The first result is always the right one, so the agent never picked a wrong item, but a criterion about what else comes back would have caught it.


---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

`trace.step()` is called once per step inside `agent.py::run_agent`, with the step name, what went in and what came back. Step 2 is the MCP call. Both runs below were with the cache off (`AI201_CACHE=0`), so the two model calls are real.

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30, size M' --trace
[1] parse_query
      in:  vintage graphic tee under $30, size M
      out: description='vintage graphic tee', size='M', max_price=30.0
      →    regex, no model call
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size='M', max_price=30.0
      out: 2 items: Y2K Baby Tee — Butterfly Print, Mesh Long-Sleeve Top — Black
      →    branch: 2 results → select
[3] select
      in:  2 results
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    took search_results[0], id lst_002
[4] suggest_outfit
      in:  new_item=lst_002, wardrobe=10 items
      out: Outfit 1: Y2K Baby Tee — Butterfly Print paired with Baggy straight-leg jeans, dark wash, Vintage black denim …
[5] create_fit_card
      in:  outfit (466 chars), new_item=lst_002
      out: Scored this Y2K butterfly baby tee on depop for just $18 and I’m obsessed with the fitted crop vibe. It looks …
      →    done

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1: Y2K Baby Tee — Butterfly Print paired with Baggy straight-leg jeans, dark wash, Vintage black denim jacket, and Chunky white sneakers.
Outfit 2: Y2K Baby Tee — Butterfly Print paired with Wide-leg khaki trousers, Black cropped zip hoodie, and Black combat boots.
These combinations work because the cropped, fitted silhouette of the baby tee balances the volume of the baggy bottoms, while the layered outerwear and footwear tie the Y2K aesthetic together.

  Fit card: Scored this Y2K butterfly baby tee on depop for just $18 and I’m obsessed with the fitted crop vibe. It looks so good styled with baggy denim or wide-leg trousers for that early 2000s look. 🦋✨ #y2kstyle #thriftfinds

2 model calls this session, 669 prompt + 166 output tokens
```

Why each step: search ran because parsing found a description; it went to `select` because the list wasn't empty; `select` took `search_results[0]` because search already sorts best match first; `suggest_outfit` and `create_fit_card` were both handed `lst_002`, the same id `select` picked.

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
      →    regex, no model call
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty → explain_empty, suggest_outfit is skipped
[3] explain_empty
      in:  re-search via MCP with filters dropped, to find which one emptied it
      out: Nothing in the listings matches 'designer ballgown' in size XXS under $5. No item matches those words at any s…
      →    stop: outfit_suggestion and fit_card stay None

  Nothing in the listings matches 'designer ballgown' in size XXS under $5. No item matches those words at any size or price, so changing the size or budget won't help. Try other words: name the kind of item (tee, jacket, jeans, sneakers, cardigan) or a style (vintage, y2k, grunge, cottagecore, 90s).

0 model calls this session
```

Three steps instead of five, and 0 model calls. The branch is doing its job.

**The three failures, triggered on purpose**

| Failure | How I triggered it | What it said before I touched it | Handler I added |
|---|---|---|---|
| Empty search | `python app.py ask 'neon ski suit size XXS under $5'` | *"Nothing in the listings matches 'neon ski suit' in size XXS under $5. No item matches those words at any size or price, so changing the size or budget won't help. Try other words: …"* | None needed. The unit 3 branch already stops and names what to change. |
| Empty wardrobe | `python app.py ask 'chunky cardigan under $40' --empty-wardrobe` | General styling advice ("Pair this earth-tone brown chunky knit cardigan with high-waisted, straight-leg cream denim…") and a fit card. No crash, not empty, but nothing told the user *why* the outfit was generic. | `run_agent` sets a new `session["notice"]` when the wardrobe has no items, and `app.py` prints it under the fit card. |
| Model unavailable | Changed one character of `GEMINI_API_KEY` in `.env`, asked `'velvet blazer in emerald green'` (never asked before, so not cached) | `ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.` with exit code 1. That's `app.py`'s catch-all, not my agent. The blazer search had already worked and the user never saw it, and in `run_eval.py` the run would have been logged as a crash. | `run_agent` catches `ModelUnavailable`, keeps the session, writes the message into `session["error"]` and adds a `ModelUnavailable` trace step. |

What each one says now:

```
$ python app.py ask 'chunky cardigan under $40' --empty-wardrobe
(running with an empty wardrobe)

  Found:    Knit Cardigan — Chunky Brown — $35.0 on depop

  Outfit:   Pair this chunky brown cardigan with straight-leg light wash denim and a fitted cream ribbed turtleneck for a cozy earth-tone look. Alternatively, style it over a floral midi slip dress in olive or rust with brown leather ankle boots for a cottagecore vibe. Lean into textures like corduroy and suede. Colors like cream, olive, tan, and rust complement the brown knit. The overall aesthetic is warm, casual, and relaxed.

  Fit card: Found this chunky brown knit on depop for $35 and it is literally the coziest cottagecore layer for fall. I’m living for these earth tones and throwing it over everything from denim to slip dresses. 🍂

#thriftfinds

  Note:     Your wardrobe is empty, so that outfit is general advice, not pieces you own. Add a few things you already wear to your wardrobe to get outfits built from them.

2 model calls this session, 505 prompt + 137 output tokens
```

```
$ python app.py ask 'olive shacket under $40'        (one character of the key changed)

  Found Shacket — Olive Canvas for $33 on poshmark, but couldn't reach the model to style it or write the fit card. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. Once that's fixed, ask again to get the outfit and fit card.

1 model calls this session
```

And the trace for the bad-key run, so you can see where it stopped:

```
[3] select
      in:  1 results
      out: Velvet Blazer — Emerald Green ($52.0, depop)
      →    took search_results[0], id lst_036
[4] ModelUnavailable
      in:  during step 'suggest'
      out: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.goo…
      →    stop: outfit_suggestion and fit_card stay None
```

Key put back afterwards, and `python test.py` passes 10 of 10 again.

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

`mcp_server.py` registers `search_listings` with a description written for an agent that can't see my code: units (US dollars), the size rule with examples, the result fields, and the empty case ("returns an empty list, never an error"). `python mcp_client.py` lists it with `description: string`, `size: string (optional)` and `max_price: number (optional)`, which matches the Tool Inventory. In `agent.py` I added a `search_listings()` that calls `mcp_client.call_tool("search_listings", {...})`, and both the loop and `explain_empty` search through it. `tools.search_listings` itself didn't change.

**Did anything behave differently?** The results didn't. Before wiring it in I ran six queries both ways, including the empty one: identical lists, same types (prices stayed floats, `brand` stayed `None`), nothing came back as a string. The unit 3 sample query even came back from the build cache through MCP, which can only happen if the item dict that reached the model prompts was byte-for-byte the same. What changed is speed. Every call starts a new server process, about 4 s each (13 s the very first time), so a normal query is about 4 s slower and the empty path, which re-searches 2–4 times, takes about 10 s.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** One prompt, in `tools.py::create_fit_card`. Nothing else in the agent changed between the two runs. I added two instructions:

```diff
-  "post — not a product description. Mention the item, the price written "
-  f"exactly as {price_text}, and the platform ({new_item.get('platform')}) "
-  "once each. Be specific about the vibe. ..."
+  "post — not a product description. Open with the outfit or the vibe, "
+  "not with how you got it: don't start with 'Scored', 'Found', "
+  "'Snagged', 'Got' or 'Just'. Mention the item, the price written "
+  f"exactly as {price_text}, and the platform ({new_item.get('platform')}) "
+  "once each, with the price and platform in a later sentence, not the "
+  "first. Be specific about the vibe. ..."
```

**Which failure it was meant to fix:** Criterion 4 (revised), the template opener. The diagnosis said the prompt's "item + price + platform" checklist was getting packed into one stock first sentence, so the fix splits the checklist across sentences and takes away the stock verbs. I kept the price and platform instructions, because (a) and (b) of criterion 4 depend on them.

### Run Log — After

`python run_eval.py --label after`, same 10 scenarios, 5 tries each, cache off, 92 model calls. Files: [results/run_2026-11-01_2355_after.md](results/run_2026-11-01_2355_after.md), `.json`, and [the scored output](results/run_2026-11-01_2355_after_scored.txt).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before tool 2 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Searched item is the item every later tool gets | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card is postable and not a template | 4 of 5 + ≤ 2 cards with the same two-word opener (revised) | PASS | PASS | PASS | PASS | PASS | MET (5/5, top opener 1 of 5) |
| 5. Query's price and size parsed and respected | 4 of 5 queries | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Before and after, side by side, on the thing the change was for:

| | Before | After |
|---|---|---|
| Criterion 4 (revised): most common two-word opener in the 5 cards | "scored this", **3 of 5 → MISSED** | "channeling ultimate", 1 of 5 → **MET** |
| Criterion 4 (a)–(c): `$24`, `depop`, ≤ 80 words | 5 of 5 | 5 of 5 |
| All 45 cards in the run: most common first word | "scored", 26 of 45 | "channeling", 14 of 45 |
| All 45 cards: the four most common first words cover | 45 of 45 | 28 of 45 |
| All 45 cards: price in the first sentence | 45 of 45 | 0 of 45 |

The five criterion-4 cards after the change:

```
1. Channeling ultimate 2000s grunge energy with this boxy graphic tee and dark wash denim. I grabbed this washed black bootleg style for $24 on depop, and the worn-in cotton makes it look authentically vintage. 🖤 #streetwear #thrifted
2. Channeling total 2000s grunge energy with this boxy, faded graphic tee. I grabbed it on depop for $24 to anchor these effortless, volume-heavy streetwear looks. 🖤 #streetwear
3. Living in this slightly boxy vintage-style graphic tee and heavy combat boots for an effortless grunge streetwear look. Picked up this 100% cotton piece on depop for $24 to anchor all my baggy denim. 🖤 #thrifted
4. Leaning all the way into grunge vibes today with this boxy graphic tee and heavy black combat boots. I picked up this 2003 tour bootleg style piece on depop for $24, and the worn-in cotton makes it look genuinely vintage. 🖤 #Streetwear
5. Channeling peak 2003 grunge energy with this boxy, faded graphic tee. It’s got that perfectly worn-in feel that anchors any effortless streetwear look, whether paired with baggy dark wash denim or layered under a jacket. I grabbed this on depop for $24. 🖤 #thrifted
```

**Did it help, and how do I know:** Yes on the criterion, and only partly on the actual problem. Revised criterion 4 went from MISSED (3 of 5 open "scored this") to MET (no two-word opener more than once), and (a)–(c) held at 5 of 5, so making the card less templated didn't cost the price or the platform. Across all 45 cards the "scored" opener is gone completely.

But reading the five cards, I'd call it a template that **moved**, not one that went away. 3 of the 5 still start with the same *word*, "Channeling", and they only pass because the second word changes (ultimate / total / peak). Across the whole run "channeling" opens 14 of 45 cards. The acquisition line I told it not to open with is now the stock *second* sentence: "grabbed" is in 26 of 45 cards ("I grabbed this … on depop for $24"). My revised criterion counts the first two words, so it can't see either of those. I set that measure before this run and I'm not changing it after seeing the result, but on a first-word count the same five cards would miss (3 of 5).


---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

No criterion is MISSED against its written target after the change. That doesn't mean nothing's broken:

1. **The fit card template moved instead of leaving (criterion 4).** 3 of 5 cards open with "Channeling", and "I grabbed this … on depop for $24" is now the stock second sentence (26 of 45 cards). What I'd do next: stop leaving variety to temperature. Have `create_fit_card` pick an opening angle in code for each call (the outfit, one detail of the item, where you'd wear it, the price as the punchline) and put that one angle in the prompt. I'd also measure it on the first *word*, not the first two. Why I stopped: the unit allows one change, and a second prompt edit on top of the first would make the two impossible to tell apart in the run log.
2. **Criterion 1 is looser than the data says it needs to be.** I allowed one miss in five for a model failure, and 90 of 90 model-backed runs across both tests finished. Next round I'd set it at 5 of 5. I didn't revise it, because a revision is for a criterion that can't be measured, and this one measures fine. It's just easy.
3. **Search lets in the wrong kind of item.** The two-thirds keyword rule means `90s track jacket` also returns the 90s Leather Bomber, and `vintage graphic tee` returns a crewneck sweatshirt and a mesh top whose *description* mentions a graphic tee. The best match is always first, so the agent never picked a wrong item in 50 tries, but none of my criteria look past `search_results[0]`. What I'd do: require the garment word (tee, jacket, jeans…) to match the title or category, not just the description. Why I stopped: it isn't one of my five, and it would be a second change.
4. **MCP is slow and has no handler of its own.** Every `call_tool` starts a fresh server, about 4 s, and the empty path searches 2–4 times to work out which filter emptied it, so an impossible query now takes about 10 s. I'd hold one connection open for the whole run. And if `mcp_server.py` won't start, the `MCPError` isn't caught in `run_agent`. It falls through to `app.py`'s catch-all, which prints a readable message but loses the session. It wasn't one of the three failure modes, so I left it.


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
