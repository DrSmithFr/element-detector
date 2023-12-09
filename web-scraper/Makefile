.PHONY: env install requirements

env:
	python3 -m venv venv
	. venv/bin/activate

install:
	. venv/bin/activate
	pip install -r requirements.txt

requirements:
	. venv/bin/activate
	-rm -f requirements.txt
	pip freeze > requirements.txt