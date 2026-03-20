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

Replace the centralized Hermes reward distribution service with protocol-native, automatic voter reward distribution. Delegates set a commission rate on-chain; the protocol distributes the remaining epoch reward directly to voters proportional to their weighted votes.

## Abstract

IoTeX currently relies on **Hermes** — a centralized, off-chain service — to distribute delegate staking rewards to voters. This proposal adds a `CommissionRate` field to the delegate registration and modifies the epoch reward grant logic to automatically distribute voter rewards on-chain. When a delegate sets a commission rate, the protocol calculates each voter's proportional share using the existing vote weight formula and credits their reward account directly. Voters claim rewards via the existing `ClaimFromRewardingFund` action. Hermes is fully deprecated once all delegates migrate.

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

### 3. Modified Epoch Reward Distribution

The `GrantEpochReward()` function in the rewarding protocol is modified:

```go
func (p *Protocol) GrantEpochReward(ctx context.Context, sm protocol.StateManager) error {
    // ... existing: identify top delegates, calculate total reward ...

    for _, delegate := range topDelegates {
        totalReward := calculateDelegateReward(delegate, totalVotes)

        if delegate.CommissionRate > 0 {
            // ── NEW: Auto-distribute to voters ──
            commission := totalReward * delegate.CommissionRate / 10000
            p.creditRewardAccount(sm, delegate.Reward, commission)

            voterPool := totalReward - commission
            buckets := p.getBucketsByCandidate(sm, delegate.Owner)
            totalWeight := big.NewInt(0)

            // Calculate total weighted votes
            for _, b := range buckets {
                if b.isActive() {
                    totalWeight.Add(totalWeight, b.WeightedVotes())
                }
            }

            // Distribute to each voter proportionally
            distributed := big.NewInt(0)
            for _, b := range buckets {
                if !b.isActive() {
                    continue
                }
                voterShare := new(big.Int).Mul(voterPool, b.WeightedVotes())
                voterShare.Div(voterShare, totalWeight)
                p.creditRewardAccount(sm, b.Owner, voterShare)
                distributed.Add(distributed, voterShare)
            }

            // Rounding dust goes to delegate
            dust := new(big.Int).Sub(voterPool, distributed)
            if dust.Sign() > 0 {
                p.creditRewardAccount(sm, delegate.Reward, dust)
            }
        } else {
            // Legacy behavior: full reward to delegate
            p.creditRewardAccount(sm, delegate.Reward, totalReward)
        }
    }
}
```

**Key properties:**
- Runs inside the protocol (Go code), not the EVM — **zero gas cost**
- Uses the existing `creditRewardAccount()` to credit each voter's unclaimed balance
- Vote weight calculation uses the same `CalculateVoteWeight()` as consensus
- Rounding dust (< 1 Rau per voter) goes to the delegate
- Only active buckets participate (unstaked/withdrawn buckets excluded)

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
- `CommissionRate = 0`: Hermes continues (legacy behavior)
- `CommissionRate > 0`: Protocol handles distribution automatically

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

#### 7.3 Modified GrantEpochReward (`action/protocol/rewarding/reward.go`)

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
        delegateReward := rewardPerDelegate[i]

        // ── NEW: Check for auto-distribution ──
        if delegate.CommissionRate > 0 {
            rewardLogs, err := p.distributeToVoters(ctx, sm, delegate, delegateReward)
            if err != nil {
                return nil, errors.Wrap(err, "distribute to voters")
            }
            logs = append(logs, rewardLogs...)
        } else {
            // Legacy: full reward to delegate
            if err := p.credit(sm, delegate.Reward, delegateReward); err != nil {
                return nil, err
            }
        }
    }
    return logs, nil
}

