# KAIZEN Manufacturing Data Contract v1.0

## Principle

KAIZEN is source-agnostic only **after** plant data is mapped into a canonical observable schema. The adapter may rename fields and derive only documented structural fields. It may not invent missing process signals.

The current full engine requires 30 source-observable fields. `unit_index` and `total_processing_s` may be deterministically derived.

Query the authoritative runtime contract at:

```text
GET /api/data/contract
```

## Modes

- DEMO — deterministic Hidden Factory with sealed truth.
- FILE — CSV/JSON history.
- REPLAY — historical data played in sequence.
- LIVE — HTTP event session buffer finalized into an analysis run.

## Live integration pattern

```text
PLC / MES / SCADA / historian / SQL / MQTT-Kafka bridge
                         ↓
                plant-specific adapter
                         ↓
          KAIZEN Manufacturing Data Contract
                         ↓
        schema validation + readiness assessment
                         ↓
              canonical observable events
                         ↓
  LSS / IE / investigator / simulation / optimizer / AI
```

KAIZEN itself currently exposes an HTTP live-ingestion boundary. A production MQTT/Kafka/OPC-UA connector belongs in the plant-specific adapter layer rather than being hard-coded into the analytics core.

## Real-world causality

External data does not have a hidden simulator answer. KAIZEN therefore blocks synthetic reveal and synthetic DOE execution for FILE/REPLAY/LIVE runs. A physical experiment must be approved/executed outside KAIZEN and its resulting measurements ingested for evaluation.
