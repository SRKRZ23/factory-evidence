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
> **Honest limits.** The demo documents and meter data are synthetic. Prices after 2026 are scenarios, not forecasts. The declaration remains the responsibility of the authorised declarant and the accredited verifier. The model makes mistakes: it misread a CN code 3 times in 30 reads, and the rules caught every one (0 false accepts). Quotes are transcribed by the model; in 1 of 66 fields a quote had a typo while the value was correct. Token Factory is a shared, rate-limited endpoint (19–55 s per page); a dedicated vLLM on AMD Developer Cloud is the production path.
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

## Video (final cut, 2:18)

Files: `~/Desktop/Factory_Evidence_demo.mp4` (1920×1080, 30 fps, H.264 + AAC, 36 MB) and `Factory_Evidence_demo.srt` (captions for YouTube).
Built from the live screen recording of 16.10.2026: voice-over (TTS, as in ACT I) and burned-in captions; the API key is never on screen.

| Time | On screen | Voice-over |
|---|---|---|
| 0:00–0:09 | Slide 1 | CBAM since January 2026 charges every imported tonne of steel. |
| 0:09–0:24 | Slide 2 | No proof of emissions → EU default: €636/t for Indonesian slab; evidence buried in scans in five languages. |
| 0:24–0:42 | App · Indonesia | Gemma on AMD reads the scan and quotes the line behind every value; rules check it against the EU tables; ACCEPT, €636 → €63. |
| 0:42–0:58 | App · Viet Nam | Missing CN code, route, verifier → NEEDS SUPPLIER; the Evolus agent on the same AMD model writes the request in Vietnamese; a person approves. |
| 0:58–1:04 | App · auditor file | Evolus AI Tool "anonymize" strips personal data. |
| 1:04–1:19 | App · Ukraine + quarter | 0.35 t/t below half the benchmark → NEEDS HUMAN; quarter €10.7M → €3.6M. |
| 1:19–1:31 | App · Module B | Transizione 5.0: 7.19% saving, 95% interval. |
| 1:31–1:44 | Terminal · live benchmark | 65/66 fields, 6/6 decisions, 0 false accepts, 9/9 Evolus calls. |
| 1:44–1:56 | Slide 5 | Where it fails: CN code misread 3 of 30 reads, caught every time. |
| 1:56–2:04 | Evolus | Agent on the space's own model on AMD, rules library, AI Tools. |
| 2:04–2:09 | Token Factory usage | 108 requests, 0 errors. |
| 2:09–2:18 | Slide 9 | The model reads, the rules decide, a person approves. |

## After submitting

- LinkedIn and X post with the demo GIF and link, using the hashtags #AMD #ROCm #lablab and the event hashtag.
- Post in the Discord showcase channel. Split the links across messages to avoid automod.
