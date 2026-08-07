```
IIP: 59
Title: Protocol-Native Voter Reward Distribution
Author: Raullen Chai (@raullen), Chen Chen (@envestcc)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-20
Updated: 2026-08-07
```

## Simple Summary

Replace Hermes-managed off-chain voter rewards with deterministic protocol
distribution. Eligible delegates' voter portions accumulate in per-delegate
pools and are paid in bounded, voter-major chunks from bucket state frozen by
copy-on-write (COW).

## Abstract

At activation, delegates whose inherited reward address is a configured Hermes
vault migrate to on-chain reward distribution. Other delegates retain legacy
handling unless their owner enables on-chain distribution through a one-way
action. Commission rates continue to come from `DelegateProfile`.

Delegate commission is paid immediately and voter portions accumulate in
pending pools. At each reward-era boundary the protocol freezes per-delegate
scalars and bucket high-water marks and opens a COW era window. Later blocks
walk 256 voter-address shards, recompute each voter's native and contract
staking weight as of the freeze height, and pay at most
`VoterBudgetPerBlock` voters. Eligible voters compound into a native staking
bucket; all others receive a direct account credit. Finalization sweeps
residual and orphaned pools without burning funds.

## Motivation

Hermes currently holds operational keys, recomputes voter weights, claims
delegate rewards, and submits distributions outside consensus. Outages delay
rewards, calculation is not enforced by block validation, auditing depends on
off-chain behavior, and service fees reduce voter income. IIP-59 moves this
process into deterministic state transitions while bounding settlement work per
block. It does not change delegate selection, vote-weight formulas,
productivity, slashing, foundation bonuses, priority tips, or legacy handling
for delegates that do not migrate.

## Specification

Candidate identity, rather than mutable owner or operator address, keys all
IIP-59 state. A **reward era** contains `EpochsPerRewardEra` epochs; epoch `E`
is an era boundary when `E > 0` and `E % EpochsPerRewardEra == 0`. `H` denotes
the era's freeze height.

The following invariants apply throughout the specification:

- frozen mode, profile rates, weight denominator, owner destination, and
  settlement amount do not change during one settlement;
- weight numerators are derived only from bucket state as of `H`;
- payouts attributed to a delegate never exceed that delegate's frozen amount;
- rewards accruing after initialization remain in the live pool for a later
  settlement; and
- cursor movement, fund movement, destination or staking writes, and logs for
  one chunk are one atomic state transition.

### 1. Activation

Before the activation hardfork, rewarding behavior is unchanged. At and after
activation a candidate is in on-chain reward mode when:

```text
candidate.voterRewardOnchainOptIn ||
(
    !candidate.rewardAddressUpdated &&
    candidate.rewardAddress in genesis.hermesRewardVaultAddresses
)
```

`hermesRewardVaultAddresses` defaults to
`io19604a05s2p3mecam2zz7d27hcr6ndyw80wvkmh` and
`io12mgttmfa2ffn9uqvn0yn37f4nz43d248l2ga85`. Candidates registered after
activation, and candidates that update their reward address after activation,
set `rewardAddressUpdated = true` and do not migrate merely by selecting a
Hermes vault. Before changing an automatically migrated candidate's reward
address, the protocol sets `voterRewardOnchainOptIn = true` to preserve its
mode.

After activation, the candidate owner may submit
`SetVoterRewardOptIn(candidateIdentifier, true)`. The action is owner-only,
idempotent, and one-way; `optIn = false` is invalid. Mode changes take effect
when the next era snapshot is written and never rewrite an active era.

Settlement requires an owner-to-contract-bucket index. In the activation
block's pre-state phase, before actions and before any era window can open, the
protocol MUST scan the configured V1, V2, and V3 contract-staking bucket state
and any contract with a recorded high-water mark, then write owner references
in ascending address order. The index is maintained with later bucket
mutations. This one-time backfill has no repair marker or later retry and MUST
be benchmarked before selecting the activation height.

### 2. Reward Configuration and Destinations

For an on-chain delegate, delegate-directed rewards are paid immediately to
the current owner account and do not create rewarding `unclaimedBalance`.
Legacy delegates continue to receive the full reward at their stored reward
address through the existing claim path. Mode is frozen per era; owner changes
affect the on-chain destination, while reward-address changes affect only
legacy mode. Each non-zero direct delegate payout emits a
`CLAIM_FROM_REWARDING_FUND` transaction log from `RewardingPoolAddr` to the
owner.

