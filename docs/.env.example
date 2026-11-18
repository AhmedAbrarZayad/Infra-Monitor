# Request Shield Model: Build and Installation Runbook

This runbook explains how to build the Request Shield classifier offline and
install its approved artifact into the ML service. Request Shield classifies
ingested HTTP request metadata into `GREEN`, `GRAY`, or `RED` zones.

The ML service can be healthy without this artifact, but `GET /ready` returns
HTTP 503 and ML request classification remains unavailable until it is
installed.

## Required output

The installed artifact is exactly this bundle:

```text
/code/artifacts/request_shield/
├── model.joblib
└── metadata.json
```

`model.joblib` is executable serialized Python data. Only install an artifact
built and reviewed by a trusted developer. Do not download or load an
untrusted `.joblib` file.

## Prerequisites

- Docker Desktop with `docker compose` available.
- The repository checked out locally.
- Enough disk and memory for CICIDS2017 (approximately 250 MB compressed and
  1.2 GB extracted).
- The ML image built from the revision that will run the artifact:

```powershell
docker compose build ml_service
```

Training inside this image ensures the artifact uses the same Python,
scikit-learn, NumPy, and joblib versions as the running ML service.

## 1. Obtain the training data

Download `MachineLearningCSV.zip` from the official CICIDS2017 dataset page:

<https://www.unb.ca/cic/datasets/ids-2017.html>

Verify the source and any published checksum before using it. Extract the CSV
files into:

```text
backend/sanitize/dataset/raw/
```

Expected files include the Monday through Friday `*.pcap_ISCX.csv` files. The
raw CSV files and generated `.npz` data are ignored by Git and must not be
committed.

## 2. Preprocess the dataset

From the repository root, run:

```powershell
docker run --rm `
  -v "${PWD}\backend:/workspace/backend" `
  -w /workspace/backend `
  infra-monitor-ml_service `
  python -m sanitize.dataset.preprocess
```

Expected output:

```text
backend/sanitize/dataset/processed/training_data.npz
```

Review the printed class distribution. The output must contain all three
classes (`GREEN=0`, `GRAY=1`, and `RED=2`). Treat missing classes, unreadable
CSV warnings, or an unexpectedly small dataset as a failed build.

## 3. Train the model artifact

Choose a unique release version. A suggested format is
`request-shield-YYYYMMDD-<git-short-sha>`.

```powershell
$modelVersion = "request-shield-20260909-abcdef0"

New-Item -ItemType Directory -Force `
  -Path ".\model\artifacts\request_shield" | Out-Null

docker run --rm `
  -v "${PWD}\backend:/workspace/backend" `
  -v "${PWD}\model\artifacts:/workspace/model/artifacts" `
  -w /workspace/backend `
  -e REQUEST_SHIELD_MODEL_VERSION=$modelVersion `
  -e REQUEST_SHIELD_ARTIFACT_DIR=/workspace/model/artifacts/request_shield `
  infra-monitor-ml_service `
  python -m sanitize.dataset.train
```

Confirm that both files exist:

```powershell
Get-ChildItem .\model\artifacts\request_shield\
Get-Content .\model\artifacts\request_shield\metadata.json
```

The metadata must include:

- the intended `model_version`;
- exactly 26 `feature_names` in the generated order;
- a non-zero `training_samples` value;
- `artifact_format_version` equal to `1`.

Keep the two files together as one immutable release. Record checksums for the
reviewed bundle:

```powershell
Get-FileHash .\model\artifacts\request_shield\model.joblib -Algorithm SHA256
Get-FileHash .\model\artifacts\request_shield\metadata.json -Algorithm SHA256
```

## 4. Test before installation

Run the ML service tests:

```powershell
docker run --rm `
  -v "${PWD}\model\app:/code/app:ro" `
  -v "${PWD}\model\tests:/code/tests:ro" `
  infra-monitor-ml_service `
  pytest -q
```

For production approval, also evaluate the artifact on a held-out dataset and
record at least the per-class precision, recall, F1 score, confusion matrix,
dataset version, source commit, reviewer, and SHA-256 checksums. Do not approve
the model using only its training-set results.

## 5. Install into the Docker volume

The Compose service mounts the named `ml_artifacts` volume at
`/code/artifacts`. Start the service, create the target directory, and copy the
reviewed bundle into it:

```powershell
docker compose up -d ml_service
docker compose exec -T ml_service mkdir -p /code/artifacts/request_shield
docker compose cp `
  .\model\artifacts\request_shield\. `
  ml_service:/code/artifacts/request_shield/
docker compose restart ml_service
```

Restarting clears any in-memory model cache and forces the next readiness or
classification request to load the installed bundle.

## 6. Verify the installation

Check liveness and model readiness independently:

```powershell
Invoke-RestMethod http://localhost:7001/health
Invoke-RestMethod http://localhost:7001/ready
docker compose ps ml_service celery_worker
docker compose logs --tail 100 ml_service celery_worker
```

Expected readiness response:

```json
{
  "status": "ready",
  "model_version": "request-shield-20260909-abcdef0"
}
```

`/health` confirms that the API and artifact storage are operational.
`/ready` additionally loads and validates the Request Shield artifact. A 503
from `/ready` means the bundle is absent, unreadable, or incompatible; inspect
the response body and ML service logs before enabling classification.

After readiness succeeds, run the backend end-to-end check:

```powershell
docker compose exec -T backend python manage.py sanitize_e2e
```

## Updating or rolling back

Before replacing a working bundle, copy its two files to a release archive
outside the Docker volume and record their checksums. Install the new reviewed
bundle using the same copy and restart steps, then repeat all verification.

To roll back, copy the previous matching `model.joblib` and `metadata.json`
bundle back into `/code/artifacts/request_shield/`, restart `ml_service`, and
verify that `/ready` reports the previous version. Never mix files from two
model releases.

## Troubleshooting

- `/health` is 200 but `/ready` is 503: the service runs, but the model bundle
  is missing or invalid. Check both files and `docker compose logs ml_service`.
- `model.joblib` is reported incompatible: rebuild using the current
  `infra-monitor-ml_service` image; do not train with an unrelated local Python
  environment.
- `feature_names` is incompatible: rebuild from the current preprocessing and
  training code. Do not edit `metadata.json` to bypass the schema check.
- The artifact disappears after `docker compose down`: normal `down` retains
  named volumes, but `docker compose down --volumes` deletes them. Reinstall
  the archived approved bundle.
- The worker is running while `/ready` is 503: ingestion and non-ML processing
  can continue, but Request Shield ML classification cannot complete until an
  artifact is installed.

## Important model limitation

CICIDS2017 contains network-flow data, while Request Shield evaluates HTTP
request metadata. The current preprocessor maps and synthesizes request-level
features from that network dataset. Treat this artifact as a baseline, validate
it against representative HTTP traffic, monitor false positives and false
negatives, and retrain with appropriately governed request-level data before
relying on it for automated security decisions.
