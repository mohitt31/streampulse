# StreamPulse FHIR evidence

The exporter creates a self-contained FHIR R4 collection Bundle: OAH-profiled Location and input Observations, locally derived forecast Observations, model Devices, prepared-alert Communications, demonstration acknowledgement Communications and Provenance. Forecast origin is a simulated time; `issued` and Provenance record actual generation. Source-calendar dates retain date precision. Source timezone and historical publication latency remain UNVERIFIED.

This is an experimental local implementation, not HL7/OAH endorsement. No Patient, clinical RiskAssessment, field visit or delivered alert is fabricated. The browser field-check builder reuses the original Python-exported forecast resources and their dependencies, then adds the local acknowledgement and demonstration measurements for download. See [interface notes](docs/INTERFACE_NOTES.md).

## Real demo versus fixtures

- `reports/fhir/bundle.json` is the **real replay demo**, selected from the frozen replay by `scripts/fhir_real_demo.py`, with a clearly labelled demonstration acknowledgement. Its predictions and model versions are not synthetic placeholders.
- `tests/fixtures/fhir/bundle.json` and `fhir/examples/` are explicit validator fixtures; their synthetic predictions and fixture model marker must not be described as real model output.
- `reports/fhir-validation/summary.json` is the recorded **fixture** result. The GitHub FHIR conformance workflow additionally validates a real demo generated in its disposable checkout. The summary does not certify every forecast ever produced.

## Official sandbox round-trip

Endpoint: `https://sandbox.hl7europe.eu/oneaquahealth/fhir`, published in the [official OAH webinar slides](https://www.oneaquahealth.eu/app/uploads/2026/09/OneAquaHealth_hackathon_session_4_Aug27-2026.pdf).

[Saved evidence](reports/fhir-validation/sandbox_roundtrip.json) records a successful transaction and matching reads of every created resource. The initial read timed out; the subsequent read-only resume retained that failure and completed the checks. No second POST was used. The source Bundle hash is recorded, and the checked-in source was unchanged.

The transaction uses POST entries and server-assigned IDs, retaining intra-Bundle `urn:uuid` references for server rewriting. Copies carry a project demo tag. Only transport metadata and tags are added; forecast values are unchanged. No existing sandbox resource is overwritten. No credentials were supplied or stored. Resource IDs are retained for traceability; this script does not delete shared sandbox data.

```bash
python3 scripts/sandbox_roundtrip.py                # dry run; no network writes
# Explicitly creates a NEW set of tagged demo resources; do not repeat just for a demo:
python3 scripts/sandbox_roundtrip.py --write --output /tmp/new-roundtrip.json
# If a read failed after the write, retry only reads using the same evidence:
python3 scripts/sandbox_roundtrip.py --resume-read --output /tmp/new-roundtrip.json
```

The script refuses to overwrite existing evidence on a write run and never automatically retries POST. It reads the committed real Bundle; it does not run a model or regenerate reports. Read-back comparison excludes only server identity/version metadata and equivalent internal reference forms. Server acceptance establishes storage/transport, not server-side enforcement of the local IG or a deployed app integration.

## Reproduce conformance checks

The OAH source, SUSHI and official HL7 validator are pinned in `fhir/tool-versions.json` and the build scripts. The validator release checksum is checked. Online terminology validation is enabled; required profile resolution and negative-control failure reasons are checked.

**Run report-producing commands only in a disposable copy/worktree.** They regenerate validation evidence and may generate a new demo acknowledgement time; the frozen review checkout must remain unchanged.

```bash
bash scripts/build_fhir.sh
python3 scripts/make_fhir_examples.py
bash scripts/validate_fhir.sh --fixtures
python3 -m unittest discover -s tests/fhir -v
PYTHONPATH=src python3 scripts/fhir_real_demo.py
bash scripts/validate_fhir.sh
```

Python, Node/npm, Java, git, curl and network access are required. `SP_PYTHON` and `SP_JAVA` can choose interpreter executables. See [FHIR conformance CI](https://github.com/mohitt31/streampulse/actions/workflows/fhir.yml) for the tested environment.

To rebuild the real demo without replacing the committed Bundle, use `--out-dir /tmp/streampulse-fhir-demo`. The full exporter also accepts `--output` for an alternate output file.

Canonical URL hosting and an OAH Citizen Science App connection remain UNVERIFIED. Local canonical URLs are identifiers, not proof of a published implementation guide. Original handoff reports are retained as historical records; current integration status is described here.

## Licensing

Project code and local FSH use the project licence. Compiled OAH definitions are rebuilt from their pinned upstream source for validation; no new claim about their redistribution rights is made. See [THIRD_PARTY_FHIR.md](THIRD_PARTY_FHIR.md).
