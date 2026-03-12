```
IIP: 58
Title: ioSwarm — Decentralized Execution Layer via Autonomous Agent Swarm
Author: Raullen Chai (@raullen)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-11
```

## Abstract

ioSwarm transforms IoTeX from a chain run by 36 delegates on 36 machines into a chain run by thousands — eventually millions — of autonomous agent nodes. Each delegate opens its execution layer to a swarm of autonomous agents that validate transactions, maintain chain state, and ultimately build entire blocks, earning IOTX rewards for their work. ioSwarm requires zero consensus-layer changes, deploys as an opt-in sidecar to each delegate's existing iotex-core node, and lays the foundation for a future where autonomous agents are the primary operators of the IoTeX network.

## Motivation

### Consensus-Execution Separation

Every blockchain has two layers of concern:

```
Consensus Layer    decide WHICH block is canonical (voting, attestation, fork choice)
Execution Layer    decide WHAT goes into the block (tx validation, EVM execution, state)
```

In most chains — including IoTeX today — both layers run on the same machine, operated by the same entity. Separating them has been a recurring theme in blockchain architecture:

| Milestone | What It Separates | How | Key EIPs |
|-----------|------------------|-----|----------|
| **Ethereum's Merge (2022)** | Consensus client from execution client | Two separate programs communicating via Engine API, but still on the **same operator's machine** | [EIP-3675](https://eips.ethereum.org/EIPS/eip-3675) (PoS transition), [Engine API](https://github.com/ethereum/execution-apis) (consensus↔execution interface), [EIP-4399](https://eips.ethereum.org/EIPS/eip-4399) (PREVRANDAO) |
| **Ethereum's ePBS** | Proposer from Builder (within block production) | Specialized builders construct blocks; validators just sign. But builders are **few and centralized** (3–5 dominant firms) | [EIP-7732](https://eips.ethereum.org/EIPS/eip-7732) (ePBS), [EIP-7898](https://eips.ethereum.org/EIPS/eip-7898) (uncouple execution payload) |
| **ioSwarm** | Consensus layer from execution layer | Execution moves to an **open network** of thousands of independent agents | This IIP |

Ethereum's Merge took years and dozens of EIPs to achieve consensus-execution separation at the *process* level — splitting one monolithic Geth client into a Beacon Chain consensus client (Prysm, Lighthouse, etc.) and an execution client (Geth, Reth, etc.) connected via the Engine API. ioSwarm takes the next step: separating them at the *network* level. The execution layer is not just a different process on the same machine, but an **open, decentralized network** of commodity agents — anyone with a $5/mo VPS can join, perform execution work, and earn rewards.

| | Ethereum ePBS | IoTeX ioSwarm |
|---|---|---|
| **Consensus** | Validators (~900K) | Delegates (36) |
| **Execution** | Builders (3–5 dominant, centralized) | Agent Swarm (thousands, open market) |
| **Relay** | MEV-Boost relay | Coordinator (embedded in delegate) |
| **Participation** | High barrier (specialized hardware, MEV expertise) | Low barrier ($5/mo VPS, anyone can join) |

At L5 (full block building), ioSwarm's architecture *includes* ePBS as a special case — the delegate becomes the proposer, the agent becomes the builder. But the broader design encompasses L1–L4, where agents perform execution work without building blocks at all. ePBS is the endgame; consensus-execution separation is the framework.

**In one sentence: ioSwarm separates the execution layer from IoTeX's consensus delegates and distributes it across an open swarm of autonomous agents, where anyone can participate and each delegate curates its own agent pool.**

### The Problem

IoTeX runs on 36 delegate nodes. Each delegate is a single machine, operated by a single entity. This is the reality of most DPoS chains: decentralization in name, but a small club of operators in practice.

ioSwarm addresses two fundamental limitations of this architecture:

**1. Scale.** One delegate backed by 1,000 agents is fundamentally more robust than one delegate on one machine. Scale that across 36 delegates and you have a network of 36,000+ execution nodes — without changing a single line of consensus code.

**2. Intelligence.** The nodes joining ioSwarm are not passive replicas replaying the same work. They are **autonomous economic agents** — programs that hold wallets, earn income, and make decisions about where and how to work. A traditional validator is statically configured: connect to one node, execute whatever it receives, collect whatever it's paid. An ioSwarm agent operates in a dynamic market of 36 delegates with varying rewards, multiple capability levels with different cost profiles, and fluctuating gas costs — and must continuously optimize to maximize its return.

This optimization pressure is what drives agents toward genuine autonomous intelligence: observing the market, reasoning about tradeoffs, and acting on their conclusions. The difference between a dumb agent and a smart one is not marginal — it can be 5-10x in real economic terms (see [Economic Example](#economic-example)).

**Today:** Agents validate transactions for a single delegate. They are workers following instructions.

**Tomorrow:** Agents maintain full chain state, build entire blocks, and autonomously select which delegates to work for based on real-time reward economics.

**The Endgame:** A competitive market of thousands of autonomous agents, each running its own economic strategy, collectively operating the IoTeX execution layer more efficiently than any fixed set of 36 machines ever could.

## Terminology

| Term | Definition |
|------|-----------|
| **Delegate** | One of IoTeX's 36 elected block producers. Runs iotex-core, participates in consensus, signs blocks. |
| **Coordinator** | A sidecar module embedded in the delegate's iotex-core node. Dispatches work to agents, tracks contributions, settles rewards. Does not participate in consensus. |
| **Agent** | An independent process (typically on a $5–20/mo VPS) that connects to a coordinator, performs execution work, and earns IOTX. The protocol is open — anyone can run an agent — but each delegate decides which agents to admit (see [Agent Admission](#sybil-resistance-and-agent-admission)). |
| **Agent Swarm** | The set of all agents connected to a single coordinator. Each delegate has its own swarm. |
| **Capability Level (L1–L5)** | A classification of agent capability, from L1 (signature verification only) to L5 (full block building). Higher levels require more resources but earn higher rewards. See [Capability Levels](#capability-levels-l1l5). |
| **Epoch** | A fixed interval (configurable, default 3 blocks / ~30s) after which the coordinator tallies agent work and settles rewards on-chain. |
| **RewardSettlement** | An on-chain smart contract that holds deposited rewards and allows agents to claim their share. Uses the F1 algorithm for O(1) proportional distribution. |
| **deltaStateDigest** | IoTeX's block header field containing a hash of the ordered state change queue (not a Merkle Trie root). This is a key structural advantage — see [deltaStateDigest](#key-design-advantage-deltastatedigest). |
| **State Diff** | An ordered list of state changes produced by executing a block. At L4+, the coordinator streams these to agents so they can maintain synchronized local state. |
| **Shadow Mode** | A validation mode where agent results are compared against the delegate's own execution but not used for block production. Used to prove agent accuracy before trusting agent results. |

## Specification

### Architecture Overview

ioSwarm consists of three components:

```
 ┌──────────────────────────────────┐    ┌─────────────────────────────┐
 │    Delegate + Coordinator        │    │  RewardSettlement (on-chain)│
 │    (iotex-core sidecar)          │    │                             │
 │                                  │    │  depositAndSettle()         │
 │  • Consensus & block signing     │───►│    coordinator deposits     │
 │  • Dispatch work to agents       │    │    IOTX each epoch          │
 │  • Track agent contributions     │    │                             │
 │  • Provision state to agents     │    │  claim()                    │
 │  • Verify agent results          │    │    agents withdraw rewards  │
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
 │  • Validate transactions         │
 │  • Execute EVM                   │
 │  • Build blocks                  │
 │                                  │
 │  Independent processes           │
 │  Any machine · Any geography     │
 └──────────────────────────────────┘
```

1. **Delegate + Coordinator** — the delegate runs consensus and block signing as before; the coordinator is an embedded sidecar that dispatches execution work to agents, provisions chain state, and settles rewards.

2. **Agent Swarm** — a set of independent agent processes, each performing execution work (from simple signature checks to full block building) and earning IOTX rewards proportional to their contribution.

3. **RewardSettlement** — an on-chain contract that receives IOTX deposits from coordinators each epoch and allows agents to claim their accumulated rewards at any time.

The amount of work an agent can perform — and the corresponding reward — depends on its **capability level**, defined next.

---

### Capability Levels (L1–L5)

ioSwarm defines five capability levels that classify what an agent can do. Each level subsumes the previous one: an L3 agent performs all L1 and L2 work plus EVM execution. Higher levels require more resources (compute, storage) but earn proportionally higher rewards.

| Level | Name | Agent State | What the Agent Does | Trust Model |
|-------|------|-------------|--------------------|--------------------|
| **L1** | Signature Verification | None | Verify ECDSA signatures | Zero-trust (shadow) |
| **L2** | Nonce & Balance Check | None | L1 + verify sender nonce and balance | Zero-trust (shadow) |
| **L3** | Stateless EVM Execution | None | L2 + execute tx in EVM sandbox with coordinator-provided state | Zero-trust (shadow) |
| **L4** | Stateful EVM Execution | Full EVM state (~1 GB) | Full EVM execution against local state with 100% accuracy | Shadow → trust-but-verify |
| **L5** | Full Block Building | Full EVM state (~1 GB) | Build entire candidate block: order txs, execute, compute block header fields | Verified delegation |

Key transitions:

- **L1–L3 are stateless.** The coordinator provides whatever state the agent needs per-task. Agents are lightweight ($5/mo VPS, <64 MB RAM) and can serve multiple delegates simultaneously.
- **L3 → L4 is the critical jump.** At L3, the coordinator provides per-tx state snapshots, but incomplete state limits EVM accuracy to ~14% on mainnet. At L4, the agent maintains full synchronized EVM state locally, achieving 100% accuracy.
- **L4 → L5 adds block building.** The agent no longer validates individual transactions — it constructs entire candidate blocks, taking on the delegate's execution workload.

The following sections detail what each component does at each level.

#### L1 — Per-Tx Signature Verification

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Pull pending txs from actpool, stream raw tx bytes to agents |
| **Agent** | Verify ECDSA signature: r and s components within secp256k1 curve order |
| **Contract** | Epoch reward settlement via `depositAndSettle()` |

Agents are stateless. No chain state required. Cost: negligible.

#### L2 — Per-Tx Nonce & Balance Validation

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Prefetch sender account snapshots (~200 bytes/tx), stream with tx |
| **Agent** | L1 checks + verify sender balance > 0, tx nonce ≥ account nonce |
| **Contract** | Same as L1 |

Agents are stateless. Coordinator provides per-tx account snapshots.

#### L3 — Per-Tx Stateless EVM Execution

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Prefetch contract state slots (~10 KB/tx), stream with tx |
| **Agent** | L2 checks + execute tx in embedded EVM sandbox, report gas used and state changes |
| **Contract** | Same as L1 |

Agents are stateless. Coordinator provides per-tx state, but **incomplete state limits accuracy to ~14% on mainnet** — the primary motivation for L4.

#### L4 — Per-Tx Stateful EVM Execution

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Export full EVM state snapshot at cold start; stream incremental state diffs per block (see [State Provisioning](#state-provisioning-l4)) |
| **Agent** | Maintain full EVM state locally (~300 MB–1.2 GB); execute txs with 100% accuracy; verify state hash chain integrity |
| **Contract** | Same as L1 |

L4 is divided into two sub-phases:

- **L4a (shadow mode):** Agent executes each tx against full local state. Results are compared against delegate execution to prove 100% accuracy. Agent results do not yet affect block production.
- **L4b (trusted execution cache):** Agent execution results are cached by the coordinator. When the delegate encounters a cached tx during block production, it skips re-execution and applies the agent's state diff directly (with precondition verification). Cache miss falls through to normal execution.

#### L5 — Full Block Building (ePBS)

| Component | Responsibility |
|-----------|---------------|
| **Coordinator** | Assign primary/standby builder roles; push full pending tx set + delegate-specified tx ordering; receive and evaluate candidate blocks |
| **Agent** | Build entire candidate block: execute txs in order, compute `deltaStateDigest`, `receiptRoot`, `logsBloom`; submit candidate to coordinator |
| **Contract** | Extended reward model: 70% primary builder / 20% participation pool / 10% best standby |

Follows Ethereum's ePBS model ([EIP-7732](https://eips.ethereum.org/EIPS/eip-7732)) adapted for IoTeX's DPoS:

| Ethereum ePBS | IoTeX ioSwarm | Role |
|--------------|---------------|------|
| Proposer | Delegate | Select best block, sign, broadcast |
| Builder | Agent | Order txs, execute, build candidate block |
| Relay | Coordinator | Route candidate blocks between agents and delegate |

#### Summary: Components × Levels

| | **Coordinator** | **Agent** | **On-chain Contract** |
|---|---|---|---|
| **L1** | Stream raw txs | Signature check | Epoch reward settlement |
| **L2** | + Prefetch account snapshots | + Nonce/balance check | Same |
| **L3** | + Prefetch contract state slots | + Stateless EVM execution | Same |
| **L4a** | + Export snapshot, stream diffs | + Full-state EVM (shadow) | Same |
| **L4b** | + Feed agent results to exec cache | + Full-state EVM (active) | Same |
| **L5** | + Assign builder roles, receive candidate blocks | + Build entire block | + Primary/standby reward split |

---

### Component 1: Delegate + Coordinator

The delegate continues to run iotex-core and participate in consensus exactly as before. The coordinator is an embedded sidecar module that manages the agent swarm. This section covers the coordinator's two main responsibilities: communicating with agents and (at L4+) provisioning chain state.

#### Coordinator-Agent Protocol

The coordinator and agents communicate via gRPC with server-side streaming:

| RPC | Direction | Level | Description |
|-----|-----------|-------|-------------|
| `Register` | Agent → Coordinator | All | Agent connects, provides capability level, region, reward wallet. Coordinator returns heartbeat interval. |
| `GetTasks` | Coordinator → Agent (stream) | L1–L4 | Coordinator pushes `TaskBatch` messages: pending txs with pre-fetched state (L1–L3) or block context (L4). |
| `SubmitResults` | Agent → Coordinator | L1–L4 | Agent returns validation results: valid/invalid, gas used, state changes, reject reason. |
| `Heartbeat` | Bidirectional | All | Periodic keep-alive (10s interval). Agents missing 6 consecutive heartbeats are evicted. Coordinator sends payout notifications. |
| `StreamStateDiffs` | Coordinator → Agent (stream) | L4+ | Incremental state changesets per block with chained state hashes. |
| `DownloadSnapshot` | Agent → Coordinator | L4+ | Agent requests state snapshot URL. Coordinator returns a download link to externally hosted snapshot (CDN/IPFS/S3), not the data itself. |
| `SubmitCandidateBlock` | Agent → Coordinator | L5 | Agent submits a fully built candidate block for delegate verification. |

**Authentication**: HMAC-SHA256 — `api_key = "iosw_" + hex(HMAC-SHA256(masterSecret, agentID))`.

#### State Provisioning (L4+)

At L1–L3, agents are stateless — the coordinator prefetches per-tx state and sends it with each task. At L4+, agents maintain full EVM state locally. The coordinator provisions this state via two mechanisms:

**1. Cold Start — State Snapshot**

The coordinator exports a flat KV dump of the 3 EVM-relevant namespaces:

| Namespace | Content | Size Estimate |
|-----------|---------|---------------|
| **Account** | All accounts: nonce, balance, codeHash, storageRoot | ~50–100 MB |
| **Code** | Contract bytecode, keyed by codeHash | ~50–100 MB |
| **Contract** | Contract storage slots (per-contract) | ~200 MB – 1 GB |

Only 3 of 10+ namespaces in IoTeX's state database are needed. Staking, Rewarding, Candidate, and other native protocol state is irrelevant to EVM execution.

```
snapshot = {
    height:          uint64,
    post_state_hash: hash,
    accounts:        map[address → Account],
    code:            map[codeHash → bytecode],
    storage:         map[(address, slot) → value],
}
```

Total snapshot size: **~300 MB – 1.2 GB** (vs Ethereum's ~245 GiB). Downloadable in ~1 minute on a $5/mo VPS.

**2. Incremental Sync — State Diffs per Block**

Every block, the coordinator broadcasts the state changeset to all connected L4+ agents:

```
state_diff = {
    height:          uint64,
    prev_state_hash: hash,   // agent's state BEFORE applying this diff
    post_state_hash: hash,   // expected state AFTER applying this diff
    block_context:   { timestamp, gas_limit, base_fee, prev_block_hash },
    changes:         [(namespace, key, old_value, new_value)],  // ordered
}
```

The changeset already exists in memory during block commit — captured from iotex-core's `workingset.go` `flusher.SerializeQueue()` with zero additional computation.

**3. State Diff Reliability**

If an agent misses a single diff, every subsequent execution produces wrong results. This is the **#1 engineering risk** for L4+.

Every diff carries `prev_state_hash` and `post_state_hash` forming a hash chain — analogous to `prevBlockHash` in blocks. After applying each diff, the agent verifies:

```
apply(diff)
local_hash = hash(local_state)
if local_hash != diff.post_state_hash:
    // STATE DIVERGENCE — request resync
```

Recovery (in priority order):
1. **Catch-up**: Request missing diffs from coordinator's rolling buffer (last ~100 blocks, ~16 min)
2. **Incremental re-snapshot**: Only changed KV pairs since agent's last known good height
3. **Full re-snapshot**: Last resort, re-download ~1 GB from an external endpoint (see below)

**Snapshot offload**: Full snapshots (~1 GB) must **not** be served directly by the coordinator. If 100 L4 agents simultaneously detect state divergence (e.g., after a network blip), requesting snapshots from the coordinator would generate ~100 GB of burst traffic, potentially saturating the delegate node's bandwidth and disrupting consensus communication. Instead, the coordinator periodically exports snapshots to external storage (CDN, IPFS, or object store such as S3) and returns a download URL via `DownloadSnapshot`. This decouples the heaviest data transfer from the block-producing node. The coordinator only serves lightweight incremental diffs (~50–200 KB/block) over the gRPC stream.

#### Key Design Advantage: deltaStateDigest

IoTeX's block header contains `deltaStateDigest` — a hash of the **ordered state change queue**, not a Merkle Trie root. This is a structural advantage over Ethereum:

- Agents do **not** need to maintain a Merkle Patricia Trie
- A flat KV store with ordered write tracking is sufficient to compute the correct digest
- State root computation is cheap — just hash the ordered write queue
- Agent state storage: ~300 MB–1.2 GB (vs Ethereum's ~245 GiB for full MPT)

This makes full block building feasible on commodity hardware.

#### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `epochRewardIOTX` | `0.5` | IOTX reward per epoch |
| `delegateCutPct` | `10` | Delegate's percentage of epoch reward |
| `epochBlocks` | `3` | Blocks per epoch (safety floor: 30s) |
| `minTasksForReward` | `1` | Minimum tasks to qualify for rewards |
| `bonusAccuracyPct` | `99.5` | Accuracy threshold for weight bonus |
| `bonusMultiplier` | `1.2` | Weight multiplier for high-accuracy agents |
| `maxAgents` | `100` | Maximum registered agents per delegate |

---

### Component 2: Agent Swarm

An agent is a single binary (`ioswarm-agent`) that connects to a coordinator, receives work, and earns IOTX. Agents are independent processes — they can run on any machine, in any geography, at any capability level. This section covers agent lifecycle and the economic dynamics of the agent market.

#### Agent Lifecycle

```
1. REGISTER    Agent connects to coordinator, declares level (L1–L5) and reward wallet
                                     │
2. RECEIVE     Coordinator pushes tasks ──► Agent validates/executes/builds
                                     │
3. SUBMIT      Agent returns results  ──► Coordinator records contribution
                                     │
4. EARN        Each epoch, coordinator settles rewards on-chain via RewardSettlement
                                     │
5. CLAIM       Agent calls claim() on RewardSettlement ──► IOTX transferred to wallet
```

Agents that miss 6 consecutive heartbeats (60s) are evicted. Reconnection is automatic — the agent re-registers and resumes work within seconds.

#### Autonomous Agent Economics

ioSwarm agents operate in an open market of 36 delegates, each with its own coordinator, reward pool, agent count, and task volume. An intelligent agent continuously optimizes three dimensions:

##### 1. Delegate Selection (Where to Work)

The effective reward rate per agent depends on the delegate's reward pool and agent count:

```
effective_rate(delegate) = epoch_reward × (1 - delegate_cut) / num_agents
```

An agent that monitors all 36 delegates can identify underserved delegates (few agents, high reward) and migrate. As agents migrate toward higher-paying delegates, the market self-balances toward equilibrium.

**Discovery mechanism**: Agents query the on-chain delegate registry for active coordinators, then probe each coordinator's `/swarm/status` endpoint for current agent count and reward parameters.

**Migration cost**: Switching delegates at L1–L3 is free (stateless). At L4+, the agent must re-download a state snapshot (~1 min for 1 GB), creating natural friction that prevents oscillation.

##### 2. Level Selection (How to Work)

Each level requires different resources and earns different reward weight:

| Level | Compute Cost | Storage | Reward Weight | Typical Hardware |
|-------|-------------|---------|---------------|------------------|
| L1 | ~0 | 0 | 1x | Any device |
| L2 | ~0 | 0 | 1x | Any device |
| L3 | Low CPU | 0 | 2–3x | $5/mo VPS |
| L4 | Medium CPU | ~1 GB | 5–10x | $10/mo VPS |
| L5 | High CPU | ~1 GB | 10–20x | $10–20/mo VPS |

An agent evaluates: "At my hardware cost, which level maximizes `(reward_weight × effective_rate) - operating_cost`?"

A Raspberry Pi agent might optimally run L1–L2 for multiple delegates simultaneously, earning small amounts from each with near-zero cost. A dedicated VPS agent runs L4 for one delegate, earning more per task but with higher fixed costs.

##### 3. Claim Timing (When to Collect)

The `claim()` transaction costs gas (~0.03 IOTX). An agent that claims every epoch wastes gas on small amounts. An intelligent agent:

- Accumulates rewards across multiple epochs
- Monitors gas prices and claims during low-fee periods
- Batches claim timing with other on-chain operations

##### Economic Example

```
Market conditions:
  Delegate A: 0.8 IOTX/epoch, 80 agents, delegate cut 10%
  Delegate B: 0.5 IOTX/epoch, 5 agents, delegate cut 15%
  Delegate C: 1.0 IOTX/epoch, 50 agents, delegate cut 5%

Effective rate per agent per epoch:
  A: 0.8 × 0.9 / 80  = 0.009 IOTX
  B: 0.5 × 0.85 / 5   = 0.085 IOTX    ← 9x better than A
  C: 1.0 × 0.95 / 50  = 0.019 IOTX

A "dumb" agent randomly picks A:          0.009 IOTX/epoch
An intelligent agent picks B:             0.085 IOTX/epoch
                                          ────────────────
                                          9.4x difference
```

This reward differential is what drives agents toward intelligent behavior. The protocol does not mandate any specific strategy — it provides the economic environment, and agents evolve their own optimization approaches.

##### Market Dynamics

As agents optimize, the system reaches a competitive equilibrium:

1. **Reward equalization**: Agents migrate toward high-rate delegates → rates equalize across delegates
2. **Level efficiency**: Agents select the level where marginal revenue exceeds marginal cost → each level finds its natural population
3. **Quality pressure**: Delegates can adjust reward weights to favor higher-level agents → agents invest in capability upgrades

This is a genuine multi-agent market, not a static assignment. Agent "intelligence" is measured by economic performance — return on invested compute — which is observable, quantifiable, and improvable over time.

---

### Component 3: RewardSettlement (On-Chain)

RewardSettlement is a smart contract that handles all reward distribution between coordinators and agents. It replaces the need for any centralized intermediary (such as IoTeX's existing Hermes service) by providing trustless, self-service reward claiming.

#### Reward Flow

```
Epoch timer fires (every ~30s)
  │
  ▼
Coordinator tallies tasks per agent and calculates weights
  │
  ▼
Coordinator deducts delegate cut (default 10%)
  │
  ▼
Coordinator calls depositAndSettle(agents[], weights[]) + sends IOTX
  │
  ▼
RewardSettlement updates cumulativeRewardPerWeight
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

The contract implements the **F1 fee distribution** algorithm from the [Cosmos SDK](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf). It tracks a global `cumulativeRewardPerWeight` that increases with each deposit:

```
On depositAndSettle:
  cumulativeRewardPerWeight += msg.value × 1e18 / totalWeight

On claim:
  pending = agent.weight × (cumulativeRewardPerWeight - agent.rewardDebt) / 1e18
```

This enables **O(1) reward calculation** regardless of agent count — no iteration over all agents needed. Adding agents, updating weights, and claiming all take constant gas.

---

### Evolution Roadmap

This IIP specifies the current ioSwarm architecture. Below we outline how each component evolves as the system matures.

#### Delegate + Coordinator → Thin Proposer

As agents take on more work, the delegate's role thins progressively:

| Phase | Delegate Responsibility | What Moves to Agents |
|-------|------------------------|---------------------|
| **Now** | Full node: consensus + execution + state | — |
| **L1–L3** | Full node + coordinator sidecar | Tx validation |
| **L4** | Consensus + state provider | Stateful EVM execution |
| **L5 (ePBS)** | Consensus + block signing only | Entire block building |
| **Future** | Proposer-only (thin client) | Everything except signing |

At the end state, a delegate becomes a **thin proposer** — similar to Lido's model for liquid staking. Token holders stake into a protocol-managed pool, and the delegate's only job is to sign blocks produced by the agent swarm. The coordinator evolves from an iotex-core sidecar into a lightweight relay connecting proposers to builders, comparable to Ethereum's MEV-Boost relay.

#### Agent Swarm → Block Builders

Agents evolve from stateless tx validators into full block builders:

- **L1–L3 (stateless)**: Commodity $5/mo VPS, no local state, pure computation. Many agents can serve many delegates simultaneously.
- **L4 (stateful)**: Agents maintain synchronized state via state diffs. Can independently verify execution correctness.
- **L5 (block builder)**: Agents construct complete candidate blocks — ordering transactions, computing state transitions, and producing `deltaStateDigest`. The best block wins.

As agents reach L5, the swarm becomes a **competitive block-building market** where agents differentiate on block quality, MEV extraction, and latency.

#### RewardSettlement → Universal Reward Layer

Today, IoTeX uses **Hermes** — a centralized service — to distribute delegate-to-voter rewards off-protocol. RewardSettlement is designed to replace Hermes and handle all reward flows on-chain:

| Reward Flow | Today (Hermes) | Future (RewardSettlement) |
|------------|----------------|--------------------------|
| Protocol → Delegate | Native staking reward | Same |
| Delegate → Voters | Hermes (centralized) | `RewardSettlement.claim()` |
| Delegate → Agent Swarm | ioSwarm (this IIP) | `RewardSettlement.claim()` |
| Protocol → Agent (direct) | Not yet | Future: protocol-native agent rewards |

As the system matures, RewardSettlement becomes the **single source of truth** for all reward distribution in the IoTeX protocol — eliminating the need for any centralized intermediary.

#### MEV and the Case for Decentralized Block Building

A common objection to decentralized block building is that MEV (Maximal Extractable Value) inevitably centralizes builders. Ethereum's experience supports this: 3–5 specialized builders dominate >90% of blocks because MEV extraction rewards the best algorithms, lowest latency, and most capital. Why would IoTeX be different?

**Short answer: IoTeX today has minimal MEV, and ioSwarm is designed to keep it that way in Phase 1.** The delegate specifies transaction ordering via an inclusion list — agents execute in that order without reordering. This eliminates front-running, sandwich attacks, and the MEV extraction that drives centralization in Ethereum's builder market.

**Longer answer: when MEV does emerge, a decentralized swarm has structural advantages over a centralized builder oligopoly.**

In traditional MEV markets, the "best algorithm" is a fixed target — whoever invests the most in low-latency infrastructure and quant teams wins permanently. But as MEV strategies become more complex and adversarial, the search space grows combinatorially. This is precisely the regime where **distributed exploration outperforms centralized optimization**:

| MEV Regime | Centralized Builders (Ethereum) | Decentralized Swarm (ioSwarm) |
|-----------|-------------------------------|------------------------------|
| **Simple arbitrage** (DEX price gaps) | Winner-take-all: fastest bot wins | Same — no advantage from decentralization |
| **Complex MEV** (cross-protocol, multi-block) | Diminishing returns: one team's search is bounded | Thousands of agents exploring different strategies in parallel |
| **Adversarial MEV** (strategy vs. counter-strategy) | Arms race between few players, high barrier | Evolutionary pressure across a large population — more diverse strategies survive |
| **Novel MEV** (new DeFi protocols, new patterns) | Slow to adapt: specialized teams have institutional inertia | Fast adaptation: any agent can try a new approach, market rewards success instantly |

The key insight: in a large, diverse agent population, the **aggregate intelligence** of thousands of independent strategies can exceed the intelligence of any single team. This is the same principle that makes markets more efficient than central planning — and it applies to MEV extraction just as it applies to price discovery.

ioSwarm's Phase 1 (no agent reordering) buys time for the agent ecosystem to mature. When Phase 2 introduces controlled reordering, the competitive landscape will be shaped by thousands of agents with diverse strategies, not a handful of incumbents. The protocol's reward structure (70% primary / 20% participation / 10% standby) further ensures that even non-winning agents earn rewards for participation, preventing the pure winner-take-all dynamic that centralizes Ethereum's builder market.

**This is not a solved problem.** MEV centralization is an active area of research across the industry. ioSwarm's contribution is structural: an open, low-barrier agent network provides more fertile ground for decentralized MEV solutions than a high-barrier, capital-intensive builder market.

## Rationale

### Why Start at the Execution Layer

ioSwarm deliberately avoids consensus-layer changes. From the protocol's perspective, a delegate running ioSwarm is identical to one running vanilla iotex-core — same key signs the block, same block format, same validation rules. This means:

- **No hard fork required** — deploy today, not after months of governance
- **No coordination between delegates** — each adopts independently
- **Zero risk to chain safety** — worst case, disable ioSwarm and the delegate returns to baseline
- **Proven path** — once the execution layer proves value, protocol-layer integration follows naturally

### Why Five Capability Levels

The five-level model serves two purposes:

**Low barrier to entry**: L1 agents only need to verify signatures — any device can participate and earn rewards. Each subsequent level adds capability and earning potential without making previous levels obsolete.

**Progressive trust**: The delegate never needs to trust agents all at once. L1–L3 run in shadow mode (advisory only). L4a proves accuracy via shadow comparison. L4b introduces trusted execution with precondition verification as a safety net. L5 delegates block building but retains re-execution verification. Each step is independently reversible.

### Why F1 Reward Distribution

The [F1 algorithm](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) (used by Cosmos SDK for staking rewards) was chosen because:

- **O(1) per operation**: Adding agents, updating weights, and claiming all take constant gas regardless of agent count
- **Proportional fairness**: Agents earn exactly proportional to their work contribution
- **No off-chain trust**: Rewards are fully on-chain and self-service — agents call `claim()` directly

Alternatives considered:
- **Direct transfer per epoch**: Gas cost scales linearly with agent count (rejected for >50 agents)
- **Off-chain payment**: Requires trusting the delegate (rejected — defeats open agent model)
- **Merkle drop**: Requires periodic root submission and proof generation (over-engineered for this use case)

### Why Autonomous Agent Economics

ioSwarm agents are called "autonomous" not because they run a language model, but because they operate in an economic environment where **intelligent behavior is rewarded** — and where the complexity of that intelligence grows with the system.

A fair objection: the delegate selection formula (`epoch_reward × (1 - delegate_cut) / num_agents`) is basic arithmetic, not autonomy. At L1–L3, this is true — an agent optimizing across 36 delegates is closer to a routing script than an autonomous system.

But this is the **starting point**, not the ceiling. Agent intelligence deepens as the system evolves:

| Phase | Decision Complexity | Intelligence Required |
|-------|--------------------|-----------------------|
| **L1–L3 (today)** | Which delegate? Which level? When to claim? | Rule-based heuristics — a static script can do this |
| **L4 (stateful)** | Above + state sync strategy, catch-up vs re-snapshot tradeoffs, multi-delegate state management | Adaptive optimization — agents must respond to changing network conditions |
| **L5 (block building)** | Above + transaction ordering, gas optimization, block composition strategy | Competitive strategy — agents compete directly on block quality |
| **L5 + MEV** | Above + MEV extraction, cross-protocol arbitrage, adversarial strategy | Emergent intelligence — the search space is combinatorial; no closed-form solution exists |

At L5 with MEV, the optimization problem becomes genuinely hard: the agent must decide which transactions to include, in what order, whether to insert its own transactions, how to balance MEV extraction against the risk of block rejection, and how to adapt its strategy as competitors counter it. This is a **multi-agent adversarial optimization problem** — the kind of problem where reinforcement learning, game-theoretic reasoning, and learned policies demonstrably outperform hand-coded heuristics.

The protocol does not prescribe any specific approach. It provides the economic environment:
1. **Transparent information**: reward rates, agent counts, and task volumes are queryable on-chain and via coordinator APIs
2. **Low switching cost**: agents can migrate between delegates without penalty (at L1–L3, instantly; at L4+, with a brief re-sync)
3. **Fair reward distribution**: F1 algorithm ensures proportional payouts with no information asymmetry

The agents' role is to exploit this information to maximize their return. A "dumb" agent uses static rules. A "smart" agent learns and adapts. The protocol doesn't care which — it measures intelligence by economic performance, and the market rewards the better agent. Over time, the competitive pressure drives the agent ecosystem toward increasingly sophisticated strategies — from scripts to learned policies to genuine autonomous economic reasoning.

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

ioSwarm (L1–L3) has been tested end-to-end on IoTeX mainnet with the RewardSettlement contract deployed at `0x96F475F87911615dD710f9cB425Af8ed0e167C89`.

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
| False positive (says invalid tx is valid) | Invalid tx reaches block builder | Delegate re-executes all txs at L1–L4a |
| False negative (says valid tx is invalid) | Valid tx delayed | Cross-validation with multiple agents |
| Denial of service (no response) | Task timeout | 2s timeout + automatic failover to other agents |
| Transaction front-running | MEV extraction | Mempool is already public via P2P; agents see same data |
| Fabricated state diffs (L4b) | Incorrect state applied | Precondition verification before applying cached results |
| Invalid candidate block (L5) | Block production delay | Delegate re-executes to verify; standby builder takes over |
| Sybil attack (many fake identities) | Occupy `maxAgents` slots, crowd out honest agents | API key authentication + delegate-controlled admission (see below) |

### Sybil Resistance and Agent Admission

ioSwarm is **permissionless at the protocol level, but curated at the coordinator level**. Anyone can run an agent — the software is open-source, requires no on-chain registration, and imposes no minimum stake at the protocol layer. However, each delegate exercises **freedom of association**: it independently decides which agents to admit to its swarm.

This creates a **free market for execution services**:

- **Open participation**: Any operator can launch an agent and offer execution services to any delegate. No protocol-level gatekeeping.
- **Delegate curation**: Each delegate's coordinator controls its own admission policy — open registration, API key auth (HMAC-SHA256), invite-only, staking requirement, or any combination. The protocol does not mandate a single approach.
- **Rate limiting**: The coordinator enforces per-agent rate limits (10 req/s, burst 20) and evicts agents that exceed them.
- **`maxAgents` as defense**: The `maxAgents` cap (default 100) bounds the coordinator's resource exposure.

This is analogous to how Ethereum validators choose which MEV-Boost relays to trust, or how mining pools choose which miners to admit. The trust relationship is between the delegate and its agents, not between the protocol and agents. Each delegate bears the cost of its own swarm and has full economic incentive to prevent abuse.

For delegates that want additional Sybil defenses beyond curation:
- **Minimum stake**: Require agents to deposit a small IOTX bond (refundable on graceful exit, slashed on misbehavior)
- **Proof of work**: Require a computational puzzle at registration to raise Sybil cost
- **Reputation scoring**: Weight rewards by historical accuracy, naturally penalizing new/untrusted agents

### Trust Model

The trust model evolves with each capability level:

| Level | Trust Model | Safety Guarantee |
|-------|------------|-----------------|
| L1–L3 | **Zero-trust** — agent results are advisory only | Delegate executes all txs independently |
| L4a | **Shadow verification** — agent results compared, not used | Delegate executes all txs independently |
| L4b | **Trust-but-verify** — cached results used with precondition check | Mismatch → fall through to delegate execution |
| L5 | **Verified delegation** — agent builds block, delegate re-executes | Mismatch → reject, penalize agent, use standby |
| Future | **Optimistic** — delegate trusts agent block, fraud detected post-hoc | Slashing as economic deterrent |

At every level, disabling ioSwarm returns the delegate to baseline operation with zero impact on block production.

### Shadow Mode Economics

A valid concern: at L1–L4a, agents perform redundant computation — the delegate re-executes all transactions independently regardless of agent results. Why pay agents for work the delegate discards?

**Shadow mode is not wasted computation. It is a paid proving ground.**

The cost of shadow mode is low and deliberate:

| | Shadow Mode (L1–L4a) | Active Mode (L4b–L5) |
|---|---|---|
| **Agent cost** | $5–10/mo VPS | Same |
| **Delegate cost** | Epoch rewards (~0.5 IOTX/30s) | Same, but delegate CPU drops |
| **What delegate gains** | Accuracy data: does this agent match my execution 100%? | Actual CPU offload, block building |
| **What agent gains** | Reputation + rewards | Higher rewards |

The delegate pays a small amount to answer a critical question: **can I trust this agent?** Without shadow mode, the delegate would have to trust agents from day one (unsafe) or never trust them at all (no path to L4b/L5). Shadow mode is the bridge.

The reward during shadow mode is funded by the delegate's own epoch reward — not by protocol inflation. Each delegate chooses how much to allocate. A delegate that sees no value can set `epochRewardIOTX: 0` and disable ioSwarm entirely. This is not a protocol-level subsidy; it is a delegate-level investment in building a verified agent workforce.

The transition out of shadow mode is the payoff:
- **L4b**: Agent results feed into the delegate's execution cache → delegate skips re-execution for cache hits → measurable CPU savings
- **L5**: Agent builds the entire block → delegate only re-executes to verify → massive CPU reduction

Shadow mode is a cost. But it is a **one-time proving cost** per agent, not a permanent overhead. Once an agent achieves 100% accuracy over a sufficient shadow period, it graduates to active mode where its work directly reduces the delegate's load.

### Known Limitations

1. **F1 departed agent issue**: When an agent departs, its on-chain weight is not zeroed automatically. The coordinator should zero departed agents' weights within 1–2 epochs.

2. **Single coordinator**: The coordinator is a single process within the delegate. If it crashes, agents cannot receive tasks until it restarts. The delegate continues producing blocks normally via iotex-core's standard execution path.

3. **State diff reliability (L4+)**: If an agent misses a state diff, all subsequent EVM execution produces wrong results. Mitigated by chained state hash verification with automatic re-snapshot on divergence. The coordinator maintains a rolling window of recent diffs (~100 blocks) for agent catch-up. Full snapshots are served via external storage (CDN/IPFS/S3), not by the coordinator directly, to avoid bandwidth storms on the delegate node.

## References

### Ethereum Consensus-Execution Separation
- [EIP-3675: Upgrade consensus to Proof-of-Stake](https://eips.ethereum.org/EIPS/eip-3675) — The Merge: formal transition from PoW to Beacon Chain consensus
- [Engine API](https://github.com/ethereum/execution-apis) — authenticated JSON-RPC interface connecting consensus clients to execution clients
- [EIP-4399: Supplant DIFFICULTY opcode with PREVRANDAO](https://eips.ethereum.org/EIPS/eip-4399) — execution-layer adaptation for PoS randomness
- [Ethereum Merge Overview](https://ethereum.org/roadmap/merge/)

### Proposer-Builder Separation
- [EIP-7732: Enshrined Proposer-Builder Separation](https://eips.ethereum.org/EIPS/eip-7732)
- [EIP-7898: Uncouple execution payload from beacon block](https://eips.ethereum.org/EIPS/eip-7898)
- [EIP-7805: FOCIL (Fork-Choice Enforced Inclusion Lists)](https://eips.ethereum.org/EIPS/eip-7805)
- [Ethereum PBS Roadmap](https://ethereum.org/roadmap/pbs)

### Reward Distribution
- [F1 Fee Distribution (Ojha & Goes, Tokenomics 2019)](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) — used by Cosmos SDK for staking reward distribution

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
