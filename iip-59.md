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
delegate-configured reward portions, and distribute the voter portion. IIP-59
moves that work into consensus.

At activation, delegates using either configured Hermes vault as their legacy
reward address switch to on-chain voter reward distribution. Others remain on
the legacy claim path and may switch later through a one-way, owner-authorized
action. The existing `DelegateProfile` contract remains the source of the
block-reward and epoch-reward voter portions; a delegate with no complete
registered profile pays 100% commission to its owner.

Delegate commission is paid immediately; voter portions accumulate in a
per-delegate pending pool. At each reward-era boundary the protocol freezes a
small set of per-delegate scalars, opens a copy-on-write window over the state
voter weights are computed from, and creates a settlement cursor. Later blocks
walk the voter address space in 256 shards, paying at most
`VoterBudgetPerBlock` distinct voters per block, with each voter's weight
recomputed on demand as of the freeze height through that window. The final
chunk sweeps residuals and orphaned pools and seals the window; a settlement
that reaches the next era boundary is carried forward rather than halting the
chain.

A voter with an eligible native staking bucket receives the reward as an added
bucket deposit. Every other voter is credited directly, in their own account or
an explicitly selected reward account, with no claim required.

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
| **Candidate identity** | Stable candidate identifier used as the key for IIP-59 state. Not the operator address, which may change. |
| **Reward era** | A run of `EpochsPerRewardEra` epochs between voter settlements. |
| **Era boundary** | An epoch `E` for which `E > 0` and `E % EpochsPerRewardEra == 0`. |
| **On-chain reward mode** | Protocol-native split and voter distribution; delegate-directed rewards go to the current owner. |
| **Legacy reward mode** | Existing behavior, "legacy mode" below: the full reward is credited to the stored reward address's rewarding balance and must be claimed. |
| **Pending voter pool** | Per-candidate balance holding voter portions not yet distributed. |
| **Voter snapshot** | Frozen per-delegate scalars for one era. Contains no per-voter list. |
| **Freeze height** | The height `H` at which an era's voter snapshots are written. Every weight the settlement pays against is evaluated as of `H`, whatever block the payment runs in. |
| **Era window** | The copy-on-write window opened at `H` and sealed at completion, preserving the as-of-`H` value of every key the weight recompute reads. |
| **Shard** | One of 256 partitions of the voter address space, selected by the first byte of the voter address. |
| **Settlement cursor** | Persistent progress record for a multi-block distribution, split into an immutable plan and a mutable progress record. |
| **Voter reward destination** | Account selected by a voter for direct payouts; the voter account by default. |

## Specification

### 1. Activation and Migration Eligibility

IIP-59 is activated by a hardfork height. Before it, legacy rewarding behavior
is unchanged. Candidate state carries two migration markers,
`voterRewardOnchainOptIn` and `rewardAddressUpdated`. At and after activation,
on-chain reward mode is enabled when:

```text
candidate.voterRewardOnchainOptIn ||
(
    !candidate.rewardAddressUpdated &&
    candidate.rewardAddress in genesis.hermesRewardVaultAddresses
)
```

`hermesRewardVaultAddresses` identifies the legacy vaults from which Hermes
distributed voter rewards, defaulting to
`io19604a05s2p3mecam2zz7d27hcr6ndyw80wvkmh` and
`io12mgttmfa2ffn9uqvn0yn37f4nz43d248l2ga85`.

The automatic rule applies only to reward addresses inherited from before the
fork. A candidate registered after activation, or one that updates its reward
address after activation, has `rewardAddressUpdated = true` and is not
automatically migrated merely because that address equals a Hermes vault.

A candidate owner may submit `SetVoterRewardOptIn(candidateIdentifier, true)`
after activation. The action is owner-only, idempotent, and one-way; an action
with `optIn = false` is invalid. If an automatically migrated candidate later
updates its reward address, the protocol first records
`voterRewardOnchainOptIn = true` to preserve its current mode.

Migration eligibility is evaluated when the protocol writes the next era
snapshot, so an explicit opt-in takes economic effect with that snapshot rather
than rewriting rewards already governed by the current one. A delegate that
meets neither condition remains entirely on the legacy path, and its profile
and voter snapshot are not used.

#### 1.1 Contract-staking owner index backfill

Settlement enumerates voters by address (section 8), so it needs an index from
owner address to the contract-staking buckets that owner holds. Native staking
already maintains one; contract staking does not, its buckets being keyed by
bucket ID with the owner as a field inside. The protocol builds a
contract-staking owner index and maintains it thereafter alongside every bucket
mutation.

The index MUST be written before any era window can open. It is built exactly
once, in the block whose height equals the activation height, in that block's
pre-state phase before any action executes. For each contract-staking
contract — the configured V1, V2, and V3 contracts plus any contract carrying a
recorded bucket high-water mark — the protocol scans that contract's bucket
state once, accumulates owner-to-bucket references in memory, and writes them
in ascending owner-address order. No persistent completion marker is required,
since every node either executes the activation block or starts from a snapshot
taken after it, and a node MUST NOT treat a later block as an opportunity to
repair the index. This is a single-block operation whose size is the deployed
contract-staking bucket population, and a network MUST confirm that population
against the activation-block budget before setting the activation height.

### 2. Reward Destinations

#### 2.1 Delegate reward destination

The destination depends on the frozen reward mode:

- **On-chain mode:** all delegate-directed rewards are paid immediately to the
  candidate's current owner account. They create no rewarding
  `unclaimedBalance` and require no claim. The stored legacy reward address is
  not used for newly generated rewards.
- **Legacy mode:** the full block reward, priority tip, epoch reward, and
  foundation bonus are credited to the stored reward address's rewarding
  balance, claimable through the existing action.

An ownership change therefore changes the direct destination for an on-chain
delegate; a reward-address update changes it only for a delegate still in
legacy mode. Mode selection is frozen in each era snapshot, so a configuration
change does not alter an active reward era or settlement.

Every non-zero direct delegate payout emits a transaction log of type
`CLAIM_FROM_REWARDING_FUND` from `RewardingPoolAddr` to the candidate owner for
the paid amount. The type describes an immediate protocol outflow, not a claim
transaction submitted by the owner.

#### 2.2 Voter direct reward destination

Each voter has one global direct reward destination, defaulting to the voter
account itself. A voter changes it with a voter-signed rewarding action, whose
payload is appended to `ActionCore` at field number 58:

```solidity
// SetVoterRewardDestination(recipient)
function setVoterRewardDestination(address recipient);

event VoterRewardDestinationSet(
    address indexed voter,
    address oldRecipient,
    address newRecipient
);
```

Only the transaction signer changes its own destination. A 20-byte non-zero
recipient different from the voter creates or replaces the override; an empty
recipient, the zero address, or the voter's own address clears it. Any other
byte length is invalid. Overrides are sparse state recording the recipient and
the height of the last set operation; clearing deletes the record, so an unset
or cleared destination reports `explicitlySet = false` and `updatedHeight = 0`.

The effective destination is resolved when the voter is paid, so a change
affects any payout not yet processed, including one in an active settlement,
but never rewrites a completed payout. It is not frozen in the era snapshot or
the settlement cursor.

Compound routing has precedence: a voter with an eligible compound bucket has
the reward deposited into that bucket and the direct destination ignored for
that payout. If compound lookup is absent, fails, or resolves to an ineligible
bucket, the fallback direct payout uses the effective destination at that
block. Crediting a contract account changes its balance only; it does not
invoke receiver code or a callback. Resolution is one level only — the
recipient's own voter reward destination is not followed.

### 3. Reward Portions from DelegateProfile

The protocol reads two fields from the existing `DelegateProfile` contract,
keyed by candidate identity: `blockRewardPortion` and `epochRewardPortion`, the
voter portions of the base block reward and of the delegate's epoch reward.
Both are basis points in `[0, 10000]` and are converted to commission rates:

```text
blockCommissionBps = 10000 - blockRewardPortion
epochCommissionBps = 10000 - epochRewardPortion
```

A profile is registered for IIP-59 only when both fields are present and valid.
If either is absent, out of range, or undecodable, the snapshot records
`registered = false` and both commission rates are `10000`, sending the full
reward streams directly to the candidate owner.

Profile rates are frozen at the next era snapshot; a profile update does not
change rewards already accumulating under the current one.

### 4. Era Snapshot and the Era Window

Voter weights are recomputed on demand during settlement, from the same bucket
state and the same weighting rules the staking and poll protocols already use,
covering both native and contract staking. No aggregated
`(candidate identity, voter)` weight table exists in state. What consensus
commits is not the weights but the conditions under which they are computed: a
per-delegate scalar snapshot, and a copy-on-write window that keeps the
underlying state readable as of one height for as long as the settlement runs.

#### 4.1 Per-delegate era snapshot

At the era boundary the protocol writes one snapshot per **opted-in**
candidate, taken from the candidate set rather than from the poll list; a
candidate not in on-chain reward mode gets no record at all. The height at
which these records are written is the freeze height `H`. The snapshot is
scalars only:

| Field | Meaning |
|---|---|
| `blockCommissionBasisPoints`, `epochCommissionBasisPoints` | Frozen profile rates (section 3). |
| `registered` | Whether a complete valid profile was found. |
| `onchainRewardEnabled` | Frozen mode selection for the era. |
| `totalWeight` | The candidate's `Votes` accumulator at `H`; the denominator of every voter share. `totalWeight == 0` means no payable voter set this era. |
| `freezeHeight` | `H` itself, carried with the snapshot rather than re-derived (section 4.3). |
| `selfStakeBucketIdx` | Self-stake bucket index at `H`, or `MaxUint64` for none. The only candidate field the weight recompute reads. |
| `snapshotHash` | Digest of the frozen parameters; the join key for the partial `DelegateDistributed` logs one settlement emits across many blocks. |

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

`flags` has bit 0 set when `registered` and bit 1 when `onchainRewardEnabled`.
`totalWeight` is left-padded to 32 bytes. The domain separator is `v2` because
`v1` scoped a digest of an entirely different shape.

If an on-chain delegate has `totalWeight == 0`, its voter pool remains pending
for a later era. It is not redirected to delegate commission.

#### 4.2 The era window

Settlement recomputes weights from bucket state over several blocks *after*
`H`, and it mutates that state itself: a compound payout grows the very bucket
whose weight a later chunk would measure. The protocol therefore opens a
copy-on-write **era window** at `H` and seals it when the settlement completes.
While the window is open:

- The first mutation of any covered key copies that key's pre-write value
  aside, tagged with `H`; later mutations in the same era leave the copy alone.
