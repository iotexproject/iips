```
IIP: 59
Title: Protocol-Native Voter Reward Distribution
Author: Raullen Chai (@raullen), Chen Chen (@envestcc)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-20
Updated: 2026-07-27
```

## Simple Summary

Replace the Hermes off-chain voter reward service with a protocol-native,
deterministic reward pipeline. After activation, every delegate's block and
epoch rewards are split between the delegate and its voters. Voter rewards
accumulate in per-delegate pools and are distributed in bounded chunks to
voter accounts or eligible compound staking buckets.

## Abstract

IoTeX delegates currently rely on Hermes to claim protocol rewards, apply
delegate-configured reward portions, and distribute the voter portion.
IIP-59 moves that work into consensus.

At activation, all delegates switch to on-chain voter reward distribution.
There is no delegate opt-in. The existing `DelegateProfile` contract remains
the source of the block-reward and epoch-reward voter portions. If a delegate
has no complete registered profile, both streams default to 100% for voters.

The protocol performs distribution in five named stages:

1. **Reward Accumulation** - block and epoch voter portions enter a
   per-delegate pending pool, while delegate commission is credited
   immediately.
2. **Settlement Initialization** - at a reward-era boundary, the protocol
   freezes voter weights and creates a persistent settlement cursor.
3. **Chunked Voter Distribution** - subsequent blocks pay at most
   `VoterBudgetPerBlock` voters in deterministic order.
4. **Settlement Finalization** - the last chunk resolves orphaned pools and
   deletes the cursor.
5. **Overrun Recovery** - if a settlement reaches the next reward-era
   boundary, its remaining pools are carried into a newly initialized
   settlement instead of halting the chain.

Voters without an eligible compound bucket receive IOTX directly in their
primary account and do not need a separate claim. Voters with an eligible
native staking bucket receive the reward as an added bucket deposit.

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

- Distribute every delegate's voter rewards under consensus after activation.
- Preserve the existing `DelegateProfile` reward portions.
- Include voting weight from protocol-supported native and contract staking.
- Support direct payout and native-bucket compounding.
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
- Preserving Hermes as an alternative path after activation.

## Terminology

| Term | Definition |
|---|---|
| **Candidate identity** | Stable candidate identifier used as the key for IIP-59 state. It is not the operator address, which may change. |
| **Reward era** | A configured run of `EpochsPerRewardEra` epochs between voter settlements. |
| **Era boundary** | An epoch `E` for which `E > 0` and `E % EpochsPerRewardEra == 0`. |
| **Effective reward address** | Address that receives delegate commission and other delegate-directed rewards after activation. |
| **Pending voter pool** | Per-candidate balance containing voter portions not yet distributed. |
| **Voter snapshot** | Frozen, address-sorted list of aggregated voter weights plus the delegate's profile rates. |
| **Settlement cursor** | Persistent progress record for a multi-block voter distribution. |
| **Direct payout** | Transfer from the rewarding protocol to the voter's primary account. No later claim is required. |
| **Compound payout** | Transfer from the rewarding protocol to an eligible native staking bucket owned by the voter. |

## Specification

### 1. Activation and Universal Transition

IIP-59 is activated by a hardfork height. Before the activation height, the
legacy rewarding behavior is unchanged. At and after the activation height:

- every delegate uses protocol-native voter reward distribution;
- no opt-in or opt-out state or action exists;
- Hermes MUST stop distributing newly generated delegate voter rewards;
- registered `DelegateProfile` portions are enforced by the protocol; and
- an unregistered or incomplete profile defaults to zero delegate commission,
  meaning 100% of both base reward streams belongs to voters.

The feature context exposes the inverse gate
`NoVoterRewardDistribution`. The IIP-59 path is active when that value is
`false`.

### 2. Effective Reward Address

The legacy candidate reward address is not automatically reused after
activation. Candidate state contains an additional marker:

```proto
message Candidate {
  // Existing fields omitted.
  bool rewardAddressUpdated = 12;
}
```

The effective post-activation reward address is:

