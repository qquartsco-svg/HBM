# HBM_System Concept (Level C)

> Korean: [00_CONCEPT.md](00_CONCEPT.md)

HBM_System is not a fabrication engine; it is a **package/system-level foundational validation engine** for HBM architecture.

- Level A (`Fabless`): device physics
- Level B (`Memory_Engine`): cell/circuit behavior
- Level C (`HBM_System`): stacking/package/channel/controller dynamics

## Edge-AI design philosophy

In edge AI, hard limits come from power, thermal envelope, and real-time constraints.  
HBM operation must prioritize **survivable performance**, not peak throughput only.

- policy switching (`SAFE/BALANCED/PERF`) under burst conditions
- power clamp when thermal/TSV risk crosses guards
- propagate lower-layer health into `omega_hbm`

## Organic integration philosophy

HBM_System is an upper-layer integrator, not an isolated model.

- `fabless.omega_global` -> signal margin contribution
- `memory.omega_global`, `rowhammer_risk`, `retention_risk` -> memory reliability contribution
- `battery.omega_battery` -> cooling/power headroom contribution
- `vectorspace.omega_vector` -> global system-health contribution
