ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PLUGIN := $(ROOT)/plugins/dot

.PHONY: install install-claude install-codex install-agy update update-claude update-codex update-agy

install: install-claude install-codex install-agy

install-claude:
	claude plugin marketplace add $(ROOT)
	claude plugin install dot@dot-local

install-codex:
	codex plugin marketplace add $(ROOT)

install-agy:
	agy plugin install $(PLUGIN)

update: update-claude update-codex update-agy

update-claude:
	claude plugin marketplace update dot-local

update-codex:
	codex plugin marketplace upgrade

update-agy:
	-agy plugin uninstall dot
	agy plugin install $(PLUGIN)