Each voter has one global direct destination, defaulting to the voter account.
The voter-signed `SetVoterRewardDestination(recipient)` action is appended to
`ActionCore` at field 58. A 20-byte, non-zero recipient other than the voter
sets the sparse override; empty bytes, zero, or self clears it; every other
length is invalid. State records the recipient and last update height. The
effective destination is resolved when a chunk pays the voter, is not followed
recursively, and changing it affects only unprocessed payouts. Crediting a
contract account does not invoke its code.

Compound routing takes precedence over the direct destination. It is resolved
at payment time from the existing `AutoDeposit` contract as specified in
section 5.3.

The protocol reads `blockRewardPortion` and `epochRewardPortion` from the
existing `DelegateProfile` contract by candidate identity. Valid values are
voter portions in basis points in `[0, 10000]`:

```text
blockCommissionBps = 10000 - blockRewardPortion
epochCommissionBps = 10000 - epochRewardPortion
```

Both fields must be present and valid. Otherwise the snapshot records
`registered = false` and both rates as `10000`, paying 100% to the owner.
Profile changes take effect at the next snapshot.

### 3. Era Snapshot and COW Window

At `H`, the protocol writes one scalar snapshot for every on-chain candidate,
whether or not it is in the poll list:

| Field | Meaning |
|---|---|
| `blockCommissionBasisPoints`, `epochCommissionBasisPoints` | Frozen rates. |
| `registered`, `onchainRewardEnabled` | Frozen profile and mode flags. |
| `totalWeight` | Candidate `Votes` at `H`, used as the allocation denominator. |
| `freezeHeight` | `H`. |
| `selfStakeBucketIdx` | Self-stake bucket at `H`, or `MaxUint64`. |
| `snapshotHash` | Join key for partial distribution events. |

```text
snapshotHash = keccak256(
    keccak256("iip59.delegatedistributed.snapshot.v2") ||
    delegate[20] || uint64_be(freezeHeight) || uint256_be(totalWeight) ||
    uint64_be(selfStakeBucketIdx) ||
    uint64_be(blockCommissionBasisPoints) ||
    uint64_be(epochCommissionBasisPoints) || flags[1]
)
```

`totalWeight` is left-padded to 32 bytes. `flags` bit 0 is `registered` and bit
1 is `onchainRewardEnabled`. A zero `totalWeight` leaves the voter pool pending
for a future era.

The protocol opens one COW era window at `H` and seals it at settlement
completion. For every native or contract bucket value and voter-index key read
by weight recomputation, the first post-`H` mutation stores the pre-write value;
creation of a key absent at `H` stores a tombstone. A frozen read returns the
copy, absence for a tombstone, or the live value when no mutation occurred.
The window also freezes the native total bucket count and each contract bucket
high-water mark. A frozen read rejects a native index at or above the count and
a contract ID above its mark. Copies are reclaimed in bounded batches after
the window seals.

Voter weights use the existing native and contract staking formulas over these
as-of-`H` values and MUST be evaluated at the work item's `freezeHeight`, not
the chunk height. A work item without that height is skipped. The frozen
`totalWeight` is a path-dependent accumulator, so it need not equal the sum of
statelessly recomputed weights; section 5.2 defines the mandatory clamp.

### 4. Reward Accumulation

For reward amount `amount` and frozen rate `commissionBps`:

```text
commission = floor(amount * commissionBps / 10000)
voterShare = amount - commission
```

Rounding favors voters. A legacy delegate does not split its reward.

For an on-chain block producer, `GrantBlockReward` pays block commission and
the full priority tip to the current owner and adds the voter share to the
candidate's pending pool. For a legacy producer, base reward and tip follow the
existing rewarding balance path. `BLOCK_REWARD` reports the immediate
commission in on-chain mode and the full credit in legacy mode; zero commission
may produce no log.

At each epoch end, existing recipient selection, exemption, productivity,
probation, slashing, and weighting run unchanged. Each resulting on-chain epoch
amount is split using `epochCommissionBps`; commission is paid to the owner and
the voter share is added to the same pending pool. `EPOCH_REWARD` reports the
immediate commission in on-chain mode and the full amount in legacy mode.
Foundation bonuses retain their calculation and log format and go to the owner
in on-chain mode or stored reward address in legacy mode.

Pending pools are keyed by candidate identity and have a sorted index for
deterministic enumeration. They are rewarding-fund liabilities, are not
claimable address balances, and may receive newer rewards while an older frozen
amount is being settled.

### 5. Settlement

#### 5.1 Initialization and cursor

