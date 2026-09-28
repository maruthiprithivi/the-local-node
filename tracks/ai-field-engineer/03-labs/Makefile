# Shortcuts. `make help` lists them.
.PHONY: help setup mock check data smoke clean-results fw-check

help:          ## list targets
	@grep -E '^[a-z-]+:.*##' Makefile | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'
setup:         ## Mac: install ollama, llama.cpp, venv, felab (lesson 00)
	bash lessons/00-setup/setup_mac.sh
mock:          ## run the offline mock LLM server on :9000
	python -m felab.mock_server
check:         ## chip, RAM, bandwidth, which servers are up
	python lessons/00-setup/check_env.py
data:          ## build data/tickets/*.jsonl
	python data/make_tickets.py
smoke:         ## run every offline lesson against the mock (~2 min)
	bash scripts/smoke_test.sh
fw-check:      ## is anything on Fireworks still billing?
	bash lessons/00-setup/fireworks_guardrails.sh
clean-results: ## wipe results/ (your measurements!)
	rm -f results/*.csv results/*.png results/*.md
