```
IIP: <to be assigned>
Title: Quantum-Safe Staking Buckets
Author: Raullen Chai (@raullenchai)
Discussions-to: https://github.com/iotexproject/iips/pulls
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-10-19
Requires: 59, 61, 64
```

## Simple Summary

Let a staker lock a native staking bucket with a second, hash-based key
(SLH-DSA, NIST FIPS 205). Once a bucket is locked, nothing that moves, re-owns,
unstakes, or re-votes it is accepted unless that key has signed it. An ECDSA
signature alone is no longer enough. Staked IOTX then stays safe even if
secp256k1 is broken, whether by a quantum computer or by an AI-assisted
mathematical result.

## Abstract

This IIP adds an opt-in **bucket guard** to native staking buckets. A guard is an
SLH-DSA-SHA2-192s public key plus a replay counter, stored in a new staking-state
namespace. It introduces two new staking actions:

* `BindBucketGuard`, sent by the bucket owner, attaches a guard to a bucket.
* `GuardedBucketOp` performs one of a closed set of bucket operations, authorized
  only by the guard.

On a guarded bucket, the existing ECDSA-authorized bucket actions fail. Any
account may sponsor (submit and pay for) a `GuardedBucketOp`. Hash-based
signatures rely only on the security of the hash function, so a guard is robust
to a break of elliptic-curve or lattice assumptions.

This IIP is a self-contained first deliverable of the IIP-64 migration. It needs
no EVM precompile, no new address format, no emergency mode, and no
account-level key change.

## Motivation

1. **Largest locked pool, rarely touched.** Native buckets hold a large share of
   IOTX, and their owners act on them a few times a year. That is the ideal
   profile for large, stateless hash-based signatures.
2. **Votes are consensus.** Delegates are elected by bucket votes. Someone who
   can forge an owner's ECDSA signature can redirect votes with
   `ChangeCandidate`. Guarding that operation removes a path to capturing
   consensus.
3. **Hash-based only.** The threat this IIP addresses is a break of a
   *structured* assumption, possibly with no hardware warning (IIP-64 §1.5). v1
   therefore admits only SLH-DSA.
4. **Ship before the full migration.** IIP-64 is a multi-year program. This IIP
   needs one hard fork and touches only the staking protocol.

## Specification

The key words MUST, SHOULD, and MAY are to be interpreted as in RFC 2119.

### 1. Activation and dependencies

All rules take effect at the height of a future hard fork (`QSBHeight`, set by
governance). Before that height, both new actions are invalid. Activation MUST
NOT precede Zanzibar Gamma, because this IIP relies on the
`RevertStakingStateOnFailedReceipt` behavior (§9).

### 2. Algorithms

The accepted set is fixed by consensus and is identical on every node.

| ID (IIP-64 §4.1.3) | Algorithm | Public key | Signature |
|---|---|---|---|
| `0x12` | SLH-DSA-SHA2-192s | 48 bytes | 16,224 bytes |

Any other algorithm ID MUST be rejected. Signatures use the FIPS 205
**external, pure** interface (`slh_sign` / `slh_verify`) with the context string
`ctx = "IOTEX-PQ-BUCKET-v1"` (18 ASCII bytes). Pre-hash (HashSLH-DSA) MUST NOT be
used. Implementations MUST select the parameter set from the algorithm ID, never
from the key or signature bytes. Additional sets, such as SHA2-256s, require a
future fork.

*Why SHA2 over SHAKE:* a benchmark of Cloudflare CIRCL v1.6.5 (Go 1.26, Apple
M3 Pro) measured SHA2-192s verification at 0.23 ms against 1.01 ms for
SHAKE-192s. The gas constants in §8 must be calibrated on linux/amd64.

### 3. Scope: which buckets can be guarded

A bucket MAY be guarded only if all of the following hold:

* (a) It is a native bucket (`ContractAddress` is empty). Contract-staking buckets
  are out of scope.
* (b) It is not the self-stake bucket of any candidate.
* (c) It has no endorsement record in any state, including an unendorse-requested
  endorsement.