The snapshot is written at the poll update freeze height `H`; settlement is
initialized in `GrantEpochReward` at the boundary epoch's final block, and the
first continuation chunk runs in the next epoch. For each currently rewarded
on-chain candidate with a non-zero pool, the immutable plan freezes candidate
identity, voter amount, owner destination, epoch commission, total weight,
snapshot hash, freeze height, and self-stake bucket index. Rewards added after
initialization remain for a later settlement.

The singleton cursor has an immutable plan and mutable progress. The plan holds
the target era, work items, epoch window, seed, and start shard. Progress holds
completion status and height, `shardsDone`, `resumeVoter`, a per-work-item
distributed total, and a skip bitmap. `targetEra` MUST agree in both records;
short distributed vectors have a zero tail. A skipped item contributes no
shares and keeps its pool pending.

The plan is written once so advancing a shard does not rewrite the work list.
The pending pool itself is not frozen: a chunk debits only shares attributed to
the plan's frozen amount, while later block and epoch shares accumulate behind
it. Progress therefore carries one distributed total per work item, including
payments made earlier in the same block.

```text
settlementSeed = keccak256(
    bytes("iip59.settlement-start.v1") ||
    parentBlockHash[32] || uint64_be(targetEra)
)
startShard = uint256_be(settlementSeed) % 256
```

`parentBlockHash` is the boundary block's parent. Shards are visited as
`(startShard + n) mod 256`; candidate order is unchanged. The normal epoch
window is `[targetEra - EpochsPerRewardEra + 1, targetEra]`. `resumeVoter` is
the last visited address in the current shard and subsequent scans skip
addresses less than or equal to it. A completed cursor is retained until the
next boundary for queries but produces no more chunk actions.

#### 5.2 Voter enumeration and allocation

Every non-epoch-final block with an incomplete cursor includes a generated
`VoterRewardChunk` action. It merges, in address order, shard-bounded ranges
from the live native and contract owner indexes and their COW copies, then
deduplicates voters. It processes at most `VoterBudgetPerBlock` distinct voters
(`0` means unbounded), not `(delegate, voter)` pairs.

A fixed second bound proportional to the voter budget limits scanned index
keys. If that bound truncates a shard, the action pays only through the address
range covered by every input stream and resumes from that coverage bound. The
cursor advances past every visited voter, including zero-weight voters, and
increments `shardsDone` only after complete coverage of a shard.

For each voter `v` and unskipped work item `d`:

```text
weight = weight of v for d from buckets as of d.freezeHeight
share  = floor(d.voterAmountFrozen * weight / d.totalWeight)
share  = min(share, d.voterAmountFrozen - d.voterDistributed)
```

The last line is mandatory: recomputed weights may exceed the frozen
denominator, but payouts MUST NOT exceed the frozen pool. Shares are combined
into one voter payment while each delegate's pending pool and distributed total
advance by its own contribution. Zero combined payments emit no transfer or
distribution entry but still advance the cursor.

#### 5.3 Payment routing and accounting

A voter compounds the combined payment only when `AutoDeposit` returns a
non-zero configured bucket ID that exists in native staking state, is owned by
that voter, and is native, active, auto-staked, and not unstaked. The staking
protocol adds the amount to that bucket, moves it from the rewarding fund to
the staking bucket pool, and emits `DEPOSIT_TO_BUCKET` from `RewardingPoolAddr`
to `StakingBucketPoolAddr`. Contract buckets contribute weight but are not
valid compound destinations.

An absent or failed lookup, unreadable bucket, or ineligible bucket falls back
deterministically to a direct credit at the effective voter destination. Direct
payment creates no rewarding `unclaimedBalance` and emits
`CLAIM_FROM_REWARDING_FUND` from `RewardingPoolAddr`. Failure to apply an
otherwise valid compound deposit fails the state transition.

Each payment atomically decreases the contributing pending pools and rewarding
total balance, advances distributed totals, applies the account or staking
write, emits logs, and persists cursor progress.

#### 5.4 Finalization and overrun

After all 256 shards:

1. For each unskipped item, remove
   `residual = voterAmountFrozen - voterDistributed` from its pending pool,
   route it through the orphan sink, and set distributed equal to the frozen
   amount. Skipped items retain their pools.
2. For every indexed pool absent from the cursor, pay the live candidate owner
   when candidate state exists; otherwise return it to rewarding-fund
   `unclaimedBalance`. Delete the orphan's index entry. Residual and orphan
   payments emit `BLOCK_REWARD`.
3. Seal the era window, make its copies reclaimable, and mark the cursor
   complete with the current height. Pools are decremented rather than deleted
   when newer rewards accrued behind the cursor.