- A key that did not exist at `H` and is created afterwards is recorded as a
  tombstone, without which a read as of `H` would fall through to the live
  value and see a bucket the era never had.
- A read as of `H` resolves to the copy when one exists, to "did not exist"
  when a tombstone exists, and to the live value otherwise — correct because
  "no copy" means "not mutated since `H`".
- Two monotonically increasing quantities are frozen as scalars instead of
  being copied per key. A read as of `H` rejects a native bucket whose index is
  **at or above** the frozen total bucket count, and a contract bucket whose ID
  is **above** the contract's frozen high-water mark.

Copies are journaled under a dense per-era sequence, so reclaiming them after
the window seals is a bounded walk that can be spread across later blocks. No
window exists before the activation height or between a settlement completing
and the next era boundary; outside an open window the per-mutation cost is a
single small control-key read.

#### 4.3 On-demand weight recomputation

During settlement, one voter's weight for one delegate is computed from the
buckets that voter holds with that delegate, read through the era window and
evaluated at that delegate's own `freezeHeight`.

The evaluation height MUST be `freezeHeight` and MUST NOT be the height of the
block the chunk runs in. A contract-staking bucket that is not timestamp-based
measures its remaining duration against a block height, so substituting the
current height would make the same bucket worth different amounts in the first
and last chunks of one settlement. A work item that reaches settlement without
a freeze height MUST be skipped rather than evaluated at a substitute height.

The recompute is stateless, while the denominator `totalWeight` is the frozen
value of a path-dependent accumulator. The sum of recomputed weights is
therefore not guaranteed to equal `totalWeight`; section 8.1 specifies the
clamp that makes every such disagreement an under-payment.

### 5. Reward Split

For an on-chain delegate and a non-negative reward amount with a commission
rate in basis points:

```text
commission = floor(amount * commissionBps / 10000)
voterShare = amount - commission
```

Rounding therefore favors voters; the delegate never receives division dust.
The split rate comes from the latest frozen snapshot, and is `10000` when no
usable profile rate is available. A legacy delegate does not execute this
split: its complete reward follows the legacy path.

### 6. Reward Accumulation

#### 6.1 Base block reward

On every block after activation, `GrantBlockReward` resolves the producer by
candidate identity and reads its frozen reward mode. For an on-chain delegate
the commission goes to the current owner account immediately and the voter
share to that candidate's pending voter pool. Priority tips are fee income,
paid in full directly to the owner and not included in the voter split. For a
legacy delegate, both the base block reward and the priority tip go to the
stored reward address's rewarding balance.

For an on-chain delegate the `BLOCK_REWARD` reward log reports the immediate
block commission, and a zero commission may produce no log; for a legacy
delegate it reports the full credited amount. The on-chain pending voter share
is later attested by `DelegateDistributed` events.

#### 6.2 Epoch reward

On the last block of every epoch, `GrantEpochReward` first applies the existing
recipient selection, vote-weight, exemption, productivity, probation, and
slashing rules. Each resulting on-chain delegate epoch amount is then split the
same way, with the voter share accumulating every epoch rather than only at era
boundaries. The `EPOCH_REWARD` log reports the immediate epoch commission for
an on-chain delegate and the full amount for a legacy delegate, which creates
no pending pool.

Unproductive-delegate slashing, probation-adjusted weights, and foundation
bonuses keep their existing calculations and log formats. The foundation bonus
is paid directly to the owner for an on-chain delegate and to the stored reward
address's rewarding balance for a legacy one.

#### 6.3 Pending voter pool

Only on-chain delegates have pending voter pools. Each is stored in the
rewarding namespace keyed by candidate identity, with a separate sorted index
permitting deterministic enumeration without scanning the namespace. The pool
is part of rewarding-fund accounting but is not an address-level unclaimed
balance and cannot be withdrawn through the normal claim action. New block and
epoch voter shares may accrue while an older frozen amount is being
distributed.

### 7. Settlement Initialization

Settlement initialization runs in `GrantEpochReward` when the current epoch is
an era boundary. This is not the same block as the freeze height `H`: poll
results are written at roughly the midpoint of the preceding epoch, so `H`
precedes the boundary epoch's final block by about one and a half epochs.
Snapshots are frozen at `H`, the cursor is created at the boundary epoch's
final block, and the first continuation chunk runs in the first block of the
following epoch.

For each currently rewarded on-chain candidate whose pending voter pool is
non-zero, the protocol creates one frozen work item carrying the candidate
identity, the frozen voter amount, the reward address, the epoch commission,
the total weight and snapshot hash from section 4.1, and the freeze height and
self-stake bucket index the recompute needs. Carrying the last two means a
chunk never reads the live candidate record, which the drain itself mutates.

The cursor is persisted as two records with different mutability, so that a
block advancing one shard does not rewrite the whole frozen delegate list. The
**plan** holds the target era, the frozen work items, the settlement seed, the
start shard, and the epoch window, and is written once. The **progress** record
holds the completion flag and height, the count of drained shards, the resume
address, the per-delegate distributed totals, and the skip bitmap, and is
rewritten by every chunk.

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
block and `targetEra` is the boundary epoch number, so every validator derives
the same `startShard`. Shard `(startShard + n) mod 256` is the `n`-th visited.
The delegate work list keeps the existing epoch-reward candidate order and is
not rotated: rotation applies to the shard sequence, the only traversal order
the drain has.

