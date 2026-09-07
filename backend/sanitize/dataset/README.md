# CICIDS2017 Dataset for Request Shield Training

## About the Dataset

**CICIDS2017** (Canadian Institute for Cybersecurity Intrusion Detection System 2017)
is the most widely cited open-source intrusion detection dataset. It contains
**~2.83 million labeled network flow records** captured over 5 days of simulated
network traffic.

### Key Statistics
- **Total records**: ~2,830,743
- **Benign records**: ~2,273,097 (80.3%)
- **Attack records**: ~557,646 (19.7%)
- **Features**: 78 network flow features + Label column
- **Attack types**: 14 categories

### Attack Types Included
| Attack Type | Zone Mapping | Count |
|---|---|---|
| BENIGN | 🟢 GREEN | ~2,273,097 |
| DoS Hulk | 🔴 RED | ~231,073 |
| PortScan | 🟡 GRAY | ~158,930 |
| DDoS | 🔴 RED | ~128,027 |
| DoS GoldenEye | 🔴 RED | ~10,293 |
| FTP-Patator | 🔴 RED | ~7,938 |
| SSH-Patator | 🔴 RED | ~5,897 |
| DoS slowloris | 🔴 RED | ~5,796 |
| DoS Slowhttptest | 🔴 RED | ~5,499 |
| Bot | 🟡 GRAY | ~1,966 |
| Web Attack – Brute Force | 🔴 RED | ~1,507 |
| Web Attack – XSS | 🔴 RED | ~652 |
| Infiltration | 🔴 RED | ~36 |
| Web Attack – Sql Injection | 🔴 RED | ~21 |
| Heartbleed | 🔴 RED | ~11 |

### Citation
> Iman Sharafaldin, Arash Habibi Lashkari, and Ali A. Ghorbani,
> "Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic
> Characterization", 4th International Conference on Information Systems
> Security and Privacy (ICISSP), 2018.

## Download Instructions

The dataset CSV files can be downloaded from the official UNB page:

1. Visit: https://www.unb.ca/cic/datasets/ids-2017.html
2. Download `MachineLearningCSV.zip` (~250MB compressed, ~1.2GB uncompressed)
3. Extract into this directory: `sanitize/dataset/raw/`

The ZIP contains 8 CSV files (one per day/session):
```
Monday-WorkingHours.pcap_ISCX.csv
Tuesday-WorkingHours.pcap_ISCX.csv
Wednesday-workingHours.pcap_ISCX.csv
Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv
Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv
Friday-WorkingHours-Morning.pcap_ISCX.csv
Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv
Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv
```

Alternative: Download from Kaggle (cleaned version):
https://www.kaggle.com/datasets/cicdataset/cicids2017

## Preprocessing

Run the preprocessing script to convert raw CICIDS2017 CSV files into our
26-feature format:

```bash
cd backend
python -m sanitize.dataset.preprocess
```

This will:
1. Load all CSV files from `sanitize/dataset/raw/`
2. Map CICIDS2017 features to our 26 request-level features
3. Map attack labels to our 3-zone classification (GREEN/GRAY/RED)
4. Handle missing values and infinities
5. Balance the dataset (undersample majority class)
6. Output `sanitize/dataset/processed/training_data.npz`

## Training

After preprocessing, train the model:

```bash
cd backend
python -m sanitize.dataset.train
```

This sends the processed data to the FastAPI ML service's
`/train-request-classifier` endpoint.
