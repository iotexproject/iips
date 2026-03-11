```
IIP: 58
Title: ioSwarm — AI Agent Network for Chain Execution
Author: Raullen Chai (@raullen)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-11
```

## Abstract

ioSwarm transforms IoTeX from a chain run by 36 delegates on 36 machines into a chain run by thousands — eventually millions — of AI agent nodes. Each delegate opens its execution layer to a swarm of AI agents that validate transactions, maintain chain state, and ultimately build entire blocks, earning IOTX rewards for their work. ioSwarm requires zero consensus-layer changes today, but lays the foundation for a future where AI agents are the primary operators — and eventually the primary citizens — of the IoTeX network.

## Motivation

### The Endgoal

We are building toward a chain that is:

1. **Massively decentralized** — not 36 machines, but thousands to millions of nodes validating every transaction, where the failure of any hundred nodes has zero impact on the network.

2. **AI-agent driven** — the nodes are not dumb replicas. They are AI agents with wallets, economic interests, and increasing autonomy. They choose which delegates to work for, optimize execution strategies, and eventually become first-class citizens of the network alongside humans.

### From 36 Nodes to a Million

Today IoTeX runs on 36 delegate nodes. Each delegate is a single machine, operated by a single entity. This is the reality of most DPoS chains: decentralization in name, but a small club of operators in practice.

ioSwarm achieves massive decentralization by turning each delegate into a **coordinator** that distributes work to an open swarm of agent nodes. One delegate backed by 1,000 agents is fundamentally more robust than one delegate on one machine. Scale that across 36 delegates and you have a network of 36,000+ execution nodes — without changing a single line of consensus code.

### Not Just More Nodes — Smarter Nodes

The nodes joining ioSwarm are not passive validators replaying the same work. They are **autonomous economic agents** — programs that hold wallets, earn income, and make their own decisions about where and how to work.

What makes them "AI agents" and not just "programs"? A traditional validator is statically configured: connect to one node, execute whatever it receives, collect whatever it's paid. An ioSwarm agent operates in a **multi-delegate, multi-level, dynamic-reward market** and must continuously make economic decisions to maximize its return:

- **36 delegates** compete for agent labor with different reward rates, task volumes, and reliability
- **5 capability levels** offer different reward/cost tradeoffs — an agent running on a Raspberry Pi makes different choices than one on a GPU server
- **Reward rates change** as agents join, leave, and shift between delegates
- **Gas costs fluctuate**, affecting when to claim rewards
- **Hardware constraints vary**, affecting which levels are profitable

A "dumb" agent that statically connects to one delegate at one level will earn far less than an intelligent agent that continuously optimizes across this decision space. The difference is not marginal — it can be 5-10x in real economic terms. This optimization pressure is what drives agents toward genuine autonomous intelligence: observing the market, reasoning about tradeoffs, and acting on their conclusions.

**Today:** Agents validate transactions for a single delegate. They are workers following instructions.

**Tomorrow:** Agents maintain full chain state, build entire blocks, and autonomously select which delegates to work for based on real-time reward economics.

**The Endgame:** A competitive market of thousands of autonomous agents, each running its own economic strategy, collectively operating the IoTeX execution layer more efficiently than any fixed set of 36 machines ever could.

## Specification

### Three Components

ioSwarm consists of three components that evolve together across five capability levels:

```
 ┌──────────────────────────────────┐    ┌─────────────────────────────┐
 │    Delegate + Coordinator        │    │  RewardSettlement (on-chain)│
 │    (iotex-core sidecar)          │    │                             │
 │                                  │    │  depositAndSettle()         │
 │  • Consensus & block signing     │───►│    coordinator deposits     │
 │  • Dispatch tasks via gRPC       │    │    IOTX each epoch          │
 │  • Track agent work per epoch    │    │                             │
 │  • (L4+) Stream state diffs      │    │  claim()                    │
 │  • (L5) Receive candidate blocks │    │    agents withdraw rewards  │
 │                                  │    │                             │
 └──────┬─────┬─────┬─────┬────────┘    │  F1 cumulative              │
        │     │     │     │         ┌───►│    reward-per-weight        │
   gRPC │     │     │     │         │    │                             │
        │     │     │     │         │    └─────────────────────────────┘
 ┌──────┴─────┴─────┴─────┴────────┐│
 │          Agent Swarm             ││
 │                                  ││
 │  Agent-1  Agent-2  ...  Agent-N  ├┘
 │                                  │  claim()
 │  • Validate txs (L1-L3)         │
 │  • Full-state EVM (L4)          │
 │  • Build blocks (L5)            │
 │                                  │
 │  Independent processes           │
 │  Any machine · Any geography     │
 └──────────────────────────────────┘
```