While a bucket is guarded, the protocol MUST keep (b) and (c) true. A guarded
bucket MUST NOT become a self-stake bucket through `CandidateActivate`, and MUST
NOT receive an endorsement record through `CandidateEndorsement`. Both fail with
`ErrBucketGuarded`. `CandidateRegister` either creates a fresh, initially
unguarded bucket or (zero-stake registration) none, so it is unaffected.

Conditions (b) and (c) are **structural**:

* (b) means no candidate's `SelfStakeBucketIdx` equals the bucket index,
  regardless of unstake or exit status.
* (c) means an endorsement-state `Get` for the bucket returns
  `ErrStateNotExist`.

Implementations MUST NOT substitute `isSelfStakeBucket` or the endorsement
`Status`. Both can report false or none for records that are still referenced or
have expired.

*Rationale:* candidate-level operations (`CandidateActivate`,
`CandidateDeactivate`, `CandidateTransferOwnership`, and the scheduled exit queue
of IIP-61) can change a self-stake bucket's role and vote weight under the
candidate's ECDSA key. They cannot be guarded without migrating candidate keys.
Excluding self-stake and endorsed buckets in v1 keeps every path that changes a
guarded bucket inside §6. Protecting delegate self-stake is left to the
candidate-key migration of IIP-64 §4.7.

### 4. State

A new staking-namespace key prefix `_bucketGuard`, appended to the existing
prefix enumeration (`_const, _bucket, _voterIndex, _candIndex, _endorsement,
_candidateRewardSnapshot, _bucketGuard`), holds the guard records:

```
key   = _bucketGuard || uint64_be(bucketIndex)
value = protobuf BucketGuard
```

```protobuf
message BucketGuard {
  uint32 algID      = 1;  // 0x12
  bytes  publicKey  = 2;  // empty iff cleared
  uint64 generation = 3;  // incremented on every bind/rotate/transfer-with-new-guard
  uint64 nonce      = 4;  // incremented on every successful GuardedBucketOp
  uint64 boundHeight = 5; // height of the most recent bind/rotate
}
```

* A bucket is **guarded** iff a record exists with a non-empty `publicKey`.
* An absent record is treated as `generation = 0, nonce = 0`.
* `generation` and `nonce` MUST NOT decrease or reset during a bucket's
  lifetime, including across a clear followed by a rebind. Clearing a guard (§6,
  TRANSFER with `clearGuard`) keeps the record as a tombstone: `algID = 0`, an
  empty `publicKey`, `boundHeight = 0`, and both counters retained. A counter
  overflow fails the action with `ErrGuardMismatch`.
* `boundHeight` is the height at which the current key was installed, by bind,
  rotate, or transfer with a new guard.
* Native bucket indices are never reused, because `totalBucketCount` is
  monotonic. Whenever a native bucket is permanently deleted, by any path
  (guarded WITHDRAW, or a legacy `WithdrawStake` or `MigrateStake` on a bucket
  that was cleared earlier), its guard record, including a tombstone, MUST be
  deleted in the same snapshot. A guard query for a deleted bucket returns
  not-found.
* The record MUST be written through the same state manager and snapshot as the
  bucket, so that revert and historical reads cover it. On the Erigon backend it
  MUST be registered as a storage object.

### 5. Action: `BindBucketGuard`

```protobuf
message BindBucketGuard {
  uint64 bucketIndex = 1;
  uint32 algID       = 2;
  bytes  publicKey   = 3;
  bytes  acceptSig   = 4;   // by publicKey over ACCEPT (§7)
}
```

Stateless validation (failure = invalid action): canonical encoding and size
(§8); `algID = 0x12`; `len(publicKey) = 48`; `len(acceptSig) = 16,224`; intrinsic
gas.

Execution (deterministic failures = failed receipt, §9.3):

1. Snapshot the state manager.
2. Load the bucket. It must exist (`ErrInvalidBucketIndex`) and be native
   (`ErrGuardScope`).
