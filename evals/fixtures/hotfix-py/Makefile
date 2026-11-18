.PHONY: test contract verify

test:
	python3 -m unittest discover -s gatehouse -t . -q

contract:
	python3 -m unittest discover -s contract -t . -q

verify: test contract
