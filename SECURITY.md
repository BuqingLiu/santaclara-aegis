# Security Policy

## Reporting a vulnerability

If you discover a security issue in the **open reference layer** of SantaClara
Aegis, please report it privately rather than opening a public issue.

- Email: **security@santaclara-aegis.example** (replace with your intake alias)
- Include a description, reproduction steps, and impact.
- We aim to acknowledge within **3 business days** and provide a remediation
  timeline.

## Scope

- In-scope: the reference-layer code and sample data in this repository.
- Out-of-scope: the proprietary `elite/` engine and the managed simulation
  service, which are covered under separate commercial agreements and their
  own security review.

## Protected secrets

This repository contains **no secrets, tokens, or client data**. The
proprietary engine and any client-specific map extracts are delivered through
the subscription channel, never committed here.
