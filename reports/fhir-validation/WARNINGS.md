# Validation warnings and informational findings

Official HL7 validator 6.10.4; FHIR 4.0.1; pinned OAH definitions and local snapshot profiles loaded. Terminology server: https://tx.fhir.org/r4.

## Positive resources

Errors: 0; fatal: 0; warnings: 0.

Every positive warning is enumerated below. CI rejects any unreviewed warning; profiles must actually resolve.

- None.

## Informational findings

- OAH indicator and component-code bindings are **preferred**. StreamPulse intentionally uses its declared local CodeSystem for daily aggregates, predictions, interval bounds, source-quality metadata, and watch flags. These are not official OAH codes; informational preferred-binding notices are expected.
- Contained-resource examples are self-contained solely for standalone validation. The exported collection uses separate, resolvable urn:uuid entries.
- Any further informational messages are retained verbatim in positive.json.

## Negative controls

The missing-performer fixture intentionally produces the base best-practice warning `All_observations_should_have_a_performer`, in addition to the required OAH cardinality error. This exact warning is reviewed and allowed only for that negative control. No warning is exempted on positive examples.

- missing-performer: {"warning": 1, "error": 1, "information": 4}; expected conformance failure, asserted by scripts/check_validation.py.
- wrong-subject-type: {"information": 4, "error": 1}; expected conformance failure, asserted by scripts/check_validation.py.
- missing-run-mode: {"information": 35, "error": 2}; expected conformance failure, asserted by scripts/check_validation.py.

A passing fixture establishes encoding/conformance behavior, not model skill, actual message delivery, source sensor quality, or authentication. The fixture forecast, all-zero model SHA, and acknowledgement are explicitly synthetic. Actual pipeline outputs must be exported and validated separately.
