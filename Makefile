visual:
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