Field notes:

- `targetEra` appears in both records and MUST match; a mismatch means one is
  stale.
- The epoch window is normally `endEpoch = targetEra` and
  `startEpoch = endEpoch - EpochsPerRewardEra + 1`. Overrun recovery carries an
  older unfinished cursor's `startEpoch` into the replacement.
- `resumeVoter` is the last voter address visited in the shard now in progress,
  empty when that shard has not been entered; resume skips every address less
  than or equal to it. It MUST be an address rather than an offset, because a
  shard's population changes between blocks and an offset would skip or repeat
  voters.
- The distributed totals are one running total per delegate, positionally
  aligned with the work items, with a short vector meaning the missing tail is
  zero. They are what the payout clamp measures against and MUST be persisted.
- The skip bitmap marks work items the drain determined it cannot pay. A
  skipped delegate contributes nothing to any voter's share and keeps its
  pending pool for a later era.

Field numbers 5, 8, 9, and 10 of the snapshot, plan, progress, and work-item
encodings belonged to a retired candidate-major drain and MUST NOT be reused.

The cursor is a singleton, and `completed = false` means a settlement is
active. A completed cursor is retained for voter queries until the next era
boundary, then cleared or overwritten. The pending pool itself is not frozen:
later rewards accrue behind the cursor, a chunk decrements only what it
distributes, and any newer balance remains available to a later settlement.

### 8. Chunked Voter Distribution

While an incomplete cursor exists, every block that is not the last block of an
epoch includes a protocol-generated `VoterRewardChunk` system action.
Epoch-final blocks run `GrantEpochReward` and do not also run a voter chunk.

One action walks the voter address space, not the delegate list. The space is
split into 256 shards by the first byte of the voter address, visited in the
rotation fixed by `startShard`. The action resumes at the cursor's current
shard, just past `resumeVoter`, and pays at most `VoterBudgetPerBlock`
**distinct voters**; zero means unbounded. There is no separate delegate or
compound limit, because a voter is paid once for everything they are owed
across every delegate they staked with, native and liquid-staking alike, in a
single combined transfer. The budget counts voters, not `(candidate, voter)`
pairs.

The voters of one shard are produced by merging, in ascending address order,
the per-shard ranges of the live native voter index, the live liquid-staking
voter index, and the corresponding copy-on-write ranges of the era window. The
merge is what makes membership as-of-`H` rather than as-of-now.

`VoterBudgetPerBlock` bounds only the voters a block *pays*. A second bound,
proportional to it, limits the index keys the block may *scan* (see Security
Considerations, "Denial of service"). When the scan bound truncates a shard,
the block pays only voters below the address range it can prove it covered end
to end, and advances `resumeVoter` to that coverage bound rather than to the
last address seen.

`resumeVoter` advances past every voter *visited*, not only every voter *paid*;
otherwise a voter whose recomputed weight is zero would be rediscovered and
re-skipped by every later block. A shard is counted in `shardsDone` only when
the scans covered it end to end.

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
`totalWeight`, which section 4.3 explains they need not. The clamp turns every
disagreement into an under-payment: a numerator that is too large stops at the
pool boundary, and one that is too small leaves a residual for section 9 to
sweep. There is no rule assigning floor-division dust to a distinguished voter.

The voter's payment is the sum of their clamped shares across all contributing
delegates, paid as one transfer to one destination. Each contributing
delegate's pending pool is drawn down by its own share and its distributed
total advances by the same amount; the clamp reads that total including payouts
made earlier in the same block. A voter whose total is zero is skipped without
a payment and without a log entry, but still advances the cursor.

#### 8.2 Direct payout

Unless compound routing succeeds, the protocol adds the voter's combined amount
directly to their effective reward-destination account balance as resolved in
the chunk block. Routing is decided once per voter and applies to the whole
combined amount, not per contributing delegate. The voter receives no rewarding
`unclaimedBalance` entry, and neither the voter nor the recipient needs to
submit `ClaimFromRewardingFund`.

Each non-zero direct payout emits a transaction log of type
`CLAIM_FROM_REWARDING_FUND` from `RewardingPoolAddr` to the effective voter
reward destination for the combined amount. The type represents an immediate
rewarding-fund outflow; it does not mean the voter submitted a claim.

#### 8.3 Compound payout

The existing `AutoDeposit` contract maps a voter to a preferred bucket ID. A
payout is compounded only if, at chunk execution, the voter has a non-zero
configured bucket ID and that bucket exists in native staking state, is a
native rather than a contract-staking bucket, is owned by the voter, has
auto-stake enabled, and is active and not unstaked.

An eligible voter's combined amount is added to that bucket through the staking
protocol, moving the value from the rewarding fund into the staking bucket
pool, and the chunk emits a `DEPOSIT_TO_BUCKET` transaction log from
`RewardingPoolAddr` to `StakingBucketPoolAddr` for the compounded amount.
Contract-staking weight participates in reward allocation, but its reward is
paid directly because contract-staking buckets are not eligible compound
targets.

If the AutoDeposit lookup fails, the configured bucket cannot be read, or the
bucket is ineligible, that voter deterministically falls back to direct payout.
A failure while applying an otherwise valid staking deposit is a
state-transition failure and is not silently converted after partial writes.

#### 8.4 Pool and fund updates

