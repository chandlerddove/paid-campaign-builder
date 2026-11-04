"""
Paid Campaign Builder
=====================
Turns a campaign plan (4 simple CSV files in /plan) into launch-ready files:

  1. google_ads_editor_import.csv   -> import into Google Ads Editor
  2. meta_bulk_import.csv           -> import into Meta Ads Manager (bulk import)
  3. launch_summary.md              -> budget, projected trials, checks, and launch rules

Before it builds anything, it checks the plan against the business rules
(budget caps, CPA target, ad text limits, naming, exclusions, tracking gate).
If a check fails with an ERROR, nothing is built.

Run it:   python3 build.py
Reuse it: edit the CSVs in /plan and run it again, or copy /plan to a new
          folder (e.g. plan_jan) and run:  python3 build.py plan_jan

No logins or API keys: the files are reviewed in Ads Editor / Ads Manager
before anything goes live. Everything is created PAUSED.
Uses only the Python standard library (nothing to install).
"""

import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
# Default plan folder is /plan. For a new launch you can copy it and run:  python3 build.py plan_jan
PLAN_DIR = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else "plan")

# Ad text limits set by Google
GOOGLE_HEADLINE_MAX = 30
GOOGLE_DESCRIPTION_MAX = 90
GOOGLE_PATH_MAX = 15
GOOGLE_LONG_HEADLINE_MAX = 90
META_HEADLINE_SOFT_MAX = 40  # Meta allows more, but longer headlines get cut off


# --------------------------------------------------------------------------
# 1. READ THE PLAN
# --------------------------------------------------------------------------
def read_csv(name):
    path = os.path.join(PLAN_DIR, name)
    # utf-8-sig handles files saved from Excel
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def split(value):
    """'a|b|c' -> ['a', 'b', 'c']"""
    return [v.strip() for v in value.split("|") if v.strip()] if value else []


def load_plan():
    settings = {r["setting"]: r["value"] for r in read_csv("settings.csv")}
    brand = settings.get("brand_name", "")

    def fill(text):  # lets the plan say {brand} instead of hard-coding the name
        return text.replace("{brand}", brand.lower()) if text else text

    campaigns = read_csv("campaigns.csv")
    groups = read_csv("ad_groups.csv")
    ads = read_csv("ads.csv")
    for c in campaigns:
        c["campaign_negatives"] = fill(c["campaign_negatives"])
    for g in groups:
        for k in ("exact_keywords", "phrase_keywords", "negative_keywords"):
            g[k] = fill(g[k])
    return settings, campaigns, groups, ads


# --------------------------------------------------------------------------
# 2. CHECK THE PLAN
# --------------------------------------------------------------------------
class Checks:
    def __init__(self):
        self.items = []  # (level, message)

    def ok(self, msg):
        self.items.append(("OK", msg))

    def warn(self, msg):
        self.items.append(("WARN", msg))

    def error(self, msg):
        self.items.append(("ERROR", msg))

    def blocker(self, msg):
        self.items.append(("BLOCKER", msg))

    @property
    def has_errors(self):
        return any(level == "ERROR" for level, _ in self.items)


def money(x):
    return "${:,.0f}".format(x)


def project(campaigns):
    """Projected trials per campaign = budget / expected CPA (from the baseline data)."""
    rows = []
    for c in campaigns:
        budget = float(c["monthly_budget"])
        cpa = float(c["expected_cpa"])
        rows.append((c, budget, cpa, budget / cpa))
    return rows


