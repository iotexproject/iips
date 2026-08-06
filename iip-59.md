```
IIP: 59
Title: Protocol-Native Voter Reward Distribution
Author: Raullen Chai (@raullen), Chen Chen (@envestcc)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-20
Updated: 2026-08-06
```

## Simple Summary

Replace Hermes-managed off-chain voter rewards with a protocol-native,
deterministic reward pipeline. At activation, delegates whose existing reward
address is one of the configured Hermes vaults migrate automatically. Other
delegates retain legacy reward handling unless their owner explicitly enables
on-chain distribution. For migrated delegates, voter rewards accumulate in
per-delegate pools and are distributed in bounded chunks to voter-selected
account destinations or eligible compound staking buckets.

## Abstract

IoTeX delegates currently rely on Hermes to claim protocol rewards, apply
delegate-configured reward portions, and distribute the voter portion.
IIP-59 moves that work into consensus.

At activation, delegates using either configured Hermes vault as their legacy
reward address switch to on-chain voter reward distribution. Delegates using
another reward address remain on the legacy claim path and may switch later
through a one-way, owner-authorized action. The existing `DelegateProfile`
contract remains the source of block-reward and epoch-reward voter portions
for on-chain delegates. If a delegate has no complete registered profile,
both streams default to 100% delegate commission, paid directly to its owner.

The protocol performs distribution in five named stages:

1. **Reward Accumulation** - block and epoch voter portions for on-chain
   delegates enter a per-delegate pending pool, while delegate commission is
   paid immediately to the owner.
2. **Settlement Initialization** - at a reward-era boundary, the protocol
   freezes each delegate's era parameters as scalars, opens a copy-on-write
   window over the state the weights are computed from, derives one
   parent-hash-based settlement seed, and creates a persistent settlement
   cursor.
3. **Chunked Voter Distribution** - subsequent blocks walk the voter address
   space in 256 shards, paying at most `VoterBudgetPerBlock` distinct voters
   per block. Each voter's weight is recomputed on demand, as of the freeze
   height, from the copy-on-write window.
4. **Settlement Finalization** - the last chunk sweeps per-delegate residuals
   and orphaned pools, seals the copy-on-write window, and marks the cursor
   complete, retaining it until the next settlement.
5. **Overrun Recovery** - if a settlement reaches the next reward-era
   boundary, its remaining pools are carried into a newly initialized
   settlement instead of halting the chain.

Voters without an eligible compound bucket receive IOTX directly in their
primary account or an explicitly selected reward account and do not need a
separate claim. Voters with an eligible native staking bucket receive the
reward as an added bucket deposit; compound routing takes precedence over the
direct reward-account selection.

## Motivation

Hermes is a centralized service outside consensus. It holds operational keys,
recomputes staking weights, claims delegate rewards, submits transfers or
staking deposits, and publishes an off-chain accounting result. This creates
several problems:

- A Hermes outage delays voter rewards.
- Reward calculations are not enforced by block validation.
- Auditing requires reproducing off-chain data and service behavior.
- Distribution fees reduce voter income.
- Delegate reward-address configuration is coupled to an external service.

IIP-59 makes the same economic process deterministic and verifiable from chain
state, receipts, and transaction logs. The design also bounds work per block so
large voter populations cannot make one settlement block exceed the consensus
time budget.

## Goals

- Migrate rewards previously managed through the configured Hermes vaults to
  consensus at activation.
- Allow other delegates to enter on-chain distribution explicitly without
  changing their legacy behavior by default.
- Preserve the existing `DelegateProfile` reward portions.
- Include voting weight from protocol-supported native and contract staking.
- Support voter-selected direct payout destinations and native-bucket
  compounding.
- Make every allocation reconstructable from frozen state and receipt logs.
- Bound voter processing per block.
- Preserve rewarding-fund accounting across partial and failed settlements.
- Expose settlement state through both native `ReadState` and Web3 reads.

## Non-Goals

- Changing how block producers or epoch-reward recipients are selected.
- Changing the staking vote-weight formula.
- Changing productivity probation, unproductive-delegate slashing, foundation
  bonuses, or priority-tip economics.
- Adding compound support for contract-staking buckets.
- Forcing delegates not using a configured Hermes vault to migrate.
- Replacing the legacy rewarding claim path for delegates that do not migrate.

## Terminology

| Term | Definition |
|---|---|
| **Candidate identity** | Stable candidate identifier used as the key for IIP-59 state. It is not the operator address, which may change. |
| **Reward era** | A configured run of `EpochsPerRewardEra` epochs between voter settlements. |
| **Era boundary** | An epoch `E` for which `E > 0` and `E % EpochsPerRewardEra == 0`. |
| **On-chain reward mode** | Protocol-native split and voter distribution. Delegate-directed rewards are paid directly to the current owner. |
| **Legacy reward mode** | Existing behavior in which the full reward is credited to the stored reward address's rewarding balance and must be claimed. |
| **Pending voter pool** | Per-candidate balance containing voter portions not yet distributed. |
| **Voter snapshot** | Frozen per-delegate scalars for one reward era: profile rates, reward mode, total voter weight, freeze height, self-stake bucket index, and a digest of all of them. It contains no per-voter list. |
| **Freeze height** | The block height `H` at which a reward era's voter snapshots are written. Every voter weight the settlement pays against is evaluated as of `H`, whatever block the payment runs in. |
| **Era window** | The copy-on-write window opened at `H` and sealed when the settlement completes. It preserves the as-of-`H` value of every key the weight recompute reads. |
| **Address shard** | One of 256 partitions of the voter address space, selected by the first byte of the voter address. |
| **Settlement seed** | Domain-separated hash that deterministically selects the first address shard visited in one settlement. |
| **Settlement cursor** | Persistent progress record for a multi-block voter distribution, split into an immutable plan and a mutable progress record. |
| **Voter reward destination** | Account selected by a voter for direct payouts. With no explicit selection, this is the voter account. |
| **Direct payout** | Transfer from the rewarding protocol to the effective voter reward destination. No later claim is required. |
| **Compound payout** | Transfer from the rewarding protocol to an eligible native staking bucket owned by the voter. |

## Specification

### 1. Activation and Migration Eligibility

IIP-59 is activated by a hardfork height. Before the activation height, the
legacy rewarding behavior is unchanged. Candidate state contains two migration
markers:

```proto
message Candidate {
  // Existing fields omitted.
  bool voterRewardOnchainOptIn = 11;
  bool rewardAddressUpdated = 12;
}
```

At and after activation, on-chain reward mode is enabled when:

```text
candidate.voterRewardOnchainOptIn ||
(
    !candidate.rewardAddressUpdated &&
    candidate.rewardAddress in genesis.hermesRewardVaultAddresses
)
```

`hermesRewardVaultAddresses` identifies the legacy vaults from which Hermes
distributed voter rewards. The default list contains:

```text
io19604a05s2p3mecam2zz7d27hcr6ndyw80wvkmh
io12mgttmfa2ffn9uqvn0yn37f4nz43d248l2ga85
```

The automatic rule applies only to reward addresses inherited from before the
fork. A candidate registered after activation, or a candidate that explicitly
updates its reward address after activation, has `rewardAddressUpdated = true`
and is not automatically migrated merely because that address equals a Hermes
vault.

A candidate owner may submit `SetVoterRewardOptIn(candidateIdentifier, true)`
after activation. The action is owner-only, idempotent, and one-way. An action
with `optIn = false` is invalid, so a migrated candidate cannot return to the
legacy path. If an automatically migrated candidate later updates its reward
address, the protocol first records `voterRewardOnchainOptIn = true` to preserve
its current mode.

Migration eligibility is evaluated when the protocol writes the next poll
snapshot. Consequently, an explicit opt-in takes economic effect with that
snapshot rather than rewriting rewards already governed by the current one.

For an on-chain delegate, registered `DelegateProfile` portions are enforced
by the protocol. An unregistered, incomplete, malformed, or unreadable profile
defaults to 100% delegate commission and zero voter portion. A delegate that
does not meet either migration condition remains entirely on the legacy path;
its profile and voter snapshot are not used.

The feature context exposes the inverse gate
`NoVoterRewardDistribution`. The IIP-59 path is active when that value is
`false`.

#### 1.1 Contract-staking owner index backfill

