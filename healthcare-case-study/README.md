# Visualization of Healthcare System Indicators and Health Outcomes: The Philippines in Comparison with East Asia and Pacific Economies, 2000 to 2023

ITD112 Final Project, also submitted as the ITD105 final requirement ([MirkoLouis/ITD105](https://github.com/MirkoLouis/ITD105)).

> **Status: scaffold.** The four CSVs in `data/processed/` (`panel_all.csv`, `panel_eap.csv`, `xsec_eap.csv`, `cluster_matrix.csv`) are **stubs** with three fake rows each (`AAA`, `BBB`, `CCC`). They only fix the column layout. No real data has been downloaded yet.

## Team

There are no fixed roles. Tasks are volunteer-based, and each task is recorded in [`docs/contribution_log.md`](docs/contribution_log.md).

| Name | GitHub username | Write access |
|---|---|---|
| | | |
| | | |
| | | |

Paper file name: `paper/Group[PUT GROUP NUMBER]_Healthcare_Indicators_PH_EAP.pdf`

## Data Source

World Bank, **World Development Indicators (WDI)**, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Indicator codes and coverage are listed in [`docs/data_dictionary.csv`](docs/data_dictionary.csv).

## Layout

```
healthcare-case-study/
├── run.py                  one-command setup and start (python run.py setup | start)
├── config/plot_spec.yaml   shared palettes, figure size, chart labels, clustering
├── data/raw/               raw WDI pulls (tracked)
├── data/processed/         analysis-ready CSVs (currently stubs)
├── R/                      R scripts (ggplot2, pheatmap)
├── python/                 Python scripts; python/viz/ for Seaborn figures
├── model/                  predictive model (scikit-learn, SHAP)
├── figures/r, figures/py   NN_name.png per chart (01_scatter, 02_line, 03_heatmap, 04_clustermap)
├── figures/model           model and SHAP figures
├── app/                    Streamlit app (Home.py + pages/)
├── paper/                  final paper
└── docs/                   data dictionary, decisions, cleaning and contribution logs
```

## Quick Start

**Prerequisites:** [Python](https://www.python.org/downloads/) 3.10 or newer, and [R](https://cran.r-project.org/) if you will run the R scripts. On Windows, tick "Add python.exe to PATH" when installing Python. R does not need to be on PATH.

From this folder (`healthcare-case-study/`), on Windows, macOS or Linux:

```
python run.py setup
python run.py start
```

On macOS/Linux, use `python3` if `python` is not found. On Windows, `py` also works.

- **`setup`** creates `.venv/` and installs `python/requirements.txt` and `app/requirements.txt` into it. It then restores the R packages pinned in `renv.lock` (WDI, dplyr, tidyr, readr, ggplot2, pheatmap, yaml) with `renv::restore()`. Without R it prints a warning and sets up Python only. You can rerun it safely, for example after a requirements file changes.
- **`start`** runs the Streamlit app at http://localhost:8501. Stop it with Ctrl+C. Any extra arguments go to Streamlit, e.g. `python run.py start --server.port 8600`.

You don't need to activate `.venv` to use these two commands. Activate it only to run the Python scripts by hand (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux).

## Run Order

1. **R scripts** in `R/`: download and clean WDI data, then draw `figures/r/`.
2. **Python scripts** in `python/`: draw the same charts into `figures/py/` from `config/plot_spec.yaml`.
3. **Model** in `model/`: train, evaluate and explain, writing to `figures/model/`.
4. **Streamlit**:

   ```
   python run.py start
   ```

   Pages 4 to 7 show `figures/r/NN_name.png` and `figures/py/NN_name.png` side by side, with a placeholder for any figure not generated yet.

## Deployment

Streamlit Community Cloud, main file path `healthcare-case-study/app/Home.py` (dependencies from `app/requirements.txt`).
