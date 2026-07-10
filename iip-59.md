```
IIP: 59
Title: Protocol-Native Voter Reward Distribution
Author: Raullen Chai (@raullen), Chen Chen (@envestcc)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-20
Requires: IIP-58
```

## Simple Summary

Replace the centralized Hermes reward distribution service with protocol-native, automatic voter reward distribution. Delegates keep the existing on-chain commission source (the `DelegateProfile` contract that Hermes reads today), and the protocol distributes the remaining reward (both block reward and epoch reward) directly to voters proportional to their weighted votes. Compound (reinvest into an existing native bucket) is preserved by reusing the existing `AutoDeposit` contract. Migration is per-delegate opt-in: legacy path stays live until a delegate explicitly switches.

## Abstract

IoTeX currently relies on **Hermes** — a centralized, off-chain service — to distribute delegate staking rewards to voters. Hermes claims a delegate's entire unclaimed balance (which includes both **block reward** and **epoch reward**) and splits it among voters off-chain, using two production contracts as its source of truth:

1. **`DelegateProfile`** (mainnet `0xfa7f50866ac45d84adf54bc767c885f92750e258`) — per-delegate voter split percentages for each reward stream, updated by delegates or by an authorized owner.
2. **`AutoDeposit`** (mainnet `io108ckwzlzpkhva7cnfceajlu7wu6ql5kq95uat9`) — per-voter compound preference (native bucket ID to reinvest into).

This proposal folds Hermes's distribution logic into the block executor while preserving both contracts as the operator-facing sources of truth:

- **Commission rates** — read from `DelegateProfile` at the previous epoch's `PutPollResult` and frozen into the poll snapshot. Two independent basis-point rates (block-stream and epoch-stream) replace the single `CommissionRate` field, matching the two portions Hermes uses today.
- **Block reward** — accumulates into a per-delegate pending pool during the epoch and is distributed together with the epoch reward at the epoch's last block, using the block-stream commission rate.
- **Epoch reward** — split with voters directly inside `GrantEpochReward()` using the epoch-stream commission rate.
- **Compound** — for each voter share, the protocol consults `AutoDeposit`: if the voter is registered and their target native bucket satisfies `Owner == voter && AutoStake && status == active`, the share is reinvested via `AddDeposit`; otherwise it is credited to the voter's unclaimed balance for pull-claim via `ClaimFromRewardingFund`.
- **Opt-in migration** — a new per-delegate on-chain flag (`VoterRewardOnchainOptIn`) gates all of the above. Delegates that do not opt in retain the exact legacy behavior (full stream credited to `RewardAddress`; off-chain Hermes continues to run for them). Hermes is deprecated only after all delegates opt in.

Because IIP-59 reads the same two contracts Hermes reads and applies the same math, voter net income matches (and slightly exceeds, due to zero service fees) the Hermes era at the same rate. Per-voter events are emitted once per delegate as a batched `DelegateDistributed` log to keep receipt size bounded at the epoch's last block.

## Motivation

### The Hermes Problem

Hermes is a centralized Go service (last updated 2022) that:

1. Claims epoch rewards on behalf of delegates
2. Queries an external GraphQL analytics endpoint for voter-to-delegate mappings
3. Calculates each voter's share off-chain
4. Sends batch transfers via a MultiSend smart contract

This architecture has critical problems:

| Problem | Impact |
|---------|--------|
| **Single point of failure** | Service downtime = voters don't get paid |
| **Centralized key custody** | Distributor private key is a security/trust risk |
| **External data dependency** | GraphQL analytics endpoint can go down or return stale data |
| **No verifiability** | Voters must trust Hermes to compute shares correctly |
| **Gas inefficiency** | Iterates over all voters every epoch via EVM MultiSend |
| **Stale codebase** | Go 1.11, no maintenance since 2022, hardcoded address patches |
| **Service fees** | BASE_CHARGE + per-voter fees extracted from rewards |

### Why Protocol-Native

All data needed for voter reward distribution already exists in the protocol's on-chain state:

- **Voter-to-delegate mappings**: `VoteBucket.CandidateAddress` in the staking protocol
- **Vote weights**: `CalculateVoteWeight()` using staked amount, duration, and auto-stake flag
- **Epoch rewards**: Calculated by `GrantEpochReward()` in the rewarding protocol
- **Reward accounts**: Per-address unclaimed balance in the rewarding fund

The only missing piece is the distribution logic — a straightforward extension of the existing `GrantEpochReward()` function.

### Why Not a Smart Contract

A contract-based approach (Merkle drop, F1 distribution) was considered but rejected:

- **Merkle drop**: Requires an off-chain bot to compute and post roots — still a centralized dependency, just lighter
- **F1 on-chain**: Gas cost is O(N) per deposit where N = number of voters. Top delegates have 2,000+ voters, requiring 80M+ gas per epoch — exceeds block gas limit
- **Precompile for staking reads**: Requires protocol change anyway — same effort as native distribution

Protocol-native distribution costs zero gas (runs in Go inside the block executor), has zero external dependencies, and is as trustless as block rewards.

## Specification

### 1. Candidate Registration Extension

Add three fields to the `Candidate` struct in the staking protocol. Two carry the commission rates read from `DelegateProfile` (see §3.5); one is the opt-in gate (see §3.7):

```go
type Candidate struct {
    Owner                    address.Address
    Operator                 address.Address
    Reward                   address.Address
    Identifier               address.Address
    Name                     string
    Votes                    *big.Int
    SelfStakeBucketIdx       uint64
    SelfStake                *big.Int
    BLSPubKey                []byte
    VoterRewardOnchainOptIn  bool    // NEW: gate — false = legacy Hermes-era behavior
    BlockCommissionRate      uint64  // NEW: basis points (0–10000), block-stream commission
    EpochCommissionRate      uint64  // NEW: basis points (0–10000), epoch-stream commission
}
```

**Field semantics:**

- `VoterRewardOnchainOptIn = false` (default): Legacy behavior — full block reward and full epoch reward go to the delegate's `Reward` account (`RewardAddress`). Off-chain Hermes continues to distribute for this delegate. `BlockCommissionRate` / `EpochCommissionRate` are ignored.
- `VoterRewardOnchainOptIn = true`: Protocol auto-distributes at epoch end (block reward is folded — see §3.1). The delegate receives `BlockCommissionRate / 10000` of accumulated block reward and `EpochCommissionRate / 10000` of epoch reward; each stream's remainder is distributed to voters proportional to weighted votes.
- Maximum commission value: `10000` (100% — delegate keeps everything, voters get nothing).
- Both rate fields are **populated by the poll layer at `PutPollResult`** from the `DelegateProfile` contract (§3.5). They are not settable by any protocol action. `VoterRewardOnchainOptIn` is likewise snapshotted at `PutPollResult` from the delegate's live opt-in state (§3.7).

Because the rates are contract-sourced, no `SetCommissionRate` action is added; the existing Hermes-era operator UX for setting rates in `DelegateProfile` is preserved.

### 2. New Action: `SetVoterRewardOptIn`

A single new protocol action lets a delegate opt into (or out of) protocol-native distribution:

```go
type SetVoterRewardOptIn struct {
    OptIn bool
}
```

**Constraints:**
- Only the candidate's `Owner` address can call this action.
- Takes effect at the **next epoch boundary** — the flag is copied into the poll snapshot at the next `PutPollResult`; the epoch that follows uses the new value (see §3.7).
- Bidirectional: a delegate can toggle back to the legacy path if operational issues arise. Opt-out drains any accumulated block-reward pool at the next epoch end using the flag value that was live for the block that was produced (see §3.1 / §3.3).
- Idempotent: calling with the current value is a no-op receipt (does not fail).
- Gas cost: ~10,000 (single-byte state write plus event emission).

Rate changes continue to be operated through `DelegateProfile` (unchanged operator UX). This action is only about switching distribution mode.

### 3. Modified Reward Distribution

