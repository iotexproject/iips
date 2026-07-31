```
IIP: 59
Title: Protocol-Native Voter Reward Distribution
Author: Raullen Chai (@raullen), Chen Chen (@envestcc)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-20
Updated: 2026-07-31
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
   freezes voter weights, derives one parent-hash-based settlement seed, and
   creates a persistent settlement cursor.
3. **Chunked Voter Distribution** - subsequent blocks pay at most
   `VoterBudgetPerBlock` voters in deterministic circular order.
4. **Settlement Finalization** - the last chunk resolves orphaned pools and
   marks the cursor complete and retains it until the next settlement.
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
| **Voter snapshot** | Frozen, address-sorted list of aggregated voter weights plus the delegate's profile rates. |
| **Settlement seed** | Domain-separated hash that deterministically selects the circular starting offset for every delegate and voter list in one settlement. |
| **Settlement cursor** | Persistent progress record for a multi-block voter distribution. |
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

#### 1.1 Voter weight materialization

Aggregated voter weights are consensus state (section 4). They are not written
before activation: nodes adopt an activated release ahead of the activation
height, and a node that wrote these entries during that window would commit
state the previous release does not write and diverge from the rest of the
network before the fork takes effect. The view is still maintained in the
activated release throughout that window, so it is accurate at the block the
gate opens.

The complete table cannot be written in the activation block; at the design
ceiling it exceeds a single block's execution budget. Starting at activation the
protocol therefore writes it across consecutive blocks, at most
`VoterWeightSeedBatchSize` pairs per block, in ascending
`(candidate identity, voter)` key order, recording its position in state so the
work resumes after a restart.

The recorded position MUST be a key rather than a numeric offset. Voters are
added and removed while the table is being written, and an offset would skip or
repeat entries as the set shifts.

No record of which pairs have already been written is required. Every block
writes the current absolute weight of each pair it modifies, so a pair modified
during this window is recorded correctly whether or not the ordered pass has
reached it, and the pass writing that pair again later is idempotent.

Until the pass completes, the protocol MUST treat the voter-weight view as
unavailable when freezing a poll snapshot. An era boundary inside this window
produces snapshots with no voter entries; the affected pools stay pending and
settle in a later era under section 15. No reward is lost.

Networks MUST size `VoterWeightSeedBatchSize` so the pass completes well within
one era.

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

### 4. Voter Weight Tracking and Snapshot

The staking protocol maintains an incremental voter-weight view. Bucket state
changes update the aggregated `(candidate identity, voter)` weight using the
same weighting rules used by the staking and poll protocols. This includes
eligible weight represented by native staking and contract staking.

These aggregated weights are consensus state. Each `(candidate identity, voter)`
pair is stored under its own key in the staking namespace, so a block writes
only the pairs it changed and a delegate with a large voter set does not pay to
rewrite that set on every bucket change. A stored weight is strictly positive; a
pair whose weight reaches zero is removed rather than stored as zero.

A node MUST load these entries at startup rather than recomputing them. The
weights a settlement pays against are then the values the network agreed on, not
a quantity each node derives for itself.

Implementations MUST NOT instead commit a summary of a locally reconstructed
table — a hash or equivalent digest — and verify it at startup. Such a check has
no safe outcome. A mismatch cannot be reconciled, because the committed summary
cannot be inverted to recover the agreed values; and it cannot be overridden,
because rewriting the entry at a height the network has already committed
diverges from the chain. The failure is also uniform: every node runs the same
maintenance logic, so every node would reach the same mismatch and refuse to
start together. Storing the weights themselves removes the second derivation and
with it the possibility of disagreement.

At `PutPollResult` for an era-boundary epoch, the protocol writes one
`CandidatePollSnapshot` per candidate:

```proto
message VoterWeightEntry {
  bytes voter = 1;
  bytes weight = 2;
}