def run_checks(settings, campaigns, groups, ads):
    chk = Checks()
    low = float(settings["cpa_target_low"])
    high = float(settings["cpa_target_high"])

    # --- names are unique and everything links up
    names = [c["campaign"] for c in campaigns]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        chk.error("Duplicate campaign names: " + ", ".join(sorted(dupes)))
    camp_by_name = {c["campaign"]: c for c in campaigns}
    groups_by_camp = defaultdict(list)
    for g in groups:
        if g["campaign"] not in camp_by_name:
            chk.error("Ad group '{}' points to unknown campaign '{}'".format(g["ad_group"], g["campaign"]))
        groups_by_camp[g["campaign"]].append(g)
    ads_by_group = defaultdict(list)
    group_keys = {(g["campaign"], g["ad_group"]) for g in groups}
    for a in ads:
        key = (a["campaign"], a["ad_group"])
        if key not in group_keys:
            chk.error("Ad '{}' points to unknown ad group '{}'".format(a["ad_name"], a["ad_group"]))
        ads_by_group[key].append(a)
    for c in campaigns:
        if not groups_by_camp[c["campaign"]]:
            chk.error("Campaign '{}' has no ad sets / ad groups".format(c["campaign"]))
    for g in groups:
        if not ads_by_group[(g["campaign"], g["ad_group"])]:
            chk.error("'{}' has no ads".format(g["ad_group"]))
    if not chk.has_errors:
        chk.ok("Every campaign has ad groups, and every ad group has ads ({} campaigns, {} ad groups, {} ads)".format(
            len(campaigns), len(groups), len(ads)))

    # --- budgets
    total = sum(float(c["monthly_budget"]) for c in campaigns)
    cap = float(settings["total_budget_cap"])
    if total > cap:
        chk.error("Total budget {} is over the {} cap".format(money(total), money(cap)))
    else:
        chk.ok("Total budget {} is within the {} cap".format(money(total), money(cap)))
    for platform in ("meta", "google"):
        planned = float(settings[platform + "_budget"])
        actual = sum(float(c["monthly_budget"]) for c in campaigns if c["platform"] == platform)
        if abs(actual - planned) > planned * 0.01:
            chk.warn("{} campaigns add up to {}, plan says {}".format(platform.title(), money(actual), money(planned)))
        else:
            chk.ok("{} campaigns add up to {} as planned".format(platform.title(), money(actual)))
    for c in campaigns:
        if c["budget_level"] == "ad_set":
            gs = groups_by_camp[c["campaign"]]
            s = sum(float(g["monthly_budget"] or 0) for g in gs)
            if abs(s - float(c["monthly_budget"])) > 1:
                chk.error("{}: ad set budgets add up to {}, campaign budget is {}".format(
                    c["campaign"], money(s), money(float(c["monthly_budget"]))))

    # --- CPA target
    for c in campaigns:
        if c["target_cpa"]:
            t = float(c["target_cpa"])
            if not (low <= t <= high):
                chk.error("{}: target CPA ${:.0f} is outside the ${:.0f}-${:.0f} target".format(c["campaign"], t, low, high))
    proj = project(campaigns)
    trials = sum(p[3] for p in proj)
    blended = total / trials
    if blended > high:
        chk.error("Projected blended CPA ${:.0f} is above the ${:.0f} ceiling".format(blended, high))
    else:
        chk.ok("Projected blended CPA ${:.0f} is inside the ${:.0f}-${:.0f} target (~{:.0f} trials)".format(blended, low, high, trials))
    for c, budget, cpa, _ in proj:
        if cpa > high:
            chk.warn("{} is expected above target (${:.0f}); cheaper campaigns offset it, so watch it weekly".format(c["campaign"], cpa))

    # --- testing budgets are big enough to call a winner
    winner_spend = float(settings["winner_spend_multiple"]) * low
    for c in campaigns:
        if "test" in c["campaign"].lower() and c["platform"] == "meta":
            n_ads = sum(len(ads_by_group[(g["campaign"], g["ad_group"])]) for g in groups_by_camp[c["campaign"]])
            per_ad = float(c["monthly_budget"]) / max(n_ads, 1)
            if per_ad < winner_spend:
                chk.warn("{}: only {} per test ad; winner rule needs {}".format(c["campaign"], money(per_ad), money(winner_spend)))
            else:
                chk.ok("{}: {} per test ad, enough to call a winner (needs {})".format(c["campaign"], money(per_ad), money(winner_spend)))

    # --- Meta: exclude people who already signed up
    for g in groups:
        if g["platform"] == "meta" and not g["exclusions"]:
            chk.warn("{}: no exclusions; we'd pay to reach people who already signed up".format(g["ad_group"]))

    # --- Google: brand stays in brand
    brand = settings.get("brand_name", "").lower()
    for c in campaigns:
        if c["platform"] == "google" and c["campaign_type"] == "Search" and "brand" not in c["campaign"].lower().replace("nonbrand", ""):
            if brand not in split(c["campaign_negatives"]):
                chk.warn("{}: brand name isn't a negative, so it can take credit for brand searches".format(c["campaign"]))

    # --- ad text limits
    text_problems = 0
    for a in ads:
        if a["platform"] == "google":
            heads, descs = split(a["headlines"]), split(a["descriptions"])
            if len(heads) < 3 or len(descs) < 2:
                chk.error("{}: needs at least 3 headlines and 2 descriptions".format(a["ad_name"]))
                text_problems += 1
            for h in heads:
                if len(h) > GOOGLE_HEADLINE_MAX:
                    chk.error("{}: headline too long ({} > {}): '{}'".format(a["ad_name"], len(h), GOOGLE_HEADLINE_MAX, h))
                    text_problems += 1
            for d in descs:
                if len(d) > GOOGLE_DESCRIPTION_MAX:
                    chk.error("{}: description too long ({} > {}): '{}'".format(a["ad_name"], len(d), GOOGLE_DESCRIPTION_MAX, d))
                    text_problems += 1
            for p in (a["path1"], a["path2"]):
                if len(p) > GOOGLE_PATH_MAX:
                    chk.error("{}: display path too long: '{}'".format(a["ad_name"], p))
                    text_problems += 1
            if a["format"] == "pmax":
                if not a["primary_text"] or len(a["primary_text"]) > GOOGLE_LONG_HEADLINE_MAX:
                    chk.error("{}: PMax needs a long headline of {} characters or fewer".format(a["ad_name"], GOOGLE_LONG_HEADLINE_MAX))
                    text_problems += 1
                if not any(len(d) <= 60 for d in descs):
                    chk.error("{}: PMax needs one description of 60 characters or fewer".format(a["ad_name"]))
                    text_problems += 1
        else:
            if len(a["headlines"]) > META_HEADLINE_SOFT_MAX:
                chk.warn("{}: Meta headline may get cut off: '{}'".format(a["ad_name"], a["headlines"]))
    if text_problems == 0:
        chk.ok("All Google ad text is within character limits")

    # --- tracking gate (the lesson from the 9/22 signup flow launch)
    if settings.get("tracking_verified", "").lower() != "yes":
        chk.blocker("Tracking not verified. Confirm the Meta pixel/CAPI trial event fires on signup flow v3 "
                    "and matches PostHog for 7 days, then set tracking_verified = yes. Everything builds PAUSED until then.")
    else:
        chk.ok("Tracking verified against PostHog")
    return chk