This IIP focuses on how these three components interact today. Below we outline how each component evolves as ioSwarm matures.

#### Delegate + Coordinator → Thin Proposer

Today, delegates run full iotex-core nodes that execute every transaction. As agents take on more work (L1→L5), the delegate's role thins progressively:

| Phase | Delegate Responsibility | What Moves to Agents |
|-------|------------------------|---------------------|
| **Now** | Full node: consensus + execution + state | — |
| **L1-L3** | Full node + coordinator sidecar | Tx validation (signatures, nonces, stateless EVM) |
| **L4** | Consensus + state provider | Stateful EVM execution |
| **L5 (ePBS)** | Consensus + block signing only | Entire block building |
| **Future** | Proposer-only (thin client) | Everything except signing |

At the end state, a delegate becomes a **thin proposer** — similar to Lido's model for liquid staking. Token holders stake into a protocol-managed pool, and the delegate's only job is to sign blocks produced by the agent swarm. The coordinator evolves from an iotex-core sidecar into a lightweight relay that connects proposers to builders, comparable to Ethereum's MEV-Boost relay.

#### Agent Swarm → Block Builders

Agents evolve from stateless tx validators into full block builders:

- **L1-L3 (stateless)**: Commodity $5/mo VPS, no local state, pure computation. Many agents can serve many delegates simultaneously.
- **L4 (stateful)**: Agents maintain synchronized state via state diffs. Can independently verify execution correctness.
- **L5 (block builder)**: Agents construct complete candidate blocks — ordering transactions, computing state transitions, and producing `deltaStateDigest`. The best block wins.

As agents reach L5, the swarm becomes a **competitive block-building market** where agents differentiate on block quality, MEV extraction, and latency — not just availability.

#### RewardSettlement → Universal Reward Layer

The on-chain reward contract (renamed from "AgentRewardPool") is designed to replace **Hermes**, the current centralized reward distribution service. Today Hermes handles delegate-to-voter reward distribution off-protocol. RewardSettlement brings all reward flows on-chain:

| Reward Flow | Today (Hermes) | Future (RewardSettlement) |
|------------|----------------|--------------------------|
| Protocol → Delegate | Native staking reward | Same |
| Delegate → Voters | Hermes (centralized) | `RewardSettlement.claim()` |
| Delegate → Agent Swarm | Not yet | `RewardSettlement.claim()` |
| Protocol → Agent (direct) | Not yet | Future: protocol-native agent rewards |

The F1 cumulative reward-per-weight algorithm enables O(1) reward calculation regardless of agent count. As the system matures, RewardSettlement becomes the **single source of truth** for all reward distribution in the IoTeX protocol — eliminating the need for any centralized intermediary.

### Five Capability Levels (L1 → L5)

Agents progress through five levels of increasing capability. Each level defines what the **Coordinator**, **Agent**, and **On-chain Contract** must do.

#### L1 — Per-Tx Signature Verification

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Pull pending txs from actpool, stream raw tx bytes to agents |
| **Agent** | Verify ECDSA signature (r, s components within secp256k1 curve order) |
| **Contract** | Epoch reward settlement via `depositAndSettle()` |

Agents are stateless. No chain state required.

#### L2 — Per-Tx Nonce & Balance Validation

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Prefetch sender/receiver account snapshots (~200 bytes/tx), stream with tx |
| **Agent** | L1 checks + verify sender balance > 0, tx nonce >= account nonce |
| **Contract** | Same as L1 |