Settlement enumerates voters by address (section 8), so it needs an index from
owner address to the contract-staking buckets that owner holds. Native staking
already maintains such an index. Contract staking does not: its buckets are
keyed by bucket ID, and the owner is a field inside the bucket. The protocol
therefore builds a contract-staking owner index and maintains it from then on
alongside every bucket mutation.

The index is built exactly once, in the block whose height equals the
activation height, before any action in that block executes. For each
contract-staking contract — the configured V1, V2, and V3 contracts plus any
contract carrying a recorded bucket high-water mark — the protocol scans that
contract's bucket state once, accumulates the owner-to-bucket references in
memory, and writes them in ascending owner-address order. The same scan
establishes each contract's frozen bucket high-water mark.

This is a single-block operation. The bucket population it must enumerate is
bounded by the deployed contract-staking supply, which is small relative to the
native bucket set; a network MUST confirm the actual population against the
activation-block budget before setting the activation height.

The index MUST be written before any era window can open. Ordering guarantees
this: the backfill runs in the block's pre-state phase, while a window can only
be opened by an action in the same or a later block, and no window can exist
before the activation height at all because the gate that opens one is the same
gate that enables IIP-59.

No persistent completion marker is required. The activation block is executed
by every node that syncs from genesis, and a node that starts from a snapshot
taken after it inherits the finished index. Because the index is built once and
never rebuilt, a node MUST NOT treat a later block as an opportunity to repair
it.

### 2. Reward Destinations

#### 2.1 Delegate reward destination

The destination depends on the frozen reward mode:

- **On-chain mode:** all delegate-directed rewards are paid immediately to the
  candidate's current owner account. They do not create a rewarding
  `unclaimedBalance` and require no claim action. The stored legacy reward
  address is not used for newly generated rewards.
- **Legacy mode:** the full block reward, priority tip, epoch reward, and
  foundation bonus are credited to the candidate's stored reward address using
  the existing rewarding balance. The recipient must submit the existing claim
  action to move those funds to its account.

An ownership change therefore changes the direct destination for an on-chain
delegate. A reward-address update changes the destination only for a delegate
that remains in legacy mode. Mode selection itself is frozen in each
`CandidatePollSnapshot`, so a configuration change does not alter an active
reward era or settlement.

Every non-zero direct delegate payout emits a transaction log with:

```text
type      = CLAIM_FROM_REWARDING_FUND
sender    = RewardingPoolAddr
recipient = candidate owner
amount    = direct delegate reward
```

The log describes an immediate protocol outflow and does not represent a claim
transaction submitted by the owner.

#### 2.2 Voter direct reward destination

Each voter has one global direct reward destination. With no explicit
configuration, the effective destination is the voter account itself. A voter
changes it by submitting the following voter-signed rewarding action after
IIP-59 activation:

```text
SetVoterRewardDestination(recipient)
```

Its action payload is appended to `ActionCore` at field number 58:

```proto
message SetVoterRewardDestination {
  bytes recipient = 1;
}
```

The EVM-compatible form is:

```solidity
function setVoterRewardDestination(address recipient);
```

Only the transaction signer changes its own destination; one account cannot
configure another voter. A 20-byte non-zero recipient different from the voter
creates or replaces the override. An empty native recipient, the zero address,
or the voter's own address clears the override and restores the voter account
as the effective destination. Any other byte length is invalid.

Overrides are sparse rewarding state keyed by:

```text
"vrd" || voter[20]
```

The stored value contains the 20-byte recipient and the block height of the
last set operation. Clearing deletes the record; consequently an unset or
cleared destination reports `explicitlySet = false` and `updatedHeight = 0`.
The state/read representation is:

```proto
message VoterRewardDestination {
  bytes recipient = 1;
  bool explicitly_set = 2;
  uint64 updated_height = 3;
}
```

The successful action emits:

```solidity
event VoterRewardDestinationSet(
    address indexed voter,
    address oldRecipient,
    address newRecipient
);
```

The protocol resolves the effective destination when the voter's chunk entry
executes. A change therefore affects any direct payout that has not yet been
processed, including an active settlement, but never rewrites a completed
payout. The destination is not frozen in the voter snapshot or settlement
cursor.

Compound routing has precedence. If the voter has an eligible compound bucket,
the reward is deposited into that voter-owned bucket and the direct destination
is ignored for that payout. If compound lookup is absent, fails, or resolves to
an ineligible bucket, the fallback direct payout uses the effective destination
at that block. Crediting a contract account changes its account balance only;
it does not invoke receiver code or a callback. Resolution is one level only:
the recipient's own voter reward destination, if any, is not followed.

### 3. Reward Portions from DelegateProfile

The protocol reads two fields from the existing `DelegateProfile` contract,
keyed by candidate identity:

- `blockRewardPortion` - voter portion of the base block reward;
- `epochRewardPortion` - voter portion of the delegate's epoch reward.

Both values are basis points in `[0, 10000]`. The protocol converts the raw
voter portions to commission rates:

```text
blockCommissionBps = 10000 - blockRewardPortion
epochCommissionBps = 10000 - epochRewardPortion
```

A profile is registered for IIP-59 only when both fields are present and
valid. If either field is absent, a value is out of range, or a per-delegate
profile read cannot be decoded, the snapshot records `registered = false` and
both commission rates are `10000`. This fallback is deterministic and sends
the full base reward streams directly to the candidate owner.

Profile rates are frozen at the next era snapshot. A profile update does not
change rewards already accumulating under the current snapshot.

### 4. Era Snapshot and the Era Window

The protocol does not maintain, and does not commit, an aggregated
`(candidate identity, voter)` weight table. Voter weights are recomputed on
demand during settlement, from the same bucket state and the same weighting
rules the staking and poll protocols already use, covering both native staking
and contract staking. What consensus commits is not the weights but the
conditions under which they are computed: a per-delegate scalar snapshot, and a
copy-on-write window that makes the underlying state readable as of one height
for as long as the settlement runs.

#### 4.1 Per-delegate era snapshot

At the era boundary the protocol writes one `CandidatePollSnapshot` per
**opted-in** candidate, taken from the candidate set rather than from the poll
list. A candidate that is not in on-chain reward mode gets no record at all; an
absent record and a record with `onchainRewardEnabled = false` are equivalent to
every consumer, so the protocol writes neither for a legacy delegate. The height
at which these records are written is the freeze height `H`.

```proto
message CandidatePollSnapshot {
  uint64 blockCommissionBasisPoints = 1;
  uint64 epochCommissionBasisPoints = 2;
  bool registered = 3;
  bool onchainRewardEnabled = 4;
  reserved 5, 8, 9;   // entries, lastWeightedIndex, hasWeightedEntries
  bytes totalWeight = 6;
  bytes snapshotHash = 7;
  uint64 freezeHeight = 10;
  uint64 selfStakeBucketIdx = 11;
}
```

The snapshot is scalars only:

- `onchainRewardEnabled` freezes mode selection for the reward era.
- `totalWeight` is the frozen value of the candidate's `Votes` accumulator at
  `H`. It is the denominator every voter share is divided by. `totalWeight == 0`
  means the delegate has no payable voter set for this era.
- `freezeHeight` is `H` itself, carried with the snapshot rather than
  re-derived; section 4.3 explains why it must travel.
- `selfStakeBucketIdx` is the candidate's self-stake bucket index at `H`, or
  `MaxUint64` for none. It is the only candidate field the weight recompute
  reads, so it is frozen as a scalar instead of the whole candidate record.
- `snapshotHash` is a digest of the frozen parameters. It is the join key
  off-chain consumers use to assemble the partial `DelegateDistributed` logs one
  settlement emits across many blocks.

```text
snapshotHash = keccak256(
    keccak256("iip59.delegatedistributed.snapshot.v2") ||
    delegate[20] ||
    uint64_be(freezeHeight) ||
    uint256_be(totalWeight) ||
    uint64_be(selfStakeBucketIdx) ||
    uint64_be(blockCommissionBasisPoints) ||
    uint64_be(epochCommissionBasisPoints) ||
    flags[1]
)
```

`flags` has bit 0 set when `registered` and bit 1 set when
`onchainRewardEnabled`. `totalWeight` is left-padded to 32 bytes. The domain
separator is `v2`, not `v1`: `v1` scoped a digest over the frozen
`(voter, weight)` list, a preimage of an entirely different shape, and bumping
it keeps the two domains disjoint rather than relying on the layouts never
colliding.