If an incomplete cursor survives to the next boundary, the protocol MUST NOT
halt. It emits `EPOCH_DRAIN_OVERRUN` with the old target era, number of named
delegates with a live balance, and their total live residue; deletes only the
cursor; and initializes a replacement from current pool balances while
preserving the oldest `startEpoch`. Opening the new era window seals the old
one, so network parameters MUST normally complete settlement before the next
freeze height.

### 6. Logs

Each chunk emits one EVM-compatible event per contributing delegate:

```solidity
event DelegateDistributed(
    uint64 indexed epoch,
    address indexed delegate,
    address rewardAddr,
    uint256 totalCommission,
    uint256 totalVoterPool,
    bytes32 snapshotHash,
    address[] voters,
    address[] recipients,
    uint256[] amounts,
    uint64[] compoundBucketIds,
    bool[] compounded
);
```

`epoch` is the chunk epoch; `delegate` is candidate identity; `rewardAddr` is
the owner frozen in the plan; `totalCommission` is the boundary epoch
commission; and `totalVoterPool` is the sum of this event's `amounts`. The five
arrays are parallel and describe each beneficiary, actual recipient,
delegate-level contribution, compound bucket, and route. Consumers MUST use
`compounded`, because bucket ID zero is valid. `snapshotHash` joins a
delegate's partial events across chunks. `amounts[i]` is this delegate's
contribution, not the voter's combined payment. For compound routes,
`recipients[i] = voters[i]` and `compoundBucketIds[i]` identifies the bucket.

Every chunk first emits `CURSOR_PROGRESS`, encoding
`targetEra:shardsDone:hex(resumeVoter):shardsRemaining` in its address field and
`"0"` as amount. `EPOCH_DRAIN_OVERRUN` encodes
`targetEra:delegatesRemaining` and the live residue. Successful configuration
actions emit:

```solidity
event VoterRewardOptInSet(bytes32 indexed candidateIdentifier, bool optIn);
event VoterRewardDestinationSet(
    address indexed voter,
    address oldRecipient,
    address newRecipient
);
```

`VoterRewardOptInSet` always carries `optIn = true`. For destination events,
old and new values are effective addresses. No append-only voter history is
stored in consensus state; receipts and these events are the historical record.
Implementations MAY expose pools, snapshots, cursor progress, destinations, and
latest settlement status through state APIs.

### 7. Parameters

| Genesis field | Default | Meaning |
|---|---:|---|
| `EpochsPerRewardEra` | 24 | Epochs between settlement initializations. |
| `VoterBudgetPerBlock` | 2000 | Distinct voters per chunk; zero is unbounded. |
| `HermesRewardVaultAddresses` | two legacy vaults | Automatic migration set. |
| `DelegateProfileContractAddress` | network-specific | Reward portions. |
| `AutoDepositContractAddress` | network-specific | Compound preferences. |

`EpochsPerRewardEra` MUST be non-zero and MUST be at least 2. Capacity SHOULD
satisfy:

```text
VoterBudgetPerBlock * availableContinuationBlocks
    >= expected distinct voters per settlement * safety factor
```

It MUST be benchmarked using distinct voters and representative mint and
validation hardware before activation. Index scans are additionally bounded by
a fixed, non-configurable multiple of `VoterBudgetPerBlock`.

## Rationale

### Hermes-targeted migration and one-way opt-in

Automatic migration follows the existing operational boundary: delegates whose
rewards already flow through a configured Hermes vault are the delegates for
which Hermes performs voter distribution. Other delegates keep their current
address and claim workflow instead of receiving an unrequested fork-time
change. A one-way opt-in prevents pending pools or active settlements from being
stranded by switching back to legacy mode. The all-to-owner profile fallback
also avoids assigning a voter portion that the delegate never configured.

### Candidate identity as the state key

Owner and operator addresses may change, whereas candidate identity is stable.
Using it for snapshots, profile lookup, pending pools, cursor entries, and
events prevents an ownership or operator rotation from splitting or stranding
a delegate's rewards.

### Recomputed weights and COW

A persistent `(delegate, voter)` weight table would have to be seeded by a
full-chain bucket scan, updated by every staking mutation, and frozen in full at
each era boundary. Its state and maintenance cost scale with delegate-voter
pairs, and a missed mutation hook can silently make the aggregate disagree with
the buckets from which it was derived.

IIP-59 instead commits the inputs needed to recompute weight: small
per-delegate scalars plus bucket and owner-index state as of `H`. Every node
derives the result from the same committed inputs. This removes the initial
seed and mutation-hook maintenance surface while keeping the source of truth in
staking state.

