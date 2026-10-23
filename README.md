# ChronoSentinel AI

ChronoSentinel AI is a prototype security monitoring and threat-analysis
system combining web application firewall (WAF) event collection,
a SQLite event store, network-event detection, supervised flow
classification, anomaly detection, and a Streamlit dashboard.

## Main components

- `app/dashboard.py` — Streamlit security dashboard.
- `app/event_collector.py` — collects and normalizes WAF container logs.
- `app/storage/event_store.py` — SQLite event persistence.
- `app/event_schema.py` — normalized security-event schema.
- `app/cyber_dna.py` — retrospective source/IP behavior analysis.
- `app/detectors/` — network-event detection logic.
- `scripts/train_supervised.py` — supervised model training and evaluation.
- `scripts/classify_flows.py` — classification of compatible flow CSV files.
- `models/` — trained model artifacts.
- `reports/` — evaluation reports and sample predictions.
- `compose.yaml` — local Docker Compose services.
- `requirements.txt` — Python environment snapshot.

## Setup

Use Python and Docker Compose in a supported Linux environment.

1. Create and activate a virtual environment.
2. Install dependencies:

   `python -m pip install -r requirements.txt`

3. Validate the Compose configuration:

   `docker compose -f compose.yaml config -q`

4. Start the configured services:

   `docker compose -f compose.yaml up -d`

5. Start the dashboard from the project root:

   `streamlit run app/dashboard.py`

6. In a separate terminal, start WAF event collection:

   `source .venv/bin/activate && python app/event_collector.py`

Stop the collector with Ctrl+C. Stop the containers with
`docker compose -f compose.yaml down`.

## Supervised classifier

The trained model expects the 66 features recorded in its model bundle.
Input CSV files must contain compatible feature columns with valid
numeric values where required. The classifier validates input features
before generating predictions.

To inspect the command-line options:

`python scripts/classify_flows.py --help`

Example, after supplying a compatible CSV:

`python scripts/classify_flows.py --csv path/to/compatible_flows.csv --output reports/flow_predictions.csv`

## Evaluation and limitations

The reported held-out evaluation is based on a stratified train/test split.
The saved metrics report records approximately 99.66% accuracy on its
held-out test partition. This result reflects the supplied dataset and
does not guarantee equivalent performance on unseen real-world traffic.
Rare classes have limited test examples, so their performance estimates
are less reliable.

Sample flow predictions are illustrative model outputs, not proof of
live network detection. WAF test results describe the tested local
requests only. HTTP status codes alone do not establish whether an
application is exploitable.

Live packet capture has not been verified in the current WSL environment.
Do not describe the prototype as a validated, production-ready network
intrusion prevention system. Predictions and anomaly flags require
investigation before being treated as confirmed incidents.

## Data and privacy

The full training dataset, local event database, virtual environment,
and temporary files are intentionally excluded from the submission
archive. Obtain the dataset separately where its license permits and
follow its original terms of use.