# --------------------------------------------------------------------------
# 3. BUILD THE FILES
# --------------------------------------------------------------------------
def with_utms(url, source, medium, campaign, content):
    """Every ad gets UTMs so PostHog (our source of truth) can see where trials came from."""
    sep = "&" if "?" in url else "?"
    return "{}{}utm_source={}&utm_medium={}&utm_campaign={}&utm_content={}".format(
        url, sep, source, medium, campaign, content)


GOOGLE_COLUMNS = (
    ["Campaign", "Campaign Type", "Campaign Status", "Budget", "Budget type", "Bid Strategy Type",
     "Target CPA", "Target Impression Share", "Networks", "Location", "Ad Group", "Ad Group Status",
     "Keyword", "Criterion Type", "Asset Group", "Audience signal", "Ad type", "Status"]
    + ["Headline {}".format(i) for i in range(1, 16)]
    + ["Description {}".format(i) for i in range(1, 5)]
    + ["Long headline 1", "Business name", "Final URL", "Path 1", "Path 2"]
)


def build_google(settings, campaigns, groups, ads, status):
    days = float(settings["days_in_month"])
    rows = []

    def row(**kw):
        r = {col: "" for col in GOOGLE_COLUMNS}
        for k, v in kw.items():
            r[k.replace("_", " ")] = v
        rows.append(r)

    for c in [c for c in campaigns if c["platform"] == "google"]:
        name = c["campaign"]
        is_pmax = c["campaign_type"] == "Performance Max"
        # Campaign: its own daily budget (no more shared budget)
        r = {col: "" for col in GOOGLE_COLUMNS}
        r.update({
            "Campaign": name, "Campaign Type": c["campaign_type"], "Campaign Status": status,
            "Budget": "{:.2f}".format(float(c["monthly_budget"]) / days), "Budget type": "Daily",
            "Bid Strategy Type": c["bid_strategy"], "Target CPA": c["target_cpa"],
            "Target Impression Share": c["target_impression_share"],
            "Networks": "" if is_pmax else "Google search",
        })
        rows.append(r)
        for loc in split(c["locations"]):
            row(Campaign=name, Location=loc)
        for neg in split(c["campaign_negatives"]):
            r = {col: "" for col in GOOGLE_COLUMNS}
            r.update({"Campaign": name, "Keyword": neg, "Criterion Type": "Campaign Negative Phrase"})
            rows.append(r)

        for g in [g for g in groups if g["campaign"] == name]:
            group_ads = [a for a in ads if a["campaign"] == name and a["ad_group"] == g["ad_group"]]
            if is_pmax:
                for a in group_ads:
                    r = {col: "" for col in GOOGLE_COLUMNS}
                    r.update({"Campaign": name, "Asset Group": g["ad_group"], "Audience signal": g["audience"],
                              "Status": status, "Long headline 1": a["primary_text"],
                              "Business name": settings.get("brand_name", ""),
                              "Final URL": with_utms(settings["landing_page"], "google", "cpc", name, g["ad_group"])})
                    for i, h in enumerate(split(a["headlines"])[:15], 1):
                        r["Headline {}".format(i)] = h
                    for i, d in enumerate(split(a["descriptions"])[:4], 1):
                        r["Description {}".format(i)] = d
                    rows.append(r)
                continue
            r = {col: "" for col in GOOGLE_COLUMNS}
            r.update({"Campaign": name, "Ad Group": g["ad_group"], "Ad Group Status": "Enabled"})
            rows.append(r)
            for kw, match in ([(k, "Exact") for k in split(g["exact_keywords"])]
                              + [(k, "Phrase") for k in split(g["phrase_keywords"])]
                              + [(k, "Negative Phrase") for k in split(g["negative_keywords"])]):
                r = {col: "" for col in GOOGLE_COLUMNS}
                r.update({"Campaign": name, "Ad Group": g["ad_group"], "Keyword": kw, "Criterion Type": match})
                rows.append(r)
            for a in group_ads:
                r = {col: "" for col in GOOGLE_COLUMNS}
                r.update({"Campaign": name, "Ad Group": g["ad_group"], "Ad type": "Responsive search ad",
                          "Status": "Enabled", "Path 1": a["path1"], "Path 2": a["path2"],
                          "Final URL": with_utms(settings["landing_page"], "google", "cpc", name, g["ad_group"])})
                for i, h in enumerate(split(a["headlines"])[:15], 1):
                    r["Headline {}".format(i)] = h
                for i, d in enumerate(split(a["descriptions"])[:4], 1):
                    r["Description {}".format(i)] = d
                rows.append(r)
    return rows