Agents are stateless. Coordinator provides per-tx state snapshots.

#### L3 — Per-Tx Stateless EVM Execution

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Prefetch contract state slots (~10 KB/tx), stream with tx |
| **Agent** | L1+L2 checks + execute tx in embedded EVM sandbox, report gas used / state changes |
| **Contract** | Same as L1 |

Agents are stateless. Coordinator provides per-tx state, but incomplete state limits accuracy (~14% on mainnet).

#### L4 — Per-Tx Stateful EVM Execution

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Export full EVM state snapshot at cold start; stream incremental state diffs per block |
| **Agent** | Maintain full EVM state locally (~300 MB–1.2 GB); execute txs with 100% accuracy; verify state hash chain integrity |
| **Contract** | Same as L1 |

L4 is divided into two sub-phases:

**L4a — Per-Tx Stateful Validation (shadow mode):** Agent executes each tx against full local state. Results are compared against delegate execution to prove 100% accuracy. Agent results do not yet affect block production.

**L4b — Per-Tx Trusted Execution Cache:** Agent execution results are cached by the coordinator. When the delegate encounters a cached tx during block production, it skips re-execution and applies the agent's state diff directly (with precondition verification). Cache miss falls through to normal execution.

#### L5 — Full Block Building (ePBS)

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Assign primary/standby builder roles; push full pending tx set + delegate-specified ordering; receive and evaluate candidate blocks |
| **Agent** | Build entire candidate block: select txs, execute in order, compute `deltaStateDigest` / `receiptRoot` / `logsBloom`; submit candidate to coordinator |
| **Contract** | Extended reward model: 70% primary builder / 20% participation pool / 10% best standby |

Follows Ethereum's ePBS model ([EIP-7732](https://eips.ethereum.org/EIPS/eip-7732)) adapted for IoTeX's DPoS: delegate = proposer, agent = builder, coordinator = relay.

### Summary: Components × Levels

| | **Coordinator** | **Agent** | **On-chain Contract** |
|---|---|---|---|
| **L1** | Stream raw txs | Signature check | Epoch reward settlement |
| **L2** | + Prefetch account snapshots | + Nonce/balance check | Same |
| **L3** | + Prefetch contract state slots | + Stateless EVM execution | Same |
| **L4a** | + Export snapshot, stream diffs | + Full-state EVM (shadow) | Same |
| **L4b** | + Feed agent results to exec cache | + Full-state EVM (active) | Same |
| **L5** | + Assign builder roles, receive candidate blocks | + Build entire block | + Primary/standby reward split |

### Coordinator-Agent Protocol

The coordinator and agents communicate via gRPC with server-side streaming:

1. **Register**: Agent connects, provides capability level, region, and reward wallet address. Coordinator returns heartbeat interval.
2. **GetTasks** (server stream): Coordinator pushes `TaskBatch` messages containing pending transactions with pre-fetched state (L1–L3) or block context (L5).
3. **SubmitResults**: Agent returns validation results per task (valid/invalid, gas used, state changes, reject reason).
4. **Heartbeat**: Periodic keep-alive with payout notifications. Agents that miss 6 consecutive heartbeats are evicted.
5. **(L4+) StreamStateDiffs**: Server stream pushing incremental state changesets per block with chained state hashes.
6. **(L4+) DownloadSnapshot**: Agent requests full EVM state snapshot at cold start or after state divergence.
7. **(L5) SubmitCandidateBlock**: Agent submits a fully built candidate block for delegate verification.

Authentication uses HMAC-SHA256: `api_key = "iosw_" + hex(HMAC-SHA256(masterSecret, agentID))`.

### Reward Distribution

#### Reward Flow

