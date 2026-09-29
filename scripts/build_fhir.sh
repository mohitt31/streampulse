#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
SP_PYTHON="${SP_PYTHON:-python3}"
SP_OAH_COMMIT=b907cf0869b59d82d9138b3d147fca66f333d911
mkdir -p vendor reports/fhir-validation tools
if [[ ! -d vendor/oah/.git ]]; then
  if [[ -d vendor/oah/input/fsh && -f vendor/oah/.streampulse-pin ]]; then
    [[ "$(cat vendor/oah/.streampulse-pin)" == "$SP_OAH_COMMIT" ]] || exit 1
  elif [[ ! -e vendor/oah ]]; then
    git init vendor/oah
    git -C vendor/oah remote add origin https://github.com/hl7-eu/oah.git
    git -C vendor/oah fetch --depth 1 origin "$SP_OAH_COMMIT"
    git -C vendor/oah checkout --detach FETCH_HEAD
  else
    echo 'Unverified vendor/oah directory; refusing to assume its provenance.' >&2
    exit 1
  fi
fi
if [[ -d vendor/oah/.git ]]; then
  [[ "$(git -C vendor/oah rev-parse HEAD)" == "$SP_OAH_COMMIT" ]] || { echo 'Wrong OAH commit' >&2; exit 1; }
  git -C vendor/oah diff --exit-code -- input/fsh sushi-config.yaml
fi
npm ci --prefix fhir --ignore-scripts
fhir/node_modules/.bin/sushi build --snapshot vendor/oah 2>&1 | tee reports/fhir-validation/sushi-oah.log
"$SP_PYTHON" scripts/package_oah.py
fhir/node_modules/.bin/sushi build --snapshot fhir 2>&1 | tee reports/fhir-validation/sushi-local.log
"$SP_PYTHON" - <<'PY'
import json,pathlib
p=pathlib.Path('fhir/fsh-generated/resources/StructureDefinition-streampulse-forecast-observation.json')
r=json.loads(p.read_text())
assert r['baseDefinition']=='http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah'
assert r.get('snapshot',{}).get('element'), 'Missing snapshot'
print('Confirmed local forecast profile derives from pinned OAH and has a snapshot')
PY
