```
IIP: 59
Title: Protocol-Native Voter Reward Distribution
Author: Raullen Chai (@raullen)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-20
Requires: IIP-58
```

## Simple Summary

Replace the centralized Hermes reward distribution service with protocol-native, automatic voter reward distribution. Delegates set a commission rate on-chain; the protocol distributes the remaining reward (both block reward and epoch reward) directly to voters proportional to their weighted votes.

## Abstract

IoTeX currently relies on **Hermes** — a centralized, off-chain service — to distribute delegate staking rewards to voters. Hermes claims a delegate's entire unclaimed balance (which includes both **block reward** and **epoch reward**) and splits it among voters off-chain. This proposal adds a `CommissionRate` field to the delegate registration and modifies **both** reward grant paths so that the same two streams are split automatically on-chain:

- **Block reward** accumulates into a per-delegate pending pool during the epoch and is distributed together with the epoch reward at the epoch's last block.
- **Epoch reward** is split with voters directly inside `GrantEpochReward()`.

When a delegate sets a commission rate, the protocol calculates each voter's proportional share using the existing vote weight formula and credits their reward account directly. Voters claim rewards via the existing `ClaimFromRewardingFund` action. Because the same two reward streams that Hermes distributed are covered, voter net income under IIP-59 matches (and slightly exceeds, due to zero service fees) the Hermes era at the same commission rate. Hermes is fully deprecated once all delegates migrate.

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

Add a `CommissionRate` field to the `Candidate` struct in the staking protocol:

```go
type Candidate struct {
    Owner              address.Address
    Operator           address.Address
    Reward             address.Address
    Identifier         address.Address
    Name               string
    Votes              *big.Int
    SelfStakeBucketIdx uint64
    SelfStake          *big.Int
    BLSPubKey          []byte
    CommissionRate     uint64  // NEW: basis points (0–10000), 0 = legacy (no auto-distribution)
}
```

- `CommissionRate = 0` (default): Legacy behavior — full epoch reward goes to delegate's reward account. Delegate uses Hermes or distributes manually.
- `CommissionRate > 0`: Protocol auto-distributes. Delegate receives `CommissionRate / 10000` of the epoch reward; the rest goes to voters proportionally.
- Maximum value: 10000 (100% — delegate keeps everything, voters get nothing).

### 2. New Action: `SetCommissionRate`

A new protocol action allows delegates to update their commission rate:

```go
type SetCommissionRate struct {
    Rate uint64  // basis points, 0–10000
}
```

**Constraints:**
- Only the candidate's `Owner` address can call this action
- Rate changes take effect at the **next epoch boundary** (not retroactively)
- Rate is stored in the candidate's on-chain state
- Gas cost: ~21,000 (simple state write)

### 3. Modified Reward Distribution