message CandidatePollSnapshot {
  uint64 blockCommissionBasisPoints = 1;
  uint64 epochCommissionBasisPoints = 2;
  bool registered = 3;
  bool onchainRewardEnabled = 4;
  repeated VoterWeightEntry entries = 5;
  bytes totalWeight = 6;
  bytes snapshotHash = 7;
  uint32 lastWeightedIndex = 8;
  bool hasWeightedEntries = 9;
}
```

`onchainRewardEnabled` freezes mode selection for the reward era. For a legacy
delegate it is false, and the protocol skips the `DelegateProfile` and voter
weight reads and stores no voter entries. For an on-chain delegate, `entries`
contains one aggregated entry per voter and is sorted by voter address bytes in
ascending order. The ordering is consensus-critical because the settlement
cursor stores numeric voter indexes. Settlement does not mutate this canonical
snapshot order; it applies a frozen circular starting offset while traversing
the list.

The snapshot caches:

- the sum of all positive voter weights;
- the index of the final positive-weight voter;
- whether at least one positive-weight entry exists; and
- a domain-separated hash of the complete ordered `(voter, weight)` list.

The snapshot hash is:

```text
keccak256(
    keccak256("iip59.delegatedistributed.snapshot.v1") ||
    uint64_be(entryCount) ||
    for each entry: voter[20] || uint256_be(weight)
)
```

These values are frozen with the snapshot. Settlement initialization determines
the allocation metadata once from that frozen list and stores it in the cursor,
so continuation blocks do not recompute total weight or rescan preceding voter
weights.

If no usable voter-weight view or no positive voter weight is available for an
on-chain delegate, its voter pool remains pending. It is not redirected to
delegate commission.

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
an era boundary.

For each currently rewarded on-chain candidate whose pending voter pool is
non-zero, the protocol creates one frozen work item:

```proto
message EpochDrainDelegateWork {
  bytes candidate_identifier = 1;
  bytes voter_amount_frozen = 2;
  bytes reward_address = 3;
  bytes epoch_commission = 4;
  bytes voter_amount_distributed = 5;
  bytes total_weight = 6;
  bytes snapshot_hash = 7;
  uint32 last_weighted_index = 8;
  bool has_weighted_entries = 9;
  uint32 voter_start_index = 10;
}