After each voter's combined transfer, the protocol decrements each contributing
candidate's pending pool by that candidate's share, decreases the rewarding
total balance by the same total outflow, and advances each contributing
candidate's distributed total. At the end of the block it persists
`shardsDone`, `resumeVoter`, the skip bitmap, and the distributed totals when
work remains. These updates occur atomically with account or staking changes.

### 9. Settlement Finalization

When all 256 shards are drained, the protocol finalizes in this order.

**1. Per-delegate residual sweep.** For each unskipped work item,
`residual = voterAmountFrozen - voterDistributed` is what floor division and
the payout clamp left behind. It is swept out of that delegate's pending pool
and folded into the distributed total, so a completed settlement satisfies
`voterDistributed == voterAmountFrozen` for every unskipped delegate by
construction. Skipped delegates are not swept; their whole frozen amount stays
pending for a later era.

**2. Orphan resolution.** A pending-pool entry not represented in the cursor
belongs to a candidate that accumulated rewards but no longer participates in
the reward split. For each: if candidate state still exists, pay the full pool
to the candidate's current owner; otherwise return the amount to the rewarding
fund's unclaimed balance. Then delete the pool's index entry.

Both the residual sweep and orphan resolution go through the same sink, each
emitting a `BLOCK_REWARD` reward log, and neither ever burns the pending
amount. A swept pool is decremented rather than deleted, because it may have
kept accruing behind the drain and that accrual belongs to the next era.

**3. Seal the era window.** No further read as of `H` is possible after this
point; copies retained by the window become reclaimable and are reclaimed in
bounded batches by later blocks.

The protocol then sets `completed = true`, records the final block height, and
retains the cursor. Completed cursors produce no further `VoterRewardChunk`
actions, and the next era boundary clears the completed cursor before
initializing its own.

### 10. Overrun Recovery

At settlement initialization, an incomplete cursor from the previous reward era
may still exist. This MUST NOT halt block production. A completed cursor is not
an overrun and is cleared without emitting an overrun log.

The protocol:

1. sums the live pending-pool balances of **every** delegate the stale cursor
   named, and counts how many still hold one;
2. emits `EPOCH_DRAIN_OVERRUN` with the old target era, that count, and the
   live residue;
3. deletes the stale cursor without deleting any pending pool; and
4. continues normal initialization, freezing current live pool balances into a
   new cursor whose start epoch preserves the oldest unfinished window.

The sum is over all delegates rather than a suffix because a voter-major drain
leaves most delegates partially paid, not a clean prefix done and a suffix
untouched. It uses the live pool balance because that is the true leftover;
already distributed amounts have left their pools and are not paid again.

Only one era window exists at a time, and the next era's window opens at the
next freeze height `H`, about one and a half epochs before the boundary block.
An overrunning drain therefore loses its window before overrun recovery detects
it: opening the new window seals the old one, which keeps the old copies
collectable but does not preserve as-of-`H` reads for the outgoing drain. The
bound that prevents this is capacity, not a runtime check — networks MUST size
`VoterBudgetPerBlock` and `EpochsPerRewardEra` so a settlement completes well
inside its era (section 14).

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

- `epoch` is the epoch containing the chunk block; `delegate` is the candidate
  identity and `rewardAddr` the owner frozen at settlement initialization.
- `totalCommission` is the epoch commission paid by the boundary
  `GrantEpochReward` for this cursor item, excluding block commission and
  commissions paid in earlier epochs of the era. `totalVoterPool` is the sum of
  `amounts` in this event's window.
- `snapshotHash` is the digest from section 4.1 and the join key across the
  many partial events one settlement emits.
- The five arrays are parallel. `voters[i]` is the beneficiary whose recomputed
  weight earned the reward; `amounts[i]` is this delegate's contribution to that
  voter's payment, not the voter's whole combined transfer, so a voter paid from
  several delegates in one block appears in several events in that block.
- For a direct payout, `recipients[i]` is the account actually credited. For a
  compound payout it equals `voters[i]` and `compoundBucketIds[i]` identifies
  the staking destination.
- `compounded[i]` is the direct-or-compound discriminator. Consumers MUST use
  it and MUST NOT infer routing from `compoundBucketIds[i]`: native bucket 0 is
  a real bucket, so `compoundBucketIds[i] == 0` is ambiguous.

A delegate may emit multiple events, whose `totalVoterPool` values sum to the
frozen amount minus the residual swept at completion. `snapshotHash` is stable
across all chunks of one settlement, so joining on it reassembles a delegate's
whole distribution.

#### 11.2 Cursor progress and overrun logs

Every `VoterRewardChunk` first emits a `CURSOR_PROGRESS` reward log whose
address field encodes `targetEra:shardsDone:hex(resumeVoter):shardsRemaining`
and whose amount is the fixed string `"0"`, so monitoring systems can detect a
stalled settlement without reading internal state.

`EPOCH_DRAIN_OVERRUN` encodes `targetEra:delegatesRemaining` in its address
field and the live pending-pool residue as its amount. It is emitted before the
new boundary epoch's per-delegate reward logs.

#### 11.3 Configuration events

A successful explicit opt-in emits the native staking receipt event
`VoterRewardOptInSet(bytes32 indexed candidateIdentifier, bool optIn)`, with
`optIn` always true.

