# HBM_System Core Formulas

> Korean: [02_FORMULAS.md](02_FORMULAS.md)

## 1) Bandwidth approximation

\[
BW = N_{stack} \cdot N_{ch} \cdot BW_{ch} \cdot \eta_{ctrl} \cdot (0.6 + 0.4 I_{work})
\]

## 2) Per-stack power density

\[
P_{stack} = \frac{N_{stack}\cdot P_{stack,base}\cdot(0.7+0.6I_{work}) + P_{interposer}}{N_{stack}}
\]

## 3) Thermal gradient approximation

\[
\Delta T = P_{stack}\cdot(1+0.08(L-4))\cdot0.45\cdot\frac{1}{C_{cool}}
\]

## 4) TSV failure risk

\[
R_{tsv} = clamp01(0.15D_{tsv} + 0.55\frac{\Delta T}{45} + 0.30(1-M_{signal}))
\]

## 5) Lower-layer integrated health

\[
\Omega_{lower}=clamp01(0.55\Omega_{fab}+0.45\Omega_{mem}-0.20R_{rh}-0.15R_{ret})
\]

## 6) Final health score

\[
\Omega_{hbm} = clamp01(
0.22\Omega_{thermal}+0.20\Omega_{tsv}+0.16\Omega_{power}+0.14\Omega_{signal}
+0.18\Omega_{lower}+0.10\Omega_{contention}
)
\]

## 7) Protection hysteresis

To avoid control chattering, trip and recover thresholds are separated:

\[
trip = (\Delta T > T_{guard}) \lor (R_{tsv} > R_{guard})
\]
\[
recover = (\Delta T < T_{recover}) \land (R_{tsv} < R_{recover})
\]

- If current state is `limited=false` and `trip=true`, limiter enters.
- If current state is `limited=true` and `recover=true`, limiter exits.

## 8) Temporal thermal dynamics

For multi-tick accumulation, we use a first-order thermal state model:

\[
\frac{dT}{dt} = k_{th}\cdot P_{stack} - \frac{T - T_{amb}}{\tau_{th}}
\]
\[
T_{k+1} = T_k + \Delta t \cdot \left(k_{th}P_{stack} - \frac{T_k - T_{amb}}{\tau_{th}}\right)
\]
