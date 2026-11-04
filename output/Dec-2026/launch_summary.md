# Launch summary: Dec-2026

**Launch status:** PAUSED until tracking is verified  
**Budget:** $120,000 / month  |  **Projected trials:** ~467  |  **Projected blended CPA:** $257 (target $250-$280)

## Checks
- ✅ **OK**: Every campaign has ad groups, and every ad group has ads (7 campaigns, 12 ad groups, 19 ads)
- ✅ **OK**: Total budget $120,000 is within the $120,000 cap
- ✅ **OK**: Meta campaigns add up to $65,000 as planned
- ✅ **OK**: Google campaigns add up to $55,000 as planned
- ✅ **OK**: Projected blended CPA $257 is inside the $250-$280 target (~467 trials)
- ⚠️ **WARN**: META_US_CreativeTesting is expected above target ($300); cheaper campaigns offset it, so watch it weekly
- ⚠️ **WARN**: META_US_Retargeting_14d is expected above target ($335); cheaper campaigns offset it, so watch it weekly
- ⚠️ **WARN**: GOOG_US_Search_NonBrand is expected above target ($292); cheaper campaigns offset it, so watch it weekly
- ⚠️ **WARN**: GOOG_US_PMax is expected above target ($303); cheaper campaigns offset it, so watch it weekly
- ⚠️ **WARN**: GOOG_UK_Search_NonBrand_Test is expected above target ($400); cheaper campaigns offset it, so watch it weekly
- ✅ **OK**: META_US_CreativeTesting: $2,500 per test ad, enough to call a winner (needs $1,500)
- ✅ **OK**: All Google ad text is within character limits
- ⛔ **BLOCKER**: Tracking not verified. Confirm the Meta pixel/CAPI trial event fires on signup flow v3 and matches PostHog for 7 days, then set tracking_verified = yes. Everything builds PAUSED until then.

## Campaigns
| Platform | Campaign | Monthly | Daily | Bidding | Expected CPA | Projected trials | Why |
|---|---|---:|---:|---|---:|---:|---|
| Meta | META_US_Prospecting_AdvPlus | $50,000 | $1,613 | Highest volume | $245 | 204 | One prospecting campaign instead of two. AdvantagePlus ($207) and Broad ($276) targeted the same broad audience and bid against each other. Meta now rewards fewer campaigns with more creative variety. Start on highest volume while tracking recovers; test a $280 cost cap after 2 clean weeks. |
| Meta | META_US_CreativeTesting | $10,000 | $323 | Highest volume | $300 | 33 | Ad set budgets so every new concept gets a fair $2500 instead of Meta starving it. Winners graduate to the prospecting campaign. |
| Meta | META_US_Retargeting_14d | $5,000 | $161 | Highest volume | $335 | 15 | Cut from ~$10K. Worst CPA in the account, and its true cost is higher once you count the prospecting spend that first reached these people. 5-month-old creative gets an A/B test against a new ad. |
| **Meta total** | | **$65,000** | | | **$258** | **252** | |
| Google | GOOG_US_Search_Brand | $10,000 | $323 | Target impression share 95% | $148 | 68 | Own budget again. It spent ~$11K/mo on its own, and its impressions fell ~30% once UK shared the budget. Cheapest trials, and it protects our name from competitors bidding on it. |
| Google | GOOG_US_Search_NonBrand | $23,000 | $742 | Target CPA $275 | $292 | 79 | Biggest Google trial source. Own budget so UK can't drain it. Brand terms are negative so brand searches stay in the brand campaign. Keep the 40 negatives added 10/6. |
| Google | GOOG_US_PMax | $17,000 | $548 | Target CPA $280 | $303 | 56 | Pricier, but it reaches YouTube, Display, Discover and Gmail that Search can't. Brand exclusions on so it doesn't take credit for people already searching our name. |
| Google | GOOG_UK_Search_NonBrand_Test | $5,000 | $161 | Maximize conversions | $400 | 12 | Fix first, then a capped test in its own budget. Before launch: confirm UK signups fire the conversion, check search terms, tighten to exact/phrase. Pause at $2500 spent with 3 or fewer trials. |
| **Google total** | | **$55,000** | | | **$256** | **215** | |