3. The caller (outer ECDSA sender) MUST be the owner (`ErrUnauthorizedOperator`).
4. §3 (b) and (c) must hold structurally (`ErrGuardScope`).
5. The guard record must be absent or a tombstone (`ErrGuardScope`).
6. `generation + 1` must not overflow (`ErrGuardMismatch`).
7. Verify `acceptSig` over `ACCEPT(newGeneration = generation+1, resultingOwner =
   owner, deadline = 0)` (`ErrGuardSignature`). This is the proof of possession.
8. Write `{algID, publicKey, generation+1, nonce (unchanged), boundHeight =
   blockHeight}`, emit the bind log, and settle.

Binding is never closed (no cutoff). After an ECDSA compromise, an attacker can
bind an unguarded bucket immediately, even while it is still locked by maturity
or withdraw delays; binding confers no recovery entitlement on the previous ECDSA
controller. **Protection requires binding before compromise.**

### 6. Action: `GuardedBucketOp`

```protobuf
message GuardedBucketOp {
  uint64 bucketIndex = 1;
  uint64 generation  = 2;
  uint64 nonce       = 3;
  uint64 deadline    = 4;   // last valid block height; MUST be > 0
  uint32 op          = 5;   // tag below
  // op-specific (unused fields MUST be empty/zero):
  bytes  recipient            = 6;   // WITHDRAW: 20-byte address
  bytes  newOwner             = 7;   // TRANSFER: 20-byte address
  string candidateName        = 8;   // CHANGE_CANDIDATE
  bytes  expectedCandidateID  = 9;   // CHANGE_CANDIDATE: 20-byte candidate identifier
  uint32 duration             = 10;  // RESTAKE: days
  bool   autoStake            = 11;  // RESTAKE
  NewGuard newGuard           = 12;  // TRANSFER (or clearGuard), ROTATE
  bool   clearGuard           = 13;  // TRANSFER only
  bytes  sig                  = 14;  // current guard key over CALL transcript (§7)
}
message NewGuard { uint32 algID = 1; bytes publicKey = 2; bytes acceptSig = 3; }
```

| `op` | Name | Effect (reuses existing handler semantics unless noted) |
|---|---|---|
| 1 | UNSTAKE | As `Unstake`, including the auto-stake, maturity, and endorsement preconditions |
| 2 | WITHDRAW | As `WithdrawStake`, but credits `recipient` rather than the caller. Deletes the bucket and the guard |
| 3 | TRANSFER | As `TransferStake` to `newOwner`. Exactly one of `newGuard` / `clearGuard` MUST be set |
| 4 | CHANGE_CANDIDATE | As `ChangeCandidate`. `candidateName` MUST resolve, at execution time, to `expectedCandidateID` |
| 5 | RESTAKE | As `Restake` with `duration` and `autoStake`, including the existing duration validation |
| 6 | ROTATE | Replace the key with `newGuard`. `generation += 1` |

Unknown `op` values MUST be rejected. There is no generic inner-action wrapper.

**Roles.** The outer ECDSA sender is the **sponsor**. It pays gas and advances
its own account nonce, and has no other effect. The guard is the bucket
**authority**. The sponsor may be any account, including the owner. Handlers
MUST receive the guard authorization explicitly, scoped to
`(bucketIndex, generation, op)`. It MUST NOT be implemented as a general flag
that bypasses ownership checks, and every handler MUST act on
`GuardedBucketOp.bucketIndex` only.

**Recipient.** `recipient` MUST be a 20-byte account address. The account is
created if absent, and contract addresses are allowed. Withdrawn IOTX leaves the
guard's protection; wallets SHOULD default to a fresh, never-spent address.

**What the guard authorizes.** TRANSFER and WITHDRAW act on the bucket's
execution-time amount, including any deposits and IIP-59 compounding that
arrived after signing.

### 7. Signed transcripts

All integers are big-endian with the stated widths. `chainID` is the native
chain ID `protocol.MustGetBlockchainCtx(ctx).ChainID` (uint32), **not** the EVM
network ID. Booleans are a single byte, `0x00` or `0x01`. Addresses are their 20
raw bytes.
`bytes(x)` is `uint32_be(len(x)) || x`. Messages are signed directly with pure
SLH-DSA, with no intermediate digest, using `ctx` from §2.

