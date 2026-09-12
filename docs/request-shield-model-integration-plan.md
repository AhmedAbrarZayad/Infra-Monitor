# Request Shield Model Integration Plan

## Goal

Make the Request Shield model runbook executable against the current repository:
produce an approved offline artifact, install it into the ML service, validate it
at readiness, and perform inference without exposing a Request Shield training
endpoint.

## Findings

1. Request Shield uses 26 HTTP-request features from `backend/sanitize/features.py`.
2. The ML service imports the six-feature service-anomaly schema from
   `model/app/schemas.py` in `model/app/main.py`; this makes valid Request Shield
   requests fail schema validation.
3. The offline trainer writes `model.joblib` and `metadata.json`, but does not
   verify the input schema, class coverage, finite values, or output metadata
   before publishing the bundle.
4. The ML loader validates feature names and model version, but does not validate
   artifact format, classifier classes, or the metadata/model relationship.
5. Compose readiness already calls `/ready`, but the runbook's successful path
   needs a deterministic artifact contract and focused tests.
6. The existing generic service-anomaly `/train` and `/infer` endpoints are a
   separate six-feature path and must remain separate from Request Shield.

## Integration Design

### 1. Establish one Request Shield schema contract

- Define the 26-feature registry in a model-service module dedicated to Request
  Shield.
- Keep the six-feature container anomaly registry in `app.schemas`.
- Validate request feature names, vector length, numeric finiteness, and bounded
  batch size at the FastAPI boundary.
- Validate the same schema when loading the artifact and when producing it.

### 2. Harden offline artifact creation

- Validate `training_data.npz` has exactly the Request Shield feature order.
- Require non-empty data, matching vector/label lengths, finite values, and all
  three labels: `0=GREEN`, `1=GRAY`, `2=RED`.
- Write metadata with model version, artifact format version, exact features,
  sample count, class distribution, and training parameters.
- Write files through temporary paths and replace them together as far as the
  filesystem permits; never publish an artifact with an incompatible metadata
  file.

### 3. Harden runtime readiness and inference

- Load the Request Shield artifact at `/ready`, not only on first inference.
- Require `artifact_format_version=1`, a non-empty model version, the exact
  26-feature registry, and classifier classes covering all three zones.
- Reject invalid vectors and invalid batch sizes before invoking the model.
- Return the installed model version from readiness and classification.
- Preserve `/health` as liveness/storage status and keep generic `/train` and
  `/infer` isolated to service anomaly detection.

### 4. Test and document the runbook path

- Add ML API tests for Request Shield readiness, missing/incompatible artifacts,
  valid classification, schema mismatch, vector length, non-finite input, and
  removed Request Shield training endpoint.
- Add offline trainer tests for metadata and rejected datasets where practical.
- Update the runbook with the exact schema contract and validation expectations.
- Keep deployment verification as: build image, preprocess, build artifact,
  checksum/review, install into `ml_artifacts`, restart, verify `/health` and
  `/ready`, then run `sanitize_e2e`.

## Delivery Order

1. Add the Request Shield schema and artifact validation helpers.
2. Update offline training to use and validate that schema.
3. Update FastAPI readiness and classification to use the dedicated schema.
4. Add focused tests and update the runbook.
5. Run syntax checks and the ML test suite in the project environment or image.

## Acceptance Criteria

- A valid 26-feature Request Shield artifact can be built using the runbook.
- `/ready` reports the approved model version only when the artifact is valid.
- `/classify-requests` accepts valid Request Shield vectors and returns zones,
  confidence, and model version.
- Six-feature service anomaly `/train` and `/infer` behavior remains intact.
- Missing, incompatible, malformed, or incomplete artifacts fail readiness and
  cannot silently classify requests.
- No production Request Shield training route exists.
