# CrashLens Pushgateway Stale Metrics Cleanup Runbook

## Selective Cleanup (Per Job/Group)

### Delete metrics for a specific job
curl -X DELETE http://localhost:9091/metrics/job/crashlens_scan

### Delete metrics for job with grouping labels
curl -X DELETE http://localhost:9091/metrics/job/crashlens_scan/project/my-project

## Admin Wipe (Emergency Reset)

### WARNING: Deletes ALL metrics
curl -X PUT http://localhost:9091/api/v1/admin/wipe

### Verify deletion
curl http://localhost:9091/metrics | grep crashlens

## Operational Best Practices

1. Post-run cleanup with timestamped jobs
2. Scheduled cleanup for stale metrics (7+ days)
3. Pre-deployment wipe for clean state
4. Monitor Pushgateway size periodically

## Security Note
- Run on private network only
- Use authentication (--web.enable-admin-api)
- Restrict DELETE access via reverse proxy
