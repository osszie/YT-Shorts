"""Pipeline stages. Each stage is an idempotent unit that reads from and writes
to the shared job record. Ordering + the two human gates live in
pipeline/orchestrator.py, mirroring the flow in STRATEGY.md §4:

    idea -> [angle engine] -> ANGLE GATE -> script -> [similarity guard]
         -> assets -> voice -> captions -> assemble -> metadata
         -> PUBLISH GATE -> upload
"""