Reserved field numbers 5, 8, and 9 previously held the materialized per-voter
entry list, the index within it that absorbed floor-division dust, and a flag
distinguishing a valid index 0 from an empty list. All three are properties of a
list that no longer exists. They MUST NOT be reused.

If an on-chain delegate has `totalWeight == 0`, its voter pool remains pending
for a later era. It is not redirected to delegate commission.

#### 4.2 The era window

Settlement recomputes weights from bucket state over several blocks *after* `H`,
and it mutates that state itself: a compound payout grows the very bucket whose
weight a later chunk would measure. Without protection, a voter paid in the
first chunk would change the weights of voters paid in later chunks, and the
era's split would stop being a function of the state at `H`.

The protocol therefore opens a copy-on-write **era window** at `H` and seals it
when the settlement completes. While the window is open:

- The first mutation of any covered key copies that key's pre-write value aside,
  tagged with `H`. Later mutations in the same era find a copy present and leave
  it alone. Only the first write is captured, which is what makes the copy the
  as-of-`H` value rather than the as-of-last-mutation value.
- A key that did not exist at `H` and is created afterwards is recorded as a
  tombstone. Absence at `H` is as consensus-relevant as presence, and without a
  tombstone a read as of `H` would fall through to the live value and see a
  bucket the era never had.
- A read as of `H` resolves to the copy when one exists, to a
  "did not exist" result when a tombstone exists, and to the live value
  otherwise — correct because "no copy" means "not mutated since `H`".
- Two monotonically increasing quantities are frozen as scalars instead of
  being copied per key: the native total bucket count and each contract's
  bucket high-water mark. A read as of `H` rejects a native bucket whose index
  is at or above the frozen count, and a contract bucket whose ID is above the
  frozen high-water mark.

Copies are journaled under a dense per-era sequence, so reclaiming them after
the window seals is a bounded walk rather than a range scan, and can be spread
across later blocks without leaving the state unbounded.

The window is gated on activation. Before the activation height no window can
exist and the layer performs no reads and no writes, so pre-fork execution is
unchanged. Between one settlement completing and the next era boundary there is
no window either, and the per-mutation cost is a single small control-key read.

#### 4.3 On-demand weight recomputation

During settlement, one voter's weight for one delegate is computed from the
buckets that voter holds with that delegate, read through the era window and
evaluated at that delegate's own `freezeHeight`.

The evaluation height MUST be `freezeHeight` and MUST NOT be the height of the
block the chunk runs in. A contract-staking bucket that is not
timestamp-based measures its remaining duration against a block height, so
substituting the current height would make the same bucket worth different
amounts in the first and last chunks of a single settlement. The copy-on-write
window alone cannot fix this; only carrying `H` can. A work item that reaches
settlement without a freeze height MUST be skipped rather than evaluated at a
substitute height.

The recompute is stateless: it reads buckets and the frozen
`selfStakeBucketIdx`. The denominator, `totalWeight`, is not — it is the frozen
value of a path-dependent accumulator that every staking handler adds to and
subtracts from. A stateless recompute and a path-dependent accumulator can
disagree, so the sum of recomputed weights is not guaranteed to equal
`totalWeight`. Section 8.1 specifies the clamp that makes every such
disagreement an under-payment rather than an over-payment.

### 5. Reward Split

For an on-chain delegate and a non-negative reward amount with a commission
rate in basis points:

```text
commission = floor(amount * commissionBps / 10000)
voterShare = amount - commission
```

Rounding therefore favors voters. The delegate never receives division dust.

The split rate comes from the latest frozen voter snapshot. If no usable
profile rate is available, the commission rate is `10000`. A legacy delegate
does not execute this split: its complete reward follows the legacy path.

### 6. Reward Accumulation

#### 6.1 Base block reward

On every block after activation, `GrantBlockReward` resolves the producer by
candidate identity and reads its frozen reward mode.

The base block reward is split as follows:

```text
commission -> current owner account immediately
voterShare -> pending voter pool[candidate identity]
```

Priority tips are fee income and are paid in full directly to the owner. They
are not included in the voter split.

For a legacy delegate:

```text
base block reward + priority tip -> stored reward address's rewarding balance
```

The legacy recipient must claim this balance using the existing rewarding
action.

For an on-chain delegate, the `BLOCK_REWARD` reward log reports the immediate
block commission and a zero commission may produce no reward log. For a legacy
delegate, it reports the full amount credited to the rewarding balance. The
on-chain pending voter share is later attested by `DelegateDistributed` events.

#### 6.2 Epoch reward

On the last block of every epoch, `GrantEpochReward` first applies the existing
recipient selection, vote-weight, exemption, productivity, probation, and
slashing rules. Each resulting on-chain delegate epoch amount is then split:

```text
commission -> current owner account immediately
voterShare -> pending voter pool[candidate identity]
```

The voter share accumulates every epoch, not only at era boundaries. For an
on-chain delegate, the `EPOCH_REWARD` reward log reports the immediate epoch
commission. For a legacy delegate, it reports the full epoch amount credited to
the rewarding balance.

For a legacy delegate, the complete post-slashing epoch amount is credited to
the stored reward address's rewarding balance and remains claimable through the
existing action. No voter pending pool is created.

Unproductive-delegate slashing remains independent of IIP-59. Slashed value
moves from the staking bucket pool back to the rewarding pool, and the existing
probation-adjusted weight affects the epoch amount before the commission split.
Foundation bonuses keep their existing calculation and log format. They are
paid directly to the owner for an on-chain delegate and credited to the stored
reward address's rewarding balance for a legacy delegate.

#### 6.3 Pending voter pool

Only on-chain delegates have pending voter pools. Each pool is stored in the
rewarding namespace under a key formed from a fixed prefix and the candidate
identity. A separate sorted identity index permits deterministic enumeration
without scanning the namespace.

The pool is part of rewarding-fund accounting but is not an address-level
unclaimed balance. It cannot be withdrawn through the normal rewarding claim
action. New block and epoch voter shares may continue to accrue while an older
frozen amount is being distributed.

### 7. Settlement Initialization

Settlement initialization runs in `GrantEpochReward` when the current epoch is
an era boundary. This is not the same block as the freeze height `H`: poll
results are written at roughly the midpoint of the preceding epoch, so `H`
precedes the boundary epoch's final block by about one and a half epochs.
Snapshots are frozen at `H`; the cursor is created at the boundary epoch's final
block; the first continuation chunk runs in the first block of the following
epoch.

For each currently rewarded on-chain candidate whose pending voter pool is
non-zero, the protocol creates one frozen work item:

```proto
message EpochDrainDelegateWork {
  bytes candidate_identifier = 1;
  bytes voter_amount_frozen = 2;
  bytes reward_address = 3;
  bytes epoch_commission = 4;
  reserved 5;             // voter_amount_distributed, now per-delegate in progress
  bytes total_weight = 6;
  bytes snapshot_hash = 7;
  reserved 8, 9, 10;      // last_weighted_index, has_weighted_entries, voter_start_index
  uint64 freeze_height = 11;
  uint64 self_stake_bucket_idx = 12;
}
```

The cursor is persisted as two records with different mutability. The plan is
written once and never rewritten; the progress record is rewritten by every
chunk. Splitting them keeps a block from rewriting the whole frozen delegate
list to record that it advanced one shard.

```proto
message EpochDrainPlan {
  uint64 target_era = 1;
  repeated EpochDrainDelegateWork delegates = 2;
  bytes settlement_seed = 3;
  reserved 4;             // delegate_start_index
  uint64 start_epoch = 5;
  uint64 end_epoch = 6;
  uint32 start_shard = 7;
}

message EpochDrainProgress {
  uint64 target_era = 1;
  reserved 2, 3, 4;       // delegate_index, voter_index, voter_amount_distributed
  bool completed = 5;
  uint64 completed_height = 6;
  bytes skipped_delegate_bitmap = 7;
  uint32 shards_done = 8;
  bytes resume_voter = 9;
  repeated bytes voter_distributed = 10;
}
```

Initialization derives exactly one seed from consensus-visible data:

```text
settlementSeed = keccak256(
    bytes("iip59.settlement-start.v1") ||
    parentBlockHash[32] ||
    uint64_be(targetEra)
)
R = uint256_be(settlementSeed)
startShard = R % 256
```

`parentBlockHash` is the hash of the block immediately preceding the boundary
block. `targetEra` is the boundary epoch number stored in the cursor. Every
validator executing the boundary block therefore derives the same `startShard`.
The delegate work list is stored in the existing epoch-reward candidate order
and is not rotated: the rotation applies to the shard sequence, which is the
only traversal order the drain has.

The fields have the following meaning:

- `target_era` is the boundary epoch number that initialized the settlement. It
  appears in both records and MUST match; a mismatch means one of the two is
  stale.
- `start_epoch` and `end_epoch` identify the epoch window covered by the
  settlement. Normally `end_epoch = target_era` and
  `start_epoch = end_epoch - EpochsPerRewardEra + 1`. Overrun recovery carries
  an older unfinished cursor's `start_epoch` into the replacement cursor.
- `completed` distinguishes a live drain from the retained result of the most
  recent completed settlement; `completed_height` is the block that ran its
  final chunk.
- `settlement_seed` is the 32-byte value `start_shard` is derived from.
- `start_shard` is the first address shard visited. Shard
  `(start_shard + n) mod 256` is the `n`-th visited.
- `shards_done` counts fully drained shards. It reaches 256, so it cannot be a
  `uint8`.
- `resume_voter` is the last voter address visited in the shard now in
  progress, empty when that shard has not been entered. Resume skips every
  address less than or equal to it. The resume point is an address rather than
  an offset because a shard's population changes between blocks and an offset
  would skip or repeat voters as it does.
- `voter_amount_frozen` is the pool balance allocated by this settlement.
- `voter_distributed` is one running total per delegate, positionally aligned
  with `delegates`; a short vector means the missing tail is still zero. The
  drain is voter-major and leaves most delegates partially paid for most of the
  settlement, so there is no index position from which per-delegate totals could
  be inferred. This vector is what the payout clamp measures against, so it must
  be persisted.
- `skipped_delegate_bitmap` marks work items the drain determined it cannot pay.
  A skipped delegate contributes nothing to any voter's share and keeps its
  pending pool for a later era.
- `reward_address` and `epoch_commission` preserve the routing and log values
  from initialization.
- `freeze_height` and `self_stake_bucket_idx` carry the two snapshot scalars the
  weight recompute needs, so a chunk never reads the live candidate record —
  which the drain itself is mutating.

Reserved field numbers in all three messages belonged to the candidate-major
drain, which walked the frozen delegate list and, inside each delegate, a frozen
voter list. Nothing in the shard walk corresponds to them and they MUST NOT be
reused.

The cursor is a singleton. `completed = false` means a settlement is active.
Its delegate work list is immutable except for the skip bitmap. A completed
cursor is retained for voter queries until the next era boundary, then cleared
or overwritten by the next settlement. This retains only one settlement and does
not create an append-only history.

The pending pool itself is not frozen: later rewards can accrue behind the
cursor. A chunk decrements only what it actually distributes. Any newer
balance remains available to a later settlement.

### 8. Chunked Voter Distribution

While an incomplete cursor exists, every block that is not the last block of an epoch
includes a protocol-generated `VoterRewardChunk` system action. Epoch-final
blocks run `GrantEpochReward` and do not also run a voter chunk.

One action walks the voter address space, not the delegate list. The space is
split into 256 shards by the first byte of the voter address, visited in the
rotation fixed by `start_shard`. The action resumes at the cursor's current
shard, just past `resume_voter`, and pays at most `VoterBudgetPerBlock`
**distinct voters**. A value of zero means unbounded. There is no separate
delegate count or compound count limit.

A voter is paid once for everything they are owed across every delegate they
staked with, native and liquid-staking alike, in a single combined transfer. The
budget therefore counts voters, not `(candidate, voter)` pairs.

The voters of one shard are produced by merging, in ascending address order, the
per-shard ranges of the live native voter index, the live liquid-staking voter
index, and the corresponding copy-on-write ranges of the era window. The merge
is what makes membership as-of-`H` rather than as-of-now.

`VoterBudgetPerBlock` bounds only the voters a block *pays*. A second bound,
proportional to it, limits the index keys the block may *scan*. Without the
second bound, one shard stuffed with addresses — the first address byte is
grindable by an attacker who generates keys — could be read in full before the
first voter is paid. When the scan bound truncates a shard, the block pays only
voters below the address range it can prove it covered end to end, and advances
`resume_voter` to that coverage bound rather than to the last address seen.

`resume_voter` advances past every voter *visited*, not only every voter *paid*:
a voter whose recomputed weight is zero must still advance the cursor, or every
later block rediscovers and re-skips them. A shard is counted in `shards_done`
only when the scans covered it end to end.

#### 8.1 Voter allocation

For voter `v` and each unskipped delegate `d` that `v` holds a frozen bucket
with:

```text
weight   = recomputed weight of v for d, as of d.freezeHeight (section 4.3)
share    = floor(d.voterAmountFrozen * weight / d.totalWeight)
share    = min(share, d.voterAmountFrozen - d.voterDistributed)
```

The second line is the **payout clamp** and is mandatory. Floor division bounds
the sum of shares by the pool only if the recomputed weights sum to at most
`totalWeight`, and section 4.3 explains why they need not: the numerator is a
stateless recompute and the denominator is a frozen path-dependent accumulator.
The clamp turns every disagreement between them into an under-payment. A
numerator that is too large stops at the pool boundary; a numerator that is too
small leaves a residual, which section 9 sweeps. Over-payment — the drain paying
out money the era never set aside — is not an acceptable outcome, and the clamp
is what forecloses it.

The voter's payment is the sum of their clamped shares across all contributing
delegates, paid as one transfer to one destination. Each contributing delegate's
pending pool is drawn down by its own share and its `voter_distributed` entry
advances by the same amount. The clamp reads `voter_distributed` including
payouts made earlier in the same block, not only those persisted by earlier
blocks.

A voter whose total is zero is skipped without a payment and without a log
entry, but still advances the cursor.

There is no rule assigning floor-division dust to a distinguished voter. Such a
rule requires knowing which voter is last in a traversal, and a shard walk over
a set whose membership is resolved per shard has no such position. The dust is
left in the pool and swept at completion instead.

#### 8.2 Direct payout

Unless compound routing succeeds, the protocol adds the voter's combined amount
directly to their effective reward-destination account balance as resolved in
the chunk block. Routing is decided once per voter and applies to the whole
combined amount; it is not decided per contributing delegate. The voter does not
receive a rewarding `unclaimedBalance` entry and neither the voter nor the
recipient needs to submit `ClaimFromRewardingFund`.

Each non-zero direct payout emits a transaction log with:

```text
type      = CLAIM_FROM_REWARDING_FUND
sender    = RewardingPoolAddr
recipient = effective voter reward destination
amount    = voter's combined amount
```

The log type represents an immediate rewarding-fund outflow; it does not mean
the voter submitted a claim transaction.

#### 8.3 Compound payout

The existing `AutoDeposit` contract maps a voter to a preferred bucket ID. A
share is compounded only if all of the following hold at chunk execution:

1. the voter has a non-zero configured bucket ID;
2. the bucket exists in native staking state;
3. the bucket is a native bucket, not a contract-staking bucket;
4. the bucket is owned by the voter;
5. auto-stake is enabled; and
6. the bucket is active and not unstaked.

An eligible voter's combined amount is added to that bucket through the staking
protocol. Compound value leaves the rewarding fund and enters the staking bucket
pool.
The chunk emits a transaction log with:

```text
type      = DEPOSIT_TO_BUCKET
sender    = RewardingPoolAddr
recipient = StakingBucketPoolAddr
amount    = total compounded amount represented by the log
```

Contract-staking weight participates in reward allocation, but its reward is
paid directly because contract-staking buckets are not eligible compound
targets.

If the AutoDeposit lookup fails, the configured bucket cannot be read, or the
bucket is ineligible, that voter deterministically falls back to direct
payout. A failure while applying an otherwise valid staking deposit is a
state-transition failure and is not silently converted after partial writes.

#### 8.4 Pool and fund updates

After each voter's combined transfer, the protocol:

- decrements each contributing candidate's pending pool by that candidate's
  share of the transfer;
