# Third-party attribution and boundaries

- OAH IG: https://github.com/hl7-eu/oah at b907cf0869b59d82d9138b3d147fca66f333d911. Compiled conformance definitions in `fhir/packages/oah-pinned.tgz` originate there and are not StreamPulse-authored MIT code. The pinned sushi-config has its licence field commented out; an explicit repository licence grant was not established here (**UNVERIFIED**). Build from the pinned source; do not represent the compiled dependency as MIT or an official published package.
- HL7 FHIR R4: https://hl7.org/fhir/R4/ ; validator release: https://github.com/hapifhir/org.hl7.fhir.core/releases/tag/6.10.4 . The validator binary is downloaded by script and not distributed in this ZIP.
- SUSHI: https://github.com/FHIR/sushi ; pinned npm release fsh-sushi 3.20.1. node_modules is not distributed.
- Hub'eau: https://hubeau.eaufrance.fr/page/api-temperature-continu ; metadata and hourly record snapshots are attributed through exact request logs. Source data are not relicensed MIT.
- Open-Meteo: https://open-meteo.com/en/docs/single-runs-api ; attribution and licence: https://open-meteo.com/en/licence . The audit uses public noncommercial API access, serial bounded requests. Data snapshots are not relicensed MIT.
- OAH field framework: https://www.oneaquahealth.eu/health-assessment-framework-for-urban-aquatic-ecosystems/ . The recommended follow-up is a prototype workflow, not an OAH-approved thermal alert policy.

No permissions, affiliation, real authority integration, or scientific validity follows from successful FHIR validation.