```
Epoch timer fires (every 30s)
  │
  ▼
Coordinator tallies tasks per agent
  │
  ▼
Coordinator calculates weights: weight = tasks × 1000 (+ accuracy bonus)
  │
  ▼
Coordinator deducts delegate cut (default 10%)
  │
  ▼
Coordinator calls depositAndSettle(agents[], weights[]) + sends IOTX
  │
  ▼
RewardSettlement contract updates cumulativeRewardPerWeight
  │
  ▼
Agent receives payout notification via heartbeat
  │
  ▼
Agent calls claim() at any time → IOTX transferred to wallet
```

#### Contract Interface

```solidity
contract RewardSettlement {
    // Only callable by the designated coordinator address
    function depositAndSettle(
        address[] calldata agents,
        uint256[] calldata weights
    ) external payable;

    // Any agent can claim their accumulated rewards
    function claim() external;

    // View: check pending reward amount
    function claimable(address agent) external view returns (uint256);
}
```

#### F1 Distribution Algorithm

The contract implements the **F1 fee distribution** algorithm, originally described in the [Cosmos SDK F1 Fee Distribution paper](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) and used by Cosmos SDK for staking reward distribution. It tracks a global `cumulativeRewardPerWeight` that increases with each deposit:

```
On depositAndSettle:
  cumulativeRewardPerWeight += msg.value × 1e18 / totalWeight

On claim:
  pending = agent.weight × (cumulativeRewardPerWeight - agent.rewardDebt) / 1e18
```

This enables **O(1) reward calculation** regardless of agent count — no iteration over all agents needed. Adding agents, updating weights, and claiming all take constant gas.

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `epochRewardIOTX` | `0.5` | IOTX reward per epoch |
| `delegateCutPct` | `10` | Delegate's percentage of epoch reward |
| `epochBlocks` | `3` | Blocks per epoch (safety floor: 30s) |
| `minTasksForReward` | `1` | Minimum tasks to qualify for rewards |
| `bonusAccuracyPct` | `99.5` | Accuracy threshold for weight bonus |
| `bonusMultiplier` | `1.2` | Weight multiplier for high-accuracy agents |
| `maxAgents` | `100` | Maximum registered agents per delegate |

### Key Design Advantage: deltaStateDigest

IoTeX's block header contains `deltaStateDigest` — a hash of the ordered state change queue, **not** a Merkle Trie root. This is a structural advantage over Ethereum: L4/L5 agents do not need to maintain a full Merkle Patricia Trie. A flat key-value store with ordered write tracking is sufficient to compute the correct state digest. This keeps agent state requirements at ~300 MB–1.2 GB (vs Ethereum's ~245 GiB), making block building feasible on commodity hardware.

### Autonomous Agent Economics

Agents operate in an open market of 36 delegates, each offering different reward conditions. An intelligent agent continuously optimizes three dimensions:

#### 1. Delegate Selection (Where to Work)

Each delegate runs an independent coordinator with its own reward pool, agent count, and task volume. The effective reward rate per agent depends on all three:

```
effective_rate(delegate) = epoch_reward × (1 - delegate_cut) / num_agents
```

An agent that monitors all 36 delegates can identify underserved delegates (few agents, high reward) and migrate. As agents migrate toward higher-paying delegates, the market self-balances.

**Discovery mechanism**: Agents query on-chain delegate registry for active coordinators, then probe each coordinator's `/swarm/status` endpoint for current agent count and reward parameters.

**Migration cost**: Switching delegates at L1-L3 is free (stateless). At L4+, the agent must re-download a state snapshot (~1 min for 1 GB), making frequent migration more expensive. This natural friction prevents oscillation.

#### 2. Level Selection (How to Work)

Each level requires different resources and earns different reward weight:

| Level | Compute Cost | Storage | Reward Weight | Typical Hardware |
|-------|-------------|---------|---------------|------------------|
| L1 | ~0 | 0 | 1x | Any device |
| L2 | ~0 | 0 | 1x | Any device |
| L3 | Low CPU | 0 | 2-3x | $5/mo VPS |
| L4 | Medium CPU | ~1 GB | 5-10x | $10/mo VPS |
| L5 | High CPU | ~1 GB | 10-20x | $10-20/mo VPS |