- decreases rewarding total balance by the same total outflow; and
- advances each contributing candidate's `voter_distributed` entry.

At the end of the block it persists `shards_done`, `resume_voter`, the skip
bitmap, and the `voter_distributed` vector when work remains. These updates
occur atomically with account or staking changes.

### 9. Settlement Finalization

When all 256 shards are drained, the protocol finalizes in this order.

**1. Per-delegate residual sweep.** For each unskipped work item:

```text
residual = voter_amount_frozen - voter_distributed
```

The residual is what floor division and the payout clamp left behind. It is
swept out of that delegate's pending pool and folded into `voter_distributed`,
so a completed settlement satisfies `voter_distributed == voter_amount_frozen`
for every unskipped delegate by construction. Skipped delegates are not swept;
their whole frozen amount stays pending for a later era.

**2. Orphan resolution.** A pending-pool entry not represented in the cursor
belongs to a candidate that accumulated rewards but no longer participates in
the current reward split. For each:

1. if candidate state still exists, pay the full pool to the candidate's
   current owner;
2. if candidate state no longer exists, return the amount to the rewarding
   fund's unclaimed balance; and
3. delete the pool and its index entry.

Both the residual sweep and orphan resolution go through one sink, so the fund
accounting has one place to be right. Each emits a `BLOCK_REWARD` reward log for
observability. Neither ever burns the pending amount. A swept pool is
decremented rather than deleted, because it may have kept accruing behind the
drain and that accrual belongs to the next era; the entry disappears on its own
when it empties.

**3. Seal the era window.** No further read as of `H` is possible after this
point. Copies retained by the window become reclaimable, and are reclaimed in
bounded batches by later blocks.

The protocol then sets `completed = true`, records the final block height, and
retains the cursor. Completed cursors do not produce further `VoterRewardChunk`
actions. At the next era boundary, the protocol clears the completed cursor
before initializing the next one.

### 10. Overrun Recovery

At settlement initialization, an incomplete cursor from the previous reward
era may still exist. This MUST NOT halt block production. A completed cursor is
not an overrun and is cleared without emitting an overrun log.

The protocol:

1. sums the live pending-pool balances of **every** delegate the stale cursor
   named, and counts how many still hold one;
2. emits `EPOCH_DRAIN_OVERRUN` with the old `target_era`, that count, and the
   live residue;
3. deletes the stale cursor without deleting any pending pool; and
4. continues normal initialization, freezing current live pool balances into
   a new cursor whose `start_epoch` preserves the oldest unfinished window.

The sum is over all delegates rather than a suffix of the work list because the
drain is voter-major: an interrupted settlement leaves most delegates partially
paid, not a clean prefix done and a suffix untouched. It uses the live pool
balance rather than the cursor's `voter_amount_frozen` because the live balance
is the true leftover — it may have accrued additional block-time credit between
the freeze and this point.

Already distributed amounts are not paid again because they have already been
removed from their pools. Undistributed residue and rewards accrued after the
old initialization remain in the live pools. The new settlement allocates
those balances using the new era's voter snapshot.

Only one era window exists at a time. The next era's window opens at the next
freeze height `H`, which precedes the boundary block by about one and a half
epochs — so an overrunning drain loses its window before overrun recovery
detects it. Opening the new window seals the old one, which keeps the old
window's copies collectable rather than leaking them; it does not preserve
as-of-`H` reads for the outgoing drain. A drain that continues past the next
freeze height would therefore compute weights against an unmaintained window.
The bound that prevents this is capacity, not a runtime check: networks MUST
size `VoterBudgetPerBlock` and `EpochsPerRewardEra` so a settlement completes
well inside its era (section 14).

### 11. Receipt and Transaction Logs

#### 11.1 DelegateDistributed

A chunk block emits one EVM-compatible event per delegate that contributed to a
payout in that block, covering every voter that delegate paid in the block:

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

- `epoch` is the epoch containing the chunk block.
- `delegate` is the candidate identity.
- `rewardAddr` is the candidate owner frozen at settlement initialization.
- `totalCommission` is the epoch commission paid by the boundary
  `GrantEpochReward` for this cursor item. It excludes block commission and
  commissions paid in earlier epochs of the era.
- `totalVoterPool` is the sum of `amounts` in this event's window.
- `snapshotHash` is the digest of the delegate's frozen era parameters
  (section 4.1). It is the join key across the many partial events one
  settlement emits.
- `voters`, `recipients`, `amounts`, `compoundBucketIds`, and `compounded` are
  parallel arrays.
- `voters[i]` is the beneficiary whose recomputed weight earned the reward.
- `amounts[i]` is this delegate's contribution to that voter's payment, not the
  voter's whole combined transfer. A voter paid from several delegates in one
  block appears in several events in that block.
- For a direct payout, `recipients[i]` is the account actually credited. For a
  compound payout, it equals `voters[i]` and `compoundBucketIds[i]` identifies
  the actual staking destination.
- `compounded[i]` is the direct-or-compound discriminator. Consumers MUST use
  it and MUST NOT infer routing from `compoundBucketIds[i]`: native bucket 0 is
  a real bucket, so `compoundBucketIds[i] == 0` is indistinguishable between a
  direct payout and a compound into bucket 0.

A delegate may emit multiple events. Their `totalVoterPool` values sum to the
frozen amount minus the residual swept at completion. `snapshotHash` remains
stable across all chunks of the same settlement, so joining on it reassembles
one delegate's whole distribution.

#### 11.2 Cursor progress

Every `VoterRewardChunk` first emits a `CURSOR_PROGRESS` reward log. Its
address field encodes:

```text
targetEra:shardsDone:hex(resumeVoter):shardsRemaining
```

`shardsRemaining` is `256 - shardsDone` while the drain is live and zero once it
finishes. Its amount is the fixed string `"0"`. Monitoring systems can detect a
stalled or slow settlement without reading internal state.

#### 11.3 Overrun log

`EPOCH_DRAIN_OVERRUN` encodes:

```text
addr   = targetEra:delegatesRemaining
amount = live pending-pool residue
```

The event is emitted before the new boundary epoch's per-delegate reward logs.

#### 11.4 Explicit opt-in event

A successful explicit opt-in emits the native staking receipt event:

```solidity
event VoterRewardOptInSet(
    bytes32 indexed candidateIdentifier,
    bool optIn
);
```

`optIn` is always true for a successful action.

#### 11.5 Voter reward destination event

A successful `SetVoterRewardDestination` action emits
`VoterRewardDestinationSet` as specified in Section 2.2. `oldRecipient` and
`newRecipient` are effective addresses: setting the first override reports the
voter as `oldRecipient`, and clearing an override reports the voter as
`newRecipient`.

### 12. State Access

Archive nodes that provide historical IIP-59 verification MUST configure
`chain.historyIndexPath` and retain the resulting history index. The new state
objects support both the native state backend and archive secondary storage.

The rewarding protocol exposes these native `ReadState` methods:

| Method | Result |
|---|---|
| `PendingBlockRewardPool(candidateID)` | Current pending voter amount for one candidate. |
| `PendingBlockRewardPoolIndex()` | Sorted candidate identities with pool entries. |
| `EpochDrainCursor()` | Active or most recently completed cursor and all frozen work items, or an empty cursor before the first settlement. |
| `VoterRewardSnapshot(candidateID)` | Frozen mode, profile rates, total weight, snapshot hash, freeze height, and self-stake bucket index. |
| `VoterRewardAddress(candidateID)` | Effective destination under the frozen mode: current owner in on-chain mode or stored reward address in legacy mode, plus the reward-address update marker. |
| `VoterRewardDestination(voterAddress)` | Effective direct voter recipient, whether an override is explicitly set, and the set height. |
| `VoterRewardStatus(voterAddress)` | One voter's status, epoch range, and total reward amount in the active or most recently completed settlement, summed across every delegate they hold a frozen bucket with. |

Equivalent Web3 read methods are available through the rewarding protocol
state interface:

```solidity
pendingBlockRewardPool(address candidateId)
pendingBlockRewardPoolIndex()
eraDrainCursor()
voterRewardDelegateSnapshot(address candidateId)
voterRewardAddress(address candidateId)
voterRewardDestination(address voter)
voterRewardStatus(address voter)
```

