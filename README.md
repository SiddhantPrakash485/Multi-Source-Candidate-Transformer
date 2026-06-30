# Multi-Source Candidate Data Transformer

**🎥 Demo Video:** [Watch the end-to-end pipeline and architecture explanation here](https://drive.google.com/file/d/1JGrRJILV2EuwRU1DQPMUJMTeHIhCPvFx/view?usp=drive_link)

---

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