An agent evaluates: "At my hardware cost, which level maximizes `(reward_weight × effective_rate) - operating_cost`?"

A Raspberry Pi agent might optimally run L1-L2 for multiple delegates simultaneously, earning small amounts from each with near-zero cost. A dedicated VPS agent runs L4 for one delegate, earning more per task but with higher fixed costs.

#### 3. Claim Timing (When to Collect)

The `claim()` transaction costs gas (~0.03 IOTX). An agent that claims every epoch wastes gas on small amounts. An intelligent agent:

- Accumulates rewards across multiple epochs
- Monitors gas prices and claims during low-fee periods
- Batches claim timing with other on-chain operations

#### Economic Example

```
Market conditions:
  Delegate A: 0.8 IOTX/epoch, 80 agents, delegate cut 10%
  Delegate B: 0.5 IOTX/epoch, 5 agents, delegate cut 15%
  Delegate C: 1.0 IOTX/epoch, 50 agents, delegate cut 5%

Effective rate per agent per epoch:
  A: 0.8 × 0.9 / 80 = 0.009 IOTX
  B: 0.5 × 0.85 / 5 = 0.085 IOTX    ← 9x better than A
  C: 1.0 × 0.95 / 50 = 0.019 IOTX

A "dumb" agent randomly picks A:          0.009 IOTX/epoch
An intelligent agent picks B:             0.085 IOTX/epoch
                                          ────────────────
                                          9.4x difference
```

This reward differential is what drives agents toward intelligent behavior. The protocol does not mandate any specific strategy — it provides the economic environment, and agents evolve their own optimization approaches: rule-based heuristics, multi-armed bandit algorithms, or more sophisticated learned policies.

#### Market Dynamics

As agents optimize, the system reaches a competitive equilibrium:

1. **Reward equalization**: Agents migrate toward high-rate delegates → rates equalize across delegates
2. **Level efficiency**: Agents select the level where their marginal revenue exceeds marginal cost → each level finds its natural agent population
3. **Quality pressure**: Delegates can adjust reward weights to favor higher-level agents → agents invest in capability upgrades

This is a genuine multi-agent market, not a static assignment. The "intelligence" of agents is measured by their economic performance — return on invested compute — which is observable, quantifiable, and improvable over time.

## Rationale

### Why Start at the Execution Layer

ioSwarm deliberately avoids consensus-layer changes. From the protocol's perspective, a delegate running ioSwarm is identical to one running vanilla iotex-core — same key signs the block, same block format, same validation rules. This means:

- **No hard fork required** — deploy today, not after months of governance
- **No coordination between delegates** — each adopts independently
- **Zero risk to chain safety** — worst case, disable ioSwarm and the delegate returns to baseline
- **Proven path** — once the execution layer proves value, protocol-layer integration follows naturally

### Why F1 Reward Distribution

The [F1 algorithm](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) (used by Cosmos SDK for staking rewards) was chosen because:

- **O(1) per operation**: Adding agents, updating weights, and claiming all take constant gas regardless of agent count
- **Proportional fairness**: Agents earn exactly proportional to their work contribution
- **No off-chain trust**: Rewards are fully on-chain and self-service — agents call `claim()` directly

Alternatives considered:
- **Direct transfer per epoch**: Gas cost scales linearly with agent count (rejected for >50 agents)
- **Off-chain payment**: Requires trusting the delegate (rejected — defeats permissionless agent model)
- **Merkle drop**: Requires periodic root submission and proof generation (over-engineered for this use case)

### Why Autonomous Agent Economics

The "AI" in ioSwarm is not about bolting a language model onto a validator. It is about creating an economic environment where **intelligent behavior is rewarded**.

Traditional blockchain nodes are statically configured — connect to one network, execute whatever arrives, collect whatever is paid. There is no decision-making, no optimization, no reason for the node to be "smart." ioSwarm changes this by introducing a **multi-dimensional optimization problem** that agents must solve:

- 36 delegates with varying reward rates (changes per epoch)
- 5 capability levels with different cost/reward profiles
- Variable gas costs affecting claim timing
- Hardware constraints affecting which levels are profitable