// distributeToVoters splits a delegate's epoch reward between commission and voters
func (p *Protocol) distributeToVoters(
    ctx context.Context,
    sm protocol.StateManager,
    delegate *staking.Candidate,
    totalReward *big.Int,
) ([]*action.Log, error) {
    // 1. Calculate delegate commission
    commission := delegate.CommissionCut(totalReward)
    if err := p.credit(sm, delegate.Reward, commission); err != nil {
        return nil, err
    }

    voterPool := new(big.Int).Sub(totalReward, commission)
    if voterPool.Sign() <= 0 {
        return nil, nil
    }

    // 2. Get all active buckets for this delegate
    stakingProtocol := staking.MustGetProtocol(protocol.MustGetRegistry(ctx))
    buckets, err := stakingProtocol.GetActiveBucketsByCandidate(sm, delegate.Owner)
    if err != nil {
        return nil, err
    }

    // 3. Calculate total weighted votes
    totalWeight := big.NewInt(0)
    type bucketWeight struct {
        owner  address.Address
        weight *big.Int
    }
    weights := make([]bucketWeight, 0, len(buckets))
    for _, b := range buckets {
        w := staking.CalculateVoteWeight(b, false) // false = not self-stake for weight calc
        totalWeight.Add(totalWeight, w)
        weights = append(weights, bucketWeight{owner: b.Owner, weight: w})
    }

    if totalWeight.Sign() == 0 {
        // No active voters — full reward to delegate
        return nil, p.credit(sm, delegate.Reward, voterPool)
    }

    // 4. Distribute proportionally
    distributed := big.NewInt(0)
    for _, bw := range weights {
        share := new(big.Int).Mul(voterPool, bw.weight)
        share.Div(share, totalWeight)
        if share.Sign() > 0 {
            if err := p.credit(sm, bw.owner, share); err != nil {
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
            delegate.Owner.Bytes(),
            append(commission.Bytes(), voterPool.Bytes()...)...,
        ),
    }}, nil
}
```

#### 7.4 GetActiveBucketsByCandidate Helper (`action/protocol/staking/protocol.go`)

```go
// GetActiveBucketsByCandidate returns all non-unstaked buckets for a delegate
func (p *Protocol) GetActiveBucketsByCandidate(
    sm protocol.StateReader,
    candidateOwner address.Address,
) ([]*VoteBucket, error) {
    // Read bucket indices for this candidate
    indices, err := p.candBucketIndices(sm, candidateOwner)
    if err != nil {
        return nil, err
    }

    var active []*VoteBucket
    for _, idx := range indices.indices() {
        b, err := p.getBucket(sm, idx)
        if err != nil {
            continue // bucket may have been withdrawn
        }
        // Skip unstaked buckets
        if b.UnstakeStartTime != nil && !b.UnstakeStartTime.IsZero() {
            continue
        }
        active = append(active, b)
    }
    return active, nil
}
```

#### 7.5 Action Definition (`action/setcommissionrate.go`)

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

#### 7.6 Protobuf Extension (`iotextypes/action.proto`)

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

Commission rate changes take effect at the next epoch boundary, not immediately. This prevents a delegate from:
1. Setting 0% commission to attract voters
2. Switching to 100% right before epoch reward distribution
3. Switching back to 0%

Epoch-boundary enforcement gives voters time to react to rate changes.

### Why Not Mandatory Auto-Distribution

`CommissionRate = 0` preserves legacy behavior because:
- Some delegates have custom distribution arrangements with voters
- Forcing auto-distribution would break existing agreements
- Gradual migration is less risky than a hard switch

### Performance Impact

Iterating over voter buckets during `GrantEpochReward`:
- Top delegates have ~2,000–4,000 buckets
- Total across all 36 delegates: ~40,000 buckets
- Each iteration: 1 multiplication + 1 division + 1 state write
- Total additional time: <10ms per epoch (negligible vs. 5-second block time)
- Memory: bucket data is already loaded by the staking protocol

## Backwards Compatibility

- **Consensus change**: Yes — modifies `GrantEpochReward()` output. Requires hard fork.
- **State schema change**: Yes — adds `CommissionRate` to `Candidate` struct. Requires state migration.
- **Default behavior**: `CommissionRate = 0` preserves exact legacy behavior. No existing delegate or voter is affected until the delegate explicitly opts in.
- **RPC compatibility**: Existing `ReadStakingData` APIs are unaffected. New `CommissionRate` field is added to `Candidate` query responses.
- **Hermes compatibility**: Hermes can continue operating for delegates with `CommissionRate = 0`. No conflict.

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

## Implementation

### Reference Implementation

A proof-of-concept bot demonstrating the core logic (voter weight calculation, proportional distribution) is available at:
- [`tools/voter-reward-poc/`](https://github.com/iotexproject/iotex-core/tree/master/tools/voter-reward-poc) — stateless tool that reads on-chain staking data, calculates voter weights, and generates reward distribution

### Protocol Changes Required

| File | Change |
|------|--------|
| `action/protocol/staking/candidate.go` | Add `CommissionRate` field to `Candidate` struct |
| `action/protocol/staking/handlers.go` | Add `handleSetCommissionRate` action handler |
| `action/protocol/rewarding/reward.go` | Modify `GrantEpochReward()` to distribute to voters |
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

## References

- [IIP-58: ioSwarm — Decentralized Execution Layer](https://github.com/iotexproject/iips/blob/main/iip-58.md)
- [Hermes v1 Source](https://github.com/iotexproject/iotex-hermes) — the centralized service being replaced
- [F1 Fee Distribution (Cosmos SDK)](https://drops.dagstuhl.de/storage/01oasics/oasics-vol071-tokenomics2019/OASIcs.Tokenomics.2019.10/OASIcs.Tokenomics.2019.10.pdf) — related reward distribution algorithm
- [IoTeX Staking Protocol](https://github.com/iotexproject/iotex-core/tree/master/action/protocol/staking) — existing on-chain staking state
- [IoTeX Rewarding Protocol](https://github.com/iotexproject/iotex-core/tree/master/action/protocol/rewarding) — existing reward distribution

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