```
CALL   = "IOTX-QSB-CALL"   || uint32 chainID || uint64 bucketIndex || owner(20)
       || uint64 generation || uint64 nonce || uint64 deadline || uint32 op
       || bytes(recipient) || bytes(newOwner)
       || bytes(candidateName) || bytes(expectedCandidateID)
       || uint32 duration || uint8 autoStake
       || uint8 hasNewGuard || [uint32 algID || bytes(publicKey)]   // if hasNewGuard
       || uint8 clearGuard

ACCEPT = "IOTX-QSB-ACCEPT" || uint32 chainID || uint64 bucketIndex
       || uint64 newGeneration || resultingOwner(20)
       || uint32 algID || bytes(publicKey) || uint64 deadline
```

* CALL is signed by the current guard key. `owner` is the bucket owner at
  execution time.
* ACCEPT is signed by the incoming key:
  * BIND: `newGeneration = generation+1`, `resultingOwner = owner`, `deadline = 0`.
  * ROTATE: `newGeneration = generation+1`, `resultingOwner = owner`, and the
    `deadline` of the CALL.
  * TRANSFER with `newGuard`: `newGeneration = generation+1`,
    `resultingOwner = newOwner`, and the `deadline` of the CALL.
* A guarded operation that installs a new key therefore carries two signatures.
* ACCEPT is the incoming key's acceptance of the resulting binding: bucket, next
  generation, resulting owner, key, and deadline. It is **not** approval of one
  particular CALL. The operation itself is authorized only by the current guard's
  CALL signature, and that signature commits to the incoming key.

### 8. Encoding, size and gas

* **Canonical encoding (consensus object).** Validity and pricing are defined
  over the **decoded** `BindBucketGuard` / `GuardedBucketOp` value, not over
  received bytes (decoders upstream of staking — API, gossip, block
  deserialization — see only decoded messages). `size` is the length of the
  canonical encoding `C(m)` of the decoded message `m`, where `C` is defined
  recursively: fields emitted in ascending field-number order; each present
  field emitted exactly once; scalar and `bytes`/`string` fields with the proto3
  default value omitted; varints in minimal (shortest) form; length prefixes
  minimal; a nested message (`newGuard`) emitted iff set, as `C(newGuard)`; no
  unknown fields. Implementations MUST compute `size` with an encoder conforming
  to this definition (not by measuring received bytes). Ingress nodes SHOULD
  additionally reject non-canonical wire encodings, but this is relay policy, not
  consensus.
* **Limits:** `size ≤ 17,000` for `BindBucketGuard` and for `GuardedBucketOp`
  without `newGuard`; `size ≤ 34,000` with `newGuard`. Checked in stateless
  validation.
* **Intrinsic gas:** `10,000 + 16·size + k·G_VERIFY`, where `k` is the number of
  SLH-DSA verifications the action requires (1, or 2 with `newGuard`); this
  replaces, for these two actions, the generic staking payload pricing (100
  gas/byte). The usual envelope rules (gas price, limit) apply unchanged.
* **`G_VERIFY = 30,000`.** Derivation: SLH-DSA-SHA2-192s verification measured
  0.233 ms (CIRCL v1.6.5, Go 1.26.5, Apple M3 Pro, darwin/arm64). The
  benchmark source, dependency versions and raw results are in
  `assets/iip-qsb/bench/` of this IIP. At the ~60 Mgas/s execution budget
  assumed by current Ethereum repricing work (≈16.7 ns/gas) this is ≈14,000 gas;
  `G_VERIFY` adds a 2× margin for slower linux/amd64 validators. The value is
  normative for this IIP. linux/amd64 measurements of the full action, not just
  the primitive, MUST be added to the assets before this IIP leaves Draft. Any
  increase MUST be made by amending this IIP and its vectors, not left to
  activation tooling.
* Conformance vectors (§Test Cases) MUST give exact `size` and gas for every op.
  34 KB actions fit within the default p2p `MaxMessageSize`.

### 9. `GuardedBucketOp` validation, execution, and failure semantics

#### 9.1 Stateless validation (failure = invalid action, not includable)

