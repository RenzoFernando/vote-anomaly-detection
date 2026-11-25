# VoteAnomaly

**Electoral Anomaly Detection System Using Data Analysis**

**Universidad ICESI | Cybersecurity**

## Overview

VoteAnomaly is an academic cybersecurity project focused on detecting anomalies and inconsistencies in simulated electoral processes through data analysis.

The system is designed to analyze electoral datasets, identify unusual voting patterns, detect inconsistencies using predefined validation rules, and apply statistical techniques to highlight potentially anomalous records.

By combining Python-based data processing, statistical analysis, and data visualization, VoteAnomaly provides an interpretable approach to evaluating the integrity and consistency of electoral information.

**Disclaimer:** This project uses exclusively simulated data for academic purposes. Detected anomalies do not constitute evidence of electoral fraud.

## Objectives

### General Objective

To design and implement a Python-based system capable of identifying and analyzing anomalies in simulated electoral datasets using rule-based validation and statistical techniques, contributing to the understanding of data integrity in cybersecurity.

### Specific Objectives

1. **Data Preparation:** Generate, structure, and preprocess a simulated electoral dataset containing voting records and relevant electoral variables.

2. **Anomaly Detection:** Implement rule-based validation and statistical methods to identify inconsistencies, unusual voting patterns, and potential outliers.

3. **Data Visualization:** Develop graphical representations that facilitate the identification, interpretation, and comparison of detected anomalies.

4. **Performance Evaluation:** Evaluate the effectiveness of the implemented detection methods, analyze their limitations, and document the findings.

## Technologies

The project uses the following technologies and tools:

- **Python:** Main programming language for data processing and anomaly detection.
- **Pandas:** Data manipulation, cleaning, and analysis.
- **NumPy:** Numerical operations and statistical calculations.
- **Matplotlib:** Data visualization and graphical representation.
- **Jupyter Notebook:** Exploratory data analysis and interactive experimentation.
- **Git & GitHub:** Version control, collaboration, and source code management.

## Methodology

The project follows a structured methodology consisting of six stages:

### 1. Dataset Generation

Create a simulated electoral dataset containing information such as registered voters, total votes, voting participation, and voting results.

The dataset includes controlled anomalous records to support the evaluation of detection techniques.

### 2. Data Preprocessing

Clean, validate, and organize the dataset to ensure consistency and prepare the information for analysis.

### 3. Exploratory Data Analysis

Examine the dataset using descriptive statistics and exploratory techniques to understand voting distributions, participation patterns, and potential irregularities.

### 4. Anomaly Detection

Implement two complementary detection approaches:

- **Rule-Based Detection:** Identify inconsistencies using predefined logical conditions and validation rules.
- **Statistical Detection:** Identify unusual observations and outliers using statistical analysis.

### 5. Visualization and Evaluation

Generate visualizations to illustrate voting patterns, detected anomalies, and relevant statistical findings.

Evaluate the detection methods by comparing their results against the known anomalies introduced into the simulated dataset.

### 6. Results and Conclusions

Interpret the findings, discuss the effectiveness and limitations of the implemented techniques, and propose potential improvements.

## Synthetic Dataset: First Steps

The dataset is generated locally rather than downloaded from Kaggle. This keeps the
exercise within the assignment's simulated-data requirement and makes the injected
anomalies known and reproducible. Kaggle may be consulted for ideas about common
column names, but its real-world election records should not be presented as
simulated data.

Generate the CSV files from the repository root:

```bash
python -m src.data_generation
```

By default, this writes 500 synthetic polling-station records to
`data/raw/electoral_dataset.csv` and reference labels for the controlled anomalies
to `data/ground_truth/anomaly_labels.csv`. The default is 25 anomalous records
(5% of the dataset), with all four anomaly types represented. To choose another
size, pass both counts; for example:

```bash
python -m src.data_generation --records 1000 --anomalies 50 --seed 42
```

The labels are kept separate from the
dataset so they can be used to evaluate detection without leaking into its input.
The generator uses a fixed seed by default; calling `generate_dataset(seed=...)`
with the same seed produces the same data.

Preprocessing and validation are available in `src/preprocessing.py`. Validation
returns a row-level issue report and does not silently remove records. Run the
validation report and focused automated checks with:

```bash
python -m src.preprocessing
python -m pytest -q tests/test_data_pipeline.py
```

For evidence, capture (1) the generated CSV preview and anomaly-label table from
`python -m src.data_generation`, (2) the findings from `python -m src.preprocessing`,
and (3) the passing test output. Save the screenshots in your personal folder
under `docs/evidence/`.

## Project Structure

The repository is organized as follows:

- **`data/`** — Raw and processed simulated electoral datasets.
- **`src/`** — Python source code for dataset generation, anomaly detection, evaluation, and visualization.
- **`notebooks/`** — Jupyter notebooks for exploratory data analysis.
- **`outputs/`** — Generated figures and analysis results.
- **`tests/`** — Automated tests for the detection logic.
- **`docs/`** — Academic report and supporting documentation.
- **`requirements.txt`** — Python project dependencies.
- **`README.md`** — Project overview and documentation.

## Team Members

| Name | Student ID |
|---|---|
| Diana Garzón | A00405150 |
| Hideki Tamura | A00348618 |
| Luna Martínez | A00401964 |
| Renzo Mosquera | A00401681 |

**Institution:** Universidad ICESI

**Course:** Cybersecurity

## Project Deliverables

### 1. Technical Report

A comprehensive academic report in PDF format documenting:

- Problem context and objectives.
- Methodology and technical approach.
- System implementation.
- Data analysis and visualizations.
- Experimental results and evaluation.
- Conclusions, limitations, and potential improvements.

### 2. Demonstration Video

A video presentation with a maximum duration of **8 minutes**, covering:

- Project overview and problem definition.
- Methodology and implemented solution.
- System functionality and practical demonstration.
- Results, findings, and conclusions.

### 3. GitHub Repository

A structured repository containing:

- Python source code.
- Simulated electoral datasets.
- Jupyter notebooks.
- Generated visualizations and results.
- Automated tests.
- Project documentation.
- Required dependencies and execution resources.

## Ethical Considerations

VoteAnomaly is developed exclusively for educational and research purposes within a controlled environment.

All electoral data used in this project is simulated. The system does not analyze actual electoral processes or make claims regarding real-world electoral fraud.

Statistically unusual observations and data inconsistencies are treated as indicators requiring further investigation, not as definitive evidence of fraudulent activity.

---

**VoteAnomaly — Universidad ICESI | Cybersecurity**
