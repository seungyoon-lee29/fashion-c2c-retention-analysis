PY ?= python3
SRC = src

.PHONY: setup eda data-quality features survival drivers impact causal figures funnel cohort abtest all test report onepager clean

setup:
	$(PY) -m pip install -r requirements.txt

eda:            ## Phase-0 feasibility gate + EDA
	cd $(SRC) && $(PY) data.py

data-quality: eda ## DuckDB SQL data cleanliness audit (docs/data_quality_report.md)
	cd $(SRC) && $(PY) data_quality.py

drivers:        ## driver importance + gap sweep + aha grid
	cd $(SRC) && $(PY) drivers.py

impact:         ## g-formula + IPTW + E-value + Markov
	cd $(SRC) && $(PY) impact.py

causal: eda     ## M2 — identifiability map: 4-lever positivity (docs/causal_report.md); needs events cache
	cd $(SRC) && $(PY) identifiability_map.py

figures: eda    ## all report figures
	cd $(SRC) && $(PY) figures.py

funnel: eda     ## M1 — DA funnel + cohort reports; needs the events cache eda builds
	cd $(SRC) && $(PY) funnel_cohort.py

cohort: funnel  ## M1 — DA cohort retention report (docs/cohort_report.md); same script

abtest: eda     ## M3 — A/B design + power table (docs/ab_test_design.md); needs events cache
	cd $(SRC) && $(PY) ab_design.py

all: onepager   ## full pipeline -> docs/ + figures + onepager

report: figures ## legacy self-contained report (writes docs/archive/report_legacy.html)
	cd $(SRC) && $(PY) report_html.py

onepager: figures cohort causal abtest data-quality ## recruiter DA one-pager (onepager.html); regen AFTER the reports it cites
	cd $(SRC) && $(PY) onepager_html.py

test:           ## offline smoke + ground-truth recovery (no network)
	$(PY) tests/test_smoke.py

clean:
	rm -rf data/*.parquet data/raw/* docs/figures/*.png __pycache__ src/__pycache__ tests/__pycache__
