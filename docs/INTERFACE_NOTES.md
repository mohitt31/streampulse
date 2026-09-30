# Browser field-check interface

The field-check profile derives from the pinned OAH `ObservationIndicatorsOah`. Each measurement is a separate final Observation with an OAH Location subject, demo Organization performer, actual user-supplied `effectiveDateTime`, and a required UCUM Quantity: temperature `Cel`, dissolved oxygen `mg/L`, optional saturation `%`. Local codes identify measurements; they are not asserted to be official OAH terminology. Demo tags and narratives prevent supplied values from being presented as verified field visits.

`Observation.basedOn` in R4 does not allow Communication. A spot measurement is not calculated from a forecast, so `derivedFrom` would misstate lineage. Required notes instead identify the alert, acknowledgement and matching target-day forecast URNs. The acknowledgement uses `Communication.inResponseTo`. Measurement Provenance targets the measurement Observations and names the demo organization; the entry timestamp and measurement timestamp remain distinct.

`buildFieldCheckBundle` is pure: no clock, network, random IDs or browser storage. It accepts the alert, its watch forecast Observations, acknowledgement, measurements, site context and model version. Site context includes the original Location and supporting resources. `scripts/pack_field_check_context.py` reads frozen inputs and reuses `fhir_export.py` resources and their dependency closure; it does not rerun training or rewrite reports. Forecast IDs, precision, extensions, model Device, input Observations and provenance are preserved.

New identifiers use the Python exporter's UUIDv5 namespace and canonical JSON scheme. Numeric measurement identity values are serialized as strings to avoid Python/JavaScript float spelling differences. Tests compare shared Location, Organization, alert and acknowledgement identifiers directly against Python. The collection Bundle is deterministic for identical inputs.

The builder rejects invalid times, values, mismatched sites/model versions/watch target dates and unresolved references. UTC times must include seconds and a timezone. The UI explicitly labels its datetime input UTC and supplies the actual submission timestamp as `recorded_at`; deterministic fixtures may supply an explicit timestamp. Optional saturation is omitted when blank and can exceed full saturation.

A spot reading is compared only to the matching forecast target day. Its difference from a daily mean is descriptive, not forecast error, biological validation or a reopened test. Dissolved oxygen is not forecast. Measurements remain in view memory; the download is the only durable field-check output. No sandbox POST, app dispatch or field visit is claimed.

## Reproduce without modifying reports

```sh
python3 scripts/pack_field_check_context.py --demo --output artifacts/field-check-context.json
node --experimental-strip-types scripts/build_field_check_demo.mjs artifacts/field-check-context.json artifacts/field-check
node --experimental-strip-types --test web/tests/fhirFieldCheck.test.mjs
bash scripts/validate_fhir.sh --field-check artifacts/field-check
```

The official validator checks examples with and without optional saturation. The negative example removes only the DO Quantity's required display unit and must fail for that cardinality violation. CI retains OperationOutcomes separately from existing reports. Browser CI exercises the form, invalid target dates, JSON download, absence of transmission, and axe checks in desktop light/dark and mobile layouts.

To rebuild the static browser context after an authorized change to source exports: `python3 scripts/pack_field_check_context.py`. Existing frozen reports remain read-only.
