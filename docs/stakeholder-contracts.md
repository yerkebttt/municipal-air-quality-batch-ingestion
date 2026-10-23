# Stakeholder and usage contracts

## Production scenario

A municipality receives an hourly export from its calibrated air-quality monitoring network. This pipeline validates, quality-labels and stores each station-hour so that authorised systems can query the result. The historical UCI Beijing files are only a test fixture for volume, missingness and replay. They are not presented as live municipal data or proof about another city.

The contracts below define who uses the data, which action they perform, what the pipeline must provide and how the prototype can be accepted or rejected. This turns stakeholder needs into explicit data and system characteristics.

## 1. Public dashboard developer

- **Action:** show the latest station conditions and a pollutant trend.
- **Input:** station, pollutant and date window.
- **Output:** latest 24 station-hours or daily minimum, mean, maximum and observation count; each record carries timestamp and quality status.
- **Freshness and granularity:** hourly after an agreed municipal export; daily values are derived for trend display.
- **Quality rule:** absence stays absence. A dashboard must not display an absent reading as zero, and warning status must remain available to the presentation layer.
- **Performance target:** each representative query completes within 2,000 ms in the stated single-user local prototype.
- **System implications:** timezone-aware timestamps, stable shared fields, flexible measurements, and a compound `{station, timestamp}` index.

## 2. Environmental analyst

- **Action:** investigate trends, data gaps and implausible readings before drawing a conclusion.
- **Input:** station, pollutant, period and optional quality status.
- **Output:** raw retained values, provenance, explicit warning reasons, completeness and aggregates with observation counts.
- **Quality rule:** the loader may flag a readable value but must not silently correct or remove it. A structurally unusable row goes to quarantine with a reason.
- **Failure condition:** missing provenance, hidden imputation or an aggregate without its observation count.
- **System implications:** embedded quality metadata, a configurable screening policy and separate rejected-record storage.

## 3. City planner and policy team

- **Action:** compare stations or equivalent periods when discussing a traffic, zoning or other intervention.
- **Input:** one pollutant, a clearly stated time window and all relevant stations.
- **Output:** per-station minimum, mean, maximum and observation count.
- **Interpretation boundary:** the pipeline supports comparison, not causal attribution. Station siting, sensor calibration, weather, spatial coverage and the selected averaging period must be reviewed by domain specialists.
- **Performance target:** the one-month, twelve-station reference comparison completes within 2,000 ms locally.
- **System implications:** cross-station time indexing, common timezone handling, source limitations and counts beside every aggregate.

## 4. Data steward and operator

- **Action:** decide whether a run is complete, safe to replay and suitable for downstream use.
- **Input:** run identifier, status, heartbeat, source count, accepted/warning/rejected counts, inserted/existing counts and benchmark history.
- **Output:** an auditable terminal state of `succeeded` or `failed` and enough evidence to diagnose a problem.
- **Reliability rule:** source rows must equal classified rows and stored plus quarantined rows. The configured fixture count must also match.
- **Recovery rule:** deterministic station-time IDs and insert-only upserts make retry and full replay idempotent. Transient database errors use bounded exponential backoff.
- **Failure condition:** a counter mismatch, unexpected source size, stale running state or missed query target.
- **System implications:** `ingestion_runs`, heartbeats, reconciliation before success, quarantine and stored query benchmarks.

## 5. Authorised warning officer

- **Action:** review possible threshold cases before any separate notification workflow.
- **Input:** quality-accepted readings and a locally approved, versioned policy owned by a named authority.
- **Output:** review candidates only.
- **Safety rule:** screening ranges are technical plausibility checks and are not health thresholds. The included threshold file is marked `example_not_approved`.
- **Failure condition:** any automatic public notification, use of an unapproved policy, or claim that a candidate is a health diagnosis.
- **System implications:** policy status is visible, candidate generation is isolated from ingestion, and no notification channel exists in this prototype.

## Acceptance evidence and limits

The complete Docker run accounted for all 420,768 source rows: 383,964 were accepted, 36,804 retained with warnings and zero were structurally rejected. The four representative queries passed the 2,000 ms local target; the slowest was the data-steward quality summary at 221.352 ms. These are repeatable prototype observations, not a production guarantee.

Production acceptance still requires stakeholder interviews and sign-off, a municipal station registry, calibration and maintenance history, a signed source manifest, approved aggregation and alert policy, authentication, TLS, backups, replication and concurrent-load testing.
