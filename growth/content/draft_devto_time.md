---
title: "Why ADAS Teams Burn 8 Weeks on Edge-Case Scenarios (and a Faster Path)"
published: true
tags: autonomousvehicles, testing, productivity, selfdriving
---

# Why ADAS Teams Burn 8 Weeks on Edge-Case Scenarios (and a Faster Path)

Ask any AV validation lead how long scenario libraries take and the answer is usually a wince: **6 to 10 weeks** for a first credible set. Here is where that time actually goes — and how to claw most of it back.

## Where the 8 weeks disappear
1. **Taxonomy design (1–2 wks).** Agreeing on what "safety-critical" means across functions.
2. **Scripting each scenario (3–4 wks).** CARLA world setup, actor behavior, weather, seeds.
3. **Telemetry wiring (1–2 wks).** Ego state, TTC, actor trajectories, ground truth.
4. **Compliance tagging (1 wk).** Mapping each case to EU-NCAP / ISO 21448 / UN-R157.
5. **Review & rework (1–2 wks).** Auditors send it back; you loop.

None of this is hard. All of it is slow and repetitive.

## The faster path
Treat scenario building like a library, not a project:
- Start from a **curated set of 23 proven safety-critical scenarios** rather than a blank page.
- Each ships with telemetry CSV + reproducible script + compliance tags — ready to drop into CI.
- Customize only the cases unique to your ODD.

## What "faster" buys you
- Validation starts in days, not months.
- Engineers spend time on *your* vehicle behavior, not boilerplate world setup.

## A sanity check before you buy
A good scenario library should let you:
- Reproduce a case deterministically (same seed → same run).
- Export telemetry you can diff across firmware versions.
- Show the SOTIF / NCAP clause each case covers.

---

### Try it in 5 minutes
We publish a free, fully reproducible sample (night pedestrian-crossing) with telemetry and compliance tags, and a full 23-scenario library for teams that want to skip the build. Custom packs are scoped by the SantaClara Aegis team on request.

Which part of your validation timeline hurts most? Message the team and we'll point you at the shortest fix.