A successful `SetVoterRewardDestination` emits `VoterRewardDestinationSet` as
specified in section 2.2. `oldRecipient` and `newRecipient` are effective
addresses: setting the first override reports the voter as `oldRecipient`, and
clearing an override reports the voter as `newRecipient`.

### 12. State Access

Archive nodes that provide historical IIP-59 verification MUST configure
`chain.historyIndexPath` and retain the resulting history index. The new state
objects support both the native state backend and archive secondary storage.

The rewarding protocol exposes these reads, each with a native `ReadState`
name and an equivalent Web3 method:

| `ReadState` | Web3 | Result |
|---|---|---|
| `PendingBlockRewardPool(candidateID)` | `pendingBlockRewardPool(address)` | Current pending voter amount for one candidate. |
| `PendingBlockRewardPoolIndex()` | `pendingBlockRewardPoolIndex()` | Sorted candidate identities with pool entries. |
| `EpochDrainCursor()` | `eraDrainCursor()` | Active or most recently completed cursor: the settlement scalars including start shard, shards done, resume address and seed, plus the frozen work items and their distributed totals. Empty before the first settlement. |
| `VoterRewardSnapshot(candidateID)` | `voterRewardDelegateSnapshot(address)` | The frozen era scalars of section 4.1. |
| `VoterRewardAddress(candidateID)` | `voterRewardAddress(address)` | Effective destination under the frozen mode, plus the reward-address update marker. |
| `VoterRewardDestination(voterAddress)` | `voterRewardDestination(address)` | Effective direct recipient, whether an override is explicitly set, and the set height. With no override the recipient is the voter, `explicitlySet` is false and the height is zero. |
| `VoterRewardStatus(voterAddress)` | `voterRewardStatus(address)` | One voter's status, epoch range, and total reward in the active or most recently completed settlement, summed across every delegate they hold a frozen bucket with. |

`VoterRewardStatus` takes one argument, not two: the drain pays a voter once
across every delegate, so there is no per-candidate answer to ask for. Its
`status` is one of:

| Status | Meaning |
|---|---|
| `NO_ACTIVE_SETTLEMENT` | No active or completed settlement cursor exists. |
| `VOTER_NOT_INCLUDED` | The voter holds no frozen bucket with any delegate in the reported settlement. |
| `WAITING` | The shard walk has not reached this voter. |
| `PROCESSED` | The shard walk has passed this voter. A zero-weight or zero-share voter can be processed without receiving funds. |
| `SNAPSHOT_UNAVAILABLE` | No era window is open, so the amount cannot be derived from the state the settlement pays against. |

Position is measured in the rotation, not in raw shard IDs: the voter's own
shard maps to a rotation position compared against `shardsDone`, and inside the
shard in progress `resumeVoter` separates visited from pending. The reported
amount is computed by the same allocation function, with the same payout clamp,
that the drain itself uses, and is therefore answerable only while the era
window is open — after sealing, the protocol reports `SNAPSHOT_UNAVAILABLE`
rather than recomputing against live state and returning a figure nobody was
paid. `PROCESSED` does not identify whether the payout was direct or
compounded, and the method retains only the most recent settlement: receipts,
not this query, are the historical record.

### 13. Voter Preparation

Voters who want direct payouts to their voting account need take no action; the
reward is in the account after settlement and requires no claim. A voter who
uses a separate treasury, custody, or tax account MAY set it with
`SetVoterRewardDestination` and verify the effective value with
`VoterRewardDestination`.

Voters who want automatic compounding SHOULD register an eligible native
staking bucket — owned by the voter, active, auto-staked, and not unstaked — in
the existing `AutoDeposit` contract before their payout is processed.
Contract-staking votes count toward reward weight, but contract buckets are not
eligible compound destinations and those rewards are paid directly.

### 14. Genesis Parameters

The following network configuration is consensus-critical:

| Field | Default | Description |
|---|---:|---|
| `EpochsPerRewardEra` | 24 | Number of epochs between settlement initializations. |
| `VoterBudgetPerBlock` | 2000 | Maximum distinct voters paid by one chunk action; zero means unbounded. |
| `HermesRewardVaultAddresses` | two legacy Hermes vaults | Reward addresses whose pre-fork delegates migrate automatically. |
| `DelegateProfileContractAddress` | network-specific | Contract containing per-delegate voter portions. |
| `AutoDepositContractAddress` | network-specific | Contract containing per-voter compound preferences. |

`EpochsPerRewardEra` MUST be non-zero, and in practice MUST be at least 2: the
era window a settlement reads is superseded at the next freeze height (section
10), which falls roughly one and a half epochs before the next era boundary, so
a one-epoch era leaves no room between the two.

For an era of `E` epochs with `B` blocks each, at most roughly `E * (B - 1)`
continuation blocks are available, because every epoch-final block is reserved
for epoch rewards. A bounded configuration should satisfy:

```text
VoterBudgetPerBlock * availableContinuationBlocks
    >= expected distinct voters per settlement * safety factor
```

Capacity MUST be estimated from the number of **distinct voter addresses** with
a frozen bucket in the era, not from the sum of per-candidate voter-list
lengths: a voter staking with ten delegates costs one unit of budget, not ten.
With the defaults and `B = 360`, nominal capacity is approximately
`24 * 359 * 2000 = 17,232,000` distinct voters per era. That count is not a
substitute for measurement: networks MUST benchmark block mint and validation
latency on representative hardware before activation. If capacity is
nonetheless exceeded, Overrun Recovery preserves funds and carries the
remaining pools forward.

