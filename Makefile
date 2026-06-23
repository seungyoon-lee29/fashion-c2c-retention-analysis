PY ?= python3
SRC = src

.PHONY: setup eda features survival drivers impact figures all test clean

setup:
	$(PY) -m pip install -r requirements.txt

eda:            ## Phase-0 feasibility gate + EDA
	cd $(SRC) && $(PY) data.py

drivers:        ## driver importance + gap sweep + aha grid
	cd $(SRC) && $(PY) drivers.py

impact:         ## g-formula + IPTW + E-value + Markov
	cd $(SRC) && $(PY) impact.py

figures:        ## all report figures
	cd $(SRC) && $(PY) figures.py

all: eda drivers impact figures   ## full pipeline -> docs/ + figures

test:           ## offline smoke + ground-truth recovery (no network)
	$(PY) tests/test_smoke.py

clean:
	rm -rf data/*.parquet data/raw/* docs/figures/*.png __pycache__ src/__pycache__ tests/__pycache__