Canonical encoding and size (§8); known `op`; per-op field rules (required
fields present, all others at default); fixed lengths (20-byte addresses,
48-byte keys, 16,224-byte signatures, `newGuard.algID = 0x12`); `deadline > 0`;
existing staking sanity checks for the op (e.g. restake duration bound,
candidate-name format); intrinsic gas.

#### 9.2 Execution

1. Snapshot the state manager before any guard or staking write.
2. Load the bucket (`ErrInvalidBucketIndex` if absent) and require it native and
   guarded (`ErrBucketNotGuarded`).
3. Require `generation`, `nonce` equal to stored; `blockHeight ≤ deadline`; no
   counter overflow (`ErrGuardMismatch`).
4. Op-specific state preconditions, with the existing handlers' receipt statuses
   (maturity, auto-stake, unstaked, etc.); for CHANGE_CANDIDATE the resolved
   candidate's identifier MUST equal `expectedCandidateID`
   (`ErrCandidateMismatch`).
5. Verify CALL, then ACCEPT if present (`ErrGuardSignature`).
6. Apply the transition (§9.4) through the existing staking state-manager helpers
   (bucket, owner/candidate indexes, bucket pool, IIP-59 copy-on-write hooks).
7. Emit success logs; settle.

#### 9.3 Failure classification

* **Deterministic protocol failures** — every condition named with a receipt
  status above or in the existing handlers — revert to the snapshot (no guard or
  staking change persists, **no success logs are emitted**), then produce a
  failed receipt that charges the sponsor's gas and advances the sponsor's
  account nonce exactly once. The guard nonce does not advance.
* **Non-deterministic/fatal errors** — storage backend errors, corruption, a
  failed snapshot revert or settlement — MUST propagate as fatal block-processing
  errors exactly as non-`ReceiptError` errors do today; they never yield an
  includable failed receipt.
* **Classification precedence.** Backend/corruption classification takes
  precedence over legacy receipt wrappers: existing helpers that wrap any read or
  write error as a `ReceiptError` (e.g. `fetchBucket`, `fetchCaller`, the
  bucket-pool credit in withdraw) MUST, when called on behalf of these actions,
  distinguish `ErrStateNotExist`-type deterministic outcomes (which keep their
  statuses) from all other storage errors (which are fatal). Any change to legacy
  actions' classification is out of scope and MUST remain fork-gated if made.
* Mempool pre-verification MAY be done but is not consensus: §9.2 steps 2–5 are
  always re-evaluated against execution-time state.

#### 9.4 Guard state transitions (on success)

| op | Bucket effect | Guard record after |
|---|---|---|
| UNSTAKE / CHANGE_CANDIDATE / RESTAKE | existing handler effect | `nonce+1`; other fields unchanged |
| WITHDRAW | bucket deleted, amount credited to `recipient` | **deleted** (log reports consumed `nonce` and resulting `nonce+1`) |
| TRANSFER + `newGuard` | owner := `newOwner` | key := new; `generation+1`; `nonce+1`; `boundHeight` := height |
| TRANSFER + `clearGuard` | owner := `newOwner` | tombstone (`algID 0`, empty key, `boundHeight 0`); `generation`, `nonce+1` retained |
| ROTATE | none | key := new; `generation+1`; `nonce+1`; `boundHeight` := height |

#### 9.5 Receipt statuses

New `ReceiptStatus` values (proposed numbers, final assignment in `iotex-proto`):
`ErrBucketGuarded = 216`, `ErrBucketNotGuarded = 217`, `ErrGuardMismatch = 218`,
`ErrGuardSignature = 219`, `ErrGuardScope = 220`, `ErrCandidateMismatch = 221`.
Existing `ErrInvalidBucketIndex (202)` and `ErrUnauthorizedOperator (203)` are
reused as stated. Proposed `ActionCore` oneof fields: `bindBucketGuard = 59`,
`guardedBucketOp = 60`.

### 10. Effects on existing actions

On a guarded bucket:

