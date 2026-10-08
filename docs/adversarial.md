# Adversarial Market Predator (Experimental Bot)

> **Context:** This document preserves the architecture, mechanics, and ablation notes for the experimental adversarial agent (`adversarial_ambush.py` and `bot_adversarial/`). While the champion agent focuses on physical choreographic efficiency and liquidity capture, this bot explores predatory order-book disruption.

---

## 1. Motivation

In Kaggriculture, both players share a single dynamic order book initialized at $I_0 = 10{,}000$. When a player sells $N$ units of a product in one turn, the units are cleared iteratively, degrading the price unit-by-unit.

Industrial farming bots on the ladder frequently accumulate massive late-game stockpiles (especially melons, wool, strawberries, and milk) and dump them in a single massive liquidation turn near Day 28–30. Because orders are submitted simultaneously and interleaved, an agent that submits a dump in **Slot 0** can depress the market price down to the $\$1.00$ floor *before* the opponent's order in later slots begins filling.

---

## 2. Architecture & Components

```
Obs Dict ──> Opponent Shadow Tape ──> Weapon Evaluator ──> Slot Sniper ──> Execution
                 (Track stocks)       (P >= 40, steep glut) (Slot 0 Dump)
```

### 2.1 Rival Shadow Tape & War Chest
- **Shadow Tape:** Tracks the opponent's tile grid and harvests over time to estimate unliquidated private inventory.
- **War Chest Accumulation:** From Day 26 (step 624) onwards, holds a targeted quantity of high-volatility assets rather than trickling them to town demand. Preserves 100% of early and mid-game capital for farm expansion.

### 2.2 Live Market Weapon Evaluator
Target commodities with severe non-linear glut penalties:
- **Melon:** $f = \text{sq}$, $\text{above\_target} = 3.6$
- **Wool:** $f = \text{sq}$, $\text{above\_target} = 2.2$
- **Strawberry:** $f = \text{linear}$, $\text{above\_target} = 1.6$
- **Milk:** $f = \text{linear}$, $\text{above\_target} = 1.6$

The evaluator dynamically checks if current market price $P \ge \$40$ and verifies that the price collapse derivative will cause disproportionate loss to the rival.

### 2.3 Surgical Slot 0 Sniper
- At liquidation turns (steps 710 and 713), prioritizes the predatory dump into **Market Queue Slot 0**.
- The simulator processes order slots round-robin (`Player0[0]`, `Player1[0]`, `Player0[1]`, `Player1[1]`, ...).
- By firing in Slot 0, market depth is cratered before an opponent's liquidation order (typically queued after `HIRE` or `BUY_PRODUCT` in slots 3–7) quotes its first unit.

### 2.4 Asymmetric Safety Gate
- If the estimated opponent stock is not significantly greater than our sacrificed volume, the ambush aborts and falls back to standard optimal liquidation.

---

## 3. Findings & Why It Was Kept Secondary

1. **In-Distribution vs. Out-of-Distribution Sensitivity:** The ambush relies on the opponent attempting a late-game dump. Against opponents with smooth daily selling (such as shop-demand-aligned traders), the war chest holding penalty slightly reduced our own capital compounding.
2. **Superiority of Pure Choreography:** Our Master Tactical Planner (`main.py`) consistently generated higher standalone net cash ($5,100+) through superior choreographic labor density and Day 0 liquidity capture without relying on opponent vulnerability.
