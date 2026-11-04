# Paid Campaign Builder

**Plan in, launch-ready campaigns out.** This tool turns a simple campaign plan (4 spreadsheets) into files you can upload to Google Ads Editor and Meta Ads Manager. Before it builds anything, it checks the plan against the business rules.

```
plan/ (4 CSVs you edit)  ──►  build.py  ──►  checks  ──►  output/<launch>/
                                                            ├─ google_ads_editor_import.csv
                                                            ├─ meta_bulk_import.csv
                                                            └─ launch_summary.md
```

## What it does

1. **Reads the plan.** It uses `settings.csv` (budgets, CPA target, rules), `campaigns.csv`, `ad_groups.csv` (ad sets and ad groups) and `ads.csv`.
2. **Checks the plan.** It won't build if anything fails:
   - Total and per-platform budgets match the plan and stay under the $120K cap
   - Every Target CPA is inside the $250–$280 range
   - **Projected blended CPA** (budget ÷ expected CPA from the last 2 months of clean data) lands on target
   - Every campaign has ad groups and every ad group has ads
   - Test budgets are big enough to call a winner (at least 6× target CPA per test ad)
   - Google headline, description and path character limits are respected
   - Meta ad sets exclude people who already signed up or pay
   - Non-brand Google campaigns use the brand name as a negative, so they can't take credit for brand searches
   - **Tracking gate:** until `tracking_verified = yes`, everything builds **PAUSED**. This comes straight from the data: when signup flow v3 launched on 9/22, Meta-reported trials fell about 60% while PostHog trials held steady. The Meta pixel broke, and the algorithm was optimizing on bad data.
3. **Builds the files:**
   - **Google Ads Editor import.** Campaigns with their own daily budgets (no shared budget), locations, campaign and ad-group negatives, exact and phrase keywords, responsive search ads, and the PMax asset group.
   - **Meta bulk import.** One row per ad, with its campaign, ad set, budget, audience, exclusions, copy, CTA and creative file.
   - **UTMs are added to every ad automatically** (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`). PostHog is the source of truth, so every trial needs to trace back to its campaign and ad.
   - **Launch summary.** Budget and projected trials per campaign, the reason behind each choice, every check result, the kill/winner/scale rules, and a pre-launch checklist.

## Run it

It needs Python 3 and nothing else (standard library only).

**Option A: in the browser, no install (GitHub Codespaces)**
1. On this repo's page, click **Code → Codespaces → Create codespace on main**
2. In the terminal at the bottom, type: `python3 build.py`

**Option B: on your computer**
```
cd paid-campaign-builder
python3 build.py
```
(On Windows, use `python build.py`.)

Example output:
```
  [OK] Total budget $120,000 is within the $120,000 cap
  [OK] Projected blended CPA $257 is inside the $250-$280 target (~467 trials)
  [OK] All Google ad text is within character limits
  [BLOCKER] Tracking not verified ... Everything builds PAUSED until then.

Built 57 Google rows and 13 Meta ads (status: PAUSED).
```

## Reuse it for the next launch

1. Copy the `plan` folder to `plan_jan` (or edit `plan` directly)
2. Change `launch_name` in `settings.csv`, then update budgets, ads or keywords in the other CSVs (Excel or Google Sheets work fine)
3. Run `python3 build.py plan_jan`
4. New files appear in `output/Jan-2027/`. Last month's files stay untouched.

Some examples of reuse:
- **New ad:** add one row to `ads.csv`
- **Moving budget:** change `monthly_budget`. The checks will tell you if the totals no longer match or the projected CPA drifts off target.
- **New market:** add a campaign row with a different `locations` value

## Upload the files

- **Google:** Google Ads Editor → *Account → Import → From file* → choose `google_ads_editor_import.csv` → review the preview → *Post*. Editor shows every change before anything goes live.
- **Meta:** Ads Manager → *Import ads in bulk* → choose `meta_bulk_import.csv`. Everything arrives paused for QA.

## Design choices

- **Spreadsheets as the input:** anyone on the team can edit a plan without touching code, and the plan doubles as documentation.
- **No API keys:** nothing goes live without a human reviewing it in Ads Editor or Ads Manager. It's safe to share and to run anywhere.
- **Paused by default, with a tracking gate:** the biggest risk in this account was trusting broken platform numbers, so the tool won't mark anything active until tracking is verified.
- **Rules live in `settings.csv`, not in people's heads:** kill, winner and scaling thresholds are written into the plan and printed in every launch summary.

## Known limits

- Column names follow the Ads Editor and Meta bulk-import templates. If an account's template differs, rename the columns in `GOOGLE_COLUMNS` / `META_COLUMNS` at the top of `build.py`, or map them in the import dialog.
- Some settings can't be imported from a file and are listed on the launch checklist: PMax brand exclusions, audience lists, and the Meta A/B test setup.
- Expected CPAs are planning estimates from historical data, not guarantees. Results are judged on PostHog trials.

## What's next

- Pull last month's PostHog and platform data automatically and refresh `expected_cpa`
- Add an AI review step that reads the launch summary and flags risky changes before launch
- Push directly through the Google Ads and Meta Marketing APIs once the access is approved

Built with Claude (Anthropic) as a coding partner. Strategy, budget split and rules were decided by me; see the AI chat history in the assessment doc.
