# Screenshots

Five images, in priority order. If you only have time for two, do **1** and **2**.

The README already references these exact filenames — drop the files in this folder, then
delete the two `<!--` / `-->` markers around the image blocks in the root `README.md`
(search for "Add screenshots"). Nothing else to edit.

## Before you capture anything

- **Warm the API.** Load `/metrics`, `/baselines` and `/slices` once. The ablation trains
  two extra models on first call; a screenshot of a loading skeleton is worse than none.
- **Light theme** (now the default). It reads better than dark when GitHub renders it on a
  white page, and better again if the judge prints or projects it.
- **Browser at ~1440px wide, zoom 90%.** Wider than that and the text is unreadable at
  GitHub's rendered width.
- **Crop out the browser chrome.** Your bookmarks bar, profile picture, other tabs and any
  personal URLs must not be in a public repository. Capture the viewport only, or crop
  afterwards. This is the single easiest way to leak something you did not mean to.
- Aim for **PNG, under ~400 KB each**. Anything larger just slows the README down.

---

## 1. `console.png` — the hero shot

**Tab:** Risk Queue. **State:** an **amber** order selected, so the right pane shows a
score, the band pill, and the SHAP driver bars.

This is the one that runs at the top of the README, and its whole job is to prove in one
glance that this is a working console rather than a notebook. Both panes visible, queue on
the left with a mix of green/amber/red rows.

## 2. `evidence.png` — the differentiator

**Tab:** Evidence. **State:** scrolled so the three threshold cards are visible —
*Shipped τ (val)*, *Oracle τ (struck through)*, *Optimism declined*.

This is the screenshot that separates the submission from every other Track-2 entry. If the
ablation table (with the logistic-regression row) fits in the same frame, better still.

## 3. `case-detail.png` — the agent, doing its job

**Tab:** Risk Queue → amber order → click **Investigate**, wait for it to finish, then click
**Execute on Razorpay (test)**.

Capture the full trace: the agent's action and confidence, the cross-vendor verifier verdict,
the tool evidence grid, the retrieved policy clauses, and the real `rzp.io` link. That link
is the proof the auto-responder is not a mock — make sure it is in frame.

## 4. `economics.png` — the money argument

**Tab:** Economics. **State:** default (slider at the shipped τ).

Frame the cost curve so **both** vertical lines are visible — the blue shipped τ and the
faint red *test-oracle (unused)* — plus the block-all-COD reference line. The ₹ confusion
matrix below it can be a second capture or the same one if it fits.

## 5. `audit.png` — bounded and accountable

**Tab:** Audit Trail. **State:** must not be empty.

Populate it first: investigate an order and log an override, then run a small batch (Batch
tab, 10 orders). You want visible rows showing *LLM agent* / *batch* badges and at least one
before→after override in the Human override column.
