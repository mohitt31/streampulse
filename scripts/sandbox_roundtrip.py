#!/usr/bin/env python3
"""Create tagged copies of the real demo in the official OAH sandbox and verify reads.

Only --write transmits resources. Never overwrites existing evidence or retries POST.
Source Bundle and frozen evaluation outputs are read-only. No credentials required or logged.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"
SOURCE = "https://www.oneaquahealth.eu/app/uploads/2026/09/OneAquaHealth_hackathon_session_4_Aug27-2026.pdf"
TAG = "https://mohitt31.github.io/streampulse/fhir/CodeSystem/sandbox-tags"
ROOT = Path(__file__).resolve().parents[1]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def transaction(bundle):
    if bundle.get("type") != "collection" or not bundle.get("entry"):
        raise ValueError("Expected a populated collection Bundle")
    entries = copy.deepcopy(bundle["entry"])
    urls = {e["fullUrl"] for e in entries}
    if len(urls) != len(entries):
        raise ValueError("Duplicate fullUrl")
    for e in entries:
        r = e["resource"]
        r.pop("id", None)  # POST creates new server-assigned IDs; no shared records overwritten.
        r.setdefault("meta", {}).setdefault("tag", []).append(
            {"system": TAG, "code": "demo", "display": "StreamPulse historical replay; no field sampling performed"})
        e["request"] = {"method": "POST", "url": r["resourceType"]}
        for ref in references(r):
            if ref.startswith("urn:uuid:") and ref not in urls:
                raise ValueError("Unresolved Bundle reference")
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def references(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "reference" and isinstance(v, str):
                yield v
            else:
                yield from references(v)
    elif isinstance(value, list):
        for v in value:
            yield from references(v)


def normalise(value, mapping):
    if isinstance(value, dict):
        return {k: (mapping.get(v, v) if k == "reference" and isinstance(v, str)
                    else normalise(v, mapping)) for k, v in value.items()}
    if isinstance(value, list):
        return [normalise(v, mapping) for v in value]
    return value


def read_matches(expected, received, mapping):
    a, b = copy.deepcopy(expected), copy.deepcopy(received)
    for r in (a, b):
        r.pop("id", None)
        for key in ("versionId", "lastUpdated"):
            r.get("meta", {}).pop(key, None)
    # Servers may render internal references as relative or absolute URLs.
    aliases = dict(mapping)
    aliases.update({BASE + "/" + ref: ref for ref in mapping.values()})
    return normalise(a, aliases) == normalise(b, aliases)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Do not send this payload to another destination.


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--resume-read", action="store_true", help="Retry only reads from saved creation evidence; never POST")
    p.add_argument("--output", type=Path, default=ROOT / "reports/fhir-validation/sandbox_roundtrip.json")
    args = p.parse_args()
    source = ROOT / "reports/fhir/bundle.json"
    raw = source.read_bytes()
    tx = transaction(json.loads(raw))
    if not (args.write or args.resume_read):
        print(f"Dry run: {len(tx['entry'])} tagged resources would be POSTed to {BASE}")
        return
    if args.output.exists() and not args.resume_read:
        raise SystemExit("Evidence already exists; choose a new output explicitly. No POST sent.")
    evidence = {"base_url": BASE, "endpoint_source": SOURCE,
                "source_bundle": str(source.relative_to(ROOT)),
                "source_bundle_sha256": hashlib.sha256(raw).hexdigest(),
                "started_at": now(), "status": "incomplete", "attempts": [], "resources": [],
                "scope": "Real historical replay; demo acknowledgement. No actual field sampling or alert delivery.",
                "credentials_used": False}
    if args.resume_read:
        evidence = json.loads(args.output.read_text())
        if evidence["base_url"] != BASE or evidence["source_bundle_sha256"] != hashlib.sha256(raw).hexdigest():
            raise SystemExit("Saved evidence does not match this endpoint and source")
        if len(evidence["resources"]) != len(tx["entry"]):
            raise SystemExit("Incomplete creation mapping; inspect manually before retrying")
        if evidence.get("error"):
            evidence.setdefault("previous_errors", []).append(evidence.pop("error"))
        evidence["status"] = "resuming_reads"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        pending = args.output.with_suffix(".json.tmp")
        pending.write_text(json.dumps(evidence, indent=2) + "\n")
        pending.replace(args.output)

    opener = urllib.request.build_opener(NoRedirect())

    def request(method, url, payload=None):
        data = json.dumps(payload, separators=(",", ":")).encode() if payload else None
        attempt = {"method": method, "url": url, "at": now(), "status_code": None}
        if data:
            attempt["request_sha256"] = hashlib.sha256(data).hexdigest()
        evidence["attempts"].append(attempt)
        save()  # Preserve the attempted write even if the process is interrupted.
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"})
        try:
            with opener.open(req, timeout=30) as response:
                body = response.read()
                attempt["status_code"] = response.status
        except urllib.error.HTTPError as error:
            attempt["status_code"] = error.code
            attempt["response_sha256"] = hashlib.sha256(error.read()).hexdigest()
            raise RuntimeError(f"{method} returned HTTP {error.code}") from error
        except urllib.error.URLError as error:
            attempt["network_error"] = str(error.reason)
            raise RuntimeError("Network failure; do not automatically retry POST") from error
        finally:
            save()
        attempt["response_sha256"] = hashlib.sha256(body).hexdigest()
        save()
        return json.loads(body)

    try:
        mapping = {}
        if not args.resume_read:
            cap = request("GET", BASE + "/metadata")
            if cap.get("resourceType") != "CapabilityStatement" or cap.get("fhirVersion") != "4.0.1":
                raise ValueError("Expected FHIR R4 CapabilityStatement")
            if not any(i.get("code") == "transaction" for r in cap.get("rest", [])
                       if r.get("mode") == "server" for i in r.get("interaction", [])):
                raise ValueError("Server does not advertise transaction support")
            result = request("POST", BASE, tx)
            if result.get("type") != "transaction-response" or len(result.get("entry", [])) != len(tx["entry"]):
                raise ValueError("Unexpected transaction response; inspect before retrying")
        else:
            result = {"entry": [{"response": {"location": r["location"], "status": r["create_status"]}}
                                for r in evidence["resources"]]}
        for sent, received in zip(tx["entry"], result["entry"]):
            response = received["response"]
            location = response.get("location", "")
            ref = location.removeprefix(BASE + "/").split("/_history/")[0]
            if not re.fullmatch(r"[A-Za-z]+/[A-Za-z0-9.-]{1,64}", ref):
                raise ValueError("Unexpected resource location; no cross-origin read attempted")
            if ref.split("/")[0] != sent["resource"]["resourceType"] or not response["status"].startswith("201"):
                raise ValueError("Expected a newly created resource of the requested type")
            mapping[sent["fullUrl"]] = ref
            if not args.resume_read:
                evidence["resources"].append({"source_full_url": sent["fullUrl"], "resource_id": ref,
                                              "create_status": response["status"], "location": location})
        save()
        for sent, item in zip(tx["entry"], evidence["resources"]):
            if args.resume_read and item.get("content_matches") is True:
                continue
            back = request("GET", BASE + "/" + item["resource_id"])
            item["read_status"] = evidence["attempts"][-1]["status_code"]
            item["content_matches"] = read_matches(sent["resource"], back, mapping)
            save()
        if not all(r["content_matches"] for r in evidence["resources"]):
            raise ValueError("Read-back content mismatch (excluding server IDs/version metadata and reference rewriting)")
        evidence["status"] = "passed"
    except (RuntimeError, ValueError, KeyError) as error:
        evidence["status"] = "failed_or_unverified"
        evidence["error"] = str(error)
    finally:
        evidence["completed_at"] = now()
        save()
    print(f"{evidence['status']}: {args.output}")
    raise SystemExit(0 if evidence["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