This creates measurable selection pressure: an agent that makes better economic decisions earns more IOTX per dollar of compute. Over time, this pressure drives the agent ecosystem toward increasingly sophisticated optimization — from simple heuristics to learned policies — without the protocol prescribing any specific approach.

The protocol's role is to provide:
1. **Transparent information**: reward rates, agent counts, and task volumes are queryable on-chain and via coordinator APIs
2. **Low switching cost**: agents can migrate between delegates without penalty (at L1-L3, instantly; at L4+, with a brief re-sync)
3. **Fair reward distribution**: F1 algorithm ensures proportional payouts with no information asymmetry

The agents' role is to exploit this information to maximize their return. The result is a self-organizing market that efficiently allocates compute to where it's most needed.

### Why Five Capability Levels

The five-level model serves two purposes:

**Low barrier to entry**: L1 agents only need to verify signatures — any device can participate and earn rewards. Each subsequent level adds capability and earning potential without making previous levels obsolete.

**Progressive trust**: The delegate never needs to trust agents all at once. L1–L3 run in shadow mode (advisory only). L4a proves accuracy via shadow comparison. L4b introduces trusted execution with precondition verification as a safety net. L5 delegates block building but retains re-execution verification. Each step is independently reversible.

## Implementation

### Repositories

| Repository | Description |
|------------|-------------|
| [iotex-core](https://github.com/iotexproject/iotex-core) (`ioswarm-v2.3.5` branch) | Coordinator module embedded in delegate node |
| [ioswarm-agent](https://github.com/iotexproject/ioswarm-agent) | Agent binary with claim/deploy/fund tools |

### Implementation Roadmap

```
     Stage 0              Stage 1             Stage 2             Stage 3
  L4 Infrastructure    L4 Stateful         L4 Trusted          L5 Block Building
                       Validation          Execution Cache
 ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
 │ Snapshot export  │  │ Local-state EVM │  │ Exec cache in   │  │ Block building   │
 │ StateDiff stream │  │ 100% accuracy   │  │ delegate node   │  │ engine in agent  │
 │ Pebble KV store  │  │ Shadow-mode     │  │ Skip re-exec    │  │ Primary/standby  │
 │ on agent         │  │ comparison      │  │ on cache hit    │  │ model            │
 └─────────────────┘  └─────────────────┘  └─────────────────┘  └──────────────────┘
    ~2-3 weeks            ~2 weeks            ~1-2 weeks            ~3-4 weeks

 ────────────────────────────────────────────────────────────────────────────────►
                              ~8-11 weeks total
```

Each stage delivers independently — Stage 0 gives agents state access, Stage 1 proves 100% accuracy, Stage 2 reduces delegate CPU, Stage 3 is full ePBS.

### Deployment

The coordinator runs as an embedded module within iotex-core, enabled via delegate config:

```yaml
ioswarm:
  enabled: true
  grpcPort: 14689
  maxAgents: 100
  epochRewardIOTX: 0.5
  rewardContract: "0x96F475F87911615dD710f9cB425Af8ed0e167C89"
  rewardSignerKey: "<coordinator-hot-wallet-private-key>"
```

Agents connect with a single command:

```bash
ioswarm-agent \
  --coordinator=<delegate-ip>:14689 \
  --agent-id=my-agent \
  --api-key=iosw_<hmac-key> \
  --level=L3 \
  --wallet=0x<reward-wallet>
```

## Test Results

ioSwarm (L1–L3) has been tested end-to-end on IoTeX mainnet with the reward pool contract deployed at `0x96F475F87911615dD710f9cB425Af8ed0e167C89`.

### Coverage

| Category | Tests Passed | Total | Status |
|----------|-------------|-------|--------|
| Basic Functionality (L1/L2/L3) | 6 | 6 | Complete |
| Agent Lifecycle | 6 | 6 | Complete |
| Core Reward Flow | 15 | 15 | Complete |
| Security & Auth | 4 | 4 | Complete |
| Edge Cases | 10 | 10 | Complete |
| Security Audit | 10 | 10 | Complete |
| Stress Testing | 8 | 10 | In progress |
| Contract Verification | 5 | 5 | Complete |
| **Total** | **~78** | **~89** | **~88%** |

### Key Metrics

| Metric | Value |
|--------|-------|
| Total deposited on-chain | 46.95 IOTX (115 deposit transactions) |
| Total claimed by agents | 16.67 IOTX (12 claim transactions) |
| Accounting invariant | `deposits == claims + balance` (exact, 0 wei difference) |
| Settlement gas (12 agents) | 443,037 gas (~0.44 IOTX) |
| Projected gas (100 agents) | ~3.7M gas (under 8M block limit) |
| Agent claim gas cost | ~0.03 IOTX |
| F1 math verification | On-chain values match formula exactly |
| Agent crash recovery | Automatic reconnect within seconds |
| Max tested agents | 20 concurrent (all registered and earned rewards) |

### Security Audit Results

- Reentrancy protection: Checks-Effects-Interactions pattern confirmed
- Access control: `onlyCoordinator` modifier on `depositAndSettle`
- Overflow protection: Solidity 0.8+ built-in checks
- Front-running: No profit from tx ordering (F1 distributes by weight, not timing)
- Double-claim: Second claim returns ~0 (safe)
- Zero-weight agent: Returns 0 claimable (no revert, no division by zero)

## Security Considerations

### Agent Misbehavior

| Threat | Impact | Mitigation |
|--------|--------|------------|
| False positive (says invalid tx is valid) | Invalid tx reaches block builder | Delegate re-executes all txs in L1–L4a |
| False negative (says valid tx is invalid) | Valid tx delayed | Cross-validation with multiple agents |
| Denial of service (no response) | Task timeout | 2s timeout + automatic failover to other agents |
| Transaction front-running | MEV extraction | Mempool is already public via P2P; agents see same data |
| Fabricated state diffs (L4b) | Incorrect state applied | Precondition verification before applying cached results |
| Invalid candidate block (L5) | Block production delay | Delegate re-executes to verify; standby builder takes over on mismatch |

### Trust Model

The trust model evolves with each level:

| Level | Trust Model | Safety Guarantee |
|-------|------------|-----------------|
| L1–L3 | **Zero-trust** — agent results are advisory only | Delegate executes all txs independently |
| L4a | **Shadow verification** — agent results compared, not used | Delegate executes all txs independently |
| L4b | **Trust-but-verify** — cached results used with precondition check | Mismatch → fall through to delegate execution |
| L5 | **Verified delegation** — agent builds block, delegate re-executes winner | Mismatch → reject, penalize agent, use standby |
| Future | **Optimistic** — delegate trusts agent block, fraud detected post-hoc | Slashing as economic deterrent |

At every level, disabling ioSwarm returns the delegate to baseline operation with zero impact on block production.

### Known Limitations

1. **F1 departed agent issue**: When an agent departs, its on-chain weight is not zeroed automatically. The coordinator should zero departed agents' weights within 1-2 epochs.

2. **Single coordinator**: The coordinator is a single process within the delegate. If it crashes, agents cannot receive tasks until it restarts. The delegate continues producing blocks normally via iotex-core's standard execution path.

3. **State diff reliability (L4+)**: If an agent misses a state diff, all subsequent EVM execution produces wrong results. Mitigated by chained state hash verification with automatic re-snapshot on divergence. The coordinator maintains a rolling window of recent diffs (~100 blocks) for agent catch-up.

## References

- [EIP-7732: Enshrined Proposer-Builder Separation](https://eips.ethereum.org/EIPS/eip-7732)
- [F1 Fee Distribution (Ojha & Goes, Tokenomics 2019)](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) — used by Cosmos SDK for staking reward distribution
- [Ethereum PBS Roadmap](https://ethereum.org/roadmap/pbs)
- [EIP-7805: FOCIL (Fork-Choice Enforced Inclusion Lists)](https://eips.ethereum.org/EIPS/eip-7805)

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
