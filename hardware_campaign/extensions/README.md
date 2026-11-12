# Supplementary hardware coverage circuits

These are **25 exact logical controls for the hardware campaign**, built from the original models. They extend coverage; they do not turn each larger research study into a hardware experiment. Actual jobs, layouts, raw counts and noise analyses belong in the parent campaign's run directories.

| Family | Rows | Width | Generic CX counts before native routing |
|---|---:|---:|---|
| Independent contacts, 3/5/7 sites; enumerated and counter predicates; plain/r1 | 12 | 3–10 | r1 enum: 30/252/1,098; counter: 42/221/317 |
| Original seeded 1,024-entry diagonal cost benchmark, r0/r1/r25 | 3 | 10 | 0/1,312/32,800 |
| Actual 16-entry semantic reader, r1 | 1 | 4 | 56 |
| Eight-step QRSM, full r0–3 and steered local r1 | 5 | 10–17 | full: 56/216/376/536; local: 174 |
| Ten-step QRSM, rewind windows 4/8, r1/r2 | 4 | 13–17 | window4: 136/202; window8: 216/362 |

The contact predicate is fewer than two absorbed sites at independent absorption probability 0.8. Every isolated oracle was tested on every input, and counter workspace is uncomputed. Both oracle styles have the same logical conditional answer; additional clean qubits and routing can change hardware cost. An exact direct classical conditional sampler is available for this toy.

The **1,024-entry case is a random diagonal cost test, not a semantic database**. It exactly reproduces the canonical seed10 mark table and 25-round cost convention. Approximately half its entries are marked, so 25 rounds are not an optimized search schedule. The 16-entry reader is separately labeled. Both require classical table/token processing; no data-loading or end-to-end speedup follows.

The eight-step circuits provide fixed-round ingredients relevant to randomized search, **not the full adaptive BBHT algorithm**. The finite-horizon circuits intentionally use the original approximate rule: reverse/replay only the last window and reflect only on those history qubits. Their metadata records conditional-history bias against the unmodified full-model target. Success at following this approximate circuit is distinct from correctly conditioning the original distribution.

## Verification and use

The frozen export is [bundle_v1/manifest.json](bundle_v1/manifest.json), [logical.qpy](bundle_v1/logical.qpy), and [ideal_probabilities.npz](bundle_v1/ideal_probabilities.npz). Every row has full ideal Z probabilities including workspace, source hashes, generic costs and one terminal `meas` register with identity logical-bit wiring. QPY round-trip equality and all 25 statevectors were checked. Native routing and device noise remain separate.

```powershell
python -m unittest discover -s hardware_campaign/extensions -p 'test_*.py' -v
python hardware_campaign/extensions/verify_bundle.py
```

Seven tests pass. The export used a 600-second timeout and 4,096 MiB process memory guard and completed in 13.3 seconds. It refuses an existing output directory. To reproduce an export, choose a new destination with `export_bundle.py --out <new-directory>`.

The pre-export isolated-oracle test corrected a compiler assumption: arbitrary-input unitary checks need `qubits_initially_zero=False`, whereas complete preparations legitimately start in zero. This is recorded in [PROTOCOL.md](PROTOCOL.md). All full exported preparations were independently checked against exact probabilities.

These superconducting circuits emulate bounded mathematical models. They do not expose a wafer, diagnose a real light source or establish a practical quantum advantage.