Two Web3 names differ from their native counterparts, deliberately. Both
`epochDrainCursor()` and `voterRewardSnapshot(address)` once returned tuples
built around the materialized per-voter entry list, and both are renamed rather
than reshaped in place: an ABI name determines a 4-byte selector, so reusing the
name while changing the tuple would let a caller built against the old interface
decode a shard counter as a delegate index, or read a `freezeHeight` where it
expected a `voters` array, and get a plausible wrong answer instead of an error.
Because IIP-59 has never been activated, the old selectors are removed outright
rather than aliased. Native `ReadState` names have no selector and keep their
original spellings.

`VoterRewardStatus` takes one argument, not two. The drain pays a voter once for
everything they are owed across every delegate, so there is no per-candidate
answer to ask for.

`VoterRewardDestination` returns:

```text
recipient
explicitlySet
updatedHeight
```

When no sparse override exists, `recipient` is the voter, `explicitlySet` is
false, and `updatedHeight` is zero. The read reports the current configuration;
the `recipients` array in the historical `DelegateDistributed` event is the
authoritative record of where an already executed direct payout went.

The `eraDrainCursor()` Web3 result returns the settlement scalars —
`targetEra`, `startEpoch`, `endEpoch`, `completed`, `completedHeight`,
`startShard`, `shardsDone`, `resumeVoter`, `settlementSeed` — followed by five
arrays parallel to one another: `candidateIds`, `voterAmounts`,
`distributedAmounts`, `rewardAddresses`, `epochCommissions`, and `totalWeights`.
Native `ReadState` returns the same values in the cursor protobuf. Together
these make the settlement's shard rotation and its progress through it
independently reconstructable.

`VoterRewardStatus` returns:

```text
targetEra
eraStartEpoch
eraEndEpoch
settlementCompleted
completedHeight
status
rewardAmount
```

`status` is one of:

| Status | Meaning |
|---|---|
| `NO_ACTIVE_SETTLEMENT` | No active or completed settlement cursor exists. |
| `VOTER_NOT_INCLUDED` | The voter holds no frozen bucket with any delegate in the reported settlement. |
| `WAITING` | The shard walk has not reached this voter. |
| `PROCESSED` | The shard walk has passed this voter. A zero-weight or zero-share voter can be processed without receiving funds. |
| `SNAPSHOT_UNAVAILABLE` | No era window is open, so the amount cannot be derived from the state the settlement pays against. |
| `CANDIDATE_NOT_INCLUDED` | Retained for wire compatibility. The query is per-voter and does not produce it. |

Position is measured in the rotation, not in raw shard IDs: the voter's own
shard maps to a rotation position that compares against `shardsDone`, and inside
the shard in progress, `resumeVoter` separates visited from pending.

`rewardAmount` is computed by the same allocation function, with the same payout
clamp, that the drain itself uses, so the reported number is the number the
drain pays as a property of the implementation rather than of two calculations
happening to agree. It sums the voter's clamped shares across every delegate
they hold a frozen bucket with.

The query is answerable only while the era window is open. Sealing the window at
completion removes the state the amount is derived from, and the protocol
reports `SNAPSHOT_UNAVAILABLE` rather than recomputing against live state and
returning a figure nobody was paid. After a settlement completes, receipts —
not this query — are the record. `settlementCompleted` and `completedHeight`
still distinguish the retained latest result from an in-progress cursor. The
method retains only the most recent settlement until the next era boundary; it
is not a historical ledger. `PROCESSED` does not identify whether the payout was
direct or compounded.

Historical verification combines these state reads with block receipts,
`DelegateDistributed` events, and transaction logs.

### 13. Voter Preparation

Voters who want direct payouts to their voting account do not need to take any
action. A voter who uses a separate treasury, custody, or tax account MAY set
that account with `SetVoterRewardDestination` and verify the effective value
with `VoterRewardDestination`. After a successful settlement, the reward is
already in the effective account and does not require a rewarding-fund claim.

Voters who want automatic compounding SHOULD register an eligible native
staking bucket in the existing `AutoDeposit` contract before their payout is
processed. The bucket must be owned by the voter, active,
auto-staked, and not unstaked. Contract-staking votes are included in reward
weight, but contract buckets are not eligible compound destinations; those
rewards are paid directly to the effective reward destination.

The legacy `ForwardRegistration` flow is not part of IIP-59 and is not
automatically migrated into protocol state. A voter that previously relied on
that contract MUST submit `SetVoterRewardDestination` to obtain equivalent
post-activation direct routing. Existing valid `AutoDeposit` registrations
remain effective without a new transaction and override direct routing when
eligible. During an active or recently completed settlement, a voter can use
`VoterRewardStatus` to check progress. After processing, the voter can verify
the direct account balance or native bucket deposit and use indexed
`DelegateDistributed` events for historical details.

### 14. Genesis Parameters

The following network configuration is consensus-critical:

| Field | Default | Description |
|---|---:|---|
| `EpochsPerRewardEra` | 24 | Number of epochs between settlement initializations. |
| `VoterBudgetPerBlock` | 2000 | Maximum distinct voters paid by one chunk action; zero means unbounded. |
| `VoterWeightSeedBatchSize` | 2000 | Deprecated and unused. It sized the per-block batch of the removed weight-table materialization. Retained as a field so existing genesis files parse; new networks SHOULD omit it. |
| `HermesRewardVaultAddresses` | two legacy Hermes vaults | Reward addresses whose pre-fork delegates migrate automatically. |
| `DelegateProfileContractAddress` | network-specific | Contract containing per-delegate voter portions. |
| `AutoDepositContractAddress` | network-specific | Contract containing per-voter compound preferences. |

`EpochsPerRewardEra` MUST be non-zero on an activated network, and in practice
MUST be at least 2. The era window that a settlement reads is superseded at the
next freeze height (section 10), which falls roughly one and a half epochs before
the next era boundary; a one-epoch era leaves no room between the two. There is
no separate compound or delegate-count limit in the settlement algorithm.

For an era containing `B` blocks per epoch and `E` epochs, at most roughly
`E * (B - 1)` continuation blocks are available because every epoch-final
block is reserved for epoch rewards. A bounded configuration should satisfy:

```text
VoterBudgetPerBlock * availableContinuationBlocks
    >= expected distinct voters per settlement * safety factor
```

Capacity MUST be estimated from the number of **distinct voter addresses** with
a frozen bucket in the era, not from the sum of per-candidate voter-list
lengths. A voter staking with ten delegates costs one unit of budget, not ten.
This is a change from earlier revisions of this specification, in which the
budget counted `(candidate, voter)` pairs; a configuration sized under the old
rule remains safe but is more conservative than necessary. Operators SHOULD
include headroom for voter growth and monitor cursor age, `shardsDone`
progress, and `EPOCH_DRAIN_OVERRUN` logs. With the defaults and `B = 360`, the
nominal capacity is approximately `24 * 359 * 2000 = 17,232,000` distinct voters
per era. Networks MUST benchmark representative validation hardware before
activation; the nominal count is not a substitute for block mint and validation
latency measurements.

The paid-voter budget is not the only per-block bound. Each block also bounds
the number of voter-index keys it may scan, at a fixed multiple of
`VoterBudgetPerBlock`, so that one address shard cannot be made expensive enough
to consume a block before the first voter is paid (section 8). Operators do not
configure this multiple; it exists so that `VoterBudgetPerBlock` bounds scan
cost as well as payout cost.

Each direct payout adds one rewarding-state lookup for the voter's sparse
destination override. With the default budget, a direct-only chunk therefore
performs at most 2,000 such lookups in addition to account writes and the
existing AutoDeposit checks. Compound payouts do not require this lookup. Each
paid voter also costs one weight recomputation per contributing delegate, read
through the era window; benchmarks MUST therefore be run against a voter
population with a representative distribution of delegates per voter, and MUST
include both mostly-unset and densely-configured destination state because
archive/history-index I/O and cache behavior can differ.

If this capacity is exceeded, Overrun Recovery preserves funds and carries the
remaining pools forward.

### 15. Failure Semantics

Failures are handled according to their scope:

| Condition | Required behavior |
|---|---|
| Missing, partial, malformed, or unreadable DelegateProfile entry | Mark that profile unregistered for the snapshot and pay 100% directly to the owner. |
| No usable voter snapshot or no positive total weight | Mark the work item skipped; keep the pool pending and retry in a future era. |
| Work item has no freeze height | Mark it skipped. Do not substitute the current block's height: a contract bucket would then be worth a different amount in each chunk of the same settlement. |
| Delegate's reward destination cannot be resolved at drain time | Mark it skipped; keep the pool pending. |
| Recomputed weights sum to more than the frozen total weight | Clamp each share to the delegate's remaining frozen pool. Never pay beyond it. |
| Candidate-view construction fails while freezing era snapshots | Fail the block. This is the one IIP-59 path that halts rather than degrades: a snapshot that silently omits delegates would freeze a wrong era for its whole length. |
| AutoDeposit lookup fails | Pay that voter directly. |
| Voter destination override is absent | Pay the voter account directly. |
| Bucket is missing, unreadable, contract-based, not owned by voter, not auto-staked, or unstaked | Pay the effective voter reward destination directly. |
| Invalid voter destination action length | Reject the action. |
| Malformed persisted voter destination state | Fail the state transition; do not guess or truncate an address. |
| Previous cursor survives to the next era boundary | Execute Overrun Recovery. |
| Frozen amount left over after floor division and clamping | Sweep the residual at completion through the same sink as orphaned pools. |
| Candidate pool becomes orphaned but candidate state exists | Pay the candidate owner directly. |
| Candidate state for an orphaned pool is absent | Return the amount to the rewarding fund's unclaimed balance. Never burn it. |
| Invalid persisted state, account write failure, staking deposit mutation failure, or log encoding failure | Fail the state transition; normal block validation and rollback apply. |
| Chunk action fails for a reason every node derives identically from committed state — no cursor, cursor already complete, fork inactive | Settle a Failure receipt. The block is valid and the cursor does not move. |
| Chunk action fails for any other reason, including any state read, state write, or range scan error | Fail the block. |

The last two rows are a single rule with a deliberate default. A Failure receipt
is itself a consensus-visible outcome — "this block paid no voters and the
cursor did not move" — so it is sound only when every node executing the block
reaches the same verdict. Whether a working set can serve an ordered range scan
is a node-local capability, not chain state; a proposer that settled Failure on
such an error would commit no payouts while validators that can scan commit
payouts, producing two state roots for one block. Implementations MUST therefore
treat "settle a Failure receipt" as opt-in per condition and halt on everything
not explicitly enumerated, rather than the reverse.

Fallback behavior MUST be deterministic from consensus state. Implementations
MUST NOT depend on an external RPC service or wall-clock result.

## Rationale

### Hermes-targeted migration and one-way opt-in

The automatic migration matches the existing operational boundary: delegates
whose rewards already flow through the configured Hermes vaults are the ones
whose voter distribution Hermes performs. Delegates that manage rewards
independently keep their established address and claim workflow, avoiding an
unrequested economic or operational change at the fork.

The owner-only opt-in lets a legacy delegate adopt protocol-native distribution
later. Making it one-way prevents accrued pending pools and frozen settlements
from being stranded by a return to legacy mode. Freezing the effective mode in
the poll snapshot removes ambiguity during a multi-block settlement.

The all-to-owner profile fallback avoids assigning a voter portion that the
delegate never configured. It is deterministic, preserves funds, and allows
the delegate to register valid portions for a later reward era.

### Candidate identity as the state key

Candidate owner and operator addresses may change. Candidate identity is the
stable key shared by staking snapshots, DelegateProfile data, pending pools,
cursor entries, and receipt events. This prevents an operator rotation from
splitting or stranding a delegate's reward history.

### Era-based settlement

Block voter rewards arrive every block, but paying every voter every epoch
would repeatedly incur snapshot and routing overhead. Accumulating for a reward
era amortizes fixed work while still paying delegate commission immediately.

### Voter-count-only bounding

The expensive work scales primarily with voters and their routing decisions.
One global voter budget bounds that work directly. A second delegate or
compound limit can reduce useful throughput without providing a clearer safety
bound.

### Recomputed weights rather than a committed weight table

An earlier revision of this specification made the aggregated
`(candidate, voter)` weights consensus state, written incrementally by every
bucket mutation and materialized into each era's snapshot. That design is
replaced here by recomputing weights on demand.

The committed table's cost was continuous and its benefit was momentary. Every
bucket change in every block paid to keep it current, and a delegate's whole
frozen entry list had to be written into state at each era boundary, so state
growth scaled with the number of `(candidate, voter)` pairs rather than with
what a settlement actually pays. The recompute reads the same buckets the table
was derived from, so it produces the same quantity from a smaller commitment:
the frozen scalars in section 4.1 and the era window in section 4.2.

The property the committed table was defended for — that no node derives the
weights for itself — is instead obtained from the era window. Every node
recomputes, but they all recompute from the same as-of-`H` state, and that state
is committed. What is agreed on is the input, not the output, and a
disagreement about the input is a state-root disagreement that block validation
already catches.

### Voter-major settlement

The previous design walked the frozen delegate list and, within each delegate, a
frozen voter list. It therefore paid a voter once per delegate: one destination
lookup, one routing decision, and one balance write per `(candidate, voter)`
pair, plus the entry list that had to be materialized to drive the walk.

Walking the voter address space instead pays each voter once for their whole
entitlement. The cost per settlement falls from the number of pairs to the
number of distinct voters, no entry list is needed to drive the traversal, and a
voter staking with many delegates receives one transfer rather than many small
ones.

Sharding by the first address byte gives a resume point that is an address
rather than an offset, which matters because the set is resolved per shard and
its membership changes between blocks. It also makes the walk's cost per block
independent of the delegate count.

### Rotated settlement starts

A fixed canonical start would repeatedly favor the same head of the shard
sequence whenever a settlement overruns its era. Selecting the first shard from
the previous block hash changes the order in which voters are served without
changing membership, weights, the proportional allocation rule, or total fund
movement. Deriving it from a hash the whole network already agrees on keeps the
state compact — one 32-byte seed and one shard index — and makes the traversal
reproducible from archive state.

Rotation no longer decides who receives floor-division dust, because no voter
receives it: the dust stays in the pool and is swept at completion. Rotation
therefore has strictly less economic influence in this design than in the
previous one.

### The payout clamp and the residual sweep

The frozen denominator is a running accumulator maintained by staking handlers;
the numerator is a stateless recompute from buckets. Two such quantities can
disagree, and one known source of disagreement is deliberately left in place:
the recompute decides the self-stake bonus by comparing bucket index to the
frozen self-stake index, while the accumulator uses a refined predicate that
accounts for endorsement expiry — a passive event with no transaction to observe
it. No stateless recompute can reproduce a path-dependent accumulator, so
changing either predicate would only move the disagreement rather than remove
it.

The clamp makes the direction of every such disagreement safe. A recomputed
weight that is too large stops at the frozen pool boundary; one that is too
small leaves a residual. Under-payment is recoverable — the residual is swept
back through the same sink as an orphaned pool, and reaches the delegate's
owner or the rewarding fund. Over-payment is not recoverable, because the money
has left the protocol. Choosing exact per-delegate conservation instead would
require a distinguished last voter to absorb the difference, which the shard
walk cannot identify, and would pay out the difference even when it arises from
an accumulator that has drifted.

### Direct account payout and voter-selected routing

Writing direct rewards to an account completes the payment in one state
transition. Keeping a second per-voter rewarding balance would require another
claim transaction and preserve unnecessary rewarding state indefinitely. A
global voter-selected destination covers custody, treasury, and tax-account
workflows without duplicating configuration for every delegate.

Resolving the destination at chunk execution gives the voter control over
unprocessed payouts and avoids copying mutable routing data into every frozen
snapshot. Recording both beneficiary and recipient in `DelegateDistributed`
preserves the historical result even after the voter changes configuration.
Sparse overrides keep default users state-free, and deleting self/zero resets
avoids permanent tombstones.

### Inline compound routing

Resolving compound preference while paying each voter avoids a separate
pending-compound state machine. The event records the actual destination
bucket, allowing auditors to verify both the decision and the staking inflow.

### Frozen inputs with live pools

Reward mode, profile rates, total voter weight, the freeze height, the
self-stake bucket index, the settlement cursor's owner destination, and the
settlement amount are frozen so all validators reproduce the same allocation
across multiple blocks. The live pool remains able to receive later rewards;
those newer funds are unambiguously deferred to a future cursor.

