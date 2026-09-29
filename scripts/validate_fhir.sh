#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
SP_PYTHON="${SP_PYTHON:-python3}"
SP_JAVA="${SP_JAVA:-java}"
SP_VALIDATOR_VERSION=6.10.4
SP_VALIDATOR_SHA256=1106b9d58f9e363e47bea7c4fc065841e5fc91fe9d062775c3bfdd212bd653cc
mkdir -p tools reports/fhir-validation
if [[ ! -f tools/validator_cli.jar ]]; then
  curl --fail --location --retry 3 --connect-timeout 30 --max-time 900 \
    "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/$SP_VALIDATOR_VERSION/validator_cli.jar" \
    --output tools/validator_cli.jar
fi
"$SP_PYTHON" - "$SP_VALIDATOR_SHA256" <<'PY'
import hashlib,pathlib,sys
actual=hashlib.sha256(pathlib.Path('tools/validator_cli.jar').read_bytes()).hexdigest()
assert actual==sys.argv[1], f'Validator checksum mismatch: {actual}'
PY
[[ -f fhir/fsh-generated/resources/StructureDefinition-streampulse-forecast-observation.json ]] || { echo 'Run scripts/build_fhir.sh first' >&2; exit 1; }
SP_BUNDLE=reports/fhir/bundle.json
if [[ "${1:-}" == '--fixtures' ]]; then SP_BUNDLE=tests/fixtures/fhir/bundle.json; fi
[[ -f "$SP_BUNDLE" ]] || { echo "Missing $SP_BUNDLE; export actual pipeline inputs or use --fixtures" >&2; exit 1; }
SP_ARGS=(-version 4.0.1 -ig fhir/packages/oah-pinned.tgz -ig fhir/fsh-generated/resources -tx https://tx.fhir.org/r4)
# All standalone examples carry a contained closure of references. No missing-profile or
# terminology-off switch is used. Parse JSON because process exit status alone is insufficient.
"$SP_PYTHON" -c 'import pathlib; pathlib.Path("reports/fhir-validation/positive.json").unlink(missing_ok=True)'
SP_STATUS=0
"$SP_JAVA" -Xmx2g -jar tools/validator_cli.jar "$SP_BUNDLE" fhir/examples/*.json "${SP_ARGS[@]}" \
  -output reports/fhir-validation/positive.json > reports/fhir-validation/positive.log 2>&1 || SP_STATUS=$?
"$SP_PYTHON" scripts/check_validation.py reports/fhir-validation/positive.json
[[ "$SP_STATUS" -eq 0 ]] || { echo "Validator exited $SP_STATUS" >&2; exit "$SP_STATUS"; }
for SP_CONTROL in missing-performer wrong-subject-type missing-run-mode; do
  "$SP_PYTHON" -c 'import pathlib,sys; pathlib.Path(sys.argv[1]).unlink(missing_ok=True)' "reports/fhir-validation/$SP_CONTROL.json"
  SP_STATUS=0
  "$SP_JAVA" -Xmx2g -jar tools/validator_cli.jar "fhir/negative-controls/$SP_CONTROL.json" "${SP_ARGS[@]}" \
    -output "reports/fhir-validation/$SP_CONTROL.json" > "reports/fhir-validation/$SP_CONTROL.log" 2>&1 || SP_STATUS=$?
  "$SP_PYTHON" scripts/check_validation.py "reports/fhir-validation/$SP_CONTROL.json" --negative "$SP_CONTROL"
done
"$SP_PYTHON" scripts/summarize_validation.py
