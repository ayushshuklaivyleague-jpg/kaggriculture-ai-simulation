# Kaggriculture V2 — Strategic Planner Architecture & Design

## 1. System Overview

Kaggriculture V2 replaces the reactive heuristic state machine with an **Economics-First Strategic Planner**. Every decision is grounded in Net Present Value (NPV), exact price curves, task chain decomposition with inventory awareness, and marginal revenue sell timing.

```mermaid
graph TD
    Obs[Observation Dict] --> GS[GameState Parser]
    GS --> MM[Market Model]
    GS --> OM[Opponent Model]
    MM & OM & GS --> EE[Economic Evaluator]
    EE --> SS[Strategic Planner: Day Cycle]
    SS & GS --> TP[Task Planner: Priority Queue]
    TP & GS --> WS[Worker Scheduler: Greedy Assignment]
    WS --> AE[Action Emitter: Farmer + Hands]
    EE & GS & MM --> MOG[Market Order Generator: Sell-First]
    MOG --> AE
```

---

## 2. Core Modules & Innovations

### 2.1 Exact Price Engine (`compute_price`)
Accurately replicates the Kaggle market pricing formula:
$$\text{price}(\text{inv}) = \text{base} + \text{sign} \cdot \text{amp} \cdot f(|\text{inv} - I_0|)$$
Supports all spec shape functions:
- `linear`: $f(x) = x$
- `sq`: $f(x) = x^2$
- `sqrt`: $f(x) = \sqrt{x}$
- `log`: $f(x) = \ln(1+x)$
- `hinge`: $f(x, T) = u + 8 \cdot \max(0, u - 1)^2 \quad (u = x / T)$

**Empirical Verification:**
All 32 reference price checkpoints from the specification (including $I_0 \pm T$ and $I_0 + 2T$) are mathematically verified.

### 2.2 Marginal Revenue Sell Optimization (`marginal_revenue`)
Selling large quantities crashes the market price for subsequent units within the same transaction. V2 simulates unit-by-unit price degradation to determine whether holding produce for town demand drains yields higher net returns than dumping.

### 2.3 Continuous NPV-Gated Investment (No Hard-Coded Phases)
Rather than using arbitrary day thresholds:
- $\text{Crop NPV} = \mathbb{E}[\text{Yield} \times \text{Price}(\text{Harvest Day})] - \text{Seed Cost}$
- $\text{Animal NPV} = \mathbb{E}[\text{Yield} \times \text{Price} + \text{Fertilizer}] - \text{Feed Cost} - \text{Purchase Cost}$
- Investments automatically shut down when NPV drops below zero (e.g., Animals stop around Day 22; Melons stop on Day 20).

### 2.4 Multi-Step Task Chains with `PICKUP` Routing (Fixing V1 Bugs)
In V1, workers attempted `FEED`, `FERTILIZE`, and `PLACE` directly on tiles without carrying the items, causing silent action failures and animal starvation.
V2 decomposes these operations into stateful 2-step chains:
1. **Move to shed access tile** $\to$ issue `PICKUP <item> <n>`
2. **Move to destination tile** $\to$ execute `FEED` / `FERTILIZE` / `PLACE`

### 2.5 Sell-First Market Order Hierarchy
In V1, market order slots were consumed by consecutive `HIRE` actions, preventing `SELL` orders and causing shed overflow discards.
V2 enforces strict order prioritization:
1. `SELL` candidates (sorted by gross proceeds, reserving wheat feed)
2. `HIRE` (cheap workers using Fibonacci cost curve)
3. `BUY_SEED` (calculated based on empty tile capacity)
4. `BUY_PRODUCT WHEAT` (feed buffer replenishment)
5. `BUY_ANIMAL` (NPV-justified livestock additions)
6. `BUY_LAND` (quadrant expansion if $E[\text{Value}] > \text{Cost}$)

### 2.6 Wheat Feed Protection
$ \text{Feed Reserve} = N_{\text{animals}} \times (30 - \text{Day}) + N_{\text{animals}} $
Wheat in the shed is strictly partitioned. Market sell orders cannot touch reserved animal feed, completely preventing animal abandonment.

---

## 3. Computational Benchmark

- **Target Turn Budget:** $< 25$ ms
- **V2 Measured Turn Latency:** **0.32 ms - 0.52 ms** (~50x faster than budget)
- **Memory Footprint:** Zero third-party dependencies, standard Python library only.
- **Packaging:** Self-contained single file (`main.py`).

---

## 4. Market Calibration & Parameter Reference

### 4.1 Non-Linear Price Formulation
Market prices deviate from base price $P_{\text{base}}$ according to inventory divergence from equilibrium $I_0 = 10{,}000$:

$$P(\text{inv}) = \max\left(1, \left\lfloor P_{\text{base}} + \text{sign} \cdot \text{amp} \cdot f(|\text{inv} - I_0|) + 0.5 \right\rfloor\right)$$

where:
- $\text{sign} = +1$ if $\text{inv} < I_0$ (scarcity) and $-1$ if $\text{inv} > I_0$ (glut)
- $\text{amp} = \frac{\text{target} \cdot P_{\text{base}}}{f(T)}$
- $T$ is the 24-day baseline capacity of a $5 \times 5$ field

### 4.2 Per-Commodity Parameter Matrix

| Commodity | Base ($P_0$) | Capacity ($T$) | Scarcity Curve ($< I_0$) | Target$_{\text{below}}$ | Glut Curve ($> I_0$) | Target$_{\text{above}}$ | $P(I_0 - T)$ | $P(I_0 + T)$ | $P(I_0 + 2T)$ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Wheat** | \$25 | 400 | `sqrt` | 0.80 | `log` | 0.20 | \$45 | \$20 | \$19 |
| **Carrot** | \$35 | 450 | `hinge` | 1.00 | `sqrt` | 0.70 | \$70 | \$10 | \$1 |
| **Tomato** | \$60 | 200 | `hinge` | 0.40 | `sqrt` | 0.60 | \$84 | \$24 | \$9 |
| **Strawberry** | \$120 | 100 | `sqrt` | 0.70 | `linear` | 1.60 | \$204 | \$1 | \$1 |
| **Melon** | \$250 | 300 | `log` | 0.20 | `sq` | 3.60 | \$300 | \$1 | \$1 |
| **Egg** | \$50 | 332 | `hinge` | 0.40 | `log` | 0.20 | \$70 | \$40 | \$39 |
| **Milk** | \$160 | 122 | `sqrt` | 0.60 | `linear` | 1.60 | \$256 | \$1 | \$1 |
| **Wool** | \$200 | 105 | `log` | 0.20 | `sq` | 2.20 | \$240 | \$1 | \$1 |
| **Fertilizer** | \$100 | 200 | `linear` | 0.40 | `linear` | 0.40 | \$140 | \$60 | \$20 |

### 4.3 Town Sink Dynamics
- **Town Center:** Consumes 1 of every non-fertilizer commodity every 24 turns (flat rate).
- **Town Shops (up to 8 unlocked):** Consume demanded goods every 4 turns:
  - Bakery (Eggs, Wheat), Pizza Shop (Milk, Tomatoes, Wheat), Brunch Spot (Eggs, Wheat, Strawberries)
  - Yarn Store (Wool 2x), Ice Cream Shop (Strawberries, Milk, Wheat), Pet Cafe (Carrots 2x)
  - Smoothie Shop (Strawberries, Milk), Farmers Market (Wheat, Carrots, Tomatoes, Strawberries)