| Existing action | Result |
|---|---|
| `Unstake`, `WithdrawStake`, `TransferStake` (including consignment), `ChangeCandidate`, `Restake` | Failed receipt `ErrBucketGuarded` |
| `MigrateStake` | Failed receipt `ErrBucketGuarded` (leaving to ERC-721 control is not permitted) |
| `CandidateActivate` targeting it / `CandidateEndorsement` on it | Failed receipt `ErrBucketGuarded` |
| `DepositToStake` | Unchanged (permitted to anyone under the existing conditions; guard state untouched) |
| IIP-59 `AddDepositForCompound` | Unchanged (permitted; guard state untouched) |

Receipt status numbers are listed in §9.5.

### 11. Events and API

Each successful `BindBucketGuard` or `GuardedBucketOp` emits **exactly one**
event log. The emitter is the staking protocol address, and the log is produced
by a single `AddEvent(topics, data)` call.

* `topic[0]` =
  `0x73a1cc2c5c34de8d095f5003eb096fa77f44357dd83dcea0225ca286942426ec`, which is
  Keccak-256 of the ASCII string
  `BucketGuard(uint64,uint64,uint64,uint64,address,address)`. The string serves
  only to derive the constant; the data below is not ABI-encoded.
* `topic[1]` = `bucketIndex`, and `topic[2]` = `op`. Each is a big-endian
  integer left-padded with zeros to 32 bytes. `op = 0` denotes BIND, and 1–6 the
  ops in §6.
* `data` = `uint64_be(generation) || uint64_be(nonce) || sponsor(20) ||
  counterparty(20)`, which is 56 bytes:
  * The counters are the resulting values. For WITHDRAW the record is deleted and
    `nonce` is the consumed value plus 1.
  * `counterparty` is `newOwner` for TRANSFER, `recipient` for WITHDRAW, and 20
    zero bytes otherwise.

The legacy per-handler logs (`unstake`, `withdrawStake`, …) are **not** emitted
for guarded ops. Transaction logs are emitted as today: gas-fee logs always
(including on failure), and for WITHDRAW one `WITHDRAW_BUCKET` transaction log
from the bucket pool to `recipient`. On failure, only the gas-settlement
transaction logs and the failed status appear.

The bucket query API returns, at a given height: `guarded`, `algID`,
`publicKey`, `generation`, `nonce`, `boundHeight`.

### 12. Wallet key derivation (wallet profile `QSB-KDF-v1`)

This section is a **wallet interoperability requirement**, not a consensus rule:
consensus verifies possession (ACCEPT), and cannot verify derivation.

```
prk = HKDF-Extract(salt = "IOTX-QSB-KDF-v1", IKM = bip39_seed)            // HMAC-SHA-512
okm = HKDF-Expand(prk, info = "slh-dsa-sha2-192s" || uint32_be(account)
                             || uint32_be(keyIndex), L = 72)
(SK.seed, SK.prf, PK.seed) = okm[0:24], okm[24:48], okm[48:72]
(sk, pk) = slh_keygen_internal(SK.seed, SK.prf, PK.seed)                  // FIPS 205 Alg. 18
```

* `account` is the BIP-44 account index of the address that will own the bucket
  after the key is installed (the binder for BIND/ROTATE; the **new owner** for
  TRANSFER with `newGuard` — the new owner's wallet produces `newGuard` and its
  ACCEPT).
* `keyIndex` is allocated per `(seed, account)`, starting at 0, incremented each
  time a new guard key is derived for that account (bind, rotate, or receiving a
  transfer); a wallet MAY reuse one key across several buckets, as transcripts are
  bucket-scoped. `keyIndex` ranges over `0 … 1023`.
* Because SLH-DSA is stateless, reusing a key index (across buckets or after a
  lost high-water mark) is **safe**; index allocation is a convenience, not a
  security requirement.
* **Recovery** requires no extra backup: guard public keys are on chain. A
  restoring wallet derives `pk` for **every** `keyIndex` in `0 … 1023` for each of
  its accounts (exhaustive, no gap limit; ≈ 26 s per account at the measured
  keygen cost, resumable) and matches against the on-chain `publicKey` of each
  guarded bucket it owns. It then continues allocating from the highest matched
  index + 1 (or any index — reuse is safe).