Historical or archive-state reads could expose the same height, but would make
consensus depend on node retention configuration. COW keeps the as-of-`H` value
inside ordinary committed state. It copies only keys first changed while the
window is open, while tombstones distinguish a key created after `H` from one
that existed at `H`. High-water marks bound the frozen bucket namespace and
prevent later creations from entering the settlement.

### Voter-major settlement

A delegate-major walk repeats destination lookup, routing, and balance writes
for every `(delegate, voter)` pair. Walking voters first combines all delegate
contributions into one payment per voter, so a voter supporting several
delegates receives one transfer and the expensive routing work scales with
distinct voters rather than pairs. A single voter budget therefore bounds the
main per-block cost directly; the scan-key bound also covers sparse indexes and
zero-weight entries that consume work without producing a payout.

Address shards make progress independent of a storage engine's iteration order
and keep the cursor compact. Rotating the starting shard avoids repeatedly
serving the same address prefix first if settlement reaches an era boundary.
The seed affects traversal order only, so it cannot change membership, weights,
commission, or total fund movement.

### Payout clamp and residual sweep

The frozen denominator is a path-dependent accumulator maintained by staking
handlers, while each numerator is recomputed statelessly from buckets. These
quantities can disagree, including around predicates such as self-stake
endorsement expiry that have no transaction at the moment they change.

The clamp makes any disagreement safe in direction: voters may be underpaid,
but rewarding-fund outflow cannot exceed the amount reserved for the delegate.
The residual sweep then restores accounting without selecting an arbitrary
"last voter" to absorb accumulator drift or floor-division dust. Assigning the
difference to such a voter would turn an accounting mismatch into a real
overpayment.

### Frozen plans and live pools

Accumulating voter portions over an era amortizes snapshot and routing work
while paying delegate commission immediately. Mode, rates, denominator, freeze
height, self-stake bucket, owner destination, and settlement amount are frozen
so a multi-block drain has stable inputs. The pending pool remains live so new
block and epoch rewards can accrue normally; because the cursor tracks only its
frozen amount, those newer rewards are unambiguously deferred to a later era.

### Direct payout and voter-selected routing

Direct account credit completes payment in one transition. Creating a second
per-voter rewarding balance would require another claim and retain state until
the voter acts. A single global destination supports custody, treasury, and tax
accounts without duplicating configuration per delegate, while sparse
overrides leave default users state-free.

Resolving destination and compound preference when the chunk executes gives
the voter control over unprocessed payouts without copying mutable routing data
into every snapshot. Distribution events record the beneficiary, actual
recipient, route, and compound bucket, preserving an auditable result after the
configuration changes.

## Backward Compatibility

Before activation and for non-migrated delegates, reward addresses, rewarding
balances, claims, and logs are unchanged. Automatically migrated or opted-in
delegates pay delegate portions to their owner, accrue voter portions in pending
pools, and pay voters directly or by native-bucket deposit. Pre-migration
rewarding balances remain claimable. Existing `DelegateProfile` and
`AutoDeposit` contracts remain the configuration sources; Hermes MUST stop
distributing post-fork rewards for automatically migrated delegates.

`ForwardRegistration` entries are not imported. A voter requiring a non-default
destination must configure it once. Historical post-activation distributions
are reconstructed from receipts and `DelegateDistributed`, not persistent
per-voter history.

## Security Considerations

Snapshots, COW entries, cursor seed, progress, and payouts are committed state,
so restart and reorganization replay deterministically. The seed is not
cryptographic randomness and MUST NOT affect eligibility, weight, commission,
or amount; it selects traversal order only.

For every delegate throughout settlement:

```text
sum(payouts from delegate) <= voterAmountFrozen
```

The clamp enforces this inequality. Chunk payments decrease both the pending
liability and rewarding total balance; finalization routes every residual or
orphan exactly once. Overrun recovery preserves existing pools and creates no
balance.

Only a voter-signed action changes that voter's direct destination. A recipient
receives no control over stake or future configuration, and no contract callback
is executed. Compound changes are atomic with rewarding accounting.

Both voters paid and index keys scanned are bounded. Snapshot size scales with
on-chain delegates, not voter pairs. The activation owner-index backfill is the
largest single-block operation and MUST fit the block budget. Contract reads
use committed EVM state with deterministic fallbacks; no consensus path uses an
off-chain service.

## Reference Implementation

[`iotexproject/iotex-core` PR #4953](https://github.com/iotexproject/iotex-core/pull/4953).
