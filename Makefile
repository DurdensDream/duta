.PHONY: seed golden

# Regenerate the staged Meridian environment (deterministic: seed 42, fixed anchor)
seed:
	python3 sim/seedgen/generate.py

# Rebuild golden-set pre-labels from the planted-case manifest (requires `make seed` first)
golden:
	python3 evals/golden/build_golden.py
