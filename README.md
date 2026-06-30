# Module 11 — Applied Lab: Service Monitoring

Add a full observability layer to the M10 backend — three Prometheus metric
families (counter, histogram, gauge), three middleware layers (request-id,
structured logging, metrics), and a `/metrics` endpoint mounted via
`prometheus_client.make_asgi_app()`. Verify end-to-end with a 3-question RAG
smoke evaluator.

The published Applied Lab guide is the canonical task list. See
TalentLMS → Module 11 → Applied Lab for the link, or check your cohort's
Slack pinned message.

## What ships here