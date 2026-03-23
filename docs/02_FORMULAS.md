# HBM_System 핵심 수식

> English: [02_FORMULAS_EN.md](02_FORMULAS_EN.md)

## 1) 대역폭 근사

\[
BW = N_{stack} \cdot N_{ch} \cdot BW_{ch} \cdot \eta_{ctrl} \cdot (0.6 + 0.4 I_{work})
\]

## 2) 스택당 전력 밀도

\[
P_{stack} = \frac{N_{stack}\cdot P_{stack,base}\cdot(0.7+0.6I_{work}) + P_{interposer}}{N_{stack}}
\]

## 3) 열 기울기 근사

\[
\Delta T = P_{stack}\cdot(1+0.08(L-4))\cdot0.45\cdot\frac{1}{C_{cool}}
\]

## 4) TSV 실패 리스크

\[
R_{tsv} = clamp01(0.15D_{tsv} + 0.55\frac{\Delta T}{45} + 0.30(1-M_{signal}))
\]

## 5) 하위 레이어 통합 건강도

\[
\Omega_{lower}=clamp01(0.55\Omega_{fab}+0.45\Omega_{mem}-0.20R_{rh}-0.15R_{ret})
\]

## 6) 최종 건강도

\[
\Omega_{hbm} = clamp01(
0.22\Omega_{thermal}+0.20\Omega_{tsv}+0.16\Omega_{power}+0.14\Omega_{signal}
+0.18\Omega_{lower}+0.10\Omega_{contention}
)
\]

## 7) 보호 히스테리시스

제어 치터링 방지를 위해 trip/recover 임계를 분리한다.

\[
trip = (\Delta T > T_{guard}) \lor (R_{tsv} > R_{guard})
\]
\[
recover = (\Delta T < T_{recover}) \land (R_{tsv} < R_{recover})
\]

- 현재 상태가 `limited=false`이고 `trip=true`면 제한 진입
- 현재 상태가 `limited=true`이고 `recover=true`면 제한 해제

## 8) 시간축 열 동역학

다중 tick 누적을 위해 1차 열 상태 모델 사용:

\[
\frac{dT}{dt} = k_{th}\cdot P_{stack} - \frac{T - T_{amb}}{\tau_{th}}
\]
\[
T_{k+1} = T_k + \Delta t \cdot \left(k_{th}P_{stack} - \frac{T_k - T_{amb}}{\tau_{th}}\right)
\]
