"""Review1 trial recipes are history, not an idempotent board generator."""
import os
if os.environ.get('R3_REVIEW1_ONE_SHOT_ECO')!='explicitly-reviewed-scratch-copy':
    raise SystemExit('Refusing historical one-shot ECO replay. Current routed PCB is authoritative. Inspect the recipe and run only on a backed-up scratch copy after explicit engineering review.')