Both `GrantBlockReward()` and `GrantEpochReward()` are modified so that a delegate with `VoterRewardOnchainOptIn == true` splits **the entire delegate-side reward flow** with voters — matching what Hermes distributed prior to this proposal (delegate's full unclaimed balance).

Because per-voter distribution is O(voters) work — expensive at 2,000+ voters — the protocol runs it only once per epoch, at the epoch's last block. Block rewards accumulate into a per-delegate pending pool during the epoch and are folded into the single epoch-end distribution call. This keeps per-block cost at O(1) while preserving voter economics.

The eligibility predicate `blockRewardEligibleForVoterSplit(fCtx, cand)` guards both `GrantBlockReward` routing and the epoch-end drain path (see §3.7). It returns true iff the fork is active, the candidate exists in the poll snapshot, `cand.VoterRewardOnchainOptIn` is true, and at least one of `BlockCommissionRate` / `EpochCommissionRate` is set. Delegates that fail the predicate follow the legacy path in full.

#### 3.1 Block Reward Accumulation

`GrantBlockReward()` (currently: credit the block reward directly to the block producer's reward account) is modified:

```go
func (p *Protocol) GrantBlockReward(ctx context.Context, sm protocol.StateManager) (*action.Log, error) {
    // ... existing: resolve producer → candidate, calculate blockReward, effectiveTip ...

    if p.blockRewardEligibleForVoterSplit(featureCtx, delegate) {
        // Priority tip stays with the producer directly — tips are inclusion
        // incentive for the block builder, not delegate compensation.
        if effectiveTip.Sign() > 0 {
            if err := p.creditRewardAccount(sm, delegate.Reward, effectiveTip); err != nil {
                return nil, err
            }
        }
        // Accumulate the base block reward to the per-delegate pending pool;
        // do NOT credit the delegate's reward account yet. The pool drains at
        // epoch end.
        return p.addPendingBlockReward(sm, delegate.Identifier, blockReward)
    }

    // Legacy: credit total block reward (base + tip) to delegate's reward
    // account immediately. Off-chain Hermes will pick it up as before.
    return p.creditRewardAccount(sm, delegate.Reward, totalReward)
}
```

**Pending pool storage.** A new per-delegate state key:

- Namespace: staking protocol
- Key: `pendingBlockReward || delegateIdentifier` (21 bytes; `delegateIdentifier` is the 20-byte candidate identifier address)
- Value: proto blob carrying `{amount *big.Int, rewardAddr address.Address, blockCommissionRate uint64}` captured at first credit; overwritten in place; deleted when drained. Freezing `rewardAddr` and `blockCommissionRate` on the pool entry lets the epoch-end drain do the split correctly even if the delegate exited the top-N mid-epoch and no longer has a fresh poll snapshot (see §3.3).

**Properties.**
- Each block does at most one state read + one state write to the pending pool. No per-voter work at block time.
- A delegate that produces blocks but exits the top-N before epoch end still has an entry in the pending pool. It is drained at epoch end (see §3.3).
- Rate changes mid-epoch have no effect on already-accumulated block rewards: the block-stream rate applied at drain time is the one that was frozen into the pool entry on the first credit (or refreshed from the current poll snapshot when the delegate is still in top-N — see §3.3). Both variants read the `PutPollResult`-anchored value, never a live contract state.
- An opt-in state change mid-epoch is likewise frozen: `blockRewardEligibleForVoterSplit` reads the opt-in flag from the poll snapshot (§3.7), which is only updated at `PutPollResult`.

#### 3.2 Epoch Reward Split

`GrantEpochReward()` is modified so each stream is split with voters using its own commission rate when the delegate is opted in. Streams are split independently to preserve the two-rate semantics inherited from the `DelegateProfile` contract (see §3.5), then commissions and voter shares are aggregated before crediting:

```go
// per-delegate loop inside GrantEpochReward
for _, delegate := range topDelegates {
    epochReward := calculateDelegateReward(delegate, totalVotes)

    // Fold in this delegate's accumulated block rewards.
    pending := p.drainPendingBlockReward(sm, delegate.Identifier)

    if p.blockRewardEligibleForVoterSplit(featureCtx, delegate) {
        // Split each stream independently, then aggregate.
        //   block-stream commission uses BlockCommissionRate
        //   epoch-stream commission uses EpochCommissionRate
        blockCommission := split(pending, delegate.BlockCommissionRate)
        epochCommission := split(epochReward, delegate.EpochCommissionRate)
        totalCommission := new(big.Int).Add(blockCommission, epochCommission)
        voterPool := new(big.Int).Sub(
            new(big.Int).Add(pending, epochReward),
            totalCommission,
        )

        rewardLogs, err := p.distributeToVoters(ctx, sm, delegate, totalCommission, voterPool)
        if err != nil { return nil, err }
        logs = append(logs, rewardLogs...)
    } else {
        // Legacy behavior: full combined reward to delegate.
        p.creditRewardAccount(sm, delegate.Reward, new(big.Int).Add(pending, epochReward))
    }
}
```

`distributeToVoters` reads the voter list from the frozen snapshot (§3.4), routes each voter's share to either the compound path (§3.6) or the unclaimed balance, aggregates per-voter allocations, and emits a **single batched log per delegate** (see next paragraph). Delegate commission is credited to `delegate.Reward` in one write.

**Batched receipt log.** Emitting one log per voter is prohibitively expensive at the epoch's last block — under load (top ~100 delegates × 2,000+ voters each) receipt trie growth and `eth_getLogs` on the epoch block become bottlenecks. Instead, one `DelegateDistributed` log is emitted per delegate:

```
event DelegateDistributed(
    uint64  indexed epoch,
    address indexed delegate,       // candidate identifier
    address         rewardAddr,     // where commission was credited
    uint256         totalCommission,
    uint256         totalVoterPool,
    bytes32         snapshotHash,   // hash of the frozen voter list (§3.4)
    address[]       voters,         // canonical sorted order, matches snapshot
    uint256[]       amounts,        // parallel array
    uint8[]         routings        // 0 = unclaimed balance, 1 = AutoDeposit compound
)
```

- `voters[i]`, `amounts[i]`, and `routings[i]` line up positionally.
- `snapshotHash` binds the log to the exact snapshot that drove distribution — off-chain reconstructors can verify without replaying state.
- A single delegate's log carries all their voters; total logs at the epoch's last block is bounded by `|topDelegates| + |orphanDrain|` (roughly ≤200), regardless of voter count.

**Key properties:**
- Runs inside the protocol (Go code), not the EVM — **zero gas cost** for the split itself. Compound routing incurs one bounded EVM call per **registered** voter (see §3.6); non-registered voters are free.
- Uses the existing `creditRewardAccount()` to credit each voter's unclaimed balance (non-compound routing).
- Vote weight calculation uses the same `CalculateVoteWeight()` as consensus — reads via the frozen snapshot (§3.4).
- Voter iteration is in canonical (sorted-by-address) order.
- Rounding dust (< 1 Rau per voter) goes to the delegate, added to `totalCommission` after all voters are credited.
- Only active buckets participate (already enforced at snapshot time — §3.4).

#### 3.3 Draining Pending Pools for Non-Top-N Delegates

A delegate that produced blocks earlier in the epoch but exits the top-N (e.g. lost votes late in the epoch), or that flipped `VoterRewardOnchainOptIn` back to `false` mid-epoch, still has a non-empty pending pool at epoch end. Leaving those funds stranded would silently confiscate block reward.

At the end of `GrantEpochReward()`, after the top-N loop runs, the protocol iterates the pending-pool namespace and drains any remaining entries. Each pool entry carries its own frozen `rewardAddr` and `blockCommissionRate` (captured at first credit), so an orphan drain does not need a fresh poll snapshot for the delegate:

```go
for _, entry := range p.allPendingBlockRewards(sm) {
    // Prefer the current poll snapshot if the delegate is still around —
    // this picks up the fresher opt-in and rate values.
    delegate, ok := topDelegateByIdentifier[entry.Identifier]
    if ok {
        // Already drained inside the top-N loop above; safety net.
        continue
    }
    // Reconstruct a synthetic *state.Candidate from the pool entry itself.
    syn := &state.Candidate{
        Identity:            entry.Identifier.String(),
        RewardAddress:       entry.RewardAddr.String(),
        BlockCommissionRate: entry.BlockCommissionRate,
    }
    if syn.BlockCommissionRate > 0 { // implies opt-in was true when credited
        p.distributeToVoters(ctx, sm, syn, split(entry.Amount, syn.BlockCommissionRate),
            new(big.Int).Sub(entry.Amount, split(entry.Amount, syn.BlockCommissionRate)))
    } else {
        // Delegate credited pre-fork or opted out before any snapshot; refund
        // the full pending amount to the frozen reward address.
        p.creditRewardAccount(sm, entry.RewardAddr, entry.Amount)
    }
    p.clearPendingBlockReward(sm, entry.Identifier)
}
```

The pending-pool namespace is bounded by the total registered candidate count (~100), so this is a bounded scan, not O(all keys). If `distributeToVoters` cannot find a voter snapshot for the delegate (delegate never had a snapshot), the full amount degrades to the frozen `rewardAddr` — voters are never stranded.

#### 3.4 Rate, Opt-In, and Voter Weight Snapshotting

To guarantee deterministic distribution (and prevent last-block stake manipulation), three per-candidate values are frozen at the **previous** epoch's `PutPollResult` (mid-epoch). Concretely, at `PutPollResult` time the protocol:

1. Calls `DelegateProfile.getEncodedProfile(delegate)` via a read-only EVM simulation for each poll candidate; parses the `blockRewardPortion` and `epochRewardPortion` fields (voter-take basis points), **inverts** them (`commission = 10000 - portion`), and writes the result into `BlockCommissionRate` / `EpochCommissionRate` on the poll-snapshotted candidate. Missing profile → both rates set to `0` (see §3.5).
2. Copies each candidate's current `VoterRewardOnchainOptIn` value into the poll-snapshotted candidate list.
3. Writes a per-candidate blob of `(voter, weightedVotes)` pairs, sorted by voter address, keyed by candidate identifier.

`distributeToVoters()` reads the frozen voter list (not the live staking view) at epoch end. `blockRewardEligibleForVoterSplit` reads the frozen opt-in flag and rates from the same snapshot. Any stake activity, rate change, or opt-in toggle between `PutPollResult` and the epoch's last block does not shift this epoch's distribution — it takes effect at the following `PutPollResult`. This gives voters a roughly 1.5-epoch reaction window when a delegate raises its commission rate or opts in / out: the change takes effect at the next `PutPollResult` (mid-epoch) and applies to rewards in the epoch after that.

#### 3.5 Commission Rate Source: `DelegateProfile` Contract

Commission rates are read from the existing `DelegateProfile` contract, which is the same source Hermes reads today. This eliminates the operator UX churn a new native action would introduce: delegates continue to manage rates through the same signer path and (in the future) the same iotex-hub UI they already use.

**Contract layout used.**

- Mainnet address: `0xfa7f50866ac45d84adf54bc767c885f92750e258`
- Testnet address: `0xd19ffB48a5C18B77c541D32c1B1ac2440c287774`
- Interface used: `getEncodedProfile(address delegate) view returns (bytes)`
- Fields consumed (names as they exist on-chain today):
  - `blockRewardPortion` — voter-take basis points for the block-reward stream
  - `epochRewardPortion` — voter-take basis points for the epoch-reward stream
  - `foundationRewardPortion` — **ignored** by IIP-59 (foundation bonus stream is out of scope; already at zero on mainnet)

**Semantics inversion.** The contract and Hermes both treat the stored portion as **voter-take** (the share going to voters). IIP-59's on-chain fields (§1) store **commission** (the share the delegate keeps). The poll bridge inverts once at snapshot time:

```
BlockCommissionRate = 10000 - blockRewardPortion   // clamped to [0, 10000]
EpochCommissionRate = 10000 - epochRewardPortion
```

**Missing-profile default.** If `getEncodedProfile` returns empty bytes or the delegate has never called `updateProfile`, both rates are set to `0` on the poll snapshot. Combined with `VoterRewardOnchainOptIn`'s independent gate (§3.7), this means: an opted-in delegate that forgets to configure their `DelegateProfile` will grant **100% commission** (voters get nothing). This is intentional — protecting voters from a mis-configured delegate is the delegate's responsibility, and the opt-in transaction is expected to come *after* the profile is set. Node operators SHOULD surface a warning in delegate tooling when an opt-in tx is submitted against a delegate with a zero-portion (or missing) profile.

**Bridge implementation.** At `PutPollResult`, one `evm.SimulateExecution` call per poll candidate is issued against the frozen block state. With ~100 delegates per epoch, this adds ~100 read-only EVM calls per `PutPollResult` (~10–50 ms total). The pattern mirrors the existing consortium poll bridge (`action/protocol/poll/consortium.go`), which already calls into the EVM from consensus. Results are cached inside the poll snapshot and are never re-read from the contract during an epoch.

**Contract governance prerequisite.** `DelegateProfile.owner()` is currently a single externally-owned account (`0x68c12a8c5d5f0a1fd13319ba4840301b0c93bd4f`). That account can rewrite every delegate's portion via `updateProfileForDelegate`. Before IIP-59 activation on mainnet, one of the following governance actions MUST land:

1. Transfer ownership to a multisig with a documented signer set (recommended); OR
2. Burn ownership (contract becomes append-only via delegate-owned `updateProfile`); OR
3. Add on-chain caps and time-delay on `updateProfile*` writes and a challenge window.

Absent one of these, a single EOA compromise can silently redirect voter reward across the entire delegate set the moment the fork activates.

#### 3.6 Compound via `AutoDeposit` Contract

Hermes today reads the existing `AutoDeposit` contract (mainnet `io108ckwzlzpkhva7cnfceajlu7wu6ql5kq95uat9`) to decide whether a voter's share is reinvested into a native bucket or transferred to their wallet. IIP-59 preserves this UX by consulting the same contract at distribution time.

**Contract interface used.**

- `bucket(address voter) view returns (int256 bucketId)` — voter's registered target native bucket (0 = not registered)
- No writes issued to the contract by the protocol.

**Routing algorithm.** For each voter share `S` in `distributeToVoters`, the protocol determines routing under the following pre-conditions (all four must hold for `AddDeposit`):

1. `bucketId := AutoDeposit.bucket(voter)` returns a non-zero value.
2. `bucket := staking.getBucket(bucketId)` succeeds and `bucket.Owner == voter`.
3. `bucket.AutoStake == true`.
4. `bucket.status == active` (not withdrawn / not in unbonding).

If all four hold, the protocol calls `Staking().AddDeposit(bucketId, S)` inside the block executor (native path, not via EVM). Otherwise, `S` is credited to `voter.unclaimedBalance` for pull-claim via the existing `ClaimFromRewardingFund` action.

**Cost.** The `AutoDeposit.bucket(voter)` call is a single `evm.SimulateExecution` per voter share, executed only inside the epoch's last block. Reads for un-registered voters are cheap (mapping miss returns `0` immediately). At mainnet scale (~40k voter credits/epoch, ~5% compound registration rate historically) this is ~2k EVM reads bounded to a single block — ~10-40 ms of extra execution at the epoch's last block. `AddDeposit` itself uses the same code path as user-initiated deposits, so gas accounting and event semantics are unchanged.

**LSD parity with Hermes.** LSD (contract-staking v1/v2/v3) holders' buckets are owned by the staking contract, not by the token holder — so `bucket.Owner == voter` fails and their share is routed to `unclaimedBalance`. Same behavior as Hermes today (iotex-hub's compound registration UI already filters `isNativeBucket && autoStake`).

**Snapshotting.** Compound preferences are read live at drain time, **not** frozen at `PutPollResult`. A voter can register in the compound contract mid-epoch and have that preference take effect at the immediately following epoch end. This is a UX choice: compound registration is a low-frequency operation and delaying it by up to 1.5 epochs would surprise users who register right after the epoch boundary. The trade-off is that a coordinated flip of compound state right before the epoch's last block can shift routing, but not amounts — an economically neutral change.

#### 3.7 Per-Delegate Opt-In and Legacy Coexistence

`VoterRewardOnchainOptIn` gates all IIP-59 behavior at the per-delegate level. It is set by `SetVoterRewardOptIn` (§2) and snapshotted at `PutPollResult` (§3.4).

**Eligibility predicate.**

```go
func (p *Protocol) blockRewardEligibleForVoterSplit(fCtx FeatureCtx, cand *state.Candidate) bool {
    return !fCtx.NoVoterRewardDistribution &&
        cand != nil &&
        cand.VoterRewardOnchainOptIn &&
        (cand.BlockCommissionRate > 0 || cand.EpochCommissionRate > 0)
}
```

- Pre-fork (`NoVoterRewardDistribution == true`): predicate is always false — legacy behavior for every delegate. Opt-in transactions before the fork are rejected at the handler.
- Post-fork, opt-out: predicate is false — full block+epoch reward flows to `RewardAddress`; off-chain Hermes continues to distribute for that delegate. No block-reward pool entry is written.
- Post-fork, opt-in, zero rates: predicate is false — same as opt-out but the delegate has explicitly signaled intent. Useful as a two-step migration (opt-in first, then rate takes effect at the following epoch when the profile update snapshots).
- Post-fork, opt-in, non-zero rate on at least one stream: predicate is true — pool + snapshot + batched log path.

**Coexistence with Hermes.** During the transition window, both systems are live in parallel — opt-out delegates are handled by off-chain Hermes exactly as today; opt-in delegates are handled by the protocol. To prevent double-payment, the Hermes service MUST filter delegates whose on-chain `VoterRewardOnchainOptIn` is true and skip them in its `distributeRewards` batch. The opt-in state is queryable via existing candidate RPC (§7.10), so no new endpoint is required. A grace period between fork activation and the first opt-in is expected (delegates verify tooling before switching).

**Reversibility.** `SetVoterRewardOptIn(false)` is allowed. Effect is delayed by one epoch via the poll snapshot. Any block-reward pool entry accumulated while opt-in was still true is drained under the old (opt-in) semantics at the following epoch end — voters are not shortchanged by a mid-flight reversal. Future block rewards go to the legacy path from the epoch after the flip.

**Deprecation exit ramp.** A future hard fork MAY promote the flag to always-true (drop the `cand.VoterRewardOnchainOptIn` clause from the predicate), forcing every delegate onto the protocol path and enabling Hermes to be shut down. That fork is out of scope for IIP-59; this proposal only introduces the mechanism.

### 4. Voter Claim Flow

Voters claim accumulated rewards using the **existing** `ClaimFromRewardingFund` action. No change needed — their reward account balance now includes auto-distributed voter rewards in addition to any other rewards. Voters who registered a compound preference via the `AutoDeposit` contract have their share **automatically reinvested** at each epoch's last block (§3.6) and skip the claim step entirely.

```
                    ┌───────────────────────────────────────┐
                    │        Rewarding Protocol             │
                    │                                       │
  Epoch end ───────►│  GrantEpochReward()                   │
                    │    ├─ split epoch stream by rateₑ     │
                    │    ├─ drain block-reward pool         │
                    │    ├─ split pooled amount by rateᵦ    │
                    │    ├─ aggregate delegate commission ──►  delegate.rewardAccount
                    │    │                                  │
                    │    ├─ per-voter route via AutoDeposit │
                    │    │   ├─ registered + active bucket ──►  Staking.AddDeposit(bucketId, sᵢ)
                    │    │   └─ otherwise ───────────────────►  voterᵢ.unclaimedBalance
                    │    │                                  │
                    │    └─ emit DelegateDistributed log    │
                    └───────────────────────────────────────┘

  Voter claims ────► ClaimFromRewardingFund()             ──► IOTX transferred to voter
```

### 5. Migration Plan

| Step | Action | Timeline |
|------|--------|----------|
| 1 | Move `DelegateProfile` ownership to multisig (or burn); confirm signer set | **Pre-fork prerequisite** |
| 2 | Deploy protocol upgrade with `SetVoterRewardOptIn`, contract-rate bridge, compound bridge, and pending pool | Hard fork |
| 3 | Delegates verify their `DelegateProfile` portions are set as desired | Post-fork |
| 4 | Delegates opt in: `SetVoterRewardOptIn(true)` | Post-fork, delegate-paced |
| 5 | Monitor auto-distribution for opted-in delegates | 1–2 weeks per cohort |
| 6 | Hermes service filters opt-in delegates from `distributeRewards` | Coordinated with (4) |
| 7 | Deprecate Hermes service once all delegates have opted in | Final |
| 8 | Optional: hard fork to remove `VoterRewardOnchainOptIn` gate (force-migrate) | Future proposal |

Delegates can opt in at their own pace. During the transition period:

- `VoterRewardOnchainOptIn = false` (default): Legacy behavior — block reward is credited to the delegate's reward account per block; epoch reward is credited whole. Off-chain Hermes continues distribution for this delegate; no on-chain behavior changes.
- `VoterRewardOnchainOptIn = true`: Protocol handles both streams automatically, using the current `DelegateProfile` portions inverted into `BlockCommissionRate` / `EpochCommissionRate` at the next `PutPollResult`. Off-chain Hermes MUST skip this delegate to avoid double-payment.

**Rate mapping from Hermes era.** Because IIP-59 reads the same `DelegateProfile` fields Hermes reads, and uses the same voter-take semantics, a delegate whose `DelegateProfile` portions are unchanged before and after opt-in sees **identical** voter net income (modulo Hermes's service fee, which disappears in IIP-59 — small net gain for voters). No rate reconfiguration is required.

### 6. ioctl Integration

New ioctl command for delegates:

```bash
# Delegate: opt in to protocol-native distribution
ioctl stake2 optin

# Delegate: opt back to legacy Hermes-managed distribution
ioctl stake2 optin --off

# Voter: check unclaimed rewards (already exists)
ioctl action balance <address>

# Voter: claim rewards (already exists)
ioctl action claim <amount>
```

Commission rate updates continue to use whatever tool the delegate uses today (contract call to `DelegateProfile.updateProfile` from the delegate's owner address, or the iotex-hub UI).

### 7. Skeleton Implementation

#### 7.1 Candidate State Extension (`action/protocol/staking/candidate.go`)

```go
// Candidate represents a delegate candidate
type Candidate struct {
    Owner                    address.Address
    Operator                 address.Address
    Reward                   address.Address
    Identifier               address.Address
    Name                     string
    Votes                    *big.Int
    SelfStakeBucketIdx       uint64
    SelfStake                *big.Int
    BLSPubKey                []byte
    VoterRewardOnchainOptIn  bool    // gates §3 distribution
    BlockCommissionRate      uint64  // basis points 0–10000; snapshotted from DelegateProfile
    EpochCommissionRate      uint64  // basis points 0–10000; snapshotted from DelegateProfile
}

// CommissionCut returns the delegate's commission from a given reward for the
// given stream. Callers pass rate = BlockCommissionRate or EpochCommissionRate.
func (c *Candidate) CommissionCut(reward *big.Int, rateBps uint64) *big.Int {
    if rateBps == 0 {
        return big.NewInt(0)
    }
    cut := new(big.Int).Mul(reward, big.NewInt(int64(rateBps)))
    cut.Div(cut, big.NewInt(10000))
    return cut
}
```

Neither commission-rate field is settable by any protocol action. Both are populated by the poll layer at `PutPollResult` from the `DelegateProfile` contract (see §7.9). `VoterRewardOnchainOptIn` is settable by `SetVoterRewardOptIn` (§7.2, §7.11).

#### 7.2 SetVoterRewardOptIn Action Handler (`action/protocol/staking/handlers.go`)

```go
func (p *Protocol) handleSetVoterRewardOptIn(
    ctx context.Context,
    act *action.SetVoterRewardOptIn,
    sm protocol.StateManager,
) (*action.Receipt, error) {
    actCtx := protocol.MustGetActionCtx(ctx)
    featureCtx := protocol.MustGetFeatureCtx(ctx)

    if featureCtx.NoVoterRewardDistribution {
        // Pre-fork guard: action is not yet active.
        return nil, action.ErrInvalidAct
    }

    cand := p.candidateCenter.GetByOwner(actCtx.Caller)
    if cand == nil {
        return nil, errors.New("caller is not a registered candidate owner")
    }
    if cand.VoterRewardOnchainOptIn == act.OptIn {
        // Idempotent no-op: emit receipt but do not mutate state.
        return p.settleAction(ctx, sm, protocol.SuccessReceiptStatus, nil,
            &action.Log{
                Address: p.addr.String(),
                Topics:  []hash.Hash256{hash.BytesToHash256([]byte("VoterRewardOptInUnchanged"))},
                Data:    []byte{boolByte(act.OptIn)},
            },
        )
    }

    updated := cand.Clone()
    updated.VoterRewardOnchainOptIn = act.OptIn

    if err := p.candidateCenter.Upsert(updated); err != nil {
        return nil, err
    }
    if err := p.putCandidate(sm, updated); err != nil {
        return nil, err
    }

    // Effective at next PutPollResult; the poll snapshot picks up the new value
    // and the epoch that follows uses it (see §3.4 / §3.7).
    return p.settleAction(ctx, sm, protocol.SuccessReceiptStatus, nil,
        &action.Log{
            Address: p.addr.String(),
            Topics:  []hash.Hash256{hash.BytesToHash256([]byte("VoterRewardOptInSet"))},
            Data:    []byte{boolByte(act.OptIn)},
        },
    )
}
```

#### 7.3 Modified GrantBlockReward (`action/protocol/rewarding/reward.go`)

```go
func (p *Protocol) GrantBlockReward(ctx context.Context, sm protocol.StateManager) (*action.Log, error) {
    blkCtx := protocol.MustGetBlockCtx(ctx)
    featureCtx := protocol.MustGetFeatureCtx(ctx)

    // ... existing: read producer, resolve to delegate, compute blockReward + effectiveTip ...

    if p.blockRewardEligibleForVoterSplit(featureCtx, delegate) {
        // Tip goes to producer directly (inclusion incentive, not delegate comp).
        if effectiveTip.Sign() > 0 {
            if err := p.creditRewardAccount(sm, delegate.Reward, effectiveTip); err != nil {
                return nil, err
            }
        }
        // Accumulate base block reward into the pending pool; freeze the
        // current rate + reward address alongside the amount so an orphan
        // drain (delegate falls out of top-N) can still split correctly.
        if err := p.addPendingBlockReward(sm, delegate, blockReward); err != nil {
            return nil, err
        }
        return &action.Log{
            Address: p.addr.String(),
            Topics:  []hash.Hash256{hash.BytesToHash256([]byte("BlockRewardPending"))},
            Data:    append(delegate.Identifier.Bytes(), blockReward.Bytes()...),
        }, nil
    }

    // Legacy path: credit total (base + tip) to delegate immediately.
    return p.creditRewardAccount(sm, delegate.Reward, totalReward)
}

// addPendingBlockReward reads the delegate's current pending pool entry, adds
// blockReward, and writes it back. State key: pendingBlockReward || delegate.Identifier
// (21 bytes). The rewardAddr and blockCommissionRate on the entry are refreshed
// from the caller's poll-snapshotted candidate — the freshest available.
func (p *Protocol) addPendingBlockReward(
    sm protocol.StateManager,
    delegate *state.Candidate,
    blockReward *big.Int,
) error {
    key := pendingBlockRewardKey(delegate.Identifier)
    var pool pendingBlockRewardPool
    switch _, err := sm.State(&pool, protocol.KeyOption(key)); errors.Cause(err) {
    case nil, state.ErrStateNotExist:
        // ok — nil-value or missing both start from zero
    default:
        return err
    }
    if pool.Amount == nil {
        pool.Amount = big.NewInt(0)
    }
    pool.Amount.Add(pool.Amount, blockReward)
    pool.RewardAddr = delegate.Reward.Bytes()
    pool.BlockCommissionRate = delegate.BlockCommissionRate
    _, err := sm.PutState(&pool, protocol.KeyOption(key))
    return err
}
```

#### 7.4 Modified GrantEpochReward (`action/protocol/rewarding/reward.go`)

```go
func (p *Protocol) GrantEpochReward(ctx context.Context, sm protocol.StateManager) ([]*action.Log, error) {
    blkCtx := protocol.MustGetBlockCtx(ctx)
    bcCtx := protocol.MustGetBlockchainCtx(ctx)
    featureCtx := protocol.MustGetFeatureCtx(ctx)
    rp := rolldpos.MustGetProtocol(protocol.MustGetRegistry(ctx))
    epochNum := rp.GetEpochNum(blkCtx.BlockHeight)

    // Existing: read admin config, calculate epoch reward per delegate
    a := admin{}
    if err := p.state(sm, _adminKey, &a); err != nil {
        return nil, err
    }
    if err := a.grantEpochReward(sm, epochNum, bcCtx); err != nil {
        return nil, err
    }

    // ... existing top-delegate selection and reward calculation ...

    var logs []*action.Log
    drainedTop := make(map[address.Address]struct{})

    for i, delegate := range topDelegates {
        epochReward := rewardPerDelegate[i]

        // Fold in this delegate's accumulated block rewards.
        pending, err := p.drainPendingBlockReward(sm, delegate.Identifier)
        if err != nil {
            return nil, err
        }
        drainedTop[delegate.Identifier] = struct{}{}

        if p.blockRewardEligibleForVoterSplit(featureCtx, delegate) {
            blockCut := delegate.CommissionCut(pending, delegate.BlockCommissionRate)
            epochCut := delegate.CommissionCut(epochReward, delegate.EpochCommissionRate)
            totalCommission := new(big.Int).Add(blockCut, epochCut)
            totalReward := new(big.Int).Add(pending, epochReward)
            voterPool := new(big.Int).Sub(totalReward, totalCommission)

            rewardLog, err := p.distributeToVoters(ctx, sm, delegate,
                totalCommission, voterPool, epochNum)
            if err != nil {
                return nil, errors.Wrap(err, "distribute to voters")
            }
            logs = append(logs, rewardLog)
        } else {
            // Legacy: full combined reward to delegate.
            total := new(big.Int).Add(epochReward, pending)
            if err := p.credit(sm, delegate.Reward, total); err != nil {
                return nil, err
            }
        }
    }

    // Drain pending pools left by delegates that produced blocks earlier but
    // are no longer in top-N (§3.3). Bounded by candidate count.
    drainLogs, err := p.drainOrphanPendingPools(ctx, sm, epochNum, drainedTop)
    if err != nil {
        return nil, err
    }
    logs = append(logs, drainLogs...)
    return logs, nil
}

// distributeToVoters splits voterPool across the frozen snapshot voter list,
// routing each share to either AddDeposit (compound) or unclaimedBalance based
// on the AutoDeposit contract (§3.6). Emits a single batched log per delegate.
func (p *Protocol) distributeToVoters(
    ctx context.Context,
    sm protocol.StateManager,
    delegate *state.Candidate,   // poll snapshot
    totalCommission *big.Int,
    voterPool *big.Int,
    epochNum uint64,
) (*action.Log, error) {
    stakingProtocol := staking.MustGetProtocol(protocol.MustGetRegistry(ctx))
    candIdentifier, err := address.FromString(delegate.Identity)
    if err != nil {
        return nil, err
    }
    voters, err := stakingProtocol.SnapshotVoterWeightsByCandidate(sm, candIdentifier)
    if err != nil {
        return nil, err
    }
    if len(voters) == 0 || voterPool.Sign() <= 0 {
        // No voters snapshotted — full remainder to delegate.
        totalCommission = new(big.Int).Add(totalCommission, voterPool)
        if err := p.credit(sm, delegate.Reward, totalCommission); err != nil {
            return nil, err
        }
        return p.newDelegateDistributedLog(candIdentifier, delegate.Reward,
            totalCommission, big.NewInt(0), nil, nil, nil, epochNum, nil), nil
    }

    totalWeight := big.NewInt(0)
    for _, v := range voters {
        totalWeight.Add(totalWeight, v.Weight)
    }
    if totalWeight.Sign() == 0 {
        totalCommission = new(big.Int).Add(totalCommission, voterPool)
        return p.newDelegateDistributedLog(candIdentifier, delegate.Reward,
            totalCommission, big.NewInt(0), nil, nil, nil, epochNum, nil),
            p.credit(sm, delegate.Reward, totalCommission)
    }

    voterAddrs := make([]address.Address, 0, len(voters))
    voterAmts := make([]*big.Int, 0, len(voters))
    voterRoutes := make([]byte, 0, len(voters))

    distributed := big.NewInt(0)
    for _, v := range voters {
        share := new(big.Int).Mul(voterPool, v.Weight)
        share.Div(share, totalWeight)
        if share.Sign() == 0 {
            continue
        }
        route, err := p.compoundOrCredit(ctx, sm, v.Voter, share)
        if err != nil {
            return nil, err
        }
        voterAddrs = append(voterAddrs, v.Voter)
        voterAmts = append(voterAmts, share)
        voterRoutes = append(voterRoutes, route)
        distributed.Add(distributed, share)
    }

    // Rounding dust to delegate.
    dust := new(big.Int).Sub(voterPool, distributed)
    if dust.Sign() > 0 {
        totalCommission = new(big.Int).Add(totalCommission, dust)
    }
    if err := p.credit(sm, delegate.Reward, totalCommission); err != nil {
        return nil, err
    }

    snapHash := stakingProtocol.VoterSnapshotHash(sm, candIdentifier)
    return p.newDelegateDistributedLog(candIdentifier, delegate.Reward,
        totalCommission, distributed, voterAddrs, voterAmts, voterRoutes,
        epochNum, snapHash[:]), nil
}
```

Where `compoundOrCredit` implements the routing decision from §3.6 (see §7.10) and `newDelegateDistributedLog` packs the batched receipt log defined in §3.2. `dedupedAmounts` are aggregated inside the loop to keep receipt payload bounded — voters with multiple buckets receive one entry each.

#### 7.5 Voter Weight Snapshot (`action/protocol/staking/voter_weight_snapshot.go`)

At each `PutPollResult`, alongside the commission-rate snapshot, the staking protocol writes a per-candidate blob of the frozen voter list:

```go
// Key layout: 1-byte tag + 20-byte candidate identifier.
func voterWeightSnapKey(candID address.Address) []byte {
    out := make([]byte, 1+len(candID.Bytes()))
    out[0] = _voterWeightSnap
    copy(out[1:], candID.Bytes())
    return out
}

// SnapshotVoterWeights writes each candidate's live voter list to state.
// Called from poll.setCandidates at PutPollResult, gated on the feature flag.
// Incremental: unchanged blobs are skipped (byte equality); candidates whose
// voter list is now empty have their blob DelState'd.
func (p *Protocol) SnapshotVoterWeights(sm protocol.StateManager) error {
    csr, err := ConstructBaseView(sm)
    if err != nil {
        return err
    }
    vd := csr.BaseView()
    if vd.voterWeights == nil {
        return nil
    }
    for _, cand := range vd.candCenter.All() {
        candID := cand.GetIdentifier()
        liveVoters := readSortedLiveVoters(vd.voterWeights, hash.BytesToHash160(candID.Bytes()))
        _, newBlob, err := encodeVoterWeightSnapshot(liveVoters)
        if err != nil {
            return err
        }
        key := voterWeightSnapKey(candID)
        oldBlob, err := readSnapshotBlob(sm, key)
        if err != nil {
            return err
        }
        switch {
        case newBlob == nil && oldBlob != nil:
            sm.DelState(protocol.NamespaceOption(_stakingNameSpace), protocol.KeyOption(key))
        case newBlob != nil && !bytes.Equal(oldBlob, newBlob):
            sm.PutState(pbFromBlob(newBlob), protocol.NamespaceOption(_stakingNameSpace), protocol.KeyOption(key))
        }
    }
    return nil
}

// SnapshotVoterWeightsByCandidate is the reader consumed by distributeToVoters.
// Returns nil (not error) when a candidate has no snapshot — the caller treats
// this as "no voters" and credits the delegate.
func (p *Protocol) SnapshotVoterWeightsByCandidate(
    sr protocol.StateReader,
    candID address.Address,
) ([]VoterWeight, error) {
    // ... State() with switch on state.ErrStateNotExist → decode → return ...
}
```

**Why per-candidate blob rather than flat `(candidate, voter)` keys:** the state API does not support prefix iteration, so a flat layout would require an auxiliary index keyed by candidate. The per-candidate blob lets a single `State()` read return the entire voter list a delegate needs.

**Determinism invariant.** The blob writer sorts by voter address before encoding; the reader consumes in that same order. Because the encoding is byte-deterministic for equal logical inputs, the "skip if unchanged" check in `SnapshotVoterWeights` is safe: unchanged voter sets produce byte-identical blobs across nodes.

#### 7.6 GetActiveBucketsByCandidate — no longer used

The PoC's `GetActiveBucketsByCandidate` helper is not needed in the final design: voter reward distribution reads from the snapshot (§7.5), not from live bucket state. This eliminates a whole class of edge cases — mid-epoch stake changes, indexer readiness skew across nodes, and self-stake bucket misclassification — that would otherwise need per-call handling in the reward path.

#### 7.7 Action Definition (`action/setvoterrewardoptin.go`)

```go
package action

// SetVoterRewardOptIn toggles a delegate's IIP-59 opt-in state.
type SetVoterRewardOptIn struct {
    AbstractAction
    optIn bool
}

func NewSetVoterRewardOptIn(optIn bool) *SetVoterRewardOptIn {
    return &SetVoterRewardOptIn{optIn: optIn}
}

func (s *SetVoterRewardOptIn) OptIn() bool { return s.optIn }

func (s *SetVoterRewardOptIn) IntrinsicGas() (uint64, error) {
    return 10000, nil
}

func (s *SetVoterRewardOptIn) Serialize() []byte {
    if s.optIn {
        return []byte{1}
    }
    return []byte{0}
}
```

#### 7.8 Protobuf Extension (`iotextypes/action.proto`)

```protobuf
// SetVoterRewardOptIn toggles a delegate's opt-in to protocol-native
// voter reward distribution introduced by IIP-59.
message SetVoterRewardOptIn {
    bool optIn = 1;
}

// Add to ActionCore.action oneof:
message ActionCore {
    // ... existing fields ...
    oneof action {
        // ... existing actions ...
        SetVoterRewardOptIn setVoterRewardOptIn = 60;
    }
}

// CandidateInfo carries all three IIP-59 fields:
message CandidateInfo {
    // ... existing fields ...
    bool   voterRewardOnchainOptIn = 20;
    uint64 blockCommissionRate      = 21;  // basis points
    uint64 epochCommissionRate      = 22;  // basis points
}
```

#### 7.9 Commission Rate Bridge (`action/protocol/staking/delegate_profile_bridge.go`)

Called from `PutPollResult` alongside the voter-weight snapshot (§7.5). Populates `BlockCommissionRate` / `EpochCommissionRate` on the poll-snapshotted candidates.

```go
var (
    // Hard-coded per §3.5 — real values are chain-parameter.
    delegateProfileAddr = mustAddress("0xfa7f50866ac45d84adf54bc767c885f92750e258")
    fieldBlockPortion   = "blockRewardPortion"
    fieldEpochPortion   = "epochRewardPortion"
)

// SnapshotCommissionRates issues one read-only EVM call per candidate against
// DelegateProfile.getEncodedProfile and writes the derived commission fields
// back onto the passed poll snapshot slice in place.
func (p *Protocol) SnapshotCommissionRates(
    ctx context.Context,
    sm protocol.StateManager,
    cands []*state.Candidate,
) error {
    for _, c := range cands {
        blk, epoch, err := p.readProfileForDelegate(ctx, sm, c.Identifier)
        if err != nil {
            return errors.Wrapf(err, "read profile for %s", c.Identifier)
        }
        c.BlockCommissionRate = invertToCommission(blk)
        c.EpochCommissionRate = invertToCommission(epoch)
    }
    return nil
}

// readProfileForDelegate calls getEncodedProfile(delegate) via evm.SimulateExecution
// against the block being sealed. Returns (blockPortionBps, epochPortionBps).
// Empty / missing profile → (0, 0).
func (p *Protocol) readProfileForDelegate(
    ctx context.Context,
    sm protocol.StateManager,
    delegate address.Address,
) (uint64, uint64, error) {
    data, err := delegateProfileABI.Pack("getEncodedProfile", ethAddr(delegate))
    if err != nil {
        return 0, 0, err
    }
    out, _, err := evm.SimulateExecution(ctx, sm, delegateProfileAddr, data)
    if err != nil {
        // Contract not deployed / not registered — degrade to 0/0 (legacy path).
        if isNotRegisteredErr(err) {
            return 0, 0, nil
        }
        return 0, 0, err
    }
    return decodeProfilePortions(out) // parse ABI-encoded (fieldName → bytes) map
}

func invertToCommission(voterPortionBps uint64) uint64 {
    if voterPortionBps >= 10000 {
        return 0 // voter takes everything → delegate takes nothing
    }
    return 10000 - voterPortionBps
}
```

#### 7.10 Compound Bridge (`action/protocol/rewarding/compound_bridge.go`)

Called from `distributeToVoters` per voter (§7.4). Reads `AutoDeposit` and routes.

```go
var (
    autoDepositAddr = mustAddress("io108ckwzlzpkhva7cnfceajlu7wu6ql5kq95uat9")
)

// Routing outcomes:
const (
    routeUnclaimedBalance = 0
    routeAutoDeposit      = 1
)

func (p *Protocol) compoundOrCredit(
    ctx context.Context,
    sm protocol.StateManager,
    voter address.Address,
    amount *big.Int,
) (byte, error) {
    // Fast path: cheap contract mapping read; miss returns 0.
    bucketID, err := p.readAutoDepositTarget(ctx, sm, voter)
    if err != nil {
        return 0, err
    }
    if bucketID == 0 {
        return routeUnclaimedBalance, p.credit(sm, voter, amount)
    }

    stakingProtocol := staking.MustGetProtocol(protocol.MustGetRegistry(ctx))
    bucket, err := stakingProtocol.BucketByIndex(sm, bucketID)
    switch {
    case errors.Is(err, staking.ErrBucketNotFound),
        bucket == nil,
        !bucket.Owner.Equal(voter),
        !bucket.AutoStake,
        !bucket.IsActive():
        // Any precondition miss → credit to unclaimed balance.
        return routeUnclaimedBalance, p.credit(sm, voter, amount)
    case err != nil:
        return 0, err
    }

    if err := stakingProtocol.AddDeposit(ctx, sm, bucketID, amount); err != nil {
        // AddDeposit failure is unexpected on a fully validated bucket; degrade
        // safely to unclaimedBalance rather than aborting the epoch.
        return routeUnclaimedBalance, p.credit(sm, voter, amount)
    }
    return routeAutoDeposit, nil
}

func (p *Protocol) readAutoDepositTarget(
    ctx context.Context,
    sm protocol.StateManager,
    voter address.Address,
) (uint64, error) {
    data, _ := autoDepositABI.Pack("bucket", ethAddr(voter))
    out, _, err := evm.SimulateExecution(ctx, sm, autoDepositAddr, data)
    if err != nil {
        return 0, nil // conservative: unregistered
    }
    v, err := autoDepositABI.Unpack("bucket", out)
    if err != nil || len(v) == 0 {
        return 0, nil
    }
    id, ok := v[0].(*big.Int)
    if !ok || id.Sign() <= 0 {
        return 0, nil
    }
    return id.Uint64(), nil
}
```

#### 7.11 Candidate RPC Surface (`action/protocol/staking/staking_statereader.go`)

`CandidateInfo` responses expose all three new fields so both Hermes (to filter opt-in delegates) and iotex-hub (to render badges) can query without a new endpoint.

## Rationale

### Why Basis Points for Commission

Using basis points (1/100th of a percent) provides sufficient granularity:
- 500 bps = 5%, 1000 bps = 10%, 2500 bps = 25%
- Integer arithmetic avoids floating-point precision issues
- Same convention used by most DeFi protocols and Cosmos SDK

### Why Epoch-Boundary Rate Changes

Commission rate changes take effect at the epoch boundary that follows the next `PutPollResult`, not immediately. This prevents a delegate from:
1. Setting 0% commission to attract voters
2. Switching to 100% right before epoch reward distribution
3. Switching back to 0%

The `PutPollResult`-anchored snapshot gives voters a roughly 1.5-epoch reaction window to observe a rate change and re-stake or unstake before it applies to a distribution.

### Why Fold Block Reward Instead of Distributing Per Block

Distributing block reward to voters at every block would run the per-voter loop up to ~100 times per epoch — expensive at 2,000+ voters per delegate and duplicative, since the same voter list is read each time. Accumulating block reward in a per-delegate pending pool during the epoch and folding it into the single epoch-end distribution has three properties that make it strictly better than per-block distribution:

- **Per-block cost stays O(1):** one state read + one state write per produced block, independent of voter count.
- **One deterministic distribution per epoch:** the same snapshot-based voter list and weights are used for both the epoch reward and the folded block reward, guaranteeing identical per-voter shares across nodes.
- **Voter economics are preserved:** total voter income is identical to per-block distribution, because commission is applied to the sum `epochReward + Σ blockReward`, and the commission rate is constant across the epoch (frozen at the previous `PutPollResult`).

### Why Not Mandatory Auto-Distribution

`VoterRewardOnchainOptIn = false` preserves legacy behavior because:
- Some delegates have custom distribution arrangements with voters (LSD-only pools, side agreements) that Hermes was configured for.
- Forcing auto-distribution at a fork would strand delegates who have not verified their `DelegateProfile` configuration.
- Gradual migration is less risky than a hard switch; §3.7 gives a clean per-delegate ramp with bidirectional escape.
- A future fork can drop the gate once every active delegate has migrated (see §5 Step 8).

### Why Reuse `DelegateProfile` Instead of a Native `SetCommissionRate` Action

An earlier draft of this proposal introduced a native `SetCommissionRate` action. The current design reuses the existing `DelegateProfile` contract:

- **Operator UX continuity.** Delegates already configure portions through this contract via `updateProfile` or the iotex-hub UI. Adding a parallel native action would create two sources of truth that could drift.
- **Two-stream semantics.** Hermes already treats block-stream and epoch-stream portions independently. Copying those two fields verbatim (with a semantic inversion, §3.5) is a strictly smaller change than defining a new dual-rate schema and migration.
- **Governance is a knowable requirement.** The single-EOA owner risk on `DelegateProfile` (§3.5) is a known and fixable problem; §5 Step 1 makes ownership migration a prerequisite. A native action would appear cleaner but would also silently discard the existing operator tooling and iotex-hub integration — a cost that outweighs the governance work.
- **Foundation Bonus scope.** The contract's `foundationRewardPortion` field is ignored by IIP-59. Foundation Bonus is already at zero on mainnet; folding it into IIP-59 is deferred to a follow-on proposal if it is ever reactivated.

### Why Native Compound Instead of Deferring to Claim Time

Two alternatives were considered for compound (reinvest into a native bucket):

- **A. Extend `ClaimFromRewardingFund` with a target parameter.** Voters would opt for compound at claim time; the protocol splits amount → bucket vs. amount → wallet inside the claim handler. Advantages: no per-voter EVM read at distribution time; compound decision is voter-driven and revocable up to the last claim. Disadvantages: passive users lose today's "set once, keep reinvesting" behavior — they must re-issue a compound claim every epoch or accumulate for manual claiming. This is a UX regression vs. Hermes.
- **B. Reuse `AutoDeposit` contract, read at drain time** (this proposal, §3.6). Preserves today's UX exactly: voter registers once, protocol auto-reinvests each epoch. Trade-off: one bounded EVM read per voter share at the epoch's last block (~10-40 ms/epoch at mainnet scale). At 40k credits/epoch this is comfortably below the block-time budget.

B is chosen for parity with the Hermes-era UX. Delegates or third parties can still build a keeper that periodically calls `ClaimFromRewardingFund` for voters who prefer wallet delivery, but no native action extension is required.

### Why a Single Batched `DelegateDistributed` Log

Emitting one log per voter share at the epoch's last block would produce roughly `Σ voters ≈ 40,000` entries. At ~180 bytes each that is ~7 MB of receipt-log payload in a single block — a 100-500× increase over today's per-epoch log volume. Consequences observed in load modeling: receipt-trie storage growth, `eth_getLogs(fromBlock=epochBlock, toBlock=epochBlock)` timeouts, and pressure on block gas / size limits under LSD expansion scenarios.

The batched `DelegateDistributed` log (§3.2) reduces the log count to `|topDelegates| + |orphanDrain| ≤ ~200` per epoch block, at the cost of a single fat payload per delegate (~30-40 KB for a 2,000-voter delegate). Total per-epoch-block receipt payload lands around ~0.5-1 MB, well within tooling budgets. The `snapshotHash` in the log binds the entry to the exact voter snapshot used so off-chain reconstructors can verify the split without replaying state.

### Performance Impact

Two hot paths are affected: `GrantBlockReward` (every block) and `GrantEpochReward` (once per epoch), plus a new bounded read at `PutPollResult` (mid-epoch).

**Per-block (`GrantBlockReward`).** Under IIP-59 the block reward is accumulated into a per-delegate pending pool instead of credited directly. Extra work per block: exactly one state read and one state write against a 21-byte key. No per-voter iteration. Overhead: sub-millisecond.

**Per-epoch (`GrantEpochReward`).** The per-voter distribution runs once per delegate at the epoch's last block:

- Top delegates have ~2,000–4,000 voters after the snapshot (§3.4)
- Total across all 36 delegates: ~40,000 voter credits per epoch
- Each iteration: 1 multiplication + 1 division + 1 state write + 1 `AutoDeposit.bucket(voter)` read (~10-40 μs)
- One additional per-delegate call reads the snapshot blob (§7.5); the blob is a single `State()` read, not a loop over indices
- One additional per-delegate log emit (batched, §3.2)
- Total additional time: ~10-50 ms per epoch (still small relative to 5-second block time)

**Per-PutPollResult (mid-epoch).** Two extra passes over the ~100 candidates:

- Voter-weight snapshot writer (§7.5): a few ms, dominated by proto marshal of changed blobs.
- Commission-rate bridge (§7.9): one `evm.SimulateExecution` per candidate (~1 ms/call → ~100 ms/PutPollResult). This is a read-only, deterministic call against the block state, mirroring the consortium poll bridge pattern.

Combined overhead: still well under the block-time budget at PutPollResult and at epoch close.

## Backwards Compatibility

- **Consensus change**: Yes — modifies both `GrantBlockReward()` and `GrantEpochReward()` output when a delegate has opted in via `VoterRewardOnchainOptIn`. Requires hard fork.
- **State schema change**: Yes — adds `VoterRewardOnchainOptIn`, `BlockCommissionRate`, `EpochCommissionRate` to `Candidate` struct; adds per-delegate pending block reward pool; adds per-candidate voter weight snapshot blob. Requires state migration (all new fields default to zero-value on existing candidates, which correctly maps to the legacy path).
- **Default behavior**: `VoterRewardOnchainOptIn = false` (the default at fork activation) preserves exact legacy behavior — block reward (base + tip) credited per block to `RewardAddress`, epoch reward credited whole to `RewardAddress`. No existing delegate or voter is affected until the delegate explicitly submits `SetVoterRewardOptIn(true)`.
- **RPC compatibility**: Existing `ReadStakingData` APIs are unaffected. Three new fields (`voterRewardOnchainOptIn`, `blockCommissionRate`, `epochCommissionRate`) are added to `CandidateInfo` responses.
- **Hermes compatibility**: Hermes MUST update its `distributeRewards` loop to skip delegates with `voterRewardOnchainOptIn == true` (available via the RPC changes above). Delegates that have not opted in continue to be handled by Hermes as before; the migration is per-delegate opt-in, not a hard cutover.
- **`DelegateProfile` contract compatibility**: No contract-side changes are required for the rate-read path. The contract's owner-based `updateProfileForDelegate` continues to work; the operator-managed portion values become the source of truth for on-chain commission. A governance action on `DelegateProfile.owner()` is a pre-fork prerequisite (§5 Step 1).
- **`AutoDeposit` contract compatibility**: No contract-side changes are required for compound. Existing `register(bucketId)` / `unregister()` behaviors are preserved; the protocol only calls the read-only `bucket(voter)` view.
- **iotex-hub / delegate tooling**: Compound registration UI, commission-rate slider, and delegate registry pages continue to work as-is. A new "IIP-59 opt-in" toggle should be added but is not required for the migration to succeed.
- **Restart safety**: The pending block reward pool, voter weight snapshot, and commission-rate snapshot are all persisted in state, so a node restart mid-epoch does not lose already-accumulated block rewards or the frozen distribution parameters. Compound and rate reads are pure functions of the block state and are automatically consistent under revert.

## Test Cases

### 1. Basic Distribution

- Delegate with 1000 bps commission, 100 IOTX epoch reward
- 3 voters: A (50 weighted votes), B (30), C (20)
- Expected: Delegate gets 10 IOTX, A gets 45 IOTX, B gets 27 IOTX, C gets 18 IOTX

### 2. Zero Commission

- Delegate with 0 bps commission (legacy mode)
- Expected: Full 100 IOTX to delegate's reward account. No voter distribution.

### 3. Full Commission

- Delegate with 10000 bps (100%) commission
- Expected: Full 100 IOTX to delegate. Voters get 0.

### 4. Rounding Dust

- Delegate with 1000 bps, 1 IOTX reward, 3 equal-weight voters
- Each voter gets 0.3 IOTX, delegate gets 0.1 IOTX + 0.0...01 Rau dust

### 5. Unstaked Bucket Exclusion

- Voter unstakes mid-epoch
- Expected: Unstaked bucket excluded from distribution. Active voters get proportionally more.

### 6. Commission Rate Change

- Delegate changes rate from 1000 to 2000 bps mid-epoch
- Expected: Current epoch uses old rate (1000). Next epoch uses new rate (2000).

### 7. Self-Stake Inclusion

- Delegate's self-stake bucket participates in distribution like any other voter
- Expected: Delegate receives commission + proportional share of voter pool for self-stake

### 8. Multiple Buckets Per Voter

- Voter has 3 buckets staked to same delegate
- Expected: Each bucket's weighted vote counted separately. Total voter reward = sum of per-bucket shares.

### 9. Block Reward Folding

- Delegate with 1000 bps commission produces 40 blocks in the epoch, each block reward 8 IOTX (total 320 IOTX pending)
- Epoch reward for the delegate is 100 IOTX
- Expected at epoch end: `totalReward = 420 IOTX`; delegate commission = 42 IOTX; voter pool = 378 IOTX distributed by frozen snapshot weights. No block-reward IOTX is stranded in the pending pool after `GrantEpochReward`.

### 10. Non-Top-N Delegate Pending Drain

- Delegate produced 10 blocks (80 IOTX pending), then lost votes and dropped out of top-N at epoch end
- Expected: no epoch reward assigned; the 80 IOTX pending pool is drained by the trailing loop (§3.3); at commission=1000 bps, delegate gets 8 IOTX and voters share 72 IOTX by the snapshotted list.

### 11. Voter Weight Snapshot Reaction Window

- Delegate raises commission on `DelegateProfile` from 500 → 2000 bps in epoch N; the contract-side write receipt lands before epoch N's `PutPollResult`
- Expected: epoch N's rewards still use 500 bps (already snapshotted from the previous epoch's `PutPollResult`). Epoch N+1 rewards use 2000 bps. A voter that unstakes in epoch N after `PutPollResult` is still counted in epoch N's distribution (snapshotted before the unstake) but not epoch N+1.

### 12. Opt-In Effect Delay

- Epoch N: delegate D has `VoterRewardOnchainOptIn = false` (legacy). D sends `SetVoterRewardOptIn(true)` in epoch N.
- Epoch N's `PutPollResult` runs; snapshot freezes `optIn = true` for D.
- Expected: epoch N's rewards still route to legacy Hermes path (`RewardAddress` gets full amount) because the poll snapshot used at epoch N grant time still carries `optIn = false` from epoch N−1. Epoch N+1's rewards use the on-chain split path. Opting back out (`SetVoterRewardOptIn(false)` in epoch N+2) has the same 1-epoch delay.

### 13. Compound Routing Preconditions

- Voter V has `AutoDeposit.bucket(V) = 7`; bucket 7 has `Owner == V`, `AutoStake == true`, `status == active`. Expected: V's share of the epoch reward is added to bucket 7 via `AddDeposit`; V's `unclaimedBalance` unchanged.
- Voter V' has registered bucket 12 but `bucket 12.Owner != V'` (transferred). Expected: fall through to `unclaimedBalance` credit.
- Voter V'' has registered bucket 9 with `AutoStake == false`. Expected: fall through to `unclaimedBalance` credit.
- Voter V''' has no auto-deposit registration (`AutoDeposit.bucket(V''') = 0`). Expected: `unclaimedBalance` credit (legacy claim path).
- Voter V'''' holds only LSD (contract-staking) buckets. Expected: `unclaimedBalance` credit (LSD holders cannot register with the compound contract; parity with today's Hermes behavior).

### 14. Empty DelegateProfile Fallback

- Delegate D has opted in (`VoterRewardOnchainOptIn = true`) but has never written a profile to `DelegateProfile`. `getEncodedProfile(D)` returns `0x`.
- Expected: `SnapshotCommissionRates` records `{BlockCommissionRate: 10000, EpochCommissionRate: 10000}` (default = full commission = 100% to delegate). All voter reward flows to the delegate's `RewardAddress` in this epoch — behavior identical to legacy Hermes for a delegate with no configuration. Emit a diagnostic log so off-chain tooling can flag the missing profile.

### 15. Batched `DelegateDistributed` Log Format

- Delegate D distributes epoch reward to 87 voters with commission split.
- Expected: exactly one `DelegateDistributed{epoch, delegate=D, voters=[87 addrs sorted], amounts=[87 uint64s in Rau], commissionAmount, snapshotHash, blockRewardComponent, epochRewardComponent}` receipt log per epoch, per opted-in delegate. `voters` and `amounts` arrays are index-aligned; `sum(amounts) + commissionAmount == blockRewardComponent × (10000 − blockCommRate) / 10000 + epochRewardComponent × (10000 − epochCommRate) / 10000 + commissionAmount`. `snapshotHash` matches the hash of the frozen voter weight snapshot for D at epoch N's `PutPollResult`. No per-voter `VOTER_REWARD` legacy log is emitted for opted-in delegates.

### 16. Hermes Double-Spend Prevention

- Delegates D₁ (opted in) and D₂ (legacy) both distribute epoch N rewards.
- Expected: on-chain, D₁ generates `DelegateDistributed` log; D₂ generates a single grant to `RewardAddress(D₂)`. Off-chain Hermes filter reads `Candidate.VoterRewardOnchainOptIn` at the epoch snapshot boundary and skips D₁ entirely from `distributeRewards`; only D₂ is processed. Assert: for any voter V, per-epoch sum-of-receipts-across-chains-and-Hermes for V is exactly one grant — either on-chain (D₁-voter) or Hermes (D₂-voter), never both.

## Implementation

### Reference Implementation

A proof-of-concept bot demonstrating the core logic (voter weight calculation, proportional distribution) is available at:
- [`tools/voter-reward-poc/`](https://github.com/iotexproject/iotex-core/tree/master/tools/voter-reward-poc) — stateless tool that reads on-chain staking data, calculates voter weights, and generates reward distribution

### Protocol Changes Required

| File | Change |
|------|--------|
| `action/protocol/context.go` | Add `EnableVoterRewardDistribution` (or the equivalent `!NoVoterRewardDistribution`) feature flag |
| `action/protocol/staking/candidate.go` | Add `VoterRewardOnchainOptIn bool`, `BlockCommissionRate uint64`, `EpochCommissionRate uint64` fields to `Candidate` struct |
| `action/protocol/staking/handler_voter_reward_optin.go` | New action handler `handleSetVoterRewardOptIn`; idempotent flip; pre-fork guard; delegate-only sender check |
| `action/protocol/staking/handlers.go` | Wire voter-weight-view deltas into all stake-mutating handlers |
| `action/protocol/staking/voter_weight_view.go` | Incremental per-candidate sorted voter weight list backing the snapshot writer |
| `action/protocol/staking/voter_weight_snapshot.go` | Per-candidate blob writer/reader (§7.5), invoked from `PutPollResult` |
| `action/protocol/poll/util.go` | Call `SnapshotCommissionRates` (contract read via `evm.SimulateExecution` against `DelegateProfile`, then invert to commission) + `SnapshotVoterWeights` in `setCandidates`; carry `VoterRewardOnchainOptIn` from `staking.Candidate` into the poll snapshot |
| `action/protocol/poll/delegate_profile_bridge.go` | New: `SnapshotCommissionRates` implementation calling `getEncodedProfile(delegate)`, decoding `EncodedDelegateProfile`, extracting `blockRewardPortion` + `epochRewardPortion`, `invertToCommission` (`10000 − portion*100`), empty-profile default |
| `action/protocol/rewarding/voter_reward.go` | `distributeToVoters` implementation reading the snapshot; per-voter `compoundOrCredit` routing; batched `DelegateDistributed` log emitter |
| `action/protocol/rewarding/auto_deposit_bridge.go` | New: `compoundOrCredit(voter, amount, sm)` — 4-precondition check (`bucketId != 0 && bucket.Owner == voter && AutoStake && status == active`) via `evm.SimulateExecution` against `AutoDeposit`; on success emit `AddDeposit` state transition; on any precondition miss fall through to `unclaimedBalance` credit |
| `action/protocol/rewarding/reward.go` | Modify `GrantBlockReward()` to split `effectiveTip` (→ producer directly) from base reward (→ pending pool) via `blockRewardEligibleForVoterSplit` predicate; modify `GrantEpochReward()` to fold pending + call `distributeToVoters` per opted-in delegate with dual rate split; orphan pool drain with synthetic `*state.Candidate` reconstruction |
| `state/candidate.go` | Add `VoterRewardOnchainOptIn`, `BlockCommissionRate`, `EpochCommissionRate` fields to `state.Candidate` (poll snapshot) |
| `action/protocol/staking/staking_statereader.go` | Expose `VoterRewardOnchainOptIn`, `BlockCommissionRate`, `EpochCommissionRate` in candidate queries |
| `api/grpcserver.go` | Surface the three new fields in gRPC responses |
| `action/action.go` + `action/protocol/staking/protocol.go` | Register `SetVoterRewardOptIn` action type (protobuf tag `60`) |
| `ioctl/newcmd/action/stake2optin.go` | New: `ioctl stake2 optin [--off]` CLI command |

### Activation

The protocol change is activated at a designated block height via the genesis configuration, following IoTeX's standard hard fork process.

## Security Considerations

- **Commission rate manipulation**: Rate changes flow through the existing `DelegateProfile` contract and are snapshotted at `PutPollResult` for the following epoch. A delegate cannot mid-epoch swap a low rate for a high rate against already-earned rewards; the frozen `{BlockCommissionRate, EpochCommissionRate}` on the poll snapshot governs the whole epoch's distribution. Voters can watch `DelegateProfile` writes on-chain and react in the epoch-window gap.
- **`DelegateProfile` contract owner governance** *(HARD PREREQUISITE)*: The `DelegateProfile` contract is currently owned by a single EOA (`0x68c12a8c5d5f0a1fd13319ba4840301b0c93bd4f`) with unrestricted rate-write authority. Once IIP-59 activates, that EOA becomes a load-bearing consensus dependency — a compromise could set every opted-in delegate's commission to 100% in one transaction. **Before the fork block**, ownership MUST be moved to a multisig (or burned to a timelocked contract), and instantaneous rate-change authority SHOULD be replaced by a delta-cap + time-delay mechanism (e.g., ≤ 500 bps change per epoch, effective 2 epochs later). This is a governance action, not a protocol change, but it is a launch prerequisite documented here so the migration plan (§5, Step 1) cannot bypass it.
- **Semantic inversion invariant**: `DelegateProfile` historically stores **voter-take** portions (matching the analyser formula `distrReward = rewardToSplit × epochRewardPerc / 100`). The bridge in §7.9 MUST invert to commission-take via `commission = 10000 − portion × 100` before writing to the poll snapshot. A regression that reads the raw portion as commission would silently swap voter and delegate shares: delegates who set voter-take = 90% (giving voters most of the reward, as they do today) would suddenly receive 90% commission. This is guarded by (a) an explicit unit test comparing bridge output against an oracle Hermes distribution over 100 mainnet delegates, and (b) a rate-sanity check in `SnapshotCommissionRates` that rejects any single-epoch drop from `>50%` voter-take to `<10%` voter-take as an inversion smell.
- **Opt-in coexistence race conditions**: During the migration window, some delegates route rewards on-chain (opted in) and some route via the legacy Hermes service (default). Hermes MUST filter opted-in delegates from `distributeRewards` at the same epoch boundary that the poll snapshot fixes, otherwise a voter is double-paid or under-paid for one epoch. The epoch-delay of the opt-in flip (§3.7) gives Hermes a full epoch to observe `VoterRewardOnchainOptIn == true` in the candidate list, filter it out of its next epoch payout, and stay in sync. A voter reconciliation job SHOULD compare on-chain `DelegateDistributed` logs against Hermes distributions per epoch until Hermes v1 is decommissioned.
- **Compound reentrancy**: `compoundOrCredit` calls `AutoDeposit.AddDeposit` (`iotex-io/hermes` fork of the auto-compound contract) inside the rewarding epoch block. The call is issued from a system context (no external caller, no return value used besides the state transition), and `AddDeposit` cannot re-enter the rewarding protocol because rewarding namespace state is only mutated in-process, not via an EVM system call surface. However, `AutoDeposit` MUST be validated to have no external callback to arbitrary addresses on `AddDeposit` before the fork; the current source has none, but any future upgrade of that contract requires a re-review under IIP-59 assumptions.
- **Vote weight correctness**: Uses the exact same `CalculateVoteWeight()` function as consensus vote counting. No separate calculation path that could diverge. LSD (contract-staking) holders are surfaced through `ContractStakingIndexer` setting per-holder `Owner` on their bucket, so they appear as ordinary voters in the weight view.
- **Rounding attacks**: Total distributed ≤ total voter pool (guaranteed by integer division). Dust goes to delegate, not lost. Applied identically to block-reward split and epoch-reward split; when both apply to the same delegate, dust from each is credited independently (no cross-subsidy).
- **Reward account overflow**: Uses `*big.Int` arithmetic — no overflow possible.
- **Denial of service**: The per-epoch iteration is bounded by total bucket count (~40,000 across all delegates). Execution time is O(N) in the number of buckets, which is already bounded by the staking protocol. Contract reads at `PutPollResult` add O(top-N) EVM calls (~24-100/epoch); `compoundOrCredit` adds O(voter-count) EVM calls (~10k-50k/epoch, one-time per epoch). Both are dominated by the existing rewarding loop's cost.
- **Pending pool integrity**: Block rewards routed to the per-delegate pending pool are drained exactly once at epoch end — either by the top-N loop (§3.2) or by the trailing orphan-drain loop (§3.3). No path leaves a pool entry across epoch boundaries; nodes cannot silently confiscate a block-producing delegate's reward. Snapshot writes and pool writes both go through the standard state manager, so restart safety and Fork/Snapshot/Revert semantics apply automatically. The frozen `blockCommissionRate` in the pool entry protects orphans (delegates who dropped out of top-N) from having their split retroactively re-priced.
- **`DelegateDistributed` log payload bound**: The per-delegate batched log carries `voters[]` + `amounts[]` sized by the delegate's active voter count. Worst case at fork (~5,000 voters on the largest delegate, 21 bytes/addr + 8 bytes/amount) ≈ 145 KB per log — under the 256 KB soft cap for receipt logs. If a delegate ever exceeds `MaxLogPayloadBytes` (constant, default 200 KB), the emitter MUST split the batch into multiple `DelegateDistributed{seq, seqTotal, ...}` logs deterministically ordered by voter address. Off-chain verifiers concatenate by `seq` and check `sum(amounts) + commissionAmount` against the total per-delegate epoch payout.
- **Snapshot determinism**: The voter weight snapshot (§7.5), the commission-rate snapshot (§3.4), and the opt-in snapshot are all written per-candidate as proto blobs with deterministic field ordering. The "skip if bytes unchanged" write path is safe only because each encoding is a pure function of the sorted logical inputs; any implementation that changes the sort key or adds non-deterministic fields (e.g. iteration order of a map, wall-clock timestamp) would break this invariant and cause block-hash divergence.
- **Contract-read determinism**: `evm.SimulateExecution` against `DelegateProfile` and `AutoDeposit` is deterministic under a fixed state root — the same state height always yields the same return bytes. However, the calls MUST run against the pre-`PutPollResult` state root, not a live mid-block state; otherwise a rate change late in the last block of an epoch could be picked up inconsistently across replays. `SnapshotCommissionRates` runs at the beginning of `PutPollResult`, before any candidate list mutation, guaranteeing a stable read point.

## References

- [IIP-58: ioSwarm — Decentralized Execution Layer](https://github.com/iotexproject/iips/blob/main/iip-58.md)
- [Hermes v1 Source](https://github.com/iotexproject/iotex-hermes) — the centralized service being replaced
- [F1 Fee Distribution (Cosmos SDK)](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) — related reward distribution algorithm
- [IoTeX Staking Protocol](https://github.com/iotexproject/iotex-core/tree/master/action/protocol/staking) — existing on-chain staking state
- [IoTeX Rewarding Protocol](https://github.com/iotexproject/iotex-core/tree/master/action/protocol/rewarding) — existing reward distribution

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
