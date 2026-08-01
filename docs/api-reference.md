# API Reference

The proprietary `elite/` engine and datasets are delivered to subscribers
through a versioned REST API and the managed simulation service. This document
describes the **contract**; concrete endpoints, auth, and SDKs are provisioned
per subscription.

> The open repository does not contain live credentials. Use the
> [sales page](https://github.com/BuqingLiu/santaclara-aegis) to request API
> access.

## Authentication

```
Authorization: Bearer <SUBSCRIBER_TOKEN>
```

Tokens are scoped per organization and rotated on a schedule.

## Endpoints (contract)

### List scenarios
`GET /v1/scenarios`

Returns the 23 scenario classes with metadata (mirrors
[`samples/scenario-manifest.sample.json`](../samples/scenario-manifest.sample.json)).

### Retrieve a dataset
`GET /v1/runs/{run_id}/scenarios/{key}/dataset`

Streams the per-scenario package: `telemetry.csv`, `events.json`,
`frames/*.png`, `summary.json` (see [`data-schema.md`](data-schema.md)).

### Request a simulation run
`POST /v1/runs`

```json
{
  "scenarios": ["pedestrian_crossing", "cut_in", "emergency_vehicle"],
  "odd": { "map": "el_camino_lawrence", "weather": "ClearNoon", "duration_s": 40 },
  "report": "dmv_compliance"
}
```

### Fetch compliance report
`GET /v1/runs/{run_id}/report`

Returns the DMV-style compliance report (PDF/MD) for the run.

## Webhooks (managed service)

For the managed simulation service, completed runs can post a webhook with the
run summary and a signed report URL.

## Rate limits & SLA

Tiers define concurrency, monthly scenario volume, and SLA — see the
[sales page](https://github.com/BuqingLiu/santaclara-aegis) pricing table.