META_COLUMNS = [
    "Campaign Name", "Campaign Status", "Campaign Objective", "Buying Type", "Campaign Daily Budget",
    "Campaign Bid Strategy", "Ad Set Name", "Ad Set Run Status", "Ad Set Daily Budget", "Optimization Goal",
    "Conversion Event", "Countries", "Age Min", "Age Max", "Advantage Audience", "Custom Audiences",
    "Excluded Custom Audiences", "Ad Name", "Ad Status", "Title", "Body", "Link Description", "Link",
    "URL Tags", "Call to Action", "Creative File",
]


def build_meta(settings, campaigns, groups, ads, status):
    """Meta bulk import is flat: one row per ad, with its campaign and ad set details repeated."""
    days = float(settings["days_in_month"])
    camps = {c["campaign"]: c for c in campaigns if c["platform"] == "meta"}
    grps = {(g["campaign"], g["ad_group"]): g for g in groups if g["platform"] == "meta"}
    rows = []
    for a in [a for a in ads if a["platform"] == "meta"]:
        c = camps[a["campaign"]]
        g = grps[(a["campaign"], a["ad_group"])]
        campaign_budget = c["budget_level"] == "campaign"
        rows.append({
            "Campaign Name": c["campaign"],
            "Campaign Status": status,
            "Campaign Objective": "Outcome " + c["objective"],
            "Buying Type": "AUCTION",
            "Campaign Daily Budget": "{:.2f}".format(float(c["monthly_budget"]) / days) if campaign_budget else "",
            "Campaign Bid Strategy": c["bid_strategy"],
            "Ad Set Name": g["ad_group"],
            "Ad Set Run Status": status,
            "Ad Set Daily Budget": "" if campaign_budget else "{:.2f}".format(float(g["monthly_budget"]) / days),
            "Optimization Goal": "Conversions",
            "Conversion Event": "StartTrial",
            "Countries": c["locations"],
            "Age Min": g["age_min"], "Age Max": g["age_max"],
            "Advantage Audience": "On" if "Advantage" in g["audience"] else "Off",
            "Custom Audiences": "" if "Advantage" in g["audience"] else ", ".join(split(g["audience"])),
            "Excluded Custom Audiences": ", ".join(split(g["exclusions"])),
            "Ad Name": a["ad_name"],
            "Ad Status": status,
            "Title": a["headlines"],
            "Body": a["primary_text"],
            "Link Description": a["descriptions"],
            "Link": settings["landing_page"],
            "URL Tags": "utm_source=facebook&utm_medium=paid_social&utm_campaign={}&utm_content={}".format(
                c["campaign"], a["ad_name"]),
            "Call to Action": a["cta"],
            "Creative File": a["creative_file"],
        })
    return rows


