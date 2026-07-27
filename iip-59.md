```
IIP: 59
Title: Protocol-Native Voter Reward Distribution
Author: Raullen Chai (@raullen), Chen Chen (@envestcc)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-20
Updated: 2026-07-21
Requires: IIP-58
Supersedes: (rev 1, rev 2 amendment)
```

## Simple Summary

Fold the Hermes off-chain reward-distribution service into the protocol. At each
epoch boundary, the protocol pays delegate commission immediately and credits
each opted-in delegate's voter share to a per-delegate pending pool. The pool is
drained over the following *reward era* (default 24 epochs) as a cursor-driven
system action, `GrantVoterRewardChunk`, executed on every non-epoch-boundary
block, bounded by two per-block caps (`VoterBudgetPerBlock`,
`CompoundBatchSize`). Compound (reinvest to an existing native bucket) is
resolved inline against the existing `AutoDeposit` contract. Migration is
per-delegate opt-in via a new `SetVoterRewardOptIn` action; delegates that do
not opt in retain full legacy behavior (Hermes continues to serve them).

## Abstract

IoTeX currently relies on **Hermes** — a centralized, off-chain service — to
distribute delegate rewards to voters. Hermes claims a delegate's unclaimed
balance (block + epoch reward) and splits it among voters off-chain, using two
production contracts as its source of truth:

1. **`DelegateProfile`** (mainnet `0xfa7f50866ac45d84adf54bc767c885f92750e258`)
   — per-delegate voter split percentages for each reward stream.
2. **`AutoDeposit`** (mainnet `io108ckwzlzpkhva7cnfceajlu7wu6ql5kq95uat9`)
   — per-voter compound preference (native bucket ID to reinvest into).

IIP-59 replaces Hermes's split logic with an in-protocol pipeline that reads
the same two contracts and applies the same math. The result is voter-net
income at or slightly above the Hermes rate (no service fee), with per-voter
payouts becoming consensus-verifiable events.

The pipeline splits work across three time scales:

- **Every block** — for opted-in producers, the base block reward is split
  into commission (immediate to `RewardAddress`) and voter share (credited to
  the delegate's pending block-reward pool). Non-opted-in delegates retain
  the legacy full-credit path.
- **Every epoch boundary (Phase A)** — the epoch reward is split per delegate.
  Commission is paid immediately; the voter share is added to the pool. A
  **frozen** work list of `(candidate, voter-total)` pairs is written into
  a persistent cursor.
- **Every non-epoch-boundary block until the pool drains (Phase B)** — the
  system action `GrantVoterRewardChunk` walks the cursor, paying up to
  `VoterBudgetPerBlock` voters per block, emitting one `DelegateDistributed`
  log per chunk, and advancing the cursor. Once all delegates in the frozen
  list are paid, the cursor is deleted.

A reward *era* is a run of `EpochsPerRewardEra` (default 24) epochs. Voter
distribution occurs at *era boundaries*, but blocks in between still emit
per-block commission and accrue their voter share into the pool, so a voter's
per-era share is the sum of one epoch grant plus (era length) blocks of
block-reward voter share. `snap.Entries` — the frozen voter weight list — is
computed at era-boundary `PutPollResult` (IIP-58 snapshot) and is byte-stable
for the entire drain, guaranteeing deterministic replay across chunks.

Because voter payouts are bounded per block, the protocol can safely support
delegates with up to 30 000 voters without any single block exceeding the
2.5 s consensus budget. When configured capacity is exceeded, the protocol
degrades gracefully: any voter share that could not drain before the next
era boundary is rolled into that era's pool rather than being dropped.

## Motivation

### The Hermes problem

Hermes is a centralized Go service (last updated 2022) that:

1. Runs a private key that must be authorized as `RewardAddress` for every
   opted-in delegate.
2. Reads `DelegateProfile` for per-stream commission rates.
3. Reads `AutoDeposit` for per-voter compound preferences.
4. Reads on-chain staking state to compute weighted voter shares.
5. Submits `ClaimFromRewardingFund` on behalf of delegates, then batches
   transfers to voters (or `AddDeposit` calls for compound targets).
6. Charges a service fee per distribution.

Failure modes today:

- **Central point of failure**: a Hermes outage delays voter payouts by
  hours to days; there is no consensus-level guarantee.
- **Off-chain trust**: the split math is not consensus-verified. Auditing
  requires a bespoke tool that recomputes what Hermes did.
- **Fee overhead**: distributing rewards costs voters approximately 5 % of
  gross income.
- **Operational drift**: as of 2022 no external contributor understands
  Hermes end-to-end; a rewrite is more risky than a protocol-side re-fold.

### Design constraints

The v3 design reflects four hard constraints that emerged during 5.5a/5.5b
implementation:

1. **Determinism.** All state that changes during voter payout must be
   recomputable byte-identically from `(SnapshotHash, cursor state,
   snap.Entries)`. This is why voter weights are frozen at era boundary
   and never re-read mid-era.

2. **Bounded block work.** A single block must never process more than
   `VoterBudgetPerBlock` voter payments (default 2000) or
   `CompoundBatchSize` delegate credits (default 500), whichever hits
   first. Both are genesis-config values gated on the feature fork.

3. **Per-item degrade over halt.** When a per-delegate operation fails
   (bad snapshot, missing candidate, contract revert on compound), the
   protocol skips that item and continues. The block is never halted.

4. **Legacy path preservation until universal opt-in.** Delegates who
   have not opted in must observe **identical** legacy behavior. The
   opt-in flag lives on the candidate record; the flag is captured into
   each era's poll snapshot, so mid-era opt-in changes do not fragment
   an ongoing distribution.

## Terminology

| Term | Definition |
|---|---|
| **Reward Era** | Run of `EpochsPerRewardEra` (default 24) consecutive epochs. Era `n` covers epochs `[n·24, n·24 + 24)`. |
| **Era Boundary** | The block that runs the last `PutPollResult` before era `n` begins — i.e., the last block of epoch `n·24 - 1`. This is where `snap.Entries` is frozen. |
| **Phase A** | `GrantEpochReward` execution at every epoch boundary block. Pays commission, updates fund, credits voter share to per-delegate pool, materializes cursor. |
| **Phase B** | `GrantVoterRewardChunk` execution at each non-epoch-boundary block while a cursor is live. Drains voter share from the pool to voters via inline compound/credit routing. |
| **Pending Block Reward Pool** | Per-delegate `*big.Int` state under `state.RewardingNamespace`, keyed by candidate identifier. Accumulates voter share from block rewards + epoch reward until drained by Phase B. |
| **Cursor** | Serialized `EpochDrainCursor` message stored in `state.RewardingNamespace`. Tracks `(TargetEra, DelegateIndex, VoterIndex, Delegates[])` between blocks. |
| **`snap.Entries`** | `[]CandidatePollSnapshotEntry`, one per voter, each `{Voter, Weight}`. Frozen at era boundary by `FreezePollSnapshot`. Immutable across the drain. |
| **DelegateProfile** | Existing on-chain contract; source of truth for per-delegate commission rates (block stream and epoch stream). |
| **AutoDeposit** | Existing on-chain contract; source of truth for per-voter compound preference (bucket ID). |
| **Opt-in** | Boolean flag on `Candidate`, `VoterRewardOnchainOptIn`. When true, IIP-59 distribution runs for that delegate; when false, all legacy paths are preserved. |

## Specification

### §1 Overview

The protocol pipeline is:

```
Every block:
  GrantBlockReward
    ├─ producer opted-in? split (commission, voterShare) via snap.BlockCommissionBasisPoints
    │  ├─ commission → RewardAddress (immediate)
    │  └─ voterShare → per-delegate pending block-reward pool
    └─ producer not opted-in? legacy: full amount → RewardAddress

Era-boundary block (also epoch-boundary):
  PutPollResult  → FreezePollSnapshot(era) → snap.Entries
  GrantEpochReward (Phase A)
    ├─ for each delegate:
    │  ├─ splitDelegateEpochReward → (commission, voterShare) via snap.EpochCommissionBasisPoints
    │  ├─ commission → grantToAccount(RewardAddress)   (EPOCH_REWARD log)
    │  └─ voterShare → creditPendingBlockRewardPool(candID)
    ├─ if any delegate has pool > 0: append to cursor.Delegates
    └─ persist cursor if len(Delegates) > 0

Non-era-boundary block (cursor live):
  CreatePostSystemActions emits GrantVoterRewardChunk
  GrantVoterRewardChunk (Phase B)
    ├─ delegateBudget = CompoundBatchSize
    ├─ voterBudget    = VoterBudgetPerBlock
    ├─ walk cursor.Delegates from cursor.DelegateIndex
    ├─ for each delegate:
    │  ├─ snap = load frozen entries
    │  ├─ startVoter = cursor.VoterIndex; endVoter = min(startVoter+voterBudget, len(snap.Entries))
    │  ├─ distributeVoterOnly(startVoter, endVoter)
    │  ├─ emit DelegateDistributed (window subset)
    │  ├─ decrement pending pool by window amount
    │  └─ advance cursor: paidLast ? (DelegateIndex++, VoterIndex=0) : VoterIndex=endVoter
    └─ if all drained: delete cursor
```

The rest of this specification defines each step.

### §2 Candidate Opt-In

#### 2.1 Candidate fields

The `staking.Candidate` protobuf gains three fields:

```proto
message Candidate {
  // ... existing fields ...
  bool     voterRewardOnchainOptIn        = 11;
  uint64   blockCommissionBasisPoints     = 12;
  uint64   epochCommissionBasisPoints     = 13;
}
```

- `voterRewardOnchainOptIn` — false by default. Controls whether IIP-59
  distribution runs for this delegate.
- `blockCommissionBasisPoints` — basis-point (bps) commission on block
  reward, 0–10 000. Default 0 (all to voters, but only if opted-in).
- `epochCommissionBasisPoints` — bps commission on epoch reward, 0–10 000.
  Default 0.

Two independent rates match the two streams Hermes reads today. Prior to
this proposal, `CommissionRate` was a single rate applied at claim time by
Hermes across both streams.

#### 2.2 `SetVoterRewardOptIn` action

A new transaction type is added:

```proto
message SetVoterRewardOptIn {
  bytes  candidate_identifier = 1;
  bool   opt_in               = 2;
  uint64 block_commission_bps = 3;
  uint64 epoch_commission_bps = 4;
}
```

Semantics:

- Signer must be the current `Owner` of the candidate identified by
  `candidate_identifier` (or, post-IIP-58, the delegate profile owner).
- Sets the three fields on the candidate record.
- Emits a `VoterRewardOptInChanged` receipt log with the new values.

Basis-point rates must satisfy `0 ≤ bps ≤ 10 000`. Reverts otherwise.

Alternative implementations may fold the same three fields into
`CandidateUpdate` instead of introducing a distinct action; the choice is
non-normative and does not affect the reward pipeline.

#### 2.3 Snapshot capture

At every `PutPollResult` (called per epoch), the current candidate list is
enumerated and, for each candidate, `voterRewardOnchainOptIn`,
`blockCommissionBasisPoints`, `epochCommissionBasisPoints`, and
`Registered` are copied into the poll snapshot under
`state.StakingNamespace`. This is the only place these fields are read from
the mutable candidate record; all downstream reward logic reads the frozen
snapshot.

Mid-epoch opt-in toggles take effect **the epoch after next**: an opt-in
transaction landing in epoch `N` is captured into the snapshot at the start
of epoch `N+1` and applied to the epoch reward at the end of epoch `N+1`.

### §3 Block-Reward Distribution (per block)

At every block, `GrantBlockReward` is called by the protocol runtime for the
block producer.

#### 3.1 Fund flow (opted-in producer)

```
totalBlockReward = adm.BlockReward
snap = staking.PollSnapshotFor(producer)
if snap != nil && snap.VoterRewardOnchainOptIn && snap.Registered:
    (commission, voterShare) = splitCommission(totalBlockReward, snap.BlockCommissionBasisPoints)
    fund.unclaimedBalance -= totalBlockReward
    account(rewardAddr).unclaimedBalance += commission
    pool(candidateIdentifier).credit(voterShare)
    emit BLOCK_REWARD (commission)   // legacy log format preserved for commission
    emit PENDING_POOL_CREDIT (voterShare, candidateIdentifier)  // new
else:
    // legacy path
    fund.unclaimedBalance -= totalBlockReward
    account(rewardAddr).unclaimedBalance += totalBlockReward
    emit BLOCK_REWARD (totalBlockReward)
```

#### 3.2 `splitCommission`

```
splitCommission(amount, bps) -> (commission, voterShare):
    commission  = amount * bps / 10_000       // integer floor division
    voterShare  = amount - commission
    return (commission, voterShare)
```

Dust from the floor division stays with the voter share (never with
commission), preserving the "voters at least break even against a
zero-fee Hermes" property.

#### 3.3 Pending block reward pool

Per-delegate state under `state.RewardingNamespace`, keyed by
`candidateIdentifier`. Supports:

- `credit(amount)` — additive; increments `unclaimed`.
- `decrement(amount)` — clamped to `unclaimed ≥ 0`. Used by Phase B when
  paying voters.
- `readTotal()` — used by Phase A when materializing the cursor.

The pool exists purely as an accounting sink. Its balance is a subset of
`fund.totalBalance` and never overpays; `Claim` cannot see this pool.

Pre-fork (`NoVoterRewardDistribution == true`), the pool code paths are
skipped; block reward goes entirely to `rewardAddr` per legacy.

### §4 Poll-Snapshot Freezing (era boundary)

#### 4.1 Era boundary predicate

```
IsEraBoundary(epochNum, epochsPerEra):
    return epochNum > 0 && (epochNum % epochsPerEra) == 0
```

The block that runs `PutPollResult` at the start of an era-boundary epoch
is the block that freezes the snapshot for the era that just ended.

#### 4.2 `FreezePollSnapshot`

Introduced in IIP-58 and extended by this proposal. Called from
`PutPollResult` when `IsEraBoundary` is true. Enumerates the candidate
list, and for each opted-in registered candidate:

- Reads the live `VoterWeightView` (per-delegate sorted voter weights).
- Materializes `[]CandidatePollSnapshotEntry` from the view.
- Serializes into the snapshot blob keyed by `candidateIdentifier`.

Non-opted-in candidates skip entry materialization; the snapshot still
carries their `VoterRewardOnchainOptIn=false` flag so downstream logic
can short-circuit correctly.

#### 4.3 `snap.Entries` layout

```proto
message CandidatePollSnapshotEntry {
  bytes voter  = 1;    // 20-byte address
  bytes weight = 2;    // big.Int serialized
}

message CandidatePollSnapshot {
  // ... commission bps, opt-in flag, registered flag ...
  repeated CandidatePollSnapshotEntry entries = 5;
  hash256 snapshot_hash                      = 6;
}
```

`entries` is sorted by `weight` descending, then by `voter` ascending as
tiebreaker, then trimmed to a chain-configured limit (currently
unlimited; the 30 000-voter design ceiling is an operational cap, not a
consensus cap).

`snapshot_hash` is `Keccak256(SerializeDeterministic(entries))` and is
emitted in every `DelegateDistributed` log so off-chain consumers can
reassemble partial chunks by `(SnapshotHash, delegate, epoch)`.

The snapshot is loaded via `staking.PollSnapshotFor(candID)`. It lives in
staking's namespace, not rewarding's, because staking is the ownership
domain.

### §5 Epoch-Reward Distribution — Phase A

#### 5.1 Trigger

`GrantEpochReward` is a protocol-generated system action at every epoch's
final block. Pre-fork behavior is preserved (single fund-decrement, no
per-delegate loop). Post-fork behavior is described here.

#### 5.2 Guard: cursor must not be live

The first check in Phase A (post-fork) reads the persisted cursor:

```
if !featureCtx.NoVoterRewardDistribution:
    existing = readEpochDrainCursor()
    if existing != nil:
        // cursor from the previous era failed to drain in time
        goto §10.2 (graceful degrade)
```

This is the only place where the "cursor pile-up" degrade path can enter;
see §10.2 for its semantics.

#### 5.3 Per-delegate loop

```
foundationBonusRecipients = pollForFoundationBonus()
epochAmt = adm.EpochReward
foreach delegate in activeDelegates:
    epochAmtForThisDelegate = split(epochAmt, votes[delegate])
    (commission, voterShare) = splitDelegateEpochReward(delegate, epochAmtForThisDelegate)

    grantToAccount(delegate.RewardAddress, commission)
    emit EPOCH_REWARD (commission)                     // legacy log preserved

    if voterShare.Sign() > 0:
        pool(candID).credit(voterShare)
        emit PENDING_POOL_CREDIT (voterShare, candID)  // new
```

`splitDelegateEpochReward` returns `(amount, 0)` for non-opted-in delegates
(legacy path: commission absorbs the whole share).

#### 5.4 Cursor materialization

After the per-delegate loop:

```
cursorEntries = []
foreach delegate in activeDelegates:
    total = pool(candID).readTotal()
    if total.Sign() > 0:
        cursorEntries.append({CandidateIdentifier: candID, VoterAmountFrozen: total})

if len(cursorEntries) > 0:
    cursor = EpochDrainCursor{
        TargetEra:     currentEra,
        DelegateIndex: 0,
        VoterIndex:    0,
        Delegates:     cursorEntries,
    }
    writeEpochDrainCursor(cursor)
```

The `VoterAmountFrozen` value is the pool total **at the moment Phase A
completes**. It captures block-reward accrual from the entire prior era
plus this epoch's voter share. It is used to allocate per-voter shares
(§6.5) but is **not** re-read from the pool during drain; the pool is
only decremented.

#### 5.5 Foundation bonus and slashing

Foundation-bonus grants and unproductive-delegate slashing are unchanged
from the legacy epoch grant; they run in the same `GrantEpochReward` call
before or after the per-delegate loop and emit their existing log formats.
Neither interacts with the pending pool.

### §6 Voter-Reward Chunk Distribution — Phase B

#### 6.1 System action

A new action type, `GrantVoterRewardChunk`, is a protocol-generated
system action with no user-visible parameters. Handler:

```go
func (p *Protocol) GrantVoterRewardChunk(
    ctx context.Context,
    sm protocol.StateManager,
) ([]*action.TransactionLog, []*action.Log, error)
```

Emits transaction logs (voter credits / autodeposit calls) and event logs
(one `DelegateDistributed` per delegate chunk in this call).

#### 6.2 Emission rule

`CreatePostSystemActions` — called by the block producer during
`PutBlock` — appends a `VoterRewardChunk` grant iff:

```
!featureCtx.NoVoterRewardDistribution
&& !IsEpochBoundaryBlock(blockHeight)
&& readEpochDrainCursor() != nil
```

The epoch-boundary block runs Phase A, not Phase B, even if the previous
era's cursor is still live (in which case §10.2 applies). Blocks on
which the cursor is nil emit nothing.

#### 6.3 Cursor advance semantics

```
delegateBudget = p.epochDrainChunkSize(ctx)   // 0 pre-fork; else CompoundBatchSize
voterBudget    = p.voterBudgetPerBlock(ctx)   // 0 pre-fork; else VoterBudgetPerBlock

remainingDelegates = delegateBudget
remainingVoters    = voterBudget

for i := cursor.DelegateIndex; i < len(cursor.Delegates); i++:
    work = cursor.Delegates[i]
    snap = staking.PollSnapshotFor(work.CandidateIdentifier)

    startVoter = cursor.VoterIndex
    total      = uint32(len(snap.Entries))
    endVoter   = total
    if voterBudget > 0 && startVoter+remainingVoters < total:
        endVoter = startVoter + remainingVoters

    (logs, paidLast, paidAmount) = distributeVoterOnly(
        work.CandidateIdentifier,
        snap,
        work.VoterAmountFrozen,       // full frozen amount, for share allocation
        startVoter, endVoter,         // payment window
    )
    decrementPendingBlockRewardPool(candID, paidAmount)

    if paidLast:
        cursor.DelegateIndex = i + 1
        cursor.VoterIndex    = 0
        if voterBudget > 0:
            remainingVoters -= (endVoter - startVoter)
        if delegateBudget > 0:
            remainingDelegates -= 1
            if remainingDelegates == 0: break
    else:
        // Mid-delegate stop — persist window advance, stop iteration
        cursor.VoterIndex = endVoter
        break

    if voterBudget > 0 && remainingVoters == 0: break

if cursor.DelegateIndex == len(cursor.Delegates):
    deleteEpochDrainCursor()
else:
    writeEpochDrainCursor(cursor)
```

`voterBudget == 0` means "unbounded"; `delegateBudget == 0` means the
same. Pre-fork both return 0, which produces a single-block drain
identical to the legacy path (which itself would have already run inside
`GrantEpochReward`).

Cursor deletion is the completion signal. The next block's
`CreatePostSystemActions` observes `cursor == nil` and stops emitting
`GrantVoterRewardChunk`.

#### 6.4 Window sizing

- `VoterBudgetPerBlock` (default 2000) — maximum voter payments per
  block. Sized to keep single-block work under ~500 ms of the 2.5 s
  block budget on reference hardware.
- `CompoundBatchSize` (default 500) — maximum distinct delegate chunks
  per block. Prevents pathological cases where thousands of tiny
  delegates each contribute one voter and per-delegate fixed overhead
  dominates.

Either cap can end a chunk. When one cap is hit, remaining work
carries forward via the cursor.

Both caps read from `genesis.Rewarding` and are gated behind
`NoVoterRewardDistribution` (§12). A value of 0 for either cap means
"disabled" and reproduces pre-5.5 behavior for that dimension.

#### 6.5 `distributeVoterOnly` — windowed payout

```go
func (p *Protocol) distributeVoterOnly(
    ctx    context.Context,
    sm     protocol.StateManager,
    candID []byte,
    snap   *CandidatePollSnapshot,
    frozenVoterAmount *big.Int,     // full pool total for allocation
    startVoter, endVoter uint32,    // payment window
) (logs []*action.Log, paidLast bool, paidAmount *big.Int, err error)
```

Behavior:

1. **Allocate over the full list.** Compute per-voter shares by weight:
   ```
   totalWeight = sum(snap.Entries[j].weight for j in [0, N))
   share[j]    = frozenVoterAmount * entries[j].weight / totalWeight
   ```
   Dust from truncation is added to the last positive-weight entry.
   This allocation is O(N) per chunk but is deterministic and identical
   across all chunks of the same delegate — a delegate split into K
   chunks yields byte-identical per-voter amounts to a single-chunk run.

2. **Pay the window.** For each `j ∈ [startVoter, endVoter)`:
   - Read `AutoDeposit(voter[j])` from the AutoDeposit contract.
     - If the voter has a registered bucket AND
       `bucket.Owner == voter[j] && bucket.AutoStake && bucket.Status == active`,
       call `bucket.AddDeposit(share[j])` — this is the "compound"
       route; append a `Route{voter, bucketID, share, kind=Compound}`
       to the chunk's routing list.
     - Otherwise, credit `share[j]` to
       `account(voter[j]).unclaimedBalance`; append
       `Route{voter, 0, share, kind=Credit}`.
   - Failures on individual voters (contract revert, bucket state
     race) fall through to the Credit route (per-item degrade,
     §10.1) and are logged as a warn event; the chunk is not aborted.

3. **Return.**
   - `paidLast = (endVoter == len(snap.Entries))`.
   - `paidAmount = sum(share[startVoter], share[startVoter+1], ..., share[endVoter-1])`.
   - `logs` includes the `DelegateDistributed` log for this chunk (§7).

### §7 `DelegateDistributed` Log

#### 7.1 Emission

Emitted once per delegate chunk inside `distributeVoterOnly`. A delegate
split across three chunks yields three `DelegateDistributed` logs, all
with identical `SnapshotHash`.

#### 7.2 Fields

```
event DelegateDistributed(
    uint64  indexed epoch,
    address indexed delegate,
    address         rewardAddr,
    uint256         totalCommission,
    uint256         totalVoterPool,
    bytes32         snapshotHash,
    address[]       voters,
    uint256[]       amounts,
    Route[]         routings
);

struct Route {
    uint8   kind;      // 1 = Compound (AutoDeposit AddDeposit), 2 = Credit
    uint256 bucketId;  // 0 for Credit
}
```

- `epoch` — the epoch during which Phase A ran (= the last epoch of the
  era being distributed).
- `delegate` — candidate identifier of this chunk.
- `rewardAddr` — the delegate's reward address at snapshot time.
- `totalCommission` — the commission amount paid at Phase A. Emitted in
  every chunk of a delegate for convenience; it is not the sum of any
  chunk-scoped data.
- **`totalVoterPool`** — **sum of `amounts[]` in this chunk only.** A
  delegate split into K chunks emits K `DelegateDistributed` logs whose
  `totalVoterPool` values sum to `work.VoterAmountFrozen`.
  Prior to this proposal (v2 amendment), `totalVoterPool` was the full
  frozen amount emitted once per delegate. Off-chain reassembly by
  `(SnapshotHash, delegate, epoch)` recovers the equivalent aggregate.
- `snapshotHash` — Keccak256 of the frozen `snap.Entries`, identical
  across all chunks of the same delegate.
- `voters`, `amounts`, `routings` — parallel arrays for the window
  `[startVoter, endVoter)`.

#### 7.3 Reassembly semantics

Off-chain consumers must aggregate by `(snapshotHash, delegate, epoch)`:

- `SUM(totalVoterPool) == work.VoterAmountFrozen` for a fully drained
  delegate.
- `CONCAT(voters[])` == first N entries of `snap.Entries.voter`, in
  order.
- `CONCAT(amounts[])` == deterministic per-voter allocation over the
  full frozen list.

Chunk order is guaranteed by block order — a later block cannot pay a
smaller `VoterIndex` window of the same delegate.

### §8 Compound Routing

The compound route (Route.kind = 1) reuses the existing `AutoDeposit`
contract. No separate compound-sweep phase exists — routing happens
inline for each voter as the window is paid.

#### 8.1 AutoDeposit lookup

The AutoDeposit interface exposed to the protocol is a Solidity contract
call:

```
autoDeposit.bucketFor(voter address) -> (uint256 bucketId, bool ok)
```

For each voter in the payment window:

1. Call `bucketFor(voter)`.
2. If `!ok`, route Credit.
3. If `ok`, look up native bucket `bucketId`.
   - If `bucket.Owner != voter` → Credit (bucket ownership changed).
   - If `!bucket.AutoStake` → Credit (auto-stake was toggled off).
   - If `bucket.Status != active` → Credit (bucket is unstaking or
     withdrawn).
   - Otherwise, call `native.AddDeposit(bucketId, share)` and route
     Compound.

The AutoDeposit contract itself is unmodified; the protocol is a new
consumer.

#### 8.2 Failure isolation

If `native.AddDeposit` reverts (e.g., because the bucket transitioned to
unstaking between snapshot and payout), the failure is caught, the route
is downgraded to Credit for that voter, and a warn log is emitted. The
chunk continues. This is the per-item degrade rule (§10.1) applied to
compound routing.

### §9 Cursor Persistence

#### 9.1 State layout

```
namespace = state.RewardingNamespace
key       = "epoch_drain_cursor"   // singleton
value     = SerializeDeterministic(EpochDrainCursor{...})
```

The cursor is a singleton across all delegates. Only one drain is in
flight at any time (era N-1's drain always completes — via graceful
degrade if necessary — before era N's Phase A materializes a new cursor).

#### 9.2 Protobuf

```proto
message EpochDrainDelegateWork {
  bytes candidate_identifier = 1;
  bytes voter_amount_frozen  = 2;   // big.Int
}

message EpochDrainCursor {
  uint64                            target_era     = 1;
  uint32                            delegate_index = 2;
  repeated EpochDrainDelegateWork   delegates      = 3;
  uint32                            voter_index    = 4;
}
```

- `target_era` — the era whose Phase A produced this cursor. Records
  provenance and is validated at drain time (mismatched target_era vs.
  observed era is a consensus error).
- `delegate_index` — index into `delegates` of the delegate currently
  being drained.
- `voter_index` — index into `snap.Entries` for the next voter to pay.
  Zero when starting a new delegate.
- `delegates` — the frozen work list from Phase A. Immutable across
  the drain.

#### 9.3 Erigon dual-storage

The state manager persists all rewarding state through the standard
`state.KeyValue` interface plus, for Erigon archive nodes, the
`systemcontracts.GenericValueContainer` bridge. `EpochDrainCursor`
implements `Encode()` and `Decode(GenericValue)` methods so archive
replay reads/writes deterministically.

### §10 Failure Handling and Graceful Degrade

#### 10.1 Per-item degrade principle

At any point in the pipeline where a per-delegate or per-voter operation
can fail (bad snapshot, missing candidate, AutoDeposit revert), the
protocol degrades that one item rather than aborting the block:

| Failure | Degrade action |
|---|---|
| Snapshot for candidate not found in Phase A | Skip that delegate; continue to next. Emit warn log. Voter share stays in fund (fund.totalBalance not decremented for this delegate). |
| Cursor references a candidate whose snapshot vanished | Skip and advance cursor: `DelegateIndex++`. Warn log. Pool for that candidate remains stranded until explicit cleanup. |
| AutoDeposit lookup or AddDeposit revert | Downgrade voter to Credit. Warn log. |
| Voter has zero weight in snap.Entries | Skipped by allocation (share = 0). |

The block is **never** halted by any of the above.

#### 10.2 Overrun handoff (cursor live at Phase A entry)

When the cursor from era `N-1` has not fully drained by the time era `N`'s
epoch-boundary block runs Phase A, the following procedure runs:

```
existing = readEpochDrainCursor()
if existing != nil:
    // 1. Finalize what remains: emit a receipt log describing residue.
    residue = sum(work.VoterAmountFrozen - pool(work.CandidateIdentifier).drained
                  for work in existing.Delegates[existing.DelegateIndex:])
    emit EPOCH_DRAIN_OVERRUN(era=existing.TargetEra, residue, remainingDelegates=len(existing.Delegates)-existing.DelegateIndex)

    // 2. Do NOT decrement the fund for the residue: the pending pool
    //    already holds it. The pool balance is a subset of fund.totalBalance.

    // 3. Drop the cursor. Residue is absorbed into the next era's pool
    //    via the normal Phase A credit path — new voter share is added
    //    on top of any stranded pool balance.
    deleteEpochDrainCursor()

    // 4. Continue Phase A normally for era N. When Phase A materializes
    //    a new cursor, its VoterAmountFrozen entries reflect the pool
    //    totals including residue from era N-1.
```

Key invariants:

- **No fund overpayment.** Residue is already inside the pending pool,
  which is a subset of `fund.totalBalance`. Rolling it into the next
  era's cursor does not double-decrement the fund.
- **Deterministic.** The residue value is computed from persisted state
  (pool balance vs. `VoterAmountFrozen`) — every validator computes the
  same value.
- **Voter economic effect.** Voters whose payout was in the residue
  window receive their share in the next era's drain instead. Their
  weight for that next era is the *new* era's frozen snapshot, so the
  share amount may differ slightly from what era `N-1` would have paid
  — this is documented as an acceptable trade for the operational
  safety of graceful degrade.
- **Observability.** The `EPOCH_DRAIN_OVERRUN` receipt log is the
  authoritative signal for off-chain monitoring. See §10.3.

The pre-v3 hard-fail semantic (`errors.Errorf("cursor unexpectedly live
at Phase A entry")`) is **removed**. Under this proposal, no consensus
error can be raised for cursor liveness; the degrade above is
consensus-legal.

#### 10.3 Off-chain observability

Two receipt logs make cursor pressure visible:

- `CURSOR_PROGRESS` (informational) — emitted at each `GrantVoterRewardChunk`
  execution with `(TargetEra, DelegateIndex, VoterIndex, DelegatesRemaining)`.
  Observability nodes track this over time; a plateau indicates a stuck
  cursor.
- `EPOCH_DRAIN_OVERRUN` — emitted only at overrun. Non-zero
  count over recent epochs indicates the configured capacity is too
  small for actual voter density (§11.4).

Both are non-consensus (info-only) logs and do not affect state.

### §11 Genesis Parameters

Under `genesis.Rewarding`:

| Field | Type | Default | Description |
|---|---|---|---|
| `EpochsPerRewardEra` | `uint64` | 24 | Number of epochs per reward era. |
| `VoterBudgetPerBlock` | `uint64` | 2000 | Max voter payments per block during Phase B. |
| `CompoundBatchSize` | `uint64` | 500 | Max distinct delegate chunks per block during Phase B. |

All three are read only when `NoVoterRewardDistribution == false`. When
that flag is true (pre-fork), the values are ignored and the legacy
single-block drain path runs.

#### 11.1 Capacity formula

The maximum voter population that can be drained in a single era is:

```
Capacity = VoterBudgetPerBlock × BlocksPerEra
BlocksPerEra ≈ EpochsPerRewardEra × BlocksPerEpoch
```

With defaults `VoterBudgetPerBlock=2000`, `EpochsPerRewardEra=24`, and
`BlocksPerEpoch≈720` (assuming 24 delegates × 30 blocks per delegate),
capacity ≈ `2000 × 17 280 = 34.56M` voter-payments per era. This
comfortably exceeds the 30 000-voter design ceiling × 100 delegates =
3M scenario.

Operators sizing the parameters should target:

```
Capacity ≥ (design_voter_count × delegate_count) × safety_factor
```

with `safety_factor ≥ 2` to leave headroom for bursty payment
distributions (compound routes cost more than credit routes; the O(N)
allocation loop per chunk sets a soft ceiling).

#### 11.2 Reference sizing

For mainnet at IIP-59 activation:

- 100 opted-in delegates × 100 average voters = 10 000 voter-payments
  per era → drains in ~5 blocks. Well within budget.
- Growth to 300 delegates × 300 voters = 90 000 voter-payments per
  era → drains in 45 blocks. Comfortable.
- Design ceiling 100 delegates × 30 000 voters = 3M voter-payments
  per era → drains in 1500 blocks (~62 minutes). Requires
  `EpochsPerRewardEra` ≥ 3 at defaults; today's 24-epoch era leaves
  16× headroom.

### §12 Feature Gating

#### 12.1 Feature flag

A single feature flag governs the entire pipeline:

```
featureCtx.NoVoterRewardDistribution : bool
```

- `true` (pre-fork) — legacy full-credit path. All post-fork code
  paths are skipped: no snapshot capture into rewarding, no per-delegate
  epoch split, no Phase B system action, no cursor persistence.
- `false` (post-fork) — pipeline as specified in §§2–10.

The flag is derived from the block context:

```
featureCtx.NoVoterRewardDistribution = !g.IsToBeEnabled(height)
```

No new named fork is introduced. The `ToBeEnabled` height is set by
governance ahead of activation and becomes the activation height of
IIP-59.

#### 12.2 Snapshot capture in staking

The staking-side snapshot extension (§4) is gated separately by
`featureCtx.EpochRewardSnapshotEntries` (introduced in IIP-58). Both
flags must be `true` for the reward pipeline to see `snap.Entries`. In
practice both flags flip at the same `ToBeEnabled` height.

#### 12.3 Pre-fork behavior preservation

Pre-fork, all functions defined in this proposal (`splitCommission`,
`splitDelegateEpochReward`, `runVoterDistributionChunk`,
`distributeVoterOnly`, cursor read/write) exist as no-ops or legacy
fallbacks:

- `splitDelegateEpochReward` returns `(amount, 0)` for every delegate
  pre-fork.
- `runVoterDistributionChunk` is not called (no cursor is ever
  materialized because Phase A skips its cursor-write branch).
- `voterBudgetPerBlock` and `epochDrainChunkSize` return 0.
- Block reward code path branches into legacy full-credit before it
  ever consults a poll snapshot.

Fund invariants (`unclaimedBalance ≤ totalBalance`) hold across the
transition — the pending pool balances are a subset of
`fund.totalBalance`, exactly like the per-address unclaimed balances
they supplement.

## Rationale

### Why per-era instead of per-epoch

An earlier design (v1) distributed voter share at every epoch boundary.
Two problems drove the pivot to per-era distribution:

1. **Block reward accrual amortization.** Block reward voter share is
   small per block (≤ 24 IOTX per opted-in producer) but arrives at every
   block. Draining it every epoch means a mostly-idle epoch grant path
   handles thousands of tiny credits. Drain per era, and the per-epoch
   grant handles at most one credit per delegate.

2. **Snapshot cost.** `snap.Entries` costs O(voters) to materialize.
   Recomputing at every epoch under an incremental view was too slow at
   30k voters. Once per era (with the view maintained incrementally
   between eras) is affordable.

### Why per-block chunking instead of per-epoch batch

An earlier v2 design paid all voters in the single epoch-boundary block.
At the 30k design ceiling that produced a single-block work item large
enough to exceed 2.5s on reference hardware, which is a consensus liveness
risk. Chunking to `VoterBudgetPerBlock` per block bounds the worst-case
block work.

### Why "delegate cap" AND "voter cap"

`CompoundBatchSize` (per-delegate cap) alone protects against a chain with
many small delegates: overhead per delegate (snapshot load, log emit) is
non-trivial. `VoterBudgetPerBlock` (per-voter cap) alone protects against
a chain with one huge delegate. Both caps are needed to cover both shapes.

### Why graceful degrade instead of hard-halt on overrun

Hard-halt violates the "per-item degrade over halt" principle (§10.1) at
the era boundary. A single misconfigured genesis parameter must not stop
mainnet block production. Rolling residue into the next era's pool is
economically neutral for validators and adds one deterministic branch to
Phase A; the alternative (halting the chain until governance intervenes)
is unacceptable.

### Why inline compound routing

An earlier v2 design introduced a separate Phase 3 `CompoundSweep`
performed hours after credit. Two issues:

1. **State complexity.** A `compound_pending_set` state was required and
   accumulated garbage on every failed compound; cleanup was manual.
2. **Voter surprise.** Voters could observe their unclaimed balance jump
   up (credit) then down (sweep) with no user-visible reason.

Inline routing at credit time keeps the state simpler and the voter
experience predictable, at the cost of ~15% more Phase B block work
(one contract call per voter). At the observed voter-per-delegate median
of ~100, this fits comfortably in the block budget.

### Why keep the DelegateProfile contract as source of truth

`DelegateProfile` is already the operator-facing source for commission
rates in the Hermes era. Delegates use existing frontends and back-office
processes to update it. Requiring them to instead learn a new on-chain
transaction (`SetVoterRewardOptIn`) for the *same* rate is friction that
delays opt-in. IIP-59 captures the rates from `DelegateProfile` at
`PutPollResult` and folds them into the poll snapshot, so the source of
truth is unchanged even as the enforcement mechanism moves on-chain.

## Backward Compatibility

Post-activation:

- **Delegates that have not opted in** observe zero change. Every
  `GrantBlockReward`, `GrantEpochReward`, `Claim` behaves as it did
  before. Hermes continues to operate on their behalf.
- **Delegates that opt in** see:
  - `RewardAddress` starts receiving *only* commission, not the full
    voter share. Their off-chain distribution scripts must be turned
    off; running them alongside IIP-59 would double-distribute.
  - The rewarding fund contract's `Claim` call no longer needs to be
    invoked on behalf of voters — voters observe their unclaimed
    balance grow directly, and can claim themselves via
    `ClaimFromRewardingFund`.
  - New per-chunk `DelegateDistributed` events replace off-chain
    reports.

Hermes-consuming dashboards continue to function during migration by
adding a filter: opted-in delegates' rewards are reported from
`DelegateDistributed` logs; non-opted-in delegates continue to be
reported from Hermes.

The two hard-migration risks:

1. **Simultaneous run.** If Hermes is not switched off for a delegate
   before their opt-in transaction lands, one epoch of double-payout
   is possible. Operational runbook (documented separately) coordinates
   opt-in with Hermes shut-off.

2. **Reward-address change.** A delegate whose `RewardAddress` is a
   contract that expects the full voter share (i.e., a Hermes-integrated
   contract) will silently receive only commission after opt-in. This
   is by design but requires operator awareness.

Hermes is deprecated once all mainnet delegates have opted in.
Governance decides the sunset date; IIP-59 does not schedule it.

## Security Considerations

### Consensus safety

The pipeline is fully deterministic. All inputs are on-chain state:
staking snapshot, cursor, pending pool balances, genesis parameters.
There is no external oracle, timer, or unbounded loop.

The bounded-work guarantee (§6.4) is enforced by the two per-block caps.
A malicious block producer cannot cause other validators to overrun the
2.5 s budget: `runVoterDistributionChunk` respects the caps regardless
of who produced the block.

### Fund conservation

`unclaimedBalance ≤ totalBalance` holds throughout:

- Block reward voter share moves `voterShare` from `fund.unclaimedBalance`
  into the pending pool, which itself is a subset of
  `fund.totalBalance`.
- Epoch reward voter share moves the same way.
- Phase B decrements the pending pool and either credits an unclaimed
  balance (Credit route) or transfers to a native bucket (Compound
  route). No new liability is created.
- The overrun handoff (§10.2) does not double-count: residue in the
  pending pool is not re-decremented from the fund; it is absorbed
  into the new cursor's per-delegate `VoterAmountFrozen`.

### Reorg safety

The cursor is written via the standard state manager (in the same
namespace as the rewarding fund) and is subject to standard state root
inclusion. A reorg that reverts Phase A also reverts the cursor
materialization; a reorg that reverts a Phase B block reverts that
chunk's payment and cursor advance. No manual reconciliation is
required.

### DoS surface

The `SetVoterRewardOptIn` action costs gas per invocation and modifies
one candidate record. The candidate registration gas schedule already
covers similar mutations. No new DoS vector is introduced.

`GrantVoterRewardChunk` is a protocol-generated system action; users
cannot submit it, so gas cost and rate limiting are not applicable.

### Compound-contract trust

The `AutoDeposit` contract remains third-party (deployed by the operator
who runs Hermes today) but its failure only downgrades voters to Credit
route via per-item degrade (§8.2). A malicious or bricked `AutoDeposit`
cannot halt or corrupt reward distribution.

### Snapshot integrity

`snap.Entries` is signed into the state root at era boundary via the
same state-tree machinery as staking buckets. A validator that produces
an incorrect snapshot fails root verification at the next block; the
chain halts on that peer only.

## Reference Implementation

The implementation lives across the following Go packages in
`iotexproject/iotex-core`:

- **`action/protocol/staking/`** — snapshot capture, `snap.Entries`
  materialization, `PollSnapshotFor`, opt-in flag on `Candidate`,
  `SetVoterRewardOptIn` action handler.
- **`action/protocol/rewarding/`** — Phase A (`GrantEpochReward`),
  Phase B (`GrantVoterRewardChunk`), cursor state (`epoch_drain_cursor.go`),
  per-delegate epoch split (`splitDelegateEpochReward`), windowed voter
  payout (`distributeVoterOnly`), pending pool
  (`pending_block_reward.go`), post-system-action emission
  (`CreatePostSystemActions`).
- **`action/protocol/rewarding/rewardingpb/`** — `EpochDrainCursor`
  and `EpochDrainDelegateWork` messages.
- **`action/protocol/rewarding/distributedlog/`** —
  `DelegateDistributed` ABI, event struct, encoder.
- **`blockchain/genesis/genesis.go`** — `EpochsPerRewardEra`,
  `VoterBudgetPerBlock`, `CompoundBatchSize`.
- **`action/protocol/context/context.go`** —
  `featureCtx.NoVoterRewardDistribution`.

The rollout is decomposed into PRs `iip-59/pr-1` through
`iip-59/pr-6` (mainnet activation). PR 6 is the activation PR and
must include:

- The `SetVoterRewardOptIn` action handler (§2.2).
- The overrun graceful-degrade path (§10.2), replacing the current
  hard-fail check at Phase A entry.
- The `EPOCH_DRAIN_OVERRUN` receipt log (§10.3).

## Appendix A: Change History

### v3 (this revision, 2026-07-21)

Complete restructure. All specification content is rewritten to match
the shipped implementation as of PRs 1 through 5.5b, with three
forward-looking sections describing planned changes for PR 6
(activation):

- **§2.2 `SetVoterRewardOptIn`** — action is specified; implementation
  is a PR 6 deliverable.
- **§10.2 Graceful degrade on cursor-live-at-Phase-A** — replaces the
  hard-fail present in the current codebase. Implementation is a PR 6
  deliverable.
- **§10.3 `EPOCH_DRAIN_OVERRUN` receipt log** — added as the
  observability primitive for overrun. Implementation is a PR 6
  deliverable.

Structural changes from v2:

- Consolidated v1 §§1–7 and v2 amendment §§8.1–8.8 into a single
  specification. The two-tier "here is what v1 said, here is how v2
  overrides" reading burden is removed.
- Cursor structure fully specified using the actual proto names
  (`EpochDrainCursor`, `EpochDrainDelegateWork`) rather than the v2
  placeholders (`VoterRewardEraCursor`).
- Action name specified as `GrantVoterRewardChunk` rather than the v2
  placeholder `GrantEraVoterReward`.
- Log name specified as `DelegateDistributed` (per chunk) rather than
  the v2 placeholder `EraVoterCredited` (per era).
- Log `TotalVoterPool` semantic explicitly redefined as chunk-scoped
  sum. Off-chain reassembly rule spelled out (§7.3).
- Phase A no longer folds commission through the pool; it pays
  commission immediately and credits only the voter share to the
  pool. This matches the v2 implementation and simplifies the fund
  accounting.
- Compound-sweep phase (v2 §8.8) removed. Compound is inline at
  credit time.
- Terminology section (§Terminology) added.
- Reference implementation section (§Reference Implementation) added,
  mapping specification sections to codebase directories.

### v2 (amendment, 2025-11)

Introduced era-based distribution. Superseded v1 §§3.2, 3.4 and the
per-epoch log format. Introduced the cursor mechanism. See prior
revision for the historical amendment text; all of its content is
now folded into v3 above.

### v1 (2026-03-20)

Original submission. Proposed per-epoch distribution, single-block
drain, `CompoundSweep` deferred phase, `SetVoterRewardOptIn` action.
Superseded by v2 (per-epoch → per-era) and v3 (deferred compound → 
inline compound; hard-fail → graceful degrade).
