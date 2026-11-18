# Request Shield bug report

2026-10-25

The Shield tab is broken by a Flutter request loop, a missing ML model, and a
Platform logger that records the app's own calls. The database currently holds
1,023 request logs. All are `PLATFORM`, all are `UNCLASSIFIED`, and 942 of them
are the app polling `.../request-shield/requests/` within about 13 minutes.

## How Request Shield works

Every observed HTTP request becomes a `RequestLog` row. The Celery task
`sanitize.classify_request_batch` sends unclassified rows to the ML service
(`POST /classify-requests`), which labels them GREEN, GRAY or RED. GRAY rows
can be escalated to Gemini. IPs with repeated RED/GRAY hits produce threat
suggestions.

| Source | Meaning | How it gets in |
| --- | --- | --- |
| `EXTERNAL` | Inbound traffic to a web server on a monitored machine (visitors, bots, attackers) | `infra-monitor-request-forwarder` (installed by `install.sh`) reads `/var/log/nginx/access.log` every 5 s and POSTs to `/api/internal/request-logs/` |
| `PLATFORM` | Traffic to the Infra-Monitor backend itself | `backend/sanitize/middleware.py` records every `/api/organizations/<id>/...` request |

`EXTERNAL` does not cover metrics or outbound calls from monitored services.
CPU, memory and container data go through Alloy to the metrics/anomaly side.

## Issues at a glance

| # | Issue | Priority | Where |
| --- | --- | --- | --- |
| 1 | Recent Requests spins forever and re-fetches in a loop | High | `frontend/lib/features/request_shield/presentation/pages/request_shield_page.dart` |
| 2 | Platform tab fills with the app's own API calls | High | `backend/sanitize/middleware.py` |
| 3 | No Request Shield model installed, so every row stays PENDING | High (setup) | ML service artifacts |
| 4 | External ingestion only reads a hardcoded nginx path and fails silently | Medium | `backend/installer/install.sh` |
| 5 | Zone filter chips do nothing | Low | `request_shield_page.dart` |
| 6 | Analytics ignores the source filter for charts | Low | `backend/sanitize/views.py` |

## 1. Recent Requests spinner and request loop

`request_shield_page.dart:32-34`:

```dart
final logs = ref.watch(shieldRequestLogsProvider(
  source != null ? {'source': source} : {},
));
```

`shieldRequestLogsProvider` is a `family` keyed by `Map<String, String>`. Dart
`Map`s compare by identity, so every `build` creates a new key and a new
provider instance. The result is a loop:

1. The new provider starts loading, which shows the spinner.
2. The data arrives, and the page (which watches it) rebuilds.
3. The rebuild creates a new Map, so a new provider starts loading again.

Each fetch is also recorded by the Platform middleware (issue 2), so the
request count climbs for as long as the tab is open.

**Fix**

- Key the family with a value-equal type, e.g. a record
  `({String? source, String? zone})`, or a small class with `==`/`hashCode`.
  Alternatively, make it a plain provider that `ref.watch`es
  `shieldSourceFilterProvider` and the zone filter provider itself.
- Optional: in `shared/widgets/async_value_view.dart`, keep showing previous
  data while refreshing (`skipLoadingOnRefresh` / `skipLoadingOnReload`)
  instead of a spinner.

## 2. Platform tab records the app's own traffic

`RequestShieldMiddleware` logs every org-scoped API call, including the Shield
tab's own polling (`analytics/` every 30 s, `requests/`, `suggestions/`) and
normal screens (`overview/`, `servers/`, `anomalies/`). Real suspicious traffic
to the backend gets buried under normal app usage.

The class docstring (`middleware.py:35`) says recording only happens when
`ShieldConfig.platform_self_monitor` is enabled. The code never checks it.

**Fix**

- Check `ShieldConfig.platform_self_monitor` for the org before recording
  (cache it so it isn't a DB query per request).
- Skip at least `/request-shield/` paths, so viewing logs doesn't create logs.
- Optionally skip authenticated `GET`s from the app, and keep failed auth,
  4xx/5xx, writes and anonymous requests.
- Recording runs synchronously in the request path (one `INSERT` per request),
  despite the "fire-and-forget" comment. Consider moving it to Celery or a
  bulk buffer.

## 3. No Request Shield model installed

The Celery worker logs this every 30 s:

```
POST http://ml_service/classify-requests "HTTP/1.1 404 Not Found"
ML service classification failed for org=... batch=100
```

`model/app/main.py:179-186` returns 404 `request_shield_model_not_found`
because nothing exists at `/code/artifacts/request_shield/` in the ML
container. So every row stays `UNCLASSIFIED` (shown as PENDING). Gemini
escalation and threat suggestions depend on classification, so they are empty
too.

**Fix**

- Train and install the artifact following
  `docs/sanitize/request-shield-model-runbook.md`.
- Make sure `GET /ready` on the ML service reports the Request Shield model as
  loaded afterwards.
- Nice to have: log the 404 once with a clear "model not installed" message
  instead of a full stack trace every 30 s.

## 4. External ingestion depends on a hardcoded nginx path

The forwarder in `install.sh` only reads `/var/log/nginx/access.log`
(`ACCESS_LOG_PATH` is hardcoded in `forwarder.env`). If the file doesn't exist,
`run_once()` returns with no log output. On a test machine with no nginx
(e.g. WSL), External stays empty with no hint why.

To test today: install nginx on the monitored machine
(`sudo apt install -y nginx && sudo service nginx start`) and send it requests.

**Fix**

- Make the log path configurable at install time (e.g. `--access-log PATH`,
  allow several paths).
- Log a warning once when the file is missing or unreadable.
- Document that the parser expects nginx/Apache "combined" format.

## 5. Zone filter chips do nothing

`request_shield_page.dart:199-207`: the tap handler builds a `filters` map,
never uses it, and invalidates the provider. The `zone` value never reaches the
API. This goes away if issue 1 is fixed by having the provider read the zone
filter.

## 6. Analytics ignores the source filter for charts

`backend/sanitize/views.py:45-55`: `zone_distribution`, `top_offending_ips`
and `zone_trend` don't receive `source`. Only `total_requests` is filtered, so
the External tab's charts would still include Platform data. Pass `source`
into those helpers in `services.py` and filter there.

## Verify the fix

- [ ] With the Shield tab open, the request count grows by a few per minute, not hundreds.
- [ ] Recent Requests shows the list without a constant spinner.
- [ ] Zone chips change the list.
- [ ] With `platform_self_monitor` off, no new PLATFORM rows appear.
- [ ] Opening the Shield tab never creates PLATFORM rows for `/request-shield/` paths.
- [ ] Celery worker logs show classified batches instead of 404s.
- [ ] Rows show SAFE / SUSPICIOUS / MALICIOUS instead of PENDING.
- [ ] With nginx on the monitored machine, `curl` requests appear under External within about 5 s.
- [ ] Switching the External/Platform tab changes the charts, not just the total.
- [ ] Delete the existing loop-generated PLATFORM rows after the fix so stats start clean.