```text
if candidate.rewardAddressUpdated:
    effectiveRewardAddress = candidate.rewardAddress
else:
    effectiveRewardAddress = candidate.ownerAddress
```

For candidates that already exist at activation, `rewardAddressUpdated` is
false, so their effective reward address follows the current owner and the
legacy reward address is ignored. A post-activation candidate registration
marks its supplied reward address as explicit. A post-activation
`CandidateUpdate` that supplies a reward address also sets the marker to true.

If ownership changes while the marker is false, the effective address follows
the new owner. Once an explicit reward address has been set, it remains the
effective address until another candidate update changes it.

The marker distinguishes migration state from a deliberately configured
address. It does not reintroduce reward-distribution opt-in.

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
both commission rates are zero. This fallback is deterministic and sends the
full base reward streams to voters.

Profile rates are frozen at the next era snapshot. A profile update does not
change rewards already accumulating under the current snapshot.

### 4. Voter Weight Tracking and Snapshot

The staking protocol maintains an incremental voter-weight view. Bucket state
changes update the aggregated `(candidate identity, voter)` weight using the
same weighting rules used by the staking and poll protocols. This includes
eligible weight represented by native staking and contract staking.

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
  repeated VoterWeightEntry entries = 5;
  bytes totalWeight = 6;
  bytes snapshotHash = 7;
  uint32 lastWeightedIndex = 8;
  bool hasWeightedEntries = 9;
}
```

`entries` contains one aggregated entry per voter and is sorted by voter
address bytes in ascending order. The ordering is consensus-critical because
the settlement cursor stores a numeric voter index.

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

If no usable voter-weight view or no positive voter weight is available, the
delegate's voter pool remains pending. It is not redirected to delegate
commission.

### 5. Reward Split

For a non-negative reward amount and a commission rate in basis points:

```text
commission = floor(amount * commissionBps / 10000)
voterShare = amount - commission
```

Rounding therefore favors voters. The delegate never receives division dust.

The split rate comes from the latest frozen voter snapshot. If no snapshot is
available after activation, the commission rate is zero.

### 6. Reward Accumulation

#### 6.1 Base block reward

On every block after activation, `GrantBlockReward` resolves the producer by
candidate identity and reads its effective reward address.

The base block reward is split as follows:

```text
commission -> effective reward address's rewarding account
voterShare -> pending voter pool[candidate identity]
```

Priority tips are fee income and are credited in full to the effective reward
address. They are not included in the voter split.

The `BLOCK_REWARD` reward log reports the immediate block commission. A zero
commission may produce no reward log. The pending voter share is later
attested by `DelegateDistributed` events.

#### 6.2 Epoch reward

On the last block of every epoch, `GrantEpochReward` first applies the existing
recipient selection, vote-weight, exemption, productivity, probation, and
slashing rules. Each resulting delegate epoch amount is then split:

```text
commission -> effective reward address's rewarding account
voterShare -> pending voter pool[candidate identity]
```

The voter share accumulates every epoch, not only at era boundaries. The
`EPOCH_REWARD` reward log reports the immediate epoch commission.

Unproductive-delegate slashing remains independent of IIP-59. Slashed value
moves from the staking bucket pool back to the rewarding pool, and the existing
probation-adjusted weight affects the epoch amount before the commission split.
Foundation bonuses keep their existing calculation and log format and are
credited to the effective reward address after activation.

#### 6.3 Pending voter pool

Each pool is stored in the rewarding namespace under a key formed from a fixed
prefix and the candidate identity. A separate sorted identity index permits
deterministic enumeration without scanning the namespace.

The pool is part of rewarding-fund accounting but is not an address-level
unclaimed balance. It cannot be withdrawn through the normal rewarding claim
action. New block and epoch voter shares may continue to accrue while an older
frozen amount is being distributed.

### 7. Settlement Initialization

Settlement initialization runs in `GrantEpochReward` when the current epoch is
an era boundary.

For each currently rewarded candidate whose pending voter pool is non-zero,
the protocol creates one frozen work item:

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
}

message EpochDrainCursor {
  uint64 target_era = 1;
  uint32 delegate_index = 2;
  repeated EpochDrainDelegateWork delegates = 3;
  uint32 voter_index = 4;
}
```

