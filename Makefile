ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PLUGIN := $(ROOT)/plugins/dot

.PHONY: install install-claude install-codex install-agy update update-claude update-codex update-agy remove remove-claude remove-codex remove-agy

install: install-claude install-codex install-agy

install-claude:
	claude plugin marketplace add $(ROOT)
	claude plugin install dot@dotagents

install-codex:
	codex plugin marketplace add $(ROOT)

install-agy:
	agy plugin install $(PLUGIN)

update: update-claude update-codex update-agy

update-claude:
	claude plugin marketplace update dotagents

update-codex:
	codex plugin marketplace upgrade

update-agy:
	-agy plugin uninstall dot
	agy plugin install $(PLUGIN)

remove: remove-claude remove-codex remove-agy

remove-claude:
	-claude plugin uninstall dot@dotagents
	claude plugin marketplace remove dotagents

remove-codex:
	codex plugin marketplace remove dotagents

remove-agy:
	agy plugin uninstall dot