Each block additionally bounds the voter-index keys it may scan, at a fixed
multiple of `VoterBudgetPerBlock` that operators do not configure (section 8).

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

The last two rows are one rule with a deliberate default. A Failure receipt is
itself a consensus-visible outcome, so it is sound only when every node reaches
the same verdict. Whether a working set can serve an ordered range scan is a
node-local capability, not chain state: a proposer that settled Failure on such
an error would commit no payouts while validators that can scan commit payouts,
producing two state roots for one block. Implementations MUST therefore treat
"settle a Failure receipt" as opt-in per condition and halt on everything not
enumerated.

Fallback behavior MUST be deterministic from consensus state. Implementations
MUST NOT depend on an external RPC service or wall-clock result.

## Rationale

### Hermes-targeted migration and one-way opt-in

The automatic migration matches the existing operational boundary: delegates
whose rewards already flow through the configured Hermes vaults are exactly the
ones whose voter distribution Hermes performs. Delegates that manage rewards
independently keep their established address and claim workflow, avoiding an
unrequested change at the fork. A one-way opt-in prevents accrued pending pools
and frozen settlements from being stranded by a return to legacy mode, and the
all-to-owner profile fallback avoids assigning a voter portion the delegate
never configured while leaving it free to register one for a later era.

### Candidate identity as the state key

Candidate owner and operator addresses may change. Candidate identity is the
stable key shared by staking snapshots, DelegateProfile data, pending pools,
cursor entries, and receipt events. This prevents an operator rotation from
splitting or stranding a delegate's reward history.

### Recomputed weights rather than a committed weight table

Committing the aggregated `(candidate, voter)` weights would cost every bucket
mutation in every block to keep them current, and would write a delegate's
whole entry list into state at each era boundary, so state growth would scale
with the number of pairs rather than with what a settlement pays. The recompute
reads the same buckets those weights were derived from, producing the same
quantity from a much smaller commitment.

The property a committed table would provide — that no node derives the weights
for itself — is instead obtained from the era window. Every node recomputes,
but all recompute from the same as-of-`H` state, and that state is committed:
what is agreed on is the input, not the output, and a disagreement about the
input is a state-root disagreement block validation already catches.

An archive or history-index lookup could serve the same as-of-`H` reads, but it
would make consensus depend on a node's retention configuration and would
answer against a height whose state the drain is concurrently mutating. Copying
a key aside on its first mutation after `H` keeps the answer in the state tree
the block is already reading, costs nothing for keys the era never touches, and
makes "no copy exists" a positive statement — with tombstones covering the one
case where it would otherwise mean the opposite.

### Voter-major settlement

A delegate-major walk would pay a voter once per delegate: one destination
lookup, one routing decision, and one balance write per `(candidate, voter)`
pair, plus a materialized entry list to drive the walk. Walking the voter
address space instead pays each voter once for their whole entitlement, so cost
per settlement falls from the number of pairs to the number of distinct voters,
a voter staking with many delegates receives one transfer rather than many
small ones, and cost per block becomes independent of the delegate count. One
global voter budget then bounds the expensive work directly; a separate
delegate or compound limit would reduce useful throughput without providing a
clearer safety bound.

Rotating the starting shard prevents a fixed canonical start from repeatedly
favoring the same head of the sequence whenever a settlement overruns. Deriving
it from the previous block hash keeps state compact and the traversal
reproducible from archive state. Rotation changes only the order in which
voters are served, not membership, weights, the allocation rule, or total fund
movement. It also does not decide who receives floor-division dust: a shard
walk over per-shard-resolved membership has no notion of a last voter to assign
it to, which is why there is no dust rule.

### The payout clamp and the residual sweep

The frozen denominator is a running accumulator maintained by staking handlers;
the numerator is a stateless recompute from buckets. Two such quantities can
disagree, and one source of disagreement is deliberately left in place: the
recompute decides the self-stake bonus by comparing bucket index to the frozen
self-stake index, while the accumulator uses a refined predicate accounting for
endorsement expiry — a passive event with no transaction to observe it. No
stateless recompute can reproduce a path-dependent accumulator, so changing
either predicate would move the disagreement rather than remove it.

The clamp makes the direction of every such disagreement safe. Under-payment is
recoverable, the residual being swept through the same sink as an orphaned pool
to the delegate's owner or the rewarding fund; over-payment is not, because the
money has left the protocol. Exact per-delegate conservation instead would
require a distinguished last voter to absorb the difference, which the shard
walk cannot identify, and would pay that difference out even when it arises
from a drifted accumulator.

### Era-based settlement with frozen inputs and live pools

Block voter rewards arrive every block, but paying every voter every epoch
would repeatedly incur snapshot and routing overhead; accumulating for an era
amortizes that fixed work while still paying delegate commission immediately.
Reward mode, profile rates, total weight, freeze height, self-stake bucket
index, the cursor's owner destination, and the settlement amount are frozen so
all validators reproduce the same allocation across multiple blocks, while the
pool itself stays live and able to receive later rewards, which are
unambiguously deferred to a future cursor.

### Direct account payout and voter-selected routing

Writing direct rewards to an account completes the payment in one state
transition; a second per-voter rewarding balance would require another claim
transaction and preserve rewarding state indefinitely. A single global
voter-selected destination covers custody, treasury, and tax-account workflows
without duplicating configuration for every delegate, and sparse overrides keep
default users state-free.

