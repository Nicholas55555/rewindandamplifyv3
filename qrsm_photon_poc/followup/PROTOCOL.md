# QRSM inference followup protocol

This study addresses numerical cutoff, independent dynamics verification, nuisance identifiability and detector dead time. It uses fresh synthetic records and preserves the original companion results. Frequencies and rates retain the original arbitrary consistent units. A microscopic photon-emitter model is not a calibrated lithography-laser model.

Before fitting, compare cavity dimensions 2 through 6 for 40 bins at the default setting and two stress settings (drive 2.1 and coupling 1.05). Compare unconditional and step-3-conditioned click probabilities, cavity occupation and top-level population. Dimension 6 is a numerical reference, not an exact infinite-cavity solution. Choose a new inference cutoff only after examining these errors; label the choice and its limits.

Independently rebuild the Hamiltonian and collapse operators with QuTiP. Compare its ODE master-equation evolution with the original matrix exponential. Use 6,000 quantum-jump trajectories over 12 bins with seed 811107, coarsening monitored photon and independent dark-count events to binary outcomes. Check unconditional and joint click statistics using simultaneous binomial intervals. The Monte Carlo check tests two implementations of the same assumed physics.

Then compare fixed-nuisance coupling fitting with joint coupling, defect-detuning, emitter-dephasing, detector-efficiency and drive fitting. Use fresh independent records, bounded multiple-start optimization, and train-only model selection. Report convergence and boundary warnings. Local information/Hessian intervals are diagnostics rather than guaranteed coverage; use a coupling profile to expose flat or competing explanations. Other nuisance parameters remain fixed and known.

Controlled measurements may vary known emitter drive and detuning; they may not assume direct control of an unknown hidden defect. Compare equal total record/bin budgets. Classical sequence models must receive the same control labels. Assess a rate-matched telegraph model and a flexible HMM rather than comparing only to IID counts.

For one-bin detector dead time, a recorded click forces the next bin's observed output to zero while the physical system still evolves under the unconditional channel. Compare correct and omitted-dead-time likelihoods. Test normalization and sampled frequencies independently. This is a discrete readout model, not a calibrated detector's timing response.

All new fits are synthetic and in-family unless a mismatch is explicitly named. Preserve negative results, parameter degeneracies and optimization failures. No QPU or API is required for this work.