message EpochDrainCursor {
  uint64 target_era = 1;
  uint32 delegate_index = 2;
  repeated EpochDrainDelegateWork delegates = 3;
  uint32 voter_index = 4;
  bytes settlement_seed = 5;
  uint32 delegate_start_index = 6;
  bool completed = 7;
  uint64 completed_height = 8;
  uint64 start_epoch = 9;
  uint64 end_epoch = 10;
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
```

`parentBlockHash` is the hash of the block immediately preceding the boundary
block. `targetEra` is the boundary epoch number stored in the cursor. Every
validator executing the boundary block therefore derives the same `R`.

The protocol uses that single `R` for every circular starting offset:

```text
delegateStartIndex = R % delegateCount
voterStartIndex[d] = R % voterCount[d]
```

Modulo is evaluated only for a non-empty list; an empty list has offset zero
and creates no distributable work. The frozen delegate work list is first
assembled in the existing epoch-reward candidate order, then persisted in
circular traversal order beginning at `delegateStartIndex`. Each canonical,
address-sorted voter snapshot remains unchanged; its work item records
`voter_start_index` instead.

The fields have the following meaning:

- `target_era` is the boundary epoch number that initialized the settlement.
- `start_epoch` and `end_epoch` identify the epoch window covered by the
  settlement. Normally `end_epoch = target_era` and
  `start_epoch = end_epoch - EpochsPerRewardEra + 1`. Overrun recovery carries
  an older unfinished cursor's `start_epoch` into the replacement cursor.
- `completed` distinguishes a live drain from the retained result of the most
  recent completed settlement; `completed_height` is the block that ran its
  final chunk.
- `settlement_seed` is the 32-byte value used for all list offsets.
- `delegate_start_index` identifies the selected start in the original
  canonical delegate list; `delegates` is stored in the resulting circular
  order.
- `delegate_index` identifies the next item in that persisted delegate order.
- `voter_start_index` identifies the selected start in the canonical voter
  snapshot.
- `voter_index` is the next logical voter position in circular traversal. Its
  physical snapshot index is
  `(voter_start_index + voter_index) % voter_count`.
- `voter_amount_frozen` is the pool balance allocated by this settlement.
- `voter_amount_distributed` is the amount already paid from that frozen
  balance.
- `reward_address` and `epoch_commission` preserve the routing and log values
  from initialization.
- `last_weighted_index` is the logical index of the final positive-weight
  voter in circular traversal; the remaining metadata preserves the frozen
  voter allocation inputs.

The cursor is a singleton. `completed = false` means a settlement is active.
Its delegate work list is immutable except for distribution progress. A
completed cursor is retained for voter queries until the next era boundary,
then cleared or overwritten by the next settlement. This retains only one
settlement and does not create an append-only history.

The pending pool itself is not frozen: later rewards can accrue behind the
cursor. A chunk decrements only what it actually distributes. Any newer
balance remains available to a later settlement.

### 8. Chunked Voter Distribution

While an incomplete cursor exists, every block that is not the last block of an epoch
includes a protocol-generated `VoterRewardChunk` system action. Epoch-final
blocks run `GrantEpochReward` and do not also run a voter chunk.

One action walks the cursor in the frozen circular delegate and voter orders.
Across all delegates touched by the action, it processes no more than
`VoterBudgetPerBlock` voter entries. A value of zero means unbounded. There is
no separate delegate count or compound count limit.

If the budget ends inside a delegate, `delegate_index` stays on that delegate
and `voter_index` advances to the next voter. If it ends exactly at a delegate
boundary, the next block starts with the next delegate.

#### 8.1 Voter allocation

For every positive-weight voter other than the final positive-weight voter in
the frozen circular traversal:

```text
share[i] = floor(voterAmountFrozen * weight[i] / totalWeight)
```

The final positive-weight voter receives:

```text
share[last] = voterAmountFrozen - sum(previous shares)
```

Zero-weight entries receive zero. The final positive-weight voter is selected
after applying `voter_start_index`, so division dust follows the same circular
order. This rule guarantees that all chunks for a completed delegate sum
exactly to `voterAmountFrozen`, independent of the chunk size.

The cursor's `total_weight`, `last_weighted_index`, and cumulative
`voter_amount_distributed` make each continuation proportional to the current
window rather than all preceding voters.

#### 8.2 Direct payout

Unless compound routing succeeds, the protocol adds the share directly to the
voter's effective reward-destination account balance as resolved in the chunk
block. The voter does not receive a rewarding `unclaimedBalance` entry and
neither the voter nor the recipient needs to submit `ClaimFromRewardingFund`.

Each non-zero direct payout emits a transaction log with:

```text
type      = CLAIM_FROM_REWARDING_FUND
sender    = RewardingPoolAddr
recipient = effective voter reward destination
amount    = voter share
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

An eligible share is added to that bucket through the staking protocol.
Compound value leaves the rewarding fund and enters the staking bucket pool.
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

After routing a window, the protocol:

- decrements the candidate's pending pool by the amount actually paid;
- decreases rewarding total balance by the same outflow;
- records the cumulative distributed amount in the cursor; and
- persists the next delegate and voter indexes when work remains.

These updates occur atomically with account or staking changes.

### 9. Settlement Finalization

When all cursor work items finish, the protocol resolves pending-pool entries
that were not represented in the cursor. Such an entry belongs to a candidate
that accumulated rewards but no longer participates in the current reward
split.

For each orphaned pool:

1. if candidate state still exists, pay the full pool directly to the
   candidate's current owner;
2. if candidate state no longer exists, return the amount to the rewarding
   fund's available balance; and
3. delete the pool and its index entry.

The fallback emits a `BLOCK_REWARD` reward log for observability. It never
burns the pending amount.

Pools represented by a cursor entry but skipped because their snapshot is
missing, changed, or has no positive voter weight are not treated as orphans.
They remain pending for a future era snapshot.

After orphan handling, the protocol sets `completed = true`, records the final
block height, and retains the cursor. Completed cursors do not produce further
`VoterRewardChunk` actions. At the next era boundary, the protocol clears the
completed cursor before initializing the next one.

### 10. Overrun Recovery

At settlement initialization, an incomplete cursor from the previous reward
era may still exist. This MUST NOT halt block production. A completed cursor is
not an overrun and is cleared without emitting an overrun log.

The protocol:

1. sums the live pending-pool balances for work items from the old
   `delegate_index` to the end;
2. emits `EPOCH_DRAIN_OVERRUN` with the old `target_era`, remaining delegate
   count, and live residue;
3. deletes the stale cursor without deleting any pending pool; and
4. continues normal initialization, freezing current live pool balances into
   a new cursor whose `start_epoch` preserves the oldest unfinished window.

Already distributed amounts are not paid again because they have already been
removed from their pools. Undistributed residue and rewards accrued after the
old initialization remain in the live pools. The new settlement allocates
those balances using the new era's voter snapshot.

### 11. Receipt and Transaction Logs

#### 11.1 DelegateDistributed

Each successfully routed delegate window emits an EVM-compatible event:

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
    uint64[] compoundBucketIds
);
```

- `epoch` is the epoch containing the chunk block.
- `delegate` is the candidate identity.
- `rewardAddr` is the candidate owner frozen at settlement initialization.
- `totalCommission` is the epoch commission paid by the boundary
  `GrantEpochReward` for this cursor item. It excludes block commission and
  commissions paid in earlier epochs of the era.
- `totalVoterPool` is the sum of `amounts` in this event's window.
- `snapshotHash` identifies the complete frozen voter-weight list.
- `voters`, `recipients`, `amounts`, and `compoundBucketIds` are parallel
  arrays.
- `voters[i]` is the beneficiary whose frozen weight earned the reward.
- For a direct payout, `recipients[i]` is the account actually credited. For a
  compound payout, it equals `voters[i]` and `compoundBucketIds[i]` identifies
  the actual staking destination.
- `compoundBucketIds[i] == 0` means direct payout.
- `compoundBucketIds[i] > 0` is the actual native bucket that received the
  compound payout.

A delegate may emit multiple events. Their block order and voter arrays,
together with the cursor's frozen start indexes, reconstruct circular cursor
order, and their `totalVoterPool` values sum to the frozen amount when the
delegate completes. `snapshotHash` remains stable across all chunks using the
same voter snapshot.

#### 11.2 Cursor progress

Every `VoterRewardChunk` first emits a `CURSOR_PROGRESS` reward log. Its
address field encodes:

```text
targetEra:delegateIndex:voterIndex:delegatesRemaining
```

Its amount is the fixed string `"0"`. Monitoring systems can detect a stalled
or slow settlement without reading internal state.

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
| `VoterRewardSnapshot(candidateID)` | Frozen mode, profile rates, voter weights, total weight, and snapshot hash. |
| `VoterRewardAddress(candidateID)` | Effective destination under the frozen mode: current owner in on-chain mode or stored reward address in legacy mode, plus the reward-address update marker. |
| `VoterRewardDestination(voterAddress)` | Effective direct voter recipient, whether an override is explicitly set, and the set height. |
| `VoterRewardStatus(candidateID, voterAddress)` | One voter's status, epoch range, circular index, and exact reward amount in the active or most recently completed settlement. |

Equivalent Web3 read methods are available through the rewarding protocol
state interface:

```solidity
pendingBlockRewardPool(address candidateId)
pendingBlockRewardPoolIndex()
epochDrainCursor()
voterRewardSnapshot(address candidateId)
voterRewardAddress(address candidateId)
voterRewardDestination(address voter)
voterRewardStatus(address candidateId, address voter)
```

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

The `epochDrainCursor()` Web3 result includes `startEpoch`, `endEpoch`,
`completed`, `completedHeight`, `settlementSeed`, `delegateStartIndex`, and a
`voterStartIndices` array parallel to the returned candidate IDs. Native
`ReadState` returns the same fields in the cursor protobuf. This makes the
latest settlement's circular order independently reconstructable.

`VoterRewardStatus` returns:

```text
targetEra
eraStartEpoch
eraEndEpoch
settlementCompleted
completedHeight
status
logicalVoterIndex
voterStartIndex
rewardAmount
```

`status` is one of:

| Status | Meaning |
|---|---|
| `NO_ACTIVE_SETTLEMENT` | No active or completed settlement cursor exists. |
| `CANDIDATE_NOT_INCLUDED` | The candidate has no frozen work item in the reported settlement. |
| `VOTER_NOT_INCLUDED` | The voter is absent from that candidate's frozen snapshot. |
| `WAITING` | The cursor has not processed this voter. |
| `PROCESSED` | The cursor has passed this voter. A zero-weight or zero-share voter can be processed without receiving funds. |
| `SNAPSHOT_UNAVAILABLE` | The frozen snapshot is missing, stale, or inconsistent with the cursor, so status cannot be derived safely. |

`logicalVoterIndex` is the voter's position after applying the settlement's
circular offset. `rewardAmount` is the exact amount assigned from the frozen
voter pool, including any integer-division remainder assigned to the final
positive-weight voter. `settlementCompleted` and `completedHeight` distinguish
the retained latest result from an in-progress cursor. The method retains only
the most recent settlement until the next era boundary; it is not a historical
ledger. `PROCESSED` does not identify whether the payout was direct or
compounded. Receipt events are the source for the executed destination and
exact per-voter payout block.

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
| `VoterBudgetPerBlock` | 2000 | Maximum voter entries processed by one chunk action; zero means unbounded. |
| `VoterWeightSeedBatchSize` | 2000 | Maximum `(candidate, voter)` weight entries written per block while materializing the weight table at activation; zero writes the whole table in one block. |
| `HermesRewardVaultAddresses` | two legacy Hermes vaults | Reward addresses whose pre-fork delegates migrate automatically. |
| `DelegateProfileContractAddress` | network-specific | Contract containing per-delegate voter portions. |
| `AutoDepositContractAddress` | network-specific | Contract containing per-voter compound preferences. |

`EpochsPerRewardEra` MUST be non-zero on an activated network. There is no
separate compound or delegate-count limit in the settlement algorithm.

`VoterWeightSeedBatchSize` applies only during the activation window described
in section 1.1 and is not consulted afterwards. It trades per-block cost against
the number of blocks the window spans, and the total work is the same either
way, so it SHOULD be sized for block-budget headroom rather than for a short
window: the window need only close well inside the first era, and an era is
several orders of magnitude longer than the pass requires at any reasonable
value. Zero is appropriate only for test networks.

For an era containing `B` blocks per epoch and `E` epochs, at most roughly
`E * (B - 1)` continuation blocks are available because every epoch-final
block is reserved for epoch rewards. A bounded configuration should satisfy:

```text
VoterBudgetPerBlock * availableContinuationBlocks
    >= expected (candidate, voter) entries per settlement * safety factor