The fields have the following meaning:

- `target_era` is the boundary epoch number that initialized the settlement.
- `delegate_index` identifies the next delegate work item.
- `voter_index` identifies the next voter within that delegate's snapshot.
- `voter_amount_frozen` is the pool balance allocated by this settlement.
- `voter_amount_distributed` is the amount already paid from that frozen
  balance.
- `reward_address` and `epoch_commission` preserve the routing and log values
  from initialization.
- the remaining metadata preserves the frozen voter allocation inputs.

The cursor is a singleton. Its presence means a settlement is active. Its
delegate work list is immutable except for distribution progress.

The pending pool itself is not frozen: later rewards can accrue behind the
cursor. A chunk decrements only what it actually distributes. Any newer
balance remains available to a later settlement.

### 8. Chunked Voter Distribution

While a cursor exists, every block that is not the last block of an epoch
includes a protocol-generated `VoterRewardChunk` system action. Epoch-final
blocks run `GrantEpochReward` and do not also run a voter chunk.

One action walks the cursor in candidate and voter order. Across all delegates
touched by the action, it processes no more than `VoterBudgetPerBlock` voter
entries. A value of zero means unbounded. There is no separate delegate count
or compound count limit.

If the budget ends inside a delegate, `delegate_index` stays on that delegate
and `voter_index` advances to the next voter. If it ends exactly at a delegate
boundary, the next block starts with the next delegate.

#### 8.1 Voter allocation

For every positive-weight voter other than the final positive-weight voter:

```text
share[i] = floor(voterAmountFrozen * weight[i] / totalWeight)
```

The final positive-weight voter receives:

```text
share[last] = voterAmountFrozen - sum(previous shares)
```

Zero-weight entries receive zero. This rule guarantees that all chunks for a
completed delegate sum exactly to `voterAmountFrozen`, independent of the
chunk size.

The cursor's `total_weight`, `last_weighted_index`, and cumulative
`voter_amount_distributed` make each continuation proportional to the current
window rather than all preceding voters.

#### 8.2 Direct payout

Unless compound routing succeeds, the protocol adds the share directly to the
voter's primary account balance. The voter does not receive a rewarding
`unclaimedBalance` entry and does not need to submit
`ClaimFromRewardingFund`.

Each non-zero direct payout emits a transaction log with:

```text
type      = CLAIM_FROM_REWARDING_FUND
sender    = RewardingPoolAddr
recipient = voter
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

1. if candidate state still exists, credit the full pool to the candidate's
   effective reward address;
2. if candidate state no longer exists, return the amount to the rewarding
   fund's available balance; and
3. delete the pool and its index entry.

The fallback emits a `BLOCK_REWARD` reward log for observability. It never
burns the pending amount.

Pools represented by a cursor entry but skipped because their snapshot is
missing, changed, or has no positive voter weight are not treated as orphans.
They remain pending for a future era snapshot.

After orphan handling, the protocol deletes the cursor. Cursor absence is the
settlement-complete signal and stops further `VoterRewardChunk` actions.

### 10. Overrun Recovery

At settlement initialization, a cursor from the previous reward era may still
exist. This MUST NOT halt block production.

The protocol:

1. sums the live pending-pool balances for work items from the old
   `delegate_index` to the end;
2. emits `EPOCH_DRAIN_OVERRUN` with the old `target_era`, remaining delegate
   count, and live residue;
3. deletes the stale cursor without deleting any pending pool; and
4. continues normal initialization, freezing current live pool balances into
   a new cursor.

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
    uint256[] amounts,
    uint64[] compoundBucketIds
);
```

