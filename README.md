# Multi-Source Candidate Data Transformer

This repository contains my submission for the Eightfold Engineering Intern (Jul-Dec 2026) assignment. It is a deterministic, rule-based pipeline that ingests candidate data from varied structured and unstructured sources, resolves conflicts, and outputs a canonical JSON profile based on a dynamic runtime configuration.

## Features
* **Modular Extractors:** Handles structured ATS JSON and unstructured GitHub API JSON.
* **Deterministic Merging:** Resolves conflicts using a confidence-weighted scoring system. Array fields (like skills) are unioned and deduplicated rather than overwritten.
* **Dynamic Projection:** Uses a runtime configuration JSON to filter, remap, and normalize fields on the fly without altering the core engine logic.
* **Zero External Dependencies:** Built using purely standard Python libraries (`json`, `re`, `argparse`).

## Prerequisites
* Python 3.7 or higher

## Setup & Execution
1. Clone this repository.
2. Ensure `config.json`, `ats_data.json`, and `github_data.json` are in the root directory alongside the python scripts.

To run the pipeline and print the output to your terminal:
```bash
python cli.py --config config.json --ats ats_data.json --github github_data.json

To run the pipeline and save the resulting canonical profile to a file:

python cli.py --config config.json --ats ats_data.json --github github_data.json --out final_profile.json


Assumptions & Design Decisions
API over NLP: For the unstructured data source requirement, I opted to parse the GitHub API rather than building a regex/NLP parser for PDF resumes. This ensures the pipeline remains robust, deterministic, and free of the "wrong-but-confident" hallucination risks associated with simple text parsing.

Email as Primary Key: The merging engine assumes that the primary email is the definitive unique identifier for a candidate across multiple systems.

Graceful Degradation: If an input file contains malformed JSON, the extractor catches the JSONDecodeError, skips the file, and proceeds with the remaining valid sources rather than crashing the run.