## Rationale

* **Guard record, not a new owner.** The owner, bucket index, voting, and rewards
  keep working unchanged. The guard is an additional lock.
* **Stateless SLH-DSA, not WOTS/XMSS.** Stateful keys fail when users sign from
  several devices or restore from a seed. Guarded operations are rare, so the
  larger signature is affordable.
* **No ECDSA escape hatch, and no emergency mode.** Any ECDSA path to remove a
  guard is a path an attacker could use. Losing the guard key is mitigated by
  deriving it from the seed (§12).
* **Explicit operations instead of wrapping existing actions.** Wrapping the
  existing actions would require signing over a byte encoding that does not
  uniquely identify the operation (`Unstake` and `WithdrawStake` share one
  payload encoding). A closed op set with a byte-exact transcript avoids this.
* **Direct transcript signing.** Signing the full transcript with pure SLH-DSA
  avoids 256-bit intermediate digests, which would cap collision resistance
  below the Category 3 target.

## Backward Compatibility

The guard is opt-in. Unguarded buckets and every existing action on them behave
exactly as before. Indexers see two new action types and new receipt statuses.

## Test Cases

The following must be covered before activation:

* Behavior at the fork boundary (`QSBHeight − 1` vs `QSBHeight`).
* Each op's success and precondition failures.
* Every rejected path in §10, including consignment and migration.
* Wrong bucket, operation, chain, owner, or candidate ID.
* Expired deadline.
* Malformed or invalid ACCEPT.
* Replay after rotation, and after clear and rebind.
* Competing sponsors for the same signed op.
* Failed execution: snapshot rollback of the guard, bucket, indexes, and pool,
  with the sponsor still charged.
* Withdraw deleting the guard.
* Both storage backends.
* FIPS 205 ACVP vectors for the primitive, plus protocol transcript vectors and
  KDF vectors.
* Exact `size` and intrinsic gas vectors for bind and every op variant.
* Exact receipt and log vectors (success and failure).
* A recovery vector for one bucket rotated 64 times (the active key at
  `keyIndex = 64`).
* Bind/activate and bind/endorse in both orders within one block; pending exits;
  expired endorsement records; transfers to and from candidate owners.
* A clear followed by a legacy withdraw, and a clear followed by migration, each
  deleting the tombstone.
* Injected storage failures on bucket reads, account reads, and pool writes. Each
  must abort block processing rather than produce a receipt.
* Vectors MUST be published with the reference implementation, before this IIP
  leaves Draft.

## Implementation

A reference implementation in `iotex-core` will touch:

* `action/`: the new action types, plus the protobuf messages in `iotex-proto`.
* `action/protocol/staking/protocol.go`: dispatch, and the guard checks in
  existing handlers.
* `handlers.go`: withdraw recipient, consignment rejection.
* `handler_stake_migrate.go`: reject guarded buckets.
* `handler_candidate_*`: reject guarded buckets.
* A new `bucket_guard.go`.
* An SLH-DSA wrapper using CIRCL `sign/slhdsa`.
* Feature-context gating.

## Security Considerations

* **Residual exposure.**
  * Delegate operator and reward keys, delegate self-stake buckets,
    contract-staking buckets, liquid balances, and IIP-59 rewards paid to
    addresses all remain ECDSA-controlled until later IIPs.
  * An elected candidate's operator identity remains ECDSA-controlled even when
    the votes for it are guarded.
* **Bind timing.** Only buckets bound before a break are protected.
* **Lost guard key.** The bucket is permanently locked. This is mitigated by the
  seed-derived key (§12).
* **Front-running.** A copied `GuardedBucketOp` executes the identical signed
  effect. A competing sponsor can only pay for it.
* **Implementation risk.** This IIP adds consensus-critical SLH-DSA verification.
  The library version MUST be pinned, the implementation MUST be tested against
  ACVP vectors, and decoding MUST be fuzzed.

## Copyright

Copyright and related rights waived via
[CC0](https://creativecommons.org/publicdomain/zero/1.0/).