- `epoch` is the epoch containing the chunk block.
- `delegate` is the candidate identity.
- `rewardAddr` is the effective address frozen at settlement initialization.
- `totalCommission` is the epoch commission paid by the boundary
  `GrantEpochReward` for this cursor item. It excludes block commission and
  commissions paid in earlier epochs of the era.
- `totalVoterPool` is the sum of `amounts` in this event's window.
- `snapshotHash` identifies the complete frozen voter-weight list.
- `voters`, `amounts`, and `compoundBucketIds` are parallel arrays.
- `compoundBucketIds[i] == 0` means direct payout.
- `compoundBucketIds[i] > 0` is the actual native bucket that received the
  compound payout.

A delegate may emit multiple events. Their block order and voter arrays
reconstruct cursor order, and their `totalVoterPool` values sum to the frozen
amount when the delegate completes. `snapshotHash` remains stable across all
chunks using the same voter snapshot.

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

### 12. State Access

Archive nodes that provide historical IIP-59 verification MUST configure
`chain.historyIndexPath` and retain the resulting history index. The new state
objects support both the native state backend and archive secondary storage.

The rewarding protocol exposes these native `ReadState` methods:

| Method | Result |
|---|---|
| `PendingBlockRewardPool(candidateID)` | Current pending voter amount for one candidate. |
| `PendingBlockRewardPoolIndex()` | Sorted candidate identities with pool entries. |
| `EpochDrainCursor()` | Current cursor and all frozen work items, or an empty cursor. |
| `VoterRewardSnapshot(candidateID)` | Frozen profile rates, voter weights, total weight, and snapshot hash. |
| `VoterRewardAddress(candidateID)` | Effective reward address and whether it was explicitly set after activation. |

Equivalent Web3 read methods are available through the rewarding protocol
state interface:

```solidity
pendingBlockRewardPool(address candidateId)
pendingBlockRewardPoolIndex()
epochDrainCursor()
voterRewardSnapshot(address candidateId)
voterRewardAddress(address candidateId)
```

Historical verification combines these state reads with block receipts,
`DelegateDistributed` events, and transaction logs.

### 13. Genesis Parameters

The following network configuration is consensus-critical:

| Field | Default | Description |
|---|---:|---|
| `EpochsPerRewardEra` | 24 | Number of epochs between settlement initializations. |
| `VoterBudgetPerBlock` | 2000 | Maximum voter entries processed by one chunk action; zero means unbounded. |
| `DelegateProfileContractAddress` | network-specific | Contract containing per-delegate voter portions. |
| `AutoDepositContractAddress` | network-specific | Contract containing per-voter compound preferences. |

`EpochsPerRewardEra` MUST be non-zero on an activated network. There is no
separate compound or delegate-count limit in the settlement algorithm.

For an era containing `B` blocks per epoch and `E` epochs, at most roughly
`E * (B - 1)` continuation blocks are available because every epoch-final
block is reserved for epoch rewards. A bounded configuration should satisfy:

```text
VoterBudgetPerBlock * availableContinuationBlocks
    >= expected voter entries per settlement * safety factor
```

If this capacity is exceeded, Overrun Recovery preserves funds and carries the
remaining pools forward.

### 14. Failure Semantics

Failures are handled according to their scope:

| Condition | Required behavior |
|---|---|
| Missing, partial, malformed, or unreadable DelegateProfile entry | Mark that profile unregistered for the snapshot and use 100% voter share. |
| No usable voter snapshot or no positive total weight | Keep the pool pending and retry in a future era. |
| Snapshot hash changes after cursor initialization | Skip the stale work item and keep its pool pending. |
| AutoDeposit lookup fails | Pay that voter directly. |
| Bucket is missing, unreadable, contract-based, not owned by voter, not auto-staked, or unstaked | Pay that voter directly. |
| Previous cursor survives to the next era boundary | Execute Overrun Recovery. |
| Candidate pool becomes orphaned but candidate state exists | Credit the effective reward address. |
| Candidate state for an orphaned pool is absent | Return the amount to rewarding available balance. |
| Invalid persisted state, account write failure, staking deposit mutation failure, or log encoding failure | Fail the state transition; normal block validation and rollback apply. |