### Copy-on-write rather than historical reads

The settlement needs to read bucket state as it was at `H` from blocks that
execute after `H`. An archive or history-index lookup could answer the same
question, but it would make consensus depend on a node's retention
configuration, and it would answer against a height whose state the drain is
concurrently mutating. Copying a key aside on its first mutation after `H`
keeps the answer in the same state tree the block is already reading, costs
nothing for keys the era never touches, and makes "no copy exists" a positive
statement — the key has not changed since `H` — rather than an absence to be
interpreted. Recording tombstones for keys created after `H` is the same
principle applied to absence, which is otherwise the one case where "no copy"
would mean the opposite of what it says.

## Backward Compatibility

Before activation, reward grants, reward addresses, claims, logs, and state are
unchanged.

Activation changes reward operations only for automatically migrated or
explicitly enabled delegates:

- Hermes MUST stop distributing rewards generated after the fork for
  automatically migrated delegates.
- Their stored legacy reward address no longer receives newly generated
  rewards; delegate-directed rewards are paid directly to the current owner.
- Their voter portions enter per-delegate pending pools rather than a delegate
  rewarding balance.
- Direct voter rewards appear immediately in the voter-selected account
  balance, defaulting to the voter account.
- Compound voter rewards appear as native staking bucket deposits.

Delegates outside the configured Hermes vault set retain their stored reward
address, full rewarding balance accrual, and claim requirement. They enter the
new behavior only after an owner-authorized opt-in action. Existing balances
accrued before migration remain claimable and are not rewritten.

Existing `DelegateProfile` and `AutoDeposit` contracts remain the configuration
sources, so delegates and voters do not need new configuration transactions
solely for IIP-59. `ForwardRegistration` entries are not imported; voters that
need a non-default direct destination must configure the protocol action once.

## Security Considerations

### Determinism and replay

All allocation inputs and the shard rotation are frozen in state and committed
to the state root. Voter weights are recomputed rather than committed, but they
are recomputed from copy-on-write state that *is* committed (section 4.2), so
two nodes that recompute differently have diverged on the state root and normal
block validation rejects one of them. A restart changes nothing, because the
recompute reads only committed state and the frozen scalars that travel with the
work item.

The settlement seed depends only on the prior block hash and the boundary epoch,
both identical for every validator executing a given boundary block. Cursor,
account, pool, and bucket changes are part of the same block state transition. A
reorganization changes the parent hash but also reverts the seed, payout, and
cursor advance together before deterministic re-execution.

The settlement seed is not a source of cryptographic randomness and MUST NOT
be used for reward eligibility, weight, commission, or total allocation. A
producer near the boundary may have limited influence over a candidate parent
block hash, but that influence selects only the starting shard, and therefore
only the order in which voters are served. It cannot change membership,
recomputed weight, commission, or total distributed value, and — unlike the
previous revision, where rotation decided who absorbed floor-division dust — it
has no effect on any voter's amount, because no voter absorbs dust.

The 256-way shard split is by the first byte of the voter address, which an
attacker can grind: generating keys until they land in a chosen shard is cheap.
This is why the per-block bound on scanned index keys exists alongside the bound
on paid voters (section 8). Without it, an attacker could concentrate addresses
in one shard and make that shard's scan, rather than any payout, consume the
block.

### Fund conservation

For each split:

```text
commission + voterShare = source reward
```

For each delegate, at every point during a settlement:

```text
sum(payouts so far from this delegate) <= voterAmountFrozen
```

This is an inequality, not an equality, and the payout clamp (section 8.1) is
what enforces it. Exact conservation is restored at completion, where the
residual `voterAmountFrozen - voterDistributed` is swept to the delegate's owner
or, if the candidate is gone, to the rewarding fund's unclaimed balance
(section 9). No path burns a residual and no path pays one twice: the sweep is
recorded in `voterDistributed`, so a completed settlement has
`voterDistributed == voterAmountFrozen` for every unskipped delegate.

The direction of the inequality is the security property. A weight recompute
that disagrees with the frozen denominator can only cause the protocol to pay
less than it set aside, never more, so no disagreement between the two can be
turned into an inflation of the rewarding fund's outflow.

Pending pools remain backed by the rewarding fund. A chunk decreases both the
pool liability and rewarding total balance by the amount leaving the protocol.
Overrun recovery never creates a new balance; it only replaces the cursor over
existing pools.

### Destination authorization and account safety

Only the voter-signed action can change that voter's direct destination. The
recipient does not gain control of the voter's stake, voting weight,
AutoDeposit configuration, or future configuration action. A voter can restore
the default by setting self or zero.

The protocol treats the recipient as an account address and performs no
contract callback. This prevents recipient code from re-entering reward or
staking transitions. It also means applications MUST NOT assume an ERC-style
receiver hook will execute. A mistaken but valid recipient is an authorized
on-chain transfer and cannot be reversed by the protocol; wallets SHOULD show
the effective address and reset semantics before signing.

### Denial of service

The voter payout loop is bounded by `VoterBudgetPerBlock` when the parameter is
non-zero, and the index scan that feeds it is bounded by a fixed multiple of the
same parameter, so neither half of a chunk is unbounded. Delegate iteration is
limited by the existing epoch-reward candidate set and has no additional IIP-59
cap. `VoterRewardChunk` is protocol-generated and cannot be submitted as an
arbitrary user action. Networks MUST size the voter budget and era length using
representative validation hardware.

Snapshot construction and DelegateProfile reads occur only at era boundaries
and only for on-chain delegates, and write a fixed number of scalars per
delegate rather than a list that scales with its voter count. Per-block cost
during a settlement is bounded by the budget rather than by any delegate's
size, so a delegate cannot be made expensive by acquiring voters.

The one-time contract-staking owner index backfill (section 1.1) is the largest
single-block operation IIP-59 introduces. It is not attacker-controlled — its
size is the deployed contract-staking bucket population at a height chosen by
governance — but it MUST be measured against the block budget before the
activation height is set, because a block that exceeds the budget at a
mandatory height stops the chain rather than degrading.

### External contract state

DelegateProfile and AutoDeposit reads execute against on-chain EVM state under
the same block context on every validator. Per-entry read failures use defined
fallbacks. No off-chain API is consulted during consensus.

### Historical observability

Archive operators must configure history indexing to retain historical IIP-59
state. Without an archive history index, current-state reads and receipt logs
remain available, but arbitrary historical cursor and pool verification is not
guaranteed.

Consensus state intentionally does not retain an append-only distribution
history for every voter. Such a history would grow without bound and duplicate
receipt data. Archive receipts and `DelegateDistributed` events are the
canonical post-activation execution record, including the candidate, voter,
amount, beneficiary voter, actual direct recipient, direct-or-compound result,
bucket ID, block, and action hash.

Indexers SHOULD expose a voter-oriented history query over that record, for
example by candidate, voter, and epoch range. A unified wallet or tax API MAY
join pre-activation Hermes records with post-activation IIP-59 events, but that
API and its retention policy are outside consensus and outside this IIP's
reference-node state transition.

## Reference Implementation

The reference implementation is in
[`iotexproject/iotex-core` PR #4953](https://github.com/iotexproject/iotex-core/pull/4953):

- `action/protocol/staking/` resolves migration mode, handles explicit opt-in,
  freezes era snapshots, maintains the native and contract-staking voter
  indexes, and recomputes voter weights as of the freeze height.
- `action/protocol/staking/eracow/` implements the copy-on-write era window,
  its tombstones, high-water marks, journal, and bounded garbage collection.
- `action/protocol/poll/` invokes snapshot freezing at era-boundary poll
  updates.
- `action/protocol/rewarding/` implements reward accumulation, cursor
  initialization, chunk distribution, voter destination state/actions,
  finalization, overrun recovery, and state reads.
- `action/protocol/rewarding/delegateprofile/` reads and validates profile
  portions.
- `action/protocol/rewarding/autodeposit/` resolves compound preferences and
  bucket eligibility.
- `action/protocol/rewarding/distributedlog/` defines and encodes
  `DelegateDistributed`.
- `action/protocol/rewarding/ethabi/` exposes the IIP-59 Web3 state interface.
- `blockchain/genesis/` defines activation and reward-era parameters.