Both `GrantBlockReward()` and `GrantEpochReward()` are modified so that a delegate with `CommissionRate > 0` splits **the entire delegate-side reward flow** with voters — matching what Hermes distributed prior to this proposal (delegate's full unclaimed balance).

Because per-voter distribution is O(voters) work — expensive at 2,000+ voters — the protocol runs it only once per epoch, at the epoch's last block. Block rewards accumulate into a per-delegate pending pool during the epoch and are folded into the single epoch-end distribution call. This keeps per-block cost at O(1) while preserving voter economics.

#### 3.1 Block Reward Accumulation

`GrantBlockReward()` (currently: credit the block reward directly to the block producer's reward account) is modified:

```go
func (p *Protocol) GrantBlockReward(ctx context.Context, sm protocol.StateManager) (*action.Log, error) {
    // ... existing: resolve producer → candidate, calculate blockReward ...

    if delegate.CommissionRate > 0 {
        // NEW: accumulate to per-delegate pending pool; do NOT credit
        // the delegate's reward account yet. The pool drains at epoch end.
        return p.addPendingBlockReward(sm, delegate.Identifier, blockReward)
    }

    // Legacy: credit block reward to delegate's reward account immediately
    return p.creditRewardAccount(sm, delegate.Reward, blockReward)
}
```

**Pending pool storage.** A new per-delegate state key:

- Namespace: staking protocol
- Key: `pendingBlockReward || delegateIdentifier` (21 bytes; `delegateIdentifier` is the 20-byte candidate identifier address)
- Value: `*big.Int` (uncredited accumulated block rewards for this delegate; deleted when drained)

**Properties.**
- Each block does at most one state read + one state write to the pending pool. No per-voter work at block time.
- A delegate that produces blocks but exits the top-N before epoch end still has an entry in the pending pool. It is drained at epoch end (see §3.3).
- Commission rate changes mid-epoch have no effect on already-accumulated block rewards, because the rate applied at drain time is the epoch-frozen rate (the same rate applied to epoch reward, snapshotted at the previous epoch's `PutPollResult` — see §3.4).

#### 3.2 Epoch Reward Split

`GrantEpochReward()` is modified so the per-delegate reward is split with voters when `CommissionRate > 0`:

```go
// per-delegate loop inside GrantEpochReward
for _, delegate := range topDelegates {
    epochReward := calculateDelegateReward(delegate, totalVotes)

    // ── NEW: fold in this delegate's accumulated block rewards ──
    pending := p.drainPendingBlockReward(sm, delegate.Identifier)
    totalReward := new(big.Int).Add(epochReward, pending)

    if delegate.CommissionRate > 0 {
        // ── NEW: Auto-distribute to voters ──
        commission := totalReward * delegate.CommissionRate / 10000
        p.creditRewardAccount(sm, delegate.Reward, commission)

        voterPool := totalReward - commission
        buckets := p.getBucketsByCandidate(sm, delegate.Identifier)
        totalWeight := big.NewInt(0)
        for _, b := range buckets {
            if b.isActive() {
                totalWeight.Add(totalWeight, b.WeightedVotes())
            }
        }

        // Distribute to each voter proportionally, in a deterministic order
        distributed := big.NewInt(0)
        for _, b := range sortedByVoter(buckets) {
            if !b.isActive() {
                continue
            }
            voterShare := new(big.Int).Mul(voterPool, b.WeightedVotes())
            voterShare.Div(voterShare, totalWeight)
            p.creditRewardAccount(sm, b.Owner, voterShare)
            distributed.Add(distributed, voterShare)
        }

        // Rounding dust (< 1 Rau per voter) goes to delegate
        dust := new(big.Int).Sub(voterPool, distributed)
        if dust.Sign() > 0 {
            p.creditRewardAccount(sm, delegate.Reward, dust)
        }
    } else {
        // Legacy behavior: full combined reward to delegate
        p.creditRewardAccount(sm, delegate.Reward, totalReward)
    }
}
```

**Key properties:**
- Runs inside the protocol (Go code), not the EVM — **zero gas cost**
- Uses the existing `creditRewardAccount()` to credit each voter's unclaimed balance
- Vote weight calculation uses the same `CalculateVoteWeight()` as consensus
- Voter iteration is in canonical (sorted-by-address) order — see §3.4 for how the voter list itself is snapshotted deterministically
- Rounding dust (< 1 Rau per voter) goes to the delegate
- Only active buckets participate (unstaked/withdrawn buckets excluded)

#### 3.3 Draining Pending Pools for Non-Top-N Delegates

A delegate that produced blocks earlier in the epoch but exits the top-N (e.g. lost votes late in the epoch) still has a non-empty pending pool at epoch end. Leaving those funds stranded would silently confiscate block reward.

At the end of `GrantEpochReward()`, after the top-N loop runs, the protocol iterates the pending-pool namespace and drains any remaining entries:

```go
for _, entry := range p.allPendingBlockRewards(sm) {
    delegate := p.candidateCenter.GetByIdentifier(entry.Identifier)
    if delegate == nil {
        // Candidate deregistered mid-epoch — return funds to reserve pool.
        // (This is an edge case; standard behavior is that identifiers persist.)
        p.returnToReserve(sm, entry.Amount)
        continue
    }
    if delegate.CommissionRate > 0 {
        p.distributeToVoters(ctx, sm, delegate, entry.Amount)
    } else {
        p.creditRewardAccount(sm, delegate.Reward, entry.Amount)
    }
    p.clearPendingBlockReward(sm, entry.Identifier)
}
```

The pending-pool namespace is bounded by the total registered candidate count (~100), so this is a bounded scan, not O(all keys).

#### 3.4 Commission Rate and Voter Weight Snapshotting

To guarantee deterministic distribution (and prevent last-block stake manipulation), both the commission rate and the per-voter weight list are frozen at the **previous** epoch's `PutPollResult` (mid-epoch). Concretely, at `PutPollResult` time the protocol:

1. Copies each candidate's current `CommissionRate` into that epoch's poll-snapshotted candidate list (which `GrantEpochReward()` reads).
2. Writes a per-candidate blob of `(voter, weightedVotes)` pairs, sorted by voter address, keyed by candidate identifier.

`distributeToVoters()` reads the frozen voter list (not the live staking view) at epoch end. Any stake activity between `PutPollResult` and the epoch's last block does not shift this epoch's distribution — it takes effect at the following `PutPollResult`. This gives voters a roughly 1.5-epoch reaction window when a delegate raises its commission rate: the change takes effect at the next `PutPollResult` (mid-epoch) and applies to rewards in the epoch after that.

### 4. Voter Claim Flow

Voters claim accumulated rewards using the **existing** `ClaimFromRewardingFund` action. No change needed — their reward account balance now includes auto-distributed voter rewards in addition to any other rewards.

```
                    ┌─────────────────────────┐
                    │   Rewarding Protocol     │
                    │                          │
  Epoch end ───────►│  GrantEpochReward()      │
                    │    │                     │
                    │    ├─ Delegate commission │──► delegate.rewardAccount
                    │    │                     │
                    │    ├─ Voter₁ share        │──► voter₁.rewardAccount
                    │    ├─ Voter₂ share        │──► voter₂.rewardAccount
                    │    └─ Voter_N share       │──► voterN.rewardAccount
                    │                          │
                    └─────────────────────────┘

  Voter claims ────► ClaimFromRewardingFund()  ──► IOTX transferred to voter
```

### 5. Migration Plan

| Step | Action | Timeline |
|------|--------|----------|
| 1 | Deploy protocol upgrade with `CommissionRate` support | Hard fork |
| 2 | Delegates opt in: `SetCommissionRate(rate)` | Post-fork |
| 3 | Monitor auto-distribution for opted-in delegates | 1–2 weeks |
| 4 | Remaining delegates migrate | 2–4 weeks |
| 5 | Deprecate Hermes service | After all delegates migrate |
| 6 | Archive Hermes repositories | Final cleanup |

Delegates can opt in at their own pace. During the transition period:
- `CommissionRate = 0`: Legacy behavior — block reward is credited to the delegate's reward account per block; epoch reward is credited whole. Delegate uses Hermes or distributes manually.
- `CommissionRate > 0`: Protocol handles distribution of **both** block and epoch reward automatically.

**Rate mapping from Hermes era.** Because IIP-59 auto-distributes the same two reward streams that Hermes distributed (block + epoch), a delegate that ran Hermes at an effective X% take can migrate by setting `CommissionRate = X * 100` bps. No upward adjustment is needed to compensate for block reward, and voters' net income at least matches the Hermes era (in practice slightly higher, since IIP-59 charges no service fee).

### 6. ioctl Integration

New ioctl commands for delegates and voters:

```bash
# Delegate: set commission rate (10% = 1000 bps)
ioctl stake2 setcommission 1000

# Voter: check unclaimed rewards (already exists)
ioctl account nonce <address>

# Voter: claim rewards (already exists)
ioctl action claim <amount>
```

### 7. Skeleton Implementation

#### 7.1 Candidate State Extension (`action/protocol/staking/candidate.go`)

```go
// Candidate represents a delegate candidate
type Candidate struct {
    Owner              address.Address
    Operator           address.Address
    Reward             address.Address
    Identifier         address.Address
    Name               string
    Votes              *big.Int
    SelfStakeBucketIdx uint64
    SelfStake          *big.Int
    BLSPubKey          []byte
    CommissionRate     uint64  // basis points 0–10000; 0 = legacy (no auto-distribution)
}

// CommissionCut returns the delegate's commission from a given reward
func (c *Candidate) CommissionCut(reward *big.Int) *big.Int {
    if c.CommissionRate == 0 {
        return new(big.Int).Set(reward) // legacy: delegate keeps all
    }
    cut := new(big.Int).Mul(reward, big.NewInt(int64(c.CommissionRate)))
    cut.Div(cut, big.NewInt(10000))
    return cut
}
```

#### 7.2 SetCommissionRate Action Handler (`action/protocol/staking/handlers.go`)

```go
func (p *Protocol) handleSetCommissionRate(ctx context.Context, act *action.SetCommissionRate, sm protocol.StateManager) (*action.Receipt, error) {
    actCtx := protocol.MustGetActionCtx(ctx)
    blkCtx := protocol.MustGetBlockCtx(ctx)

    // Only candidate owner can set commission
    cand := p.candidateCenter.GetByOwner(actCtx.Caller)
    if cand == nil {
        return nil, errors.New("caller is not a registered candidate owner")
    }
    if act.Rate > 10000 {
        return nil, errors.New("commission rate exceeds 10000 bps")
    }

    // Clone and update — takes effect at next epoch boundary
    updated := cand.Clone()
    updated.CommissionRate = act.Rate

    if err := p.candidateCenter.Upsert(updated); err != nil {
        return nil, err
    }
    if err := p.putCandidate(sm, updated); err != nil {
        return nil, err
    }

    return p.settleAction(ctx, sm, protocol.SuccessReceiptStatus, nil,
        &action.Log{
            Address: p.addr.String(),
            Topics:  []hash.Hash256{hash.BytesToHash256([]byte("CommissionRateSet"))},
            Data:    byteutil.Uint64ToBytesBigEndian(act.Rate),
        },
    )
}
```

#### 7.3 Modified GrantBlockReward (`action/protocol/rewarding/reward.go`)

```go
func (p *Protocol) GrantBlockReward(ctx context.Context, sm protocol.StateManager) (*action.Log, error) {
    blkCtx := protocol.MustGetBlockCtx(ctx)
    featureCtx := protocol.MustGetFeatureCtx(ctx)

    // ... existing: read producer, resolve to delegate, compute blockReward ...

    if featureCtx.EnableVoterRewardDistribution && delegate.CommissionRate > 0 {
        // NEW: accumulate to per-delegate pending pool instead of crediting now.
        // The pool is drained and folded into the voter distribution in GrantEpochReward.
        if err := p.addPendingBlockReward(sm, delegate.Identifier, blockReward); err != nil {
            return nil, err
        }
        return &action.Log{
            Address: p.addr.String(),
            Topics:  []hash.Hash256{hash.BytesToHash256([]byte("BlockRewardPending"))},
            Data:    append(delegate.Identifier.Bytes(), blockReward.Bytes()...),
        }, nil
    }

    // Legacy path: credit delegate immediately.
    return p.creditRewardAccount(sm, delegate.Reward, blockReward)
}

// addPendingBlockReward reads the delegate's current pending pool, adds blockReward,
// and writes it back. State key: pendingBlockReward || delegate.Identifier (21 bytes).
func (p *Protocol) addPendingBlockReward(
    sm protocol.StateManager,
    delegateID address.Address,
    blockReward *big.Int,
) error {
    key := pendingBlockRewardKey(delegateID)
    var pool pendingBlockRewardPool
    switch _, err := sm.State(&pool, protocol.KeyOption(key)); errors.Cause(err) {
    case nil, state.ErrStateNotExist:
        // ok — nil-value or missing both start from zero
    default:
        return err
    }
    pool.Amount = new(big.Int).Add(pool.Amount, blockReward)
    _, err := sm.PutState(&pool, protocol.KeyOption(key))
    return err
}
```

#### 7.4 Modified GrantEpochReward (`action/protocol/rewarding/reward.go`)

```go
func (p *Protocol) GrantEpochReward(ctx context.Context, sm protocol.StateManager) ([]*action.Log, error) {
    blkCtx := protocol.MustGetBlockCtx(ctx)
    bcCtx := protocol.MustGetBlockchainCtx(ctx)
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
    for i, delegate := range topDelegates {
        epochReward := rewardPerDelegate[i]

        // Fold in this delegate's accumulated block rewards.
        pending, err := p.drainPendingBlockReward(sm, delegate.Identifier)
        if err != nil {
            return nil, err
        }
        totalReward := new(big.Int).Add(epochReward, pending)

        if delegate.CommissionRate > 0 {
            rewardLogs, err := p.distributeToVoters(ctx, sm, delegate, totalReward)
            if err != nil {
                return nil, errors.Wrap(err, "distribute to voters")
            }
            logs = append(logs, rewardLogs...)
        } else {
            // Legacy: full combined reward to delegate.
            if err := p.credit(sm, delegate.Reward, totalReward); err != nil {
                return nil, err
            }
        }
    }

    // Drain any pending pools left by delegates that produced blocks earlier but
    // exited the top-N before epoch end (see §3.3). Bounded by candidate count.
    drainLogs, err := p.drainOrphanPendingPools(ctx, sm)
    if err != nil {
        return nil, err
    }
    logs = append(logs, drainLogs...)
    return logs, nil
}

// distributeToVoters splits totalReward between the delegate's commission
// and the voter pool. Voter list and per-voter weights are read from the
// snapshot written at the previous epoch's PutPollResult (§3.4), not the
// live staking view.
func (p *Protocol) distributeToVoters(
    ctx context.Context,
    sm protocol.StateManager,
    delegate *state.Candidate,   // poll snapshot; carries frozen CommissionRate
    totalReward *big.Int,
) ([]*action.Log, error) {
    // 1. Delegate commission (rounded down)
    commission := delegate.CommissionCut(totalReward)
    if err := p.credit(sm, delegate.Reward, commission); err != nil {
        return nil, err
    }

    voterPool := new(big.Int).Sub(totalReward, commission)
    if voterPool.Sign() <= 0 {
        return nil, nil
    }

    // 2. Read the frozen voter list snapshotted at the previous PutPollResult
    stakingProtocol := staking.MustGetProtocol(protocol.MustGetRegistry(ctx))
    candIdentifier, err := address.FromString(delegate.Identity)
    if err != nil {
        return nil, err
    }
    voters, err := stakingProtocol.SnapshotVoterWeightsByCandidate(sm, candIdentifier)
    if err != nil {
        return nil, err
    }
    if len(voters) == 0 {
        // No voters snapshotted — full remainder to delegate.
        return nil, p.credit(sm, delegate.Reward, voterPool)
    }

    // 3. Total weight
    totalWeight := big.NewInt(0)
    for _, v := range voters {
        totalWeight.Add(totalWeight, v.Weight)
    }
    if totalWeight.Sign() == 0 {
        return nil, p.credit(sm, delegate.Reward, voterPool)
    }

    // 4. Distribute in the snapshot's canonical (sorted-by-voter) order
    distributed := big.NewInt(0)
    for _, v := range voters {
        share := new(big.Int).Mul(voterPool, v.Weight)
        share.Div(share, totalWeight)
        if share.Sign() > 0 {
            if err := p.credit(sm, v.Voter, share); err != nil {
                return nil, err
            }
            distributed.Add(distributed, share)
        }
    }

    // 5. Rounding dust to delegate
    dust := new(big.Int).Sub(voterPool, distributed)
    if dust.Sign() > 0 {
        if err := p.credit(sm, delegate.Reward, dust); err != nil {
            return nil, err
        }
    }

    return []*action.Log{{
        Address: p.addr.String(),
        Topics:  []hash.Hash256{hash.BytesToHash256([]byte("VoterRewardDistributed"))},
        Data: append(
            candIdentifier.Bytes(),
            append(commission.Bytes(), voterPool.Bytes()...)...,
        ),
    }}, nil
}
```

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

#### 7.7 Action Definition (`action/setcommissionrate.go`)

```go
package action

// SetCommissionRate is the action to set a delegate's commission rate
type SetCommissionRate struct {
    AbstractAction
    rate uint64
}

// NewSetCommissionRate creates a new SetCommissionRate action
func NewSetCommissionRate(rate uint64) *SetCommissionRate {
    return &SetCommissionRate{rate: rate}
}

// Rate returns the commission rate in basis points
func (s *SetCommissionRate) Rate() uint64 { return s.rate }

// IntrinsicGas returns the intrinsic gas for this action
func (s *SetCommissionRate) IntrinsicGas() (uint64, error) {
    return 10000, nil // minimal gas — simple state write
}

// Serialize returns the serialized bytes of the action
func (s *SetCommissionRate) Serialize() []byte {
    return byteutil.Uint64ToBytesBigEndian(s.rate)
}
```

#### 7.8 Protobuf Extension (`iotextypes/action.proto`)

```protobuf
// SetCommissionRate sets a delegate's voter reward commission rate
message SetCommissionRate {
    uint64 rate = 1;  // basis points, 0–10000
}

// Add to ActionCore.action oneof:
message ActionCore {
    // ... existing fields ...
    oneof action {
        // ... existing actions ...
        SetCommissionRate setCommissionRate = 60;
    }
}

// Add CommissionRate to CandidateInfo response:
message CandidateInfo {
    // ... existing fields ...
    uint64 commissionRate = 20;  // basis points
}
```

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

`CommissionRate = 0` preserves legacy behavior because:
- Some delegates have custom distribution arrangements with voters
- Forcing auto-distribution would break existing agreements
- Gradual migration is less risky than a hard switch

### Performance Impact

Two hot paths are affected: `GrantBlockReward` (every block) and `GrantEpochReward` (once per epoch).

**Per-block (`GrantBlockReward`).** Under IIP-59 the block reward is accumulated into a per-delegate pending pool instead of credited directly. Extra work per block: exactly one state read and one state write against a 21-byte key. No per-voter iteration. Overhead: sub-millisecond.

**Per-epoch (`GrantEpochReward`).** The per-voter distribution runs once per delegate at the epoch's last block:

- Top delegates have ~2,000–4,000 voters after the snapshot (§3.4)
- Total across all 36 delegates: ~40,000 voter credits per epoch
- Each iteration: 1 multiplication + 1 division + 1 state write
- One additional per-delegate call reads the snapshot blob (§7.5); the blob is a single `State()` read, not a loop over indices
- Total additional time: <10ms per epoch (negligible vs. 5-second block time)

**Per-PutPollResult (mid-epoch).** The snapshot writer walks all candidates (~100) and writes only the ones whose voter list changed. This adds one `State()` read + at most one `PutState`/`DelState` per candidate, run once per epoch. Overhead: a few milliseconds, dominated by proto marshal of changed blobs.

## Backwards Compatibility

- **Consensus change**: Yes — modifies both `GrantBlockReward()` and `GrantEpochReward()` output when `CommissionRate > 0`. Requires hard fork.
- **State schema change**: Yes — adds `CommissionRate` to `Candidate` struct, adds the per-delegate pending block reward pool, adds the per-candidate voter weight snapshot blob. Requires state migration.
- **Default behavior**: `CommissionRate = 0` preserves exact legacy behavior — block reward is credited per block, epoch reward whole. No existing delegate or voter is affected until the delegate explicitly opts in.
- **RPC compatibility**: Existing `ReadStakingData` APIs are unaffected. New `CommissionRate` field is added to `Candidate` query responses.
- **Hermes compatibility**: Hermes can continue operating for delegates with `CommissionRate = 0`. No conflict.
- **Restart safety**: The pending block reward pool and voter weight snapshot are persisted in state, so a node restart mid-epoch does not lose already-accumulated block rewards or the frozen voter list.

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

- Delegate raises commission from 500 → 2000 bps in epoch N, `SetCommissionRate` receipt lands before epoch N's `PutPollResult`
- Expected: epoch N's rewards still use 500 bps (already snapshotted). Epoch N+1 rewards use 2000 bps. A voter that unstakes in epoch N after `PutPollResult` is still counted in epoch N's distribution (snapshotted before the unstake) but not epoch N+1.

## Implementation

### Reference Implementation

A proof-of-concept bot demonstrating the core logic (voter weight calculation, proportional distribution) is available at:
- [`tools/voter-reward-poc/`](https://github.com/iotexproject/iotex-core/tree/master/tools/voter-reward-poc) — stateless tool that reads on-chain staking data, calculates voter weights, and generates reward distribution

### Protocol Changes Required

| File | Change |
|------|--------|
| `action/protocol/context.go` | Add `EnableVoterRewardDistribution` (or the equivalent `!NoVoterRewardDistribution`) feature flag |
| `action/protocol/staking/candidate.go` | Add `CommissionRate` (+ `CommissionRateLastEpoch`) field to `Candidate` struct |
| `action/protocol/staking/handlers.go` | Add `handleSetCommissionRate` action handler; wire voter-weight-view deltas into all stake-mutating handlers |
| `action/protocol/staking/voter_weight_view.go` | Incremental per-candidate sorted voter weight list backing the snapshot writer |
| `action/protocol/staking/voter_weight_snapshot.go` | Per-candidate blob writer/reader (§7.5), invoked from `PutPollResult` |
| `action/protocol/poll/util.go` | Call `snapshotCommissionRates` + `SnapshotVoterWeights` in `setCandidates` |
| `action/protocol/rewarding/voter_reward.go` | `distributeToVoters` implementation reading the snapshot |
| `action/protocol/rewarding/reward.go` | Modify `GrantBlockReward()` to route to pending pool; modify `GrantEpochReward()` to fold pending + call `distributeToVoters`; orphan pool drain |
| `state/candidate.go` | Add `CommissionRate` field to `state.Candidate` (poll snapshot) |
| `action/protocol/staking/staking_statereader.go` | Expose `CommissionRate` in candidate queries |
| `api/grpcserver.go` | Surface `CommissionRate` in gRPC responses |

### Activation

The protocol change is activated at a designated block height via the genesis configuration, following IoTeX's standard hard fork process.

## Security Considerations

- **Commission rate manipulation**: Rate changes are epoch-delayed, preventing mid-epoch manipulation. Voters can monitor rate changes via on-chain events and re-stake if needed.
- **Vote weight correctness**: Uses the exact same `CalculateVoteWeight()` function as consensus vote counting. No separate calculation path that could diverge.
- **Rounding attacks**: Total distributed ≤ total voter pool (guaranteed by integer division). Dust goes to delegate, not lost.
- **Reward account overflow**: Uses `*big.Int` arithmetic — no overflow possible.
- **Denial of service**: The per-epoch iteration is bounded by total bucket count (~40,000 across all delegates). Execution time is O(N) in the number of buckets, which is already bounded by the staking protocol.
- **Pending pool integrity**: Block rewards routed to the per-delegate pending pool are drained exactly once at epoch end — either by the top-N loop (§3.2) or by the trailing orphan-drain loop (§3.3). No path leaves a pool entry across epoch boundaries; nodes cannot silently confiscate a block-producing delegate's reward. Snapshot writes and pool writes both go through the standard state manager, so restart safety and Fork/Snapshot/Revert semantics apply automatically.
- **Snapshot determinism**: The voter weight snapshot (§7.5) is written per-candidate as a proto blob with voters sorted by address. The "skip if bytes unchanged" write path is safe only because the encoding is a pure function of the sorted logical list; any implementation that changes the sort key or adds non-deterministic fields (e.g. iteration order of a map) would break this invariant and cause block-hash divergence.

## References

- [IIP-58: ioSwarm — Decentralized Execution Layer](https://github.com/iotexproject/iips/blob/main/iip-58.md)
- [Hermes v1 Source](https://github.com/iotexproject/iotex-hermes) — the centralized service being replaced
- [F1 Fee Distribution (Cosmos SDK)](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) — related reward distribution algorithm
- [IoTeX Staking Protocol](https://github.com/iotexproject/iotex-core/tree/master/action/protocol/staking) — existing on-chain staking state
- [IoTeX Rewarding Protocol](https://github.com/iotexproject/iotex-core/tree/master/action/protocol/rewarding) — existing reward distribution

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