Fallback behavior MUST be deterministic from consensus state. Implementations
MUST NOT depend on an external RPC service or wall-clock result.

## Rationale

### Universal activation

A protocol hardfork should have one reward rule. Per-delegate opt-in would
retain two accounting paths, require Hermes to remain active, and make reward
behavior depend on mutable migration state. Universal activation removes that
ambiguity. The all-to-voters default also prevents an unregistered delegate
from receiving voter funds merely because it did not configure a profile.

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

### Direct account payout

Writing direct rewards to the voter account completes the payment in one state
transition. Keeping a second per-voter rewarding balance would require another
claim transaction and preserve unnecessary rewarding state indefinitely.

### Inline compound routing

Resolving compound preference while paying each voter avoids a separate
pending-compound state machine. The event records the actual destination
bucket, allowing auditors to verify both the decision and the staking inflow.

### Frozen inputs with live pools

Voter weights, profile rates, reward address, and the settlement amount are
frozen so all validators reproduce the same allocation across multiple blocks.
The live pool remains able to receive later rewards; those newer funds are
unambiguously deferred to a future cursor.

## Backward Compatibility

Before activation, reward grants, reward addresses, claims, logs, and state are
unchanged.

Activation is intentionally not backward compatible for delegate reward
operations:

- Hermes MUST stop distributing rewards generated after the fork.
- The legacy reward address is ignored for migrated candidates until a new
  reward address is explicitly set; the owner is the default.
- Delegate rewarding balances receive only commission and existing
  delegate-directed rewards, not the voter portion.
- Direct voter rewards appear immediately in account balance.
- Compound voter rewards appear as native staking bucket deposits.

Existing `DelegateProfile` and `AutoDeposit` contracts remain the configuration
sources, so delegates and voters do not need new configuration transactions
solely for IIP-59.

## Security Considerations

### Determinism and replay

All allocation inputs are frozen in state, ordered canonically, and committed
to the state root. Cursor, account, pool, and bucket changes are part of the
same block state transition. A reorganization reverts both a payout and its
cursor advance.

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

### Denial of service

The voter payout loop is bounded by `VoterBudgetPerBlock` when the parameter is
non-zero. Delegate iteration is limited by the existing epoch-reward candidate
set and has no additional IIP-59 cap. `VoterRewardChunk` is protocol-generated
and cannot be submitted as an arbitrary user action. Networks MUST size the
voter budget and era length using representative validation hardware.

Snapshot construction and DelegateProfile reads occur only at era boundaries.
The voter-weight view is maintained incrementally so boundary work does not
need to rebuild weights from all historical buckets.

### External contract state

DelegateProfile and AutoDeposit reads execute against on-chain EVM state under
the same block context on every validator. Per-entry read failures use defined
fallbacks. No off-chain API is consulted during consensus.

### Historical observability

Archive operators must configure history indexing to retain historical IIP-59
state. Without an archive history index, current-state reads and receipt logs
remain available, but arbitrary historical cursor and pool verification is not
guaranteed.

## Reference Implementation

The reference implementation is in
[`iotexproject/iotex-core` PR #4953](https://github.com/iotexproject/iotex-core/pull/4953):

- `action/protocol/staking/` maintains voter weights, freezes snapshots, and
  resolves the effective reward address.
- `action/protocol/poll/` invokes snapshot freezing at era-boundary poll
  updates.
- `action/protocol/rewarding/` implements reward accumulation, cursor
  initialization, chunk distribution, finalization, overrun recovery, and
  state reads.
- `action/protocol/rewarding/delegateprofile/` reads and validates profile
  portions.
- `action/protocol/rewarding/autodeposit/` resolves compound preferences and
  bucket eligibility.
- `action/protocol/rewarding/distributedlog/` defines and encodes
  `DelegateDistributed`.
- `action/protocol/rewarding/ethabi/` exposes the IIP-59 Web3 state interface.
- `blockchain/genesis/` defines activation and reward-era parameters.
