# Factory Evidence: lablab submission kit (AMD ACT III)

Deadline: **18.10.2026, 10:00 UTC = 15:00 Tashkent**. Target: submit by **12:00 Tashkent**. Only the team leader (Sardor_R) can submit.

> Before submitting:
> - Re-run `python scripts/export_static.py && python scripts/build_deck.py` after live AMD runs, so every number comes from the app.
> - Replace the PENDING row on slide 5 with the measured values.
> - Open the repo in an incognito window to check it is public and that the MIT licence shows in the About box.

## Form fields

**Project title** (≤ 60):
> Factory Evidence: verified CBAM savings on AMD

**Short description** (≤ 150, 147 chars):
> Reads steel suppliers' emissions documents in any language with open models on AMD, checks them against EU CBAM tables and cuts carbon border cost.

**Track:** Track 1 · Intelligent Industry. Partner prizes: Evolus Business Agents on AMD + Google (if confirmed eligible).

**Technology tags:** AMD Token Factory · AMD ROCm · Gemma · Evolus · FastAPI · Python · Docker

**Long description:**

> **Problem.** Since 1 January 2026 the EU Carbon Border Adjustment Mechanism (CBAM) charges every tonne of imported steel, aluminium, cement and fertiliser for its embedded emissions. If the foreign mill cannot prove its emissions, the importer must use the EU default value plus a mark-up that rises from 10% to 30% by 2028. For slab from Indonesia that is about €636 per tonne in 2026. With verified supplier data it is about €63 (official EC tables). Italy has 2,400+ authorised CBAM declarants. The evidence exists, but it is buried in supplier scans and email threads in Chinese, Turkish, Indonesian, Ukrainian or Vietnamese.
>
> **What it does.** Factory Evidence runs that intake end to end:
> 1. Read: an open model served on AMD reads each supplier document in any language and returns every field together with the verbatim line it came from.
> 2. Check: deterministic rules, not the model, validate each value against the official EC tables. They check accredited verification, plausibility against the EU benchmark for the production route, arithmetic, reporting period and origin.
> 3. Decide: every document ends in one of three outcomes, ACCEPT, NEEDS SUPPLIER or NEEDS HUMAN. Nothing is auto-accepted when the numbers do not add up.
> 4. Act: an Evolus agent, "CBAM Supplier Follow-up", running on the space's own model (Gemma-4-31B-IT on AMD), writes the request to the supplier in the supplier's own language from the validator's facts and a CBAM rules knowledge library. The Evolus AI Tool "anonymize" removes personal data from the evidence file before it goes to the auditor. A person approves every request in the app before anything is sent.
> 5. Count: the agent shows € exposure per supplier and per quarter: at the EU default, with the evidence already verified, and if pending suppliers verify.
>
> Module B covers Transizione 5.0 energy evidence. A baseline regression (production, weather, hour of week) measures an efficiency retrofit with a 95% interval and drafts the note for the certified energy manager. No language model touches the numbers.
>
> **Built on AMD.** Every model call goes to Gemma-4-31B-IT served on AMD infrastructure (AMD Token Factory), both from the app and from the Evolus agent, which is connected to the same AMD endpoint as the space's own model. Confidential trade documents never go to a closed API. The demo shows a live AMD inference panel with latency per page and tokens per second.
>
> **Measured this week:**
> - field accuracy on 6 supplier documents in 6 languages: 65/66 (98.5%) in the last run, 92.4–98.5% over 5 full runs
> - 0 false accepts in 30 documents; decisions 6/6 in the last run
> - the model misread a CN code 3 times in 30 reads; the rules caught it every time and never auto-accepted, and a rules-guided re-read fixed it once
> - median 19–55 s per page on the shared AMD endpoint, 6 documents in 54–109 s with 4 in parallel
> - Evolus: 3/3 supplier requests written by the agent on the AMD model, 9/9 Evolus API calls OK
> - CBAM calculator matches the verified reference model in 18/18 cases within €1/t
> - 123 countries of official EC default values parsed
> - energy module recovers 7.19% against a true saving of 7.20% (95% interval 6.92–7.47%)
> - 34/34 tests, Docker, MIT
>
> **Honest limits.** The demo documents and meter data are synthetic. Prices after 2026 are scenarios, not forecasts. The declaration remains the responsibility of the authorised declarant and the accredited verifier.
>
> **Business model.** SaaS for CBAM declarants plus a fee per verified tonne, priced at a small fraction of the saving: 1,000 t of Indonesian slab saves about €572k. Sold through customs brokers, CBAM consultants and audit firms, with Evolus as the delivery layer for Italian SMEs. Next: the same intake for EUDR (December 2026) and the battery Digital Product Passport (February 2027).
>
> Built solo by Sardor Razikov (AMD Developer Hackathon ACT I: 1st place, AI Agents).

