.PHONY: dev install test

dev:
	pipenv install --dev

install:
	pipenv install

test:
	pipenv run python3 -m unittest test_lifecycle_hook_handler.py
