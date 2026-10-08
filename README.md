# 🌾 Kaggriculture: Championship Tactical Planner & Economic Market Simulation

[![Kaggle Competition](https://img.shields.io/badge/Kaggle-Competition-20BEFF?logo=kaggle&logoColor=white)](https://www.kaggle.com/competitions/kaggriculture)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Environment](https://img.shields.io/badge/Environment-kaggle--environments-orange)](https://pypi.org/project/kaggle-environments/)
[![League Win Rate](https://img.shields.io/badge/League_Win_Rate-70%25_vs_Top_Traders-brightgreen)](#4-benchmark-results)

**Kaggle Competition:** [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture)  
Autonomous tactical farming agent, dynamic liquidity arbitrage, and tournament evaluation framework built for the Kaggle Kaggriculture $50,000 AI Simulation Challenge.

---

## 1. What I Built

**Kaggriculture** is a turn-based farming simulation where two players compete over a 30-day season (720 turns, 24 turns/day) to maximize final bank cash. Players manage a spatial grid, hire labor with Fibonacci cost scaling, and trade harvested commodities against an automated market maker with non-linear price degradation.

I engineered the **Master Tactical Planner (`main.py`)**, an autonomous agent that achieves **70.0% win rate against the top public ladder champion (The 2945 Farm)** and **100% win rate against standard baselines**. 

Rather than relying on ungrounded heuristics or unconstrained reinforcement learning, the agent solves two coupled problems:
1. **Physical Labor Optimization:** Frame-perfect coordination of the farmer and hired hands to clear land, maintain crops, and prevent animal starvation with zero wasted turns.
2. **Dynamic Economic Arbitrage:** Strategic timing of market trades to exploit endogenous inventory cycles created by autonomous town consumption while protecting livestock feed reserves.

---

## 2. Why the Economic Strategy Works

In Kaggriculture, raw farm output does not guarantee victory—**how and when you sell determines your realized price**:

- **Early Liquidity Generation (Productive Opening):** Standard agents idle workers on Day 0 while waiting for land clearance. The champion dispatches Farm Hand 1 on turn 0 to coordinate `(2,4)`—a future pasture site—to plant and water an extra wheat crop. This temporary crop is harvested on turn 54 and delivered on turn 57, injecting critical early capital into the bank before market prices decline. The pasture is restored immediately afterward without losing a single livestock turn.
- **Dynamic Milk Retention (`nomilk` Rule):** Cow milk has a high base value ($160/unit), but gluts crash the price to $1.00. The agent detects when milk-consuming shops (`PIZZA_SHOP`, `ICE_CREAM_SHOP`, `SMOOTHIE_SHOP`) are unlocked in town. If active, it preserves cows and sells milk directly into recurring town demand ticks; if absent, it transitions capacity toward wool and eggs.
- **Feed Reserve Guard:** Animals escape if unfed for two consecutive days. The agent dynamically partitions warehouse inventory:
  $$\text{Wheat Reserve} = N_{\text{animals}} \times (30 - \text{Day}) + N_{\text{animals}}$$
  Market orders are strictly prohibited from touching reserved wheat, guaranteeing 0% livestock abandonment.
- **Endogenous Price Timing:** Town center and town shops consume commodities on deterministic schedules (every 4 and 24 turns), temporarily draining market supply. Selling produce immediately after town consumption ticks captures top-of-curve prices before rival supply refills the market.
- **Terminal Asset Liquidation:** Over turns 710–718, the agent shifts from continuous compounding to total liquidation, converting all stored produce, feed, and excess inventory into cash before the season closes.

---

## 3. Champion Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   OBSERVATION INGESTION                     │
│    Grid State (10x10) │ Market Prices & Inv │ Town Shops     │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│   PHYSICAL LABOR SCHEDULER   │        │     MARKET ORDER PIPELINE    │
│  - Movement Action Tapes     │        │  1. Sell Candidates (Non-Feed│
│  - Stateful Task Chains      │        │  2. Fibonacci Hire (Labor)   │
│    (PICKUP -> FEED/FERTILIZE)│        │  3. Seed Purchases           │
│  - Pasture / Coop Lifecycle  │        │  4. Terminal Liquidation     │
└──────────────┬───────────────┘        └──────────────┬───────────────┘
               │                                       │
               └───────────────────────┬───────────────┘
                                       ▼
                       ACTION EMITTER (Farmer, Hands, Market)
```

The agent runs as a self-contained module in [`main.py`](main.py):
- **Deterministic Action Tapes:** Early-game sequences (opening wheat loop, quadrant purchase, structure placement) execute via calibrated action tapes to guarantee zero coordination collisions between multiple farm hands.
- **Stateful Task Chains:** Prevents silent engine failures by strictly decomposing compound operations into `MOVE` $\to$ `PICKUP` $\to$ `EXECUTE` sequences.
- **Sub-Millisecond Execution:** Operates at **0.32 ms – 0.52 ms per turn** (~50x faster than Kaggle's 25 ms timeout threshold), ensuring zero risk of timing out in production.

---

## 4. Benchmark Results

All evaluations use a **paired league evaluation harness** across identical `(seed, opponent, seat)` triples for both Seat 0 and Seat 1 to completely eliminate board layout variance and seat advantage.

### Opponent League Performance

| Opponent Benchmark | Match Count | Record (W-L-T) | Win Rate | Paired Delta Margin [95% CI] | Result |
|:---|:---:|:---:|:---:|:---:|:---:|
| **The 2945 Farm (Upstream Champion)** | 10 Paired Games | **7W - 3L - 0T** | **70.0%** | **+\$1,240** [+\$420, +\$2,060] | **Significant Win** |
| **Market Shock Baseline** | 10 Paired Games | **6W - 4L - 0T** | **60.0%** | **+\$680** [-\$110, +\$1,470] | Positive Margin |
| **Deterministic Starter** | 20 Paired Games | **20W - 0L - 0T** | **100.0%** | **+\$3,850** [+\$3,100, +\$4,600] | Undefeated |

### Robustness & Generalization
Evaluated across out-of-distribution (OOD) seeds `[42, 12345, 99999, 777777, 20260920]`:
- **Average Final Cash:** **\$5,120+** (starting capital: \$3,000)
- **Engine Fault Rate:** **0.0%** (zero status errors, zero animal escapes across all seeds)
- **Turn Latency:** **0.32 ms – 0.52 ms** (zero timeouts)

---

## 5. What Failed / What I Learned

Throughout development, several intuitive approaches proved counterproductive under empirical testing:

1. **Continuous Analytical NPV Replanning (V2):**
   - *Hypothesis:* Calculating continuous Net Present Value for every tile and dynamic replanning on every turn should beat static action tapes.
   - *Outcome:* In a deterministic spatial grid, dynamic replanners suffered from pathing hesitation and worker congestion. Rigid choreographic action tapes with stateful task chains outperformed free-form planners by 15–20% in net cash. The analytical model and technical documentation are preserved in [`archive/v2/`](archive/v2/).
2. **Speculative Counter-Planning Layers:**
   - *Hypothesis:* Predicting opponent moves and altering our early crop mix to counter their anticipated sales would avoid shared gluts.
   - *Outcome:* Ablation experiments demonstrated that speculative counter-planning degraded performance on out-of-distribution seeds by 8–12%. Farm development velocity mattered far more than early-game opponent interference.
3. **Predatory Order-Book Ambush (Adversarial Bot):**
   - *Hypothesis:* Stockpiling a war chest and dumping it in Slot 0 at steps 710/713 could front-run and crater the market price before rival orders execute.
   - *Outcome:* While effective against opponents with huge end-of-season bulk dumps, it imposed a holding cost against steady-selling opponents. Pure choreographic density proved universally superior. The implementation is preserved in [`docs/adversarial.md`](docs/adversarial.md) and [`archive/adversarial/`](archive/adversarial/).

---

## 6. Reproduction

### Installation
Requires Python 3.10+ and `kaggle-environments`:

```bash
# Clone the repository
git clone https://github.com/ayushshuklaivyleague-jpg/kaggriculture-ai-simulation.git
cd kaggriculture-ai-simulation

# Install dependencies
pip install -U kaggle-environments numpy
```

### Run Head-to-Head Matches
Execute a local 10-game match against the upstream ladder leader:
```bash
python eval_head_to_head.py
```

### Run Paired League Evaluation
Execute the paired tournament against upstream trading bots with 95% bootstrap confidence intervals:
```bash
python league_eval_harness.py
```

### Submit to Kaggle
```bash
kaggle competitions submit kaggriculture -f main.py -m "Kaggriculture Champion Tactical Planner v9.3"
```

---

## 7. Repository Structure

```
kaggriculture-ai-simulation/
├── README.md                       # Research narrative, benchmarks, and quickstart
├── main.py                         # 🌟 Master Tactical Planner (Champion entrypoint)
├── submission.py                   # Self-contained single-file submission
├── FINAL_NOTEBOOK.ipynb            # Canonical tournament & submission notebook
│
├── eval_head_to_head.py            # Paired head-to-head match runner vs Upstream 2945
├── league_eval_harness.py          # Paired league evaluation harness with bootstrap CI
├── run_extensive_eval.py           # 24-game multi-seed stress test
├── run_ablation_matrix.py          # Causal ablation runner for speculative layers
├── test_simulation.py              # Environment and integration smoke tests
│
├── opponent_2945_upstream.py       # Benchmark opponent: Upstream 2945 Farm
├── opponent_market_shock.py        # Benchmark opponent: Market Shock baseline
│
├── docs/
│   └── adversarial.md              # Research notes on predatory order-book ambush
├── archive/
│   ├── adversarial/                # Experimental ambush bot and test suite
│   ├── v2/                         # Analytical NPV planner and design specs
│   └── ...                         # Historical ablation variants & diagnostic tools
│
├── LICENSE                         # Apache License 2.0
├── NOTICE.txt                      # Attribution notices for open-source derivations
└── .gitignore                      # Git configuration
```

---

## 📜 License & Attributions

This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

### Upstream Lineage
- **Choreography Chassis:** Built upon *The 2945 Farm* by Thomas Tschinkel, yhay81, destbreso, aurax7, tetsutani, and prvsiyan under Apache-2.0.
- **Productive Opening:** Dmitrii Gluzdov (temporary early wheat cultivation on future pasture site).
- **Economic Formulation & Feed Guard:** Ayush A. Shukla (Dynamic milk retention, feed inventory partition, terminal liquidation).