```

Capacity MUST be estimated from the sum of voter-list lengths across all
settled candidates, not from the number of distinct voter addresses. Operators
SHOULD include headroom for voter growth and monitor cursor age, remaining
entries, and `EPOCH_DRAIN_OVERRUN` logs. With the defaults and `B = 360`, the
nominal capacity is approximately `24 * 359 * 2000 = 17,232,000`
candidate-voter entries per era. Networks MUST benchmark representative
validation hardware before activation; the nominal count is not a substitute
for block mint and validation latency measurements.

Each direct payout adds one rewarding-state lookup for the voter's sparse
destination override. With the default budget, a direct-only chunk therefore
performs at most 2,000 such lookups in addition to account writes and the
existing AutoDeposit checks. Compound payouts do not require this lookup.
Benchmarks MUST include both mostly-unset and densely-configured destination
state because archive/history-index I/O and cache behavior can differ.

If this capacity is exceeded, Overrun Recovery preserves funds and carries the
remaining pools forward.

### 15. Failure Semantics

Failures are handled according to their scope:

| Condition | Required behavior |
|---|---|
| Missing, partial, malformed, or unreadable DelegateProfile entry | Mark that profile unregistered for the snapshot and pay 100% directly to the owner. |
| No usable voter snapshot or no positive total weight | Keep the pool pending and retry in a future era. |
| Era boundary reached before the activation-time weight materialization completes | Freeze snapshots with no voter entries; keep the pools pending and settle in a later era. This is an expected transient, not an error. |
| Snapshot hash changes after cursor initialization | Skip the stale work item and keep its pool pending. |
| AutoDeposit lookup fails | Pay that voter directly. |
| Voter destination override is absent | Pay the voter account directly. |
| Bucket is missing, unreadable, contract-based, not owned by voter, not auto-staked, or unstaked | Pay the effective voter reward destination directly. |
| Invalid voter destination action length | Reject the action. |
| Malformed persisted voter destination state | Fail the state transition; do not guess or truncate an address. |
| Previous cursor survives to the next era boundary | Execute Overrun Recovery. |
| Candidate pool becomes orphaned but candidate state exists | Pay the candidate owner directly. |
| Candidate state for an orphaned pool is absent | Return the amount to rewarding available balance. |
| Invalid persisted state, account write failure, staking deposit mutation failure, or log encoding failure | Fail the state transition; normal block validation and rollback apply. |

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

### Rotated settlement starts

A fixed canonical start would repeatedly favor the same head of the delegate
and voter lists whenever a settlement overruns its era. Selecting a circular
start from the previous block hash changes which entries are processed first
without changing membership, weights, the proportional allocation rule, or
total fund movement. Because exact conservation assigns integer-division dust
to the final positive-weight voter in traversal order, rotation can change the
recipient of that bounded remainder. Reusing one seed for all lists keeps the
state compact and makes the entire traversal straightforward to reproduce from
archive state.

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

Reward mode, voter weights, profile rates, the settlement cursor's owner
destination, and the settlement amount are frozen so all validators reproduce
the same allocation across multiple blocks. The live pool remains able to
receive later rewards; those newer funds are unambiguously deferred to a future
cursor.

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

All allocation inputs and circular offsets are frozen in state and committed
to the state root. Aggregated voter weights are likewise committed and are
loaded rather than recomputed (section 4), so a restart cannot produce a node
whose weights differ from the network's. The settlement seed depends only on the
prior block hash and the boundary epoch, both identical for every validator
executing a given boundary block. Cursor, account, pool, and bucket changes are
part of the same block state transition. A reorganization changes the parent
hash but also reverts the seed, payout, and cursor advance together before
deterministic re-execution.

The settlement seed is not a source of cryptographic randomness and MUST NOT
be used for reward eligibility, weight, commission, or total allocation. A
producer near the boundary may have limited influence over a candidate parent
block hash, but that influence changes only service order and which final
positive-weight voter receives the integer-division remainder. It cannot change
list membership, frozen weight, commission, or total distributed value. For
`N` positive-weight voters, the remainder added beyond ordinary floor
allocation is strictly less than `N` rau.

### Fund conservation

For each split:

```text
commission + voterShare = source reward
```

For each completed delegate settlement:

```text
sum(direct payouts) + sum(compound payouts) = voterAmountFrozen
```

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
non-zero. Delegate iteration is limited by the existing epoch-reward candidate
set and has no additional IIP-59 cap. `VoterRewardChunk` is protocol-generated
and cannot be submitted as an arbitrary user action. Networks MUST size the
voter budget and era length using representative validation hardware.

Snapshot construction and DelegateProfile reads occur only at era boundaries
and only for on-chain delegates. The voter-weight view is maintained
incrementally so boundary work does not need to rebuild weights from all
historical buckets.

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

- `action/protocol/staking/` maintains voter weights, resolves migration mode,
  handles explicit opt-in, and freezes snapshots.
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
