.PHONY: env install requirements

env:
	python3 -m venv env
	. env/bin/activate

install:
	. env/bin/activate
	pip install -r requirements.txt

requirements:
	. env/bin/activate
	pip freeze > requirements.txt