Resolving the destination at chunk execution gives the voter control over
unprocessed payouts and avoids copying mutable routing data into every frozen
snapshot, while recording both beneficiary and recipient in
`DelegateDistributed` preserves the historical result after a configuration
change. Resolving compound preference inline avoids a separate pending-compound
state machine, and the event records the actual destination bucket so auditors
can verify both the decision and the staking inflow.

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
address, full rewarding balance accrual, and claim requirement, and enter the
new behavior only after an owner-authorized opt-in. Existing balances accrued
before migration remain claimable and are not rewritten. Existing
`DelegateProfile` and `AutoDeposit` contracts remain the configuration sources,
so no new configuration transaction is needed solely for IIP-59.
`ForwardRegistration` entries are not imported; voters that need a non-default
direct destination must configure the protocol action once.

Consensus state intentionally does not retain an append-only distribution
history for every voter, which would grow without bound and duplicate receipt
data. Archive receipts and `DelegateDistributed` events are the canonical
post-activation execution record, including candidate, voter, amount,
beneficiary, actual recipient, direct-or-compound result, bucket ID, block, and
action hash. Indexers SHOULD expose a voter-oriented history query over that
record; a unified wallet or tax API MAY join pre-activation Hermes records with
post-activation IIP-59 events, but that API is outside consensus.

## Security Considerations

### Determinism and replay

All allocation inputs and the shard rotation are frozen in state and committed
to the state root. Voter weights are recomputed rather than committed, but from
copy-on-write state that *is* committed (section 4.2), so two nodes that
recompute differently have diverged on the state root and normal block
validation rejects one of them. A restart changes nothing, because the
recompute reads only committed state and the scalars travelling with the work
item, and a reorganization reverts the seed, payout, and cursor advance
together before deterministic re-execution.

The seed is not a source of cryptographic randomness and MUST NOT be used for
reward eligibility, weight, commission, or total allocation. A producer near
the boundary may have limited influence over a candidate parent block hash, but
that influence selects only the starting shard, and therefore only the order in
which voters are served — not membership, weight, commission, or any voter's
amount.

### Fund conservation

For each split, `commission + voterShare = source reward`. For each delegate,
at every point during a settlement:

```text
sum(payouts so far from this delegate) <= voterAmountFrozen
```

This is an inequality, not an equality, and the payout clamp (section 8.1)
enforces it. The direction is the security property: a weight recompute that
disagrees with the frozen denominator can only cause the protocol to pay less
than it set aside, never more, so no disagreement can be turned into an
inflation of rewarding-fund outflow. Exact conservation is restored at
completion, where the residual is swept to the delegate's owner or, if the
candidate is gone, to the rewarding fund's unclaimed balance (section 9). No
path burns a residual and no path pays one twice: the sweep is recorded in the
distributed total, so a completed settlement has
`voterDistributed == voterAmountFrozen` for every unskipped delegate.

Pending pools remain backed by the rewarding fund; a chunk decreases both the
pool liability and the rewarding total balance by the amount leaving the
protocol. Overrun recovery never creates a new balance, only a new cursor over
existing pools.

### Destination authorization and account safety

Only the voter-signed action can change that voter's direct destination. The
recipient gains no control of the voter's stake, voting weight, AutoDeposit
configuration, or future configuration action, and a voter can restore the
default by setting self or zero. The protocol treats the recipient as an
account address and performs no contract callback, which prevents recipient
code from re-entering reward or staking transitions; applications MUST NOT
assume an ERC-style receiver hook will execute. A mistaken but valid recipient
is an authorized on-chain transfer and cannot be reversed by the protocol, so
wallets SHOULD show the effective address and reset semantics before signing.

### Denial of service

The voter payout loop is bounded by `VoterBudgetPerBlock` when non-zero, and
the index scan feeding it by a fixed multiple of the same parameter, so neither
half of a chunk is unbounded. The second bound is what makes the shard split
safe: the first address byte is cheap to grind, so without it an attacker could
concentrate addresses in one shard and make that shard's scan, rather than any
payout, consume the block. Delegate iteration is limited by the existing
epoch-reward candidate set, and `VoterRewardChunk` is protocol-generated and
cannot be submitted as an arbitrary user action.

Snapshot construction and DelegateProfile reads occur only at era boundaries
and only for on-chain delegates, writing a fixed number of scalars per delegate
rather than a list scaling with its voter count, so a delegate cannot be made
expensive by acquiring voters. DelegateProfile and AutoDeposit reads execute
against on-chain EVM state under the same block context on every validator,
with defined fallbacks per entry and no off-chain API consulted during
consensus.

The one-time contract-staking owner index backfill (section 1.1) is the largest
single-block operation IIP-59 introduces. It is not attacker-controlled — its
size is the deployed bucket population at a height chosen by governance — but
it MUST be measured against the block budget before the activation height is
set, because a block that exceeds the budget at a mandatory height stops the
chain rather than degrading.

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
- `action/protocol/rewarding/delegateprofile/` and `.../autodeposit/` read the
  profile portions and resolve compound preferences.
- `action/protocol/rewarding/distributedlog/` defines and encodes
  `DelegateDistributed`; `.../ethabi/` exposes the Web3 state interface.
- `blockchain/genesis/` defines activation and reward-era parameters.