def write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def write_summary(path, settings, campaigns, groups, ads, chk, status):
    low, high = float(settings["cpa_target_low"]), float(settings["cpa_target_high"])
    days = float(settings["days_in_month"])
    proj = project(campaigns)
    total = sum(p[1] for p in proj)
    trials = sum(p[3] for p in proj)
    kill_spend = float(settings["kill_spend_multiple"]) * low
    win_spend = float(settings["winner_spend_multiple"]) * low
    L = []
    L.append("# Launch summary: {}".format(settings["launch_name"]))
    L.append("")
    gate = "PAUSED until tracking is verified" if status == "PAUSED" else "Ready to enable after QA"
    L.append("**Launch status:** {}  ".format(gate))
    L.append("**Budget:** {} / month  |  **Projected trials:** ~{:.0f}  |  **Projected blended CPA:** ${:.0f} (target ${:.0f}-${:.0f})".format(
        money(total), trials, total / trials, low, high))
    L.append("")
    L.append("## Checks")
    icons = {"OK": "✅", "WARN": "⚠️", "ERROR": "❌", "BLOCKER": "⛔"}
    for level, msg in chk.items:
        L.append("- {} **{}**: {}".format(icons[level], level, msg))
    L.append("")
    L.append("## Campaigns")
    L.append("| Platform | Campaign | Monthly | Daily | Bidding | Expected CPA | Projected trials | Why |")
    L.append("|---|---|---:|---:|---|---:|---:|---|")
    for platform in ("meta", "google"):
        for c, budget, cpa, t in [p for p in proj if p[0]["platform"] == platform]:
            bid = c["bid_strategy"] + (" ${}".format(c["target_cpa"]) if c["target_cpa"] else "") + (
                " {}".format(c["target_impression_share"]) if c["target_impression_share"] else "")
            L.append("| {} | {} | {} | {} | {} | ${:.0f} | {:.0f} | {} |".format(
                platform.title(), c["campaign"], money(budget), money(budget / days), bid, cpa, t, c["why"]))
        sub = [p for p in proj if p[0]["platform"] == platform]
        sb, st = sum(p[1] for p in sub), sum(p[3] for p in sub)
        L.append("| **{} total** | | **{}** | | | **${:.0f}** | **{:.0f}** | |".format(platform.title(), money(sb), sb / st, st))
    L.append("")
    L.append("Expected CPAs come from the clean period of the last 2 months (before the 9/15 UK launch and the 9/22 tracking break). Basis for each is in `plan/campaigns.csv`.")
    L.append("")
    L.append("## Ad sets, ad groups and ads")
    for c in campaigns:
        L.append("**{}**".format(c["campaign"]))
        for g in [g for g in groups if g["campaign"] == c["campaign"]]:
            names = [a["ad_name"] for a in ads if a["campaign"] == c["campaign"] and a["ad_group"] == g["ad_group"]]
            budget = " ({} / mo)".format(money(float(g["monthly_budget"]))) if g["monthly_budget"] else ""
            kws = ["[{}]".format(k) for k in split(g["exact_keywords"])] + ['"{}"'.format(k) for k in split(g["phrase_keywords"])]
            target = ", ".join(split(g["audience"])) if g["audience"] else ("Keywords: " + ", ".join(kws) if kws else "")
            if g["exclusions"]:
                target += ". Excludes: " + ", ".join(split(g["exclusions"]))
            L.append("- `{}`{}: {}. Ads: {}".format(g["ad_group"], budget, target, ", ".join(names)))
        L.append("")
    L.append("## Rules for judging results (always use PostHog trials, not platform-reported)")
    L.append("- **Too early to judge:** under {} days or under {} spend.".format(settings["min_days_before_judging"], money(kill_spend)))
    L.append("- **Kill:** {} spent with {} trial(s) or fewer, or CPA above $400 after {}.".format(
        money(kill_spend), settings["kill_max_trials"], money(win_spend)))
    L.append("- **Winner:** at least {} spent, CPA at or under ${:.0f}, and at least {:.0f}% better than the control.".format(
        money(win_spend), low, float(settings["winner_min_improvement"]) * 100))
    L.append("- **Scale:** raise budget {:.0f}% every {} days while PostHog CPA stays under ${:.0f}. Add new hooks of the winning concept so frequency stays down.".format(
        float(settings["scale_step"]) * 100, settings["scale_every_days"], high))
    L.append("")
    L.append("## Before you press go")
    L.append("- [ ] Meta pixel + Conversions API `StartTrial` event fires on signup flow v3 (Events Manager > Test events), and matches PostHog for 7 days")
    L.append("- [ ] UTMs survive the new signup flow (direct/other trials rose after September; check nothing is stripping them)")
    L.append("- [ ] UK: conversion action fires on UK signups; review search terms before the test")
    L.append("- [ ] Audiences exist in Meta with these names: Customers_All, TrialSignups_90d, WebsiteVisitors_14d, VideoViewers_50pct_14d")
    L.append("- [ ] PMax: brand exclusion list applied; audience signals attached (not importable by file)")
    L.append("- [ ] Old shared budget `Google_Main_Shared` removed; old campaigns paused")
    L.append("- [ ] Retargeting A/B test set up in Meta Experiments (control vs new)")
    L.append("- [ ] Creative files uploaded to the Meta media library with the file names in `plan/ads.csv`")
    L.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# --------------------------------------------------------------------------
