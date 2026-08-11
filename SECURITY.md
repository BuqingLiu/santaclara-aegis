# Security & Compliance

## Scenario data integrity
- Every scenario ships with a **20 Hz CARLA telemetry CSV** recorded from a real simulation run — not hand-crafted numbers.
- Each run is **reproducible**: the bundled `run_*.py` script replays the exact scenario in CARLA 0.9.16.
- A **compliance JSON** maps the scenario to EU NCAP 2026/2030, ISO 21448 (SOTIF), and UN-R157 requirements.

## How we validate
1. Define the triggering condition and Operational Design Domain (ODD).
2. Run the scenario in CARLA with ego + actors; log telemetry.
3. Annotate risk and SOTIF validation targets.
4. Peer-review the annotation before release.

## Reporting a vulnerability or data issue
- Email **8069dg@163.com** with subject `SECURITY: <short description>`.
- We acknowledge within 2 business days and provide a remediation timeline.

## Licensing & revenue integrity
- All payments are processed through verified channels (PayPal `paypal.me/LiuXiaochu2`, WeChat QR).
- We do **not** fabricate usage, payment, or compliance figures. Paid status reflects only real received payments.