Expected CPAs come from the clean period of the last 2 months (before the 9/15 UK launch and the 9/22 tracking break). Basis for each is in `plan/campaigns.csv`.

## Ad sets, ad groups and ads
**META_US_Prospecting_AdvPlus**
- `US_Broad_AdvantageAudience`: Advantage+ audience (no interest targeting). Excludes: Customers_All, TrialSignups_90d. Ads: Founder_UGC_v3_HookA_Problem, Founder_UGC_v3_HookB_Result, Founder_UGC_v3_HookC_Objection, UGC_Agency_Owner, Demo_Screen_Walkthrough, Static_AgentStack_Benefits, Carousel_Case_Study

**META_US_CreativeTesting**
- `Test_Customer_Testimonial` ($2,500 / mo): Advantage+ audience (no interest targeting). Excludes: Customers_All, TrialSignups_90d. Ads: Test_Customer_Testimonial_v1
- `Test_Demo_15s` ($2,500 / mo): Advantage+ audience (no interest targeting). Excludes: Customers_All, TrialSignups_90d. Ads: Test_Demo_15s_v1
- `Test_Static_ROI_Stat` ($2,500 / mo): Advantage+ audience (no interest targeting). Excludes: Customers_All, TrialSignups_90d. Ads: Test_Static_ROI_Stat_v1
- `Test_UGC_InHouse_Marketer` ($2,500 / mo): Advantage+ audience (no interest targeting). Excludes: Customers_All, TrialSignups_90d. Ads: Test_UGC_InHouse_Marketer_v1

**META_US_Retargeting_14d**
- `Visitors_and_Viewers_14d`: WebsiteVisitors_14d, VideoViewers_50pct_14d. Excludes: Customers_All, TrialSignups_90d. Ads: Retargeting_Testimonial_CONTROL, Retargeting_Founder_Proof_NEW

**GOOG_US_Search_Brand**
- `Brand_Core`: Keywords: [agentstack], [agentstack seo], [agentstack pricing], [agentstack ai], "agentstack". Ads: RSA_Brand_v1

**GOOG_US_Search_NonBrand**
- `AI_SEO_Agent`: Keywords: [ai seo agent], [agentic seo], [ai seo tool], "ai seo agent", "agentic seo software". Ads: RSA_AI_SEO_Agent_v1
- `SEO_Automation`: Keywords: [seo automation software], [automated seo tool], "seo automation". Ads: RSA_SEO_Automation_v1
- `Agency_SEO_Tools`: Keywords: [seo software for agencies], [white label seo tool], "seo tools for agencies". Ads: RSA_Agency_Tools_v1

**GOOG_US_PMax**
- `AG_SEO_Teams_and_Agencies`: Signals: customer list, site visitors, custom segment: people searching SEO software. Ads: AssetGroup_v1

**GOOG_UK_Search_NonBrand_Test**
- `UK_AI_SEO_Agent`: Keywords: [ai seo agent], [agentic seo], [seo automation software], "ai seo agent". Ads: RSA_UK_AI_SEO_Agent_v1

## Rules for judging results (always use PostHog trials, not platform-reported)
- **Too early to judge:** under 7 days or under $750 spend.
- **Kill:** $750 spent with 1 trial(s) or fewer, or CPA above $400 after $1,500.
- **Winner:** at least $1,500 spent, CPA at or under $250, and at least 20% better than the control.
- **Scale:** raise budget 20% every 3 days while PostHog CPA stays under $280. Add new hooks of the winning concept so frequency stays down.

## Before you press go
- [ ] Meta pixel + Conversions API `StartTrial` event fires on signup flow v3 (Events Manager > Test events), and matches PostHog for 7 days
- [ ] UTMs survive the new signup flow (direct/other trials rose after September; check nothing is stripping them)
- [ ] UK: conversion action fires on UK signups; review search terms before the test
- [ ] Audiences exist in Meta with these names: Customers_All, TrialSignups_90d, WebsiteVisitors_14d, VideoViewers_50pct_14d
- [ ] PMax: brand exclusion list applied; audience signals attached (not importable by file)
- [ ] Old shared budget `Google_Main_Shared` removed; old campaigns paused
- [ ] Retargeting A/B test set up in Meta Experiments (control vs new)
- [ ] Creative files uploaded to the Meta media library with the file names in `plan/ads.csv`
