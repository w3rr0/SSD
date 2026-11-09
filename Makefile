.PHONY: visual run_visual baseline test olist_report olist_validation olist_plots queue_validation run_visual_olist scenarios

# run_visual is the old name of this target; both start the same page.
visual run_visual:
	uv run runners/run_visual.py

baseline:
	uv run runners/run_baseline.py

test:
	uv run pytest

olist_report:
	uv run runners/olist_report.py

olist_validation:
	uv run runners/olist_validation.py

olist_plots:
	uv run runners/olist_plots.py

queue_validation:
	uv run runners/queue_validation.py

run_visual_olist:
	uv run runners/run_visual_olist.py

scenarios:
	uv run runners/run_scenarios.py