**Links:**
- Repo: https://github.com/SRKRZ23/factory-evidence
- Demo: https://factory-evidence.netlify.app
- Slides: `deck/Factory_Evidence_deck.pdf`
- Cover: `assets/team_cover_16x9.png` (or a dedicated submission cover)
- Video: YouTube, unlisted or public

## Video: 2:45, live app on screen at least 60% of the time

The voice-over is written first. Record it per segment (your own voice is preferred; the fallback is TTS, as in ACT I). Captions are burned in, music sits at −25 dB, export is 1080p30 H.264 at about 6 Mbps (under 300 MB). **In CapCut, tick the Audio checkbox on export.**

| Time | On screen | Voice-over |
|---|---|---|
| 0:00–0:12 | Slide 1, then the KPI strip of the app | "An Italian steel importer is paying ten million euros in carbon border tax this quarter. Most of it is avoidable, because the proof is already in their inbox. This is Factory Evidence." |
| 0:12–0:35 | Slide 2: the default table | "Since January, CBAM charges every imported tonne. If the foreign mill cannot prove its emissions, the importer pays the EU default: six hundred thirty-six euros per tonne of Indonesian slab, versus sixty-three with verified data. The evidence exists, in scans in Chinese, Turkish, Indonesian." |
| 0:35–1:05 | App: click Indonesia. Scan, then fields with quotes, then ACCEPT, then €636 → €63 | "The model, running on AMD, reads the certificate in Indonesian and quotes the exact line behind every number. Then rules, not the model, check it against the official EU tables: verified, plausible for a blast-furnace route, arithmetic consistent. Accepted. Six hundred thirty-six becomes sixty-three." |
| 1:05–1:30 | App: click Ukraine. NEEDS HUMAN, implausible flag | "This Ukrainian mill claims 0.35 tonnes of CO2 per tonne of slab, a quarter of the EU benchmark for its route. Too good to be true, so it goes to a person, not into the declaration." |
| 1:30–1:55 | App: click India. NEEDS SUPPLIER, letter in the supplier's language, Evolus workflow | "India: the numbers are plausible but self-declared. The agent writes to the supplier in their language, saying exactly what is missing and what it costs, and Evolus runs the follow-up." |
| 1:55–2:15 | App: AMD inference panel and slide 5 | "Everything runs on open models served on AMD: [N] pages per minute, [X] seconds per page, confidential trade data never leaves for a closed API. Our calculator matches the reference model in 18 of 18 cases." |
| 2:15–2:32 | Slide 6, then slide 7 | "Across one quarter: €10.7 million at defaults, €3.6 million with the evidence already accepted. Priced at a fraction of the saving, sold through customs brokers and CBAM advisors." |
| 2:32–2:45 | Slide 9 plus links | "The model reads, rules decide, a person approves. I'm Sardor Razikov. I won ACT I with RepoMind, and this week I built Factory Evidence. Repo and demo are linked below." |

## After submitting

- LinkedIn and X post with the demo GIF and link, using the hashtags #AMD #ROCm #lablab and the event hashtag.
- Post in the Discord showcase channel. Split the links across messages to avoid automod.