# 4. RUN
# --------------------------------------------------------------------------
def main():
    settings, campaigns, groups, ads = load_plan()
    print("\nChecking plan '{}' ...\n".format(settings["launch_name"]))
    chk = run_checks(settings, campaigns, groups, ads)
    for level, msg in chk.items:
        print("  [{}] {}".format(level, msg))

    if chk.has_errors:
        print("\nFix the ERROR items in /plan and run again. Nothing was built.\n")
        sys.exit(1)

    status = "ACTIVE" if settings.get("tracking_verified", "").lower() == "yes" else "PAUSED"
    out = os.path.join(HERE, "output", settings["launch_name"])
    os.makedirs(out, exist_ok=True)
    g_rows = build_google(settings, campaigns, groups, ads, "Paused" if status == "PAUSED" else "Enabled")
    m_rows = build_meta(settings, campaigns, groups, ads, status)
    write_csv(os.path.join(out, "google_ads_editor_import.csv"), GOOGLE_COLUMNS, g_rows)
    write_csv(os.path.join(out, "meta_bulk_import.csv"), META_COLUMNS, m_rows)
    write_summary(os.path.join(out, "launch_summary.md"), settings, campaigns, groups, ads, chk, status)

    print("\nBuilt {} Google rows and {} Meta ads (status: {}).".format(len(g_rows), len(m_rows), status))
    print("Files are in: {}\n".format(os.path.relpath(out, HERE)))


if __name__ == "__main__":
    main()
