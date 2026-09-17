PY ?= .venv/bin/python
export PYTHONPATH := src

.PHONY: setup gen run eval workbook examples all test clean

setup:
	python3 -m venv .venv && .venv/bin/pip install -q openpyxl pytest

gen:
	$(PY) -m poc_d04 gen

run:
	$(PY) -m poc_d04 run --backend rule

eval:
	$(PY) -m poc_d04 eval

workbook:
	$(PY) -m poc_d04 workbook

examples:
	$(PY) -m poc_d04 examples

all:
	$(PY) -m poc_d04 all

test:
	$(PY) -m pytest -q

clean:
	rm -rf out data examples/D04_오프라인_추출결과
serve:
	$(PY) -m poc_d04 serve
