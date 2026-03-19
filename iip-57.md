```
IIP: 57
Title: Trustless Bridge: Replacing Keys with Proofs
Author: TBD (@TBD)
Discussions-to: TBD
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-03-03
Supersedes: IIP-55
```

## Abstract

The ioTube bridge was compromised on February 21, 2026 because it trusted keys — a single validator owner key was stolen, bypassing all security. This IIP replaces that trust model entirely: instead of keys, the new bridge trusts **mathematical proofs**.

This proposal introduces a ZK Light Client Bridge that uses Succinct SP1 zero-knowledge proofs to cryptographically verify IoTeX's 24-delegate BFT consensus on Ethereum. No multisig, no trusted relayers, no upgradable validator contracts — just a proof that either verifies or doesn't. For deposits (Ethereum → IoTeX), the existing 17/24 delegate BFT consensus attests events. For withdrawals (IoTeX → Ethereum), a ZK proof of block finality and receipt inclusion is verified on-chain by Ethereum. The bridge supports USDT, USDC, WETH, and WBTC, with competitive proving open to all delegates and a hybrid fee model that sustains operations without protocol subsidies.

## Motivation

### The ioTube Hack (February 21, 2026)

On February 21, 2026, the ioTube cross-chain bridge was exploited for approximately $4.4M. The attacker compromised a single validator owner private key on the Ethereum side, used it to upgrade the Validator contract to a malicious version that bypassed all signature checks, and drained both the MintPool and TokenSafe contracts.

**Root cause**: The ioTube bridge relied on a single validator owner key for critical administrative operations — a single point of failure. This is an architectural flaw, not a smart contract bug. The IoTeX L1 chain and consensus were unaffected.

### Why Not Fix the Existing Bridge? (IIP-55)

After the ioTube exploit, **IIP-55** ("Dynamic Witness Committee for ioTube") was proposed as an incremental upgrade. IIP-55 introduces rotating witness committees selected via VRF from the delegate pool, per-token witness sets, and a new `TransferValidatorV3` contract. While IIP-55 improves operational hygiene, it does not address the fundamental architectural flaw that caused the hack:

**IIP-55 still trusts keys.** The core verification model remains N-of-M multisig — a rotating committee of 8 delegates must produce >2/3 signatures to authorize transfers. This is a strictly better multisig, but it is still a multisig. The attack surface is reduced in size but identical in kind:

| Property | ioTube (pre-hack) | IIP-55 | IIP-57 (this proposal) |
|----------|-------------------|--------|------------------------|
| **Trust model** | Static witness keys | Rotating witness keys | ZK mathematical proof |
| **What an attacker must compromise** | 1 owner key | >2/3 of 8 committee keys (~6 keys) | Break ZK proof soundness (mathematically infeasible) |
| **Key compromise window** | Permanent | Per-epoch (~hours) | N/A — no keys in verification path |
| **Ethereum verification** | Trusts signatures | Trusts signatures | Verifies IoTeX consensus cryptographically |
| **Upgradable validator contract** | Yes (exploited) | Yes (`TransferValidatorV3`) | No — immutable light client + verified proofs |
| **Off-chain trust dependency** | Relayers + witnesses | Relayers + witness committee service | None — proof is self-contained |

Specific concerns with IIP-55:

1. **Smaller committee = smaller security margin**: IIP-55 selects ~8 witnesses per epoch from the delegate pool. Compromising 6 keys (>2/3 of 8) during a single epoch is a realistic attack for a state-level adversary — significantly easier than compromising 17 of 24 full delegates. The ioTube hack demonstrated that even a single key compromise can be catastrophic when combined with contract upgrade rights.

2. **Upgradable contracts remain**: `TransferValidatorV3` is an upgradable contract — the exact attack vector used in the ioTube hack. The attacker didn't break the signature scheme; they upgraded the validator contract to bypass it entirely. IIP-55 does not eliminate this vector.

3. **Off-chain witness committee service**: IIP-55 introduces a new off-chain service that computes committee membership and submits proposals to relayers. This adds another trusted component to the system — another piece of infrastructure that can be compromised, go offline, or be manipulated.

4. **No independent verification by Ethereum**: Under IIP-55, Ethereum still cannot independently verify that a transfer was legitimately finalized on IoTeX. It only checks that enough witness keys signed a message — it has no way to distinguish legitimate witness signatures from signatures produced by compromised keys. A ZK proof, by contrast, proves that IoTeX's actual consensus (17/24 delegates signing a block) endorsed the transaction.

IIP-55 is a reasonable operational improvement for a multisig bridge, but given that ZK light client technology is now production-ready, this proposal argues that the correct response to the ioTube hack is to **eliminate the key-based trust model entirely** rather than incrementally harden it.

### Why ZK Proofs?

Every major cross-chain bridge hack exploited **trusted intermediaries**:

| Hack | Loss | Attack Vector |
|------|------|--------------|
| Ronin (2022) | $625M | 5/9 validator private keys compromised |
| Wormhole (2022) | $326M | Signature verification bypass |
| Nomad (2022) | $190M | Trusted root initialized to zero |
| Harmony (2022) | $100M | 2/5 multisig keys compromised |
| **ioTube (2026)** | **$4.4M** | **Single validator key compromised** |

A ZK light client bridge eliminates this entire attack surface. Instead of trusting N-of-M key holders, the bridge trusts **mathematics**: a ZK proof is either valid or not — there are no keys to steal, no contracts to upgrade, no signatures to forge.

### Why Now?

1. **ZK proving technology is mature**: SP1 proof generation for consensus verification takes ~30-90 seconds (down from hours in 2024). On-chain Groth16 verification costs only ~280K gas (~$2-5).
2. **Production precedent**: Succinct's ZK light client bridge secures $40M+ TVL on Gnosis Chain.
3. **IoTeX's 24-delegate BFT is ZK-friendly**: Proving 17 ECDSA signatures is significantly simpler than proving Ethereum's ~1M validator consensus, making IoTeX an ideal candidate for ZK light client verification.
4. **User trust must be rebuilt**: After the ioTube hack, a mathematically verifiable bridge is the strongest possible statement of security.

### Why Not Become a Rollup?

IoTeX is a sovereign L1 with its own consensus, governance, 3-second block times, and DePIN-specific features. Becoming a ZK rollup, OP rollup, or Based rollup would mean:

- Surrendering sovereignty to Ethereum
- Losing independent consensus and governance
- Being constrained by Ethereum's 12-second block times
- Fundamentally changing IoTeX's architecture and DePIN mission

This IIP preserves IoTeX's full sovereignty while adding trust-minimized Ethereum interoperability.

### Ethereum L2 Landscape Context

As of early 2026, Ethereum's rollup ecosystem is dominated by Optimistic rollups (~85-90% of L2 TVL) due to first-mover advantage, with ZK rollups growing rapidly. Ethereum's own roadmap is evolving — Vitalik Buterin acknowledged in February 2026 that the original rollup-centric model "no longer makes sense" in its pure form. The Ethereum Foundation's new Platform Team is building an Ethereum Interoperability Layer (EIL) to unify 55+ L2s. Additionally, Native Rollups (EIP-8079) are being designed as a long-term solution where Ethereum's own execution engine verifies rollup state transitions.

For IoTeX, the appropriate architecture is not to become any type of rollup, but to remain a sovereign L1 with a ZK-verified bridge to Ethereum. This positions IoTeX to participate in the EIL ecosystem and potentially adopt Native Rollup verification when EIP-8079 matures (estimated 2027+).

## Specification

### Overview

```
Ethereum → IoTeX (Deposit):
  User locks tokens on ETH → 17/24 IoTeX delegates attest deposit →
  Bridge protocol mints wrapped tokens on IoTeX

IoTeX → Ethereum (Withdrawal):
  User burns wrapped tokens on IoTeX → Withdrawal event in receipt →
  SP1 ZK proof of IoTeX consensus + receipt inclusion →
  Relayer submits proof to Ethereum → User claims unlocked tokens
```

### Delegate Participation: What Changes for a Delegate?

Today, each IoTeX delegate runs an `iotex-core` node and participates in Roll-DPoS consensus (propose blocks, sign endorsements). After this IIP, delegates gain **two additional responsibilities**:

```
Current Delegate Setup:
┌────────────────────────────┐
│  iotex-core node           │
│  - produce blocks          │
│  - sign endorsements       │
│  - earn block rewards      │
└────────────────────────────┘

After IIP-57:
┌────────────────────────────┐     ┌──────────────────────────────┐
│  iotex-core node           │     │  Bridge Sidecar Process      │
│  (upgraded to Yosemite)    │     │  (new, runs alongside node)  │
│                            │     │                              │
│  NEW: Bridge Protocol      │     │  1. Connects to Ethereum RPC │
│  - processes BridgeAttest  │     │     (Infura/Alchemy/self)    │
│  - counts attestations     │     │  2. Watches Deposit events   │
│  - mints wrapped tokens    │     │  3. Feeds deposit data to    │
│  - serves proof API        │◄────│     iotex-core node          │
│                            │     │                              │
│  NEW: Receipt Proof API    │     │  Cost: ~$50/month for ETH    │
│  - iotx_getBridgeReceipt   │     │        RPC endpoint          │
│    Proof endpoint          │     │                              │
└────────────────────────────┘     └──────────────────────────────┘
                                    (delegates also compete to submit
                                     ZKP to Ethereum for fee rewards,
                                     see Relayer Model below)
```

**Key point**: The Bridge Protocol (light client logic, attestation counting, proof API) runs **inside iotex-core** as a native protocol module — the same way staking and rewarding protocols work today. It is NOT a separate service.

**The Bridge Sidecar** is a lightweight process that:
- Connects to an Ethereum RPC endpoint (~$50/month for Infura/Alchemy, or free if delegate runs own ETH node)
- Watches for `Deposit` events on the `BridgeVault` contract
- Feeds confirmed deposit data to the iotex-core node
- The iotex-core bridge protocol then includes `BridgeAttestation` system actions in blocks

**Delegates do NOT need to hold ETH** for the sidecar. The sidecar only reads Ethereum state — it never sends transactions to Ethereum.

---

### Delegate Flowchart: ETH → IoTeX Deposit

```
USER                    ETHEREUM              DELEGATE (×24)              IoTeX
 │                        │                        │                       │
 │  1. approve(USDT)      │                        │                       │
 │──────────────────────►│                        │                       │
 │                        │                        │                       │
 │  2. deposit(USDT,      │                        │                       │
 │     1000, iotexAddr)   │                        │                       │
 │──────────────────────►│                        │                       │
 │                        │                        │                       │
 │    User pays ETH gas   │  3. Deposit event      │                       │
 │    (~$5-15)            │       emitted          │                       │
 │                        │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─►│                       │
 │                        │                        │                       │
 │                        │  4. EACH delegate's    │                       │
 │                        │     sidecar sees the   │                       │
 │                        │     Deposit event      │                       │
 │                        │                        │                       │
 │                        │  5. Wait 64 ETH blocks │                       │
 │                        │     for finality       │                       │
 │                        │     (~15 minutes)      │                       │
 │                        │                        │                       │
 │                        │                 6. Sidecar feeds deposit       │
 │                        │                    data to iotex-core          │
 │                        │                        │                       │
 │                        │                 7. When it's this delegate's   │
 │                        │                    turn to produce a block:    │
 │                        │                    include BridgeAttestation   │
 │                        │                    as SYSTEM ACTION            │
 │                        │                        │                       │
 │                        │                    ┌───┴───────────────┐       │
 │                        │                    │ COST TO DELEGATE: │       │
 │                        │                    │ $0 (zero)         │       │
 │                        │                    │                   │       │
 │                        │                    │ System actions    │       │
 │                        │                    │ have no gas fee.  │       │
 │                        │                    │ Same as how       │       │
 │                        │                    │ PutPollResult     │       │
 │                        │                    │ works today.      │       │
 │                        │                    └───┬───────────────┘       │
 │                        │                        │                       │
 │                        │                 8. Other delegates also        │
 │                        │                    include their own           │
 │                        │                    BridgeAttestation in        │
 │                        │                    their blocks                │
 │                        │                        │                       │
 │                        │                        │  9. Bridge Protocol   │
 │                        │                        │     counts unique     │
 │                        │                        │     attestations:     │
 │                        │                        │     1...2...17 ✓      │
 │                        │                        │────────────────────►│
 │                        │                        │                     │
 │                        │                        │  10. 17/24 reached! │
 │                        │                        │      Protocol auto- │
 │                        │                        │      mints 1000     │
 │                        │                        │      wUSDT to user  │
 │                        │                        │      on IoTeX       │
 │                        │                        │                     │
 User receives 1000 wUSDT on IoTeX ✓               │                     │
 Total time: ~15 min (ETH finality) + ~1 min (17 attestations)           │
```

**Delegate cost for deposits: ZERO.** System actions are free. The sidecar only reads Ethereum (no ETH needed).

---

### Delegate Flowchart: IoTeX → ETH Withdrawal (The Hard Part)

```
USER              IoTeX                COMPETING          SUCCINCT        ETHEREUM
 │                  │                  RELAYER             PROVER           │
 │                  │                  (any of 24           NETWORK          │
 │                  │                   delegates)          │               │
 │  1. Call         │                      │                │               │
 │  withdraw(wUSDT, │                      │                │               │
 │  1000, ethAddr)  │                      │                │               │
 │────────────────►│                      │                │               │
 │                  │                      │                │               │
 │  User pays IOTX  │  2. BridgeManager   │                │               │
 │  gas (~$0.001)   │     burns 1000      │                │               │
 │                  │     wUSDT           │                │               │
 │                  │     emits           │                │               │
 │                  │     Withdrawal      │                │               │
 │                  │     event           │                │               │
 │                  │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ►│                │               │
 │                  │                      │                │               │
 │                  │  3. Relayer watches  │                │               │
 │                  │     for Withdrawal   │                │               │
 │                  │     events, batches  │                │               │
 │                  │     them (10 min or  │                │               │
 │                  │     50 withdrawals)  │                │               │
 │                  │                      │                │               │
 │                  │  4. Batch ready!     │                │               │
 │                  │     Relayer calls    │                │               │
 │                  │     iotx_getBridge   │                │               │
 │                  │     ReceiptProof     │                │               │
 │                  │◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                │               │
 │                  │     (RPC call to     │                │               │
 │                  │      iotex-core)     │                │               │
 │                  │                      │                │               │
 │                  │  5. iotex-core       │                │               │
 │                  │     returns:         │                │               │
 │                  │     - block header   │                │               │
 │                  │     - 17+ endorse-   │                │               │
 │                  │       ment sigs      │                │               │
 │                  │     - receipt Merkle  │                │               │
 │                  │       proof          │                │               │
 │                  │     - delegate set   │                │               │
 │                  │─ ─ ─ ─ ─ ─ ─ ─ ─ ─►│                │               │
 │                  │                      │                │               │
 │                  │               6. Relayer sends       │               │
 │                  │                  all data to SP1     │               │
 │                  │                  Prover Network      │               │
 │                  │                      │───────────────►│               │
 │                  │                      │                │               │
 │                  │                      │  7. SP1 Prover │               │
 │                  │                      │     generates  │               │
 │                  │                      │     ZK proof   │               │
 │                  │                      │     (~30-90s)  │               │
 │                  │                      │                │               │
 │                  │                      │  8. Returns    │               │
 │                  │                      │     Groth16    │               │
 │                  │                      │◄───────────────│               │
 │                  │                      │     proof      │               │
 │                  │                      │                │               │
 │                  │               9. Relayer submits     │               │
 │                  │                  proof to Ethereum   │               │
 │                  │                  IoTeXLightClient    │               │
 │                  │                  .verifyBlock()      │               │
 │                  │                      │───────────────────────────────►│
 │                  │                      │                │               │
 │                  │                      │           ┌────┴───────────┐   │
 │                  │                      │           │ RELAYER PAYS   │   │
 │                  │                      │           │ ETH GAS HERE   │   │
 │                  │                      │           │ ~$3-5 per batch│   │
 │                  │                      │           │                │   │
 │                  │                      │           │ REIMBURSED from│   │
 │                  │                      │           │ bridge treasury│   │
 │                  │                      │           │ (see Economics)│   │
 │                  │                      │           └────┬───────────┘   │
 │                  │                      │                │               │
 │                  │                      │               10. Ethereum     │
 │                  │                      │                   verifies     │
 │                  │                      │                   ZK proof     │
 │                  │                      │                   (~280K gas)  │
 │                  │                      │                   stores       │
 │                  │                      │                   verified     │
 │                  │                      │                   IoTeX state  │
 │                  │                      │                │               │
 │  11. User (or anyone) calls                             │               │
 │      BridgeVault.claimWithdrawal()                      │               │
 │      on Ethereum                                        │               │
 │─────────────────────────────────────────────────────────────────────────►│
 │                                                                         │
 │      User pays own ETH gas for claim (~$0.60)                           │
 │      OR relayer includes claim in batch                                 │
 │                                                                         │
 │  12. BridgeVault unlocks 1000 USDT (minus fee)                         │
 │      Fee = max($5, 0.1% × 1000) = $5.00                               │
 │      User receives: 995 USDT                                           │
 │◄─────────────────────────────────────────────────────────────────────────│
 │                                                                         │
 User receives 995 USDT on Ethereum ✓
 Total time: ~10 min (batch window) + ~1-9 min (proof) + ~0.5 min (submit)
```

---

### Relayer Model: Competitive Proving with Fallback

```
                    HOW RELAYING WORKS

  Any delegate can run the relayer service and compete to submit
  ZK proofs. The FIRST valid submission wins 50% of the batch fees.
  This is a free market — no designated rotation required.

  ┌─────────────────────────────────────────────────────────────┐
  │ What happens every 10-minute batch window:                  │
  │                                                             │
  │ t=0:    Batch window opens, withdrawals accumulate          │
  │                                                             │
  │ t=10m:  Batch window closes.                                │
  │         All competing delegates start proving simultaneously│
  │                                                             │
  │ t=11m:  GPU delegate finishes proof in ~1 min → SUBMITS     │
  │         → receives 50% of all fees in this batch ← WINNER  │
  │         → IoTeXLightClient.verifyBlock() returns true       │
  │                                                             │
  │ t=18m:  CPU delegate finishes proof in ~8 min               │
  │         → calls verifyBlock() → returns false (already done)│
  │         → only wastes ~30K gas (early exit, no ZK verify)   │
  │         → learns to check on-chain state before submitting  │
  │                                                             │
  │ Smart relayers: check latestVerified.height before          │
  │ submitting to avoid wasting any gas at all.                 │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ What if NO delegate submits within 30 minutes?              │
  │                                                             │
  │ PERMISSIONLESS FALLBACK:                                    │
  │                                                             │
  │ t=30m:  Fallback window opens. Now ANYONE can submit:       │
  │         - Other delegates                                   │
  │         - Third-party relayers                               │
  │         - MEV searchers                                     │
  │         - The user themselves                               │
  │                                                             │
  │ The fallback submitter earns 1.5x gas cost as bounty        │
  │ from the bridge treasury, ON TOP of the 50% fee share.     │
  │                                                             │
  │ This guarantees: withdrawals are NEVER permanently stuck.   │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ WHY COMPETITIVE > DESIGNATED ROTATION:                      │
  │                                                             │
  │ Designated rotation: if delegate #5 is offline, users       │
  │ wait until the 30-min fallback window. Every offline        │
  │ delegate = guaranteed 30-min delay.                         │
  │                                                             │
  │ Competitive: 24 delegates all try. If even ONE is online    │
  │ with a GPU, proof arrives in ~1 minute. Probability of      │
  │ all 24 being offline simultaneously: effectively zero.      │
  │                                                             │
  │ In practice, 2-5 serious delegates will run GPU provers     │
  │ and compete for the 50% fee reward. The rest participate    │
  │ in consensus + deposit attestation (which is mandatory and  │
  │ free), and earn block rewards as usual.                     │
  └─────────────────────────────────────────────────────────────┘
```

---

### Delegate Economics: Costs and Rewards

```
═══════════════════════════════════════════════════════════════════
  DELEGATE COSTS (per epoch as relayer, ~72 minutes)
═══════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────┬────────────┬───────────────┐
  │ Cost Item                       │ Amount     │ Who Pays      │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ Ethereum RPC endpoint           │ ~$50/month │ Delegate      │
  │ (Infura/Alchemy for sidecar)    │ shared     │ (operational) │
  │                                 │ across all │               │
  │                                 │ epochs     │               │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ ETH gas for proof submission    │ ~$3-5      │ Delegate pays │
  │ (only when it's your turn as    │ per batch  │ upfront, then │
  │  relayer, ~1x per 72 min epoch) │            │ REIMBURSED    │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ SP1 proof generation            │ ~$0.10-1   │ Bridge        │
  │ (Succinct Prover Network fee)   │ per proof  │ Treasury      │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ IoTeX gas for attestation       │ $0         │ FREE          │
  │ (system action, no gas)         │            │ (protocol)    │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ Compute/hardware                │ $0 extra   │ N/A           │
  │ (sidecar is lightweight,        │            │               │
  │  runs on existing node server)  │            │               │
  └─────────────────────────────────┴────────────┴───────────────┘

  Net out-of-pocket per epoch as relayer: ~$3-5 ETH gas
  (immediately reimbursed from bridge treasury)

  Ongoing cost: ~$50/month for ETH RPC
  (or $0 if delegate already runs an Ethereum node)


═══════════════════════════════════════════════════════════════════
  DELEGATE REWARDS
═══════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────┬────────────┬───────────────┐
  │ Revenue Source                  │ Amount     │ Mechanism     │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ 1. 50% of withdrawal fees      │ 50% of fee │ Sent directly │
  │    (relayer delegate reward)    │ collected  │ to relayer    │
  │                                 │            │ who submitted │
  │                                 │            │ the ZK proof  │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ 2. Gas reimbursement            │ 100% of    │ Included in   │
  │    (ETH gas for proof submit)   │ gas spent  │ the 50% share │
  ├─────────────────────────────────┼────────────┼───────────────┤
  │ 3. Existing block rewards       │ unchanged  │ Same as today │
  │    (not affected by bridge)     │            │               │
  └─────────────────────────────────┴────────────┴───────────────┘

  Fee model: max($5 fixed, 0.1% × withdrawal amount)
  Minimum withdrawal: $100

  Fee distribution:
  ┌──────────────────────────┬────────┬──────────────────────────┐
  │ Recipient                │ Share  │ Purpose                  │
  ├──────────────────────────┼────────┼──────────────────────────┤
  │ Relayer delegate         │  50%   │ Gas + reward for ZKP     │
  │ Bridge treasury          │  30%   │ Operations + SP1 costs   │
  │ Security reserve         │  20%   │ Emergency fund           │
  └──────────────────────────┴────────┴──────────────────────────┘

  Example at $10M monthly withdrawal volume:
  - Average fee per withdrawal ≈ max($5, 0.1%) → ~$10K+ total fees/month
  - Fee split:
      50% → relayer delegate = ~$5,000/month ÷ 24 delegates
           = ~$208/delegate/month (shared across rotation)
      30% → bridge treasury (operations + SP1 prover costs)
      20% → security reserve

  At $100M monthly volume:
  - Relayer reward: ~$2,083/delegate/month
  - Treasury: well-funded for all operational costs


═══════════════════════════════════════════════════════════════════
  HOW THE BRIDGE TREASURY WORKS
═══════════════════════════════════════════════════════════════════

  Withdrawal fees accumulate in the BridgeVault contract on Ethereum
  as actual USDT/USDC/WETH/WBTC.

  Fee formula: max(fixedFee[token], 0.1% × withdrawal amount)
  Fixed fees and minimums are set PER TOKEN (different decimals):

  ┌───────────┬───────────┬──────────────┬──────────────────────┐
  │ Token     │ Decimals  │ Fixed Fee    │ Min Withdrawal       │
  ├───────────┼───────────┼──────────────┼──────────────────────┤
  │ USDT      │ 6         │ 5e6 (~$5)    │ 100e6 (~$100)        │
  │ USDC      │ 6         │ 5e6 (~$5)    │ 100e6 (~$100)        │
  │ WETH      │ 18        │ 0.002e18     │ 0.04e18 (~$100)      │
  │           │           │ (~$5@$2500)  │                      │
  │ WBTC      │ 8         │ 8000 (~$5    │ 160000 (~$100        │
  │           │           │  @$60K/BTC)  │  @$60K/BTC)          │
  └───────────┴───────────┴──────────────┴──────────────────────┘
  Note: fixedFee and minWithdrawal are adjustable via governance
  to track price changes.

  ┌──────────────────────────────────────────────────────────┐
  │  EXAMPLE 1: Small withdrawal (500 USDT)                  │
  │                                                          │
  │  Fee: max($5, 0.1% × 500) = max($5, $0.50) = $5.00     │
  │  User receives: 495 USDT                                 │
  │  Fee split: Relayer $2.50 │ Treasury $1.50 │ Reserve $1  │
  │                                                          │
  ├──────────────────────────────────────────────────────────┤
  │  EXAMPLE 2: Large withdrawal (10,000 USDT)               │
  │                                                          │
  │  Fee: max($5, 0.1% × 10000) = max($5, $10) = $10.00    │
  │  User receives: 9,990 USDT                               │
  │  Fee split: Relayer $5 │ Treasury $3 │ Reserve $2        │
  │                                                          │
  ├──────────────────────────────────────────────────────────┤
  │  EXAMPLE 3: Withdrawal (0.5 WETH ≈ $1,250)              │
  │                                                          │
  │  Fee: max(0.002 WETH, 0.1% × 0.5) = max(0.002, 0.0005) │
  │      = 0.002 WETH (~$5)                                  │
  │  User receives: 0.498 WETH                               │
  │  Fee split: Relayer 0.001 │ Treasury 0.0006 │ Rsv 0.0004│
  └──────────────────────────────────────────────────────────┘

  Fee distribution (on-chain, automatic):
  1. Relayer submits ZK proof batch to Ethereum
  2. BridgeVault processes each claim, deducts fee
  3. 50% of fee → relayer address (msg.sender)
  4. 30% of fee → bridge treasury
  5. 20% of fee → security reserve
```

---

### Delegate Requirements Summary

```
═══════════════════════════════════════════════════════════════════
  WHAT EACH DELEGATE MUST DO TO PARTICIPATE IN THE BRIDGE
═══════════════════════════════════════════════════════════════════

  MANDATORY (all 24 delegates):
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  1. Upgrade iotex-core to Yosemite version                  │
  │     (one-time, before hard fork height)                     │
  │                                                             │
  │  2. Run the Bridge Sidecar process                          │
  │     - Lightweight Go binary running alongside iotex-core    │
  │     - Connects to an Ethereum RPC endpoint                  │
  │     - Watches for Deposit events on BridgeVault             │
  │     - Feeds deposit data to iotex-core                      │
  │     - COST: ~$50/month for Ethereum RPC, $0 compute         │
  │     - DOES NOT NEED ETH (read-only)                         │
  │                                                             │
  │  3. Your iotex-core node automatically includes             │
  │     BridgeAttestation system actions in blocks you produce  │
  │     - No manual intervention needed                          │
  │     - Same as PutPollResult today — automatic               │
  │     - COST: $0 (system actions are gasless)                 │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

  OPTIONAL — COMPETE FOR RELAYER REWARDS (any delegate, any time):
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  4. Run the Relayer Service (iotex-bridge-relayer)          │
  │     - Watches IoTeX for Withdrawal events                   │
  │     - Every 10 min: generates ZK proof + submits to ETH    │
  │     - FIRST delegate to submit valid proof WINS 50% of fees│
  │                                                             │
  │  5. Choose your proving method:                             │
  │                                                             │
  │     OPTION A: CPU (existing server, no extra cost)          │
  │     - Proving time: ~8-9 minutes                            │
  │     - Cost: $0 extra                                        │
  │     - Wins when faster provers are offline                  │
  │                                                             │
  │     OPTION B: GPU (add NVIDIA card or rent cloud GPU)       │
  │     - Proving time: ~1 minute                               │
  │     - Cost: ~$200/month cloud or ~$1,500 one-time           │
  │     - Wins most batches = highest earnings                  │
  │                                                             │
  │     OPTION C: Succinct Prover Network API                   │
  │     - Proving time: ~1-2 minutes                            │
  │     - Cost: ~$0.10-1.00 per proof                           │
  │     - No hardware needed, just API call                     │
  │                                                             │
  │  6. Hold ~0.05 ETH for gas                                  │
  │     - Each batch submission costs ~0.01 ETH (~$3-5)         │
  │     - Covered by 50% fee share (winner earns > gas cost)   │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

  OPTIONAL — EXTRA INFRASTRUCTURE:
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  7. Run own Ethereum full node instead of using Infura      │
  │     - Saves ~$50/month RPC cost                              │
  │     - Better reliability and latency                         │
  │     - Recommended for serious relayer competitors           │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

---

### Where Does Each Component Run?

```
═══════════════════════════════════════════════════════════════════
  DEPLOYMENT MAP: What runs where?
═══════════════════════════════════════════════════════════════════

  ON ETHEREUM (Solidity contracts, deployed once):
  ┌─────────────────────────────────────────────────────────────┐
  │  IoTeXLightClient.sol    — stores verified IoTeX state      │
  │  BridgeVault.sol         — locks/unlocks USDT/USDC/WETH/BTC│
  │  SP1 Groth16 Verifier    — already deployed by Succinct     │
  │                            at 0x397A5f7f3dBd538f...         │
  └─────────────────────────────────────────────────────────────┘

  ON IoTeX (Solidity contracts, deployed once):
  ┌─────────────────────────────────────────────────────────────┐
  │  BridgeManager.sol       — mints/burns wrapped tokens       │
  │  WrappedToken.sol (×4)   — wUSDT, wUSDC, wWETH, wWBTC      │
  └─────────────────────────────────────────────────────────────┘

  INSIDE iotex-core (Go, upgraded at Yosemite hard fork):
  ┌─────────────────────────────────────────────────────────────┐
  │  Bridge Protocol         — handles BridgeAttestation,       │
  │                            counts attestations, triggers    │
  │                            mint at 17/24 threshold          │
  │  Receipt Proof API       — serves iotx_getBridgeReceiptProof│
  │                            for relayer to build ZK inputs   │
  └─────────────────────────────────────────────────────────────┘

  ALONGSIDE iotex-core (separate Go process per delegate):
  ┌─────────────────────────────────────────────────────────────┐
  │  Bridge Sidecar          — watches Ethereum Deposit events, │
  │                            feeds to iotex-core bridge       │
  │                            protocol via local RPC           │
  └─────────────────────────────────────────────────────────────┘

  ON COMPETING RELAYER'S SERVER (separate Go process, any delegate):
  ┌─────────────────────────────────────────────────────────────┐
  │  Relayer Service         — watches IoTeX Withdrawal events, │
  │                            batches, calls SP1 prover,       │
  │                            submits proof to Ethereum        │
  └─────────────────────────────────────────────────────────────┘

  ON SUCCINCT PROVER NETWORK (third-party, decentralized):
  ┌─────────────────────────────────────────────────────────────┐
  │  SP1 Prover              — receives proving request from    │
  │                            relayer, generates Groth16 ZK    │
  │                            proof in ~30-90 seconds,         │
  │                            returns proof bytes              │
  │                            Cost: ~$0.10-1.00 per proof      │
  └─────────────────────────────────────────────────────────────┘
```

---

### Who Pays What? Complete Fee Flow

```
═══════════════════════════════════════════════════════════════════
  DIRECTION 1: ETHEREUM → IoTeX (DEPOSIT)
═══════════════════════════════════════════════════════════════════

  ┌───────────────┬──────────────┬──────────┬──────────────────┐
  │ Step          │ Who Pays     │ Cost     │ Notes            │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Lock on ETH   │ User         │ ~$5-15   │ ETH gas for      │
  │               │              │          │ approve + deposit│
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Watch ETH     │ Delegate     │ ~$50/mo  │ Ethereum RPC     │
  │ events        │ (shared)     │ shared   │ subscription     │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Attest on     │ Nobody       │ $0       │ System action,   │
  │ IoTeX         │              │          │ no gas fee       │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Mint wrapped  │ Nobody       │ $0       │ Protocol-level   │
  │ token         │              │          │ state change     │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ TOTAL         │ User         │ ~$5-15   │                  │
  └───────────────┴──────────────┴──────────┴──────────────────┘


═══════════════════════════════════════════════════════════════════
  DIRECTION 2: IoTeX → ETHEREUM (WITHDRAWAL)
═══════════════════════════════════════════════════════════════════

  ┌───────────────┬──────────────┬──────────┬──────────────────┐
  │ Step          │ Who Pays     │ Cost     │ Notes            │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Burn on IoTeX │ User         │ ~$0.001  │ IOTX gas for     │
  │               │              │          │ withdraw() call  │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ ZK proof      │ Bridge       │ ~$0.10-1 │ Succinct Prover  │
  │ generation    │ Treasury     │ per batch│ Network fee      │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Submit proof  │ Relayer      │ ~$3-5    │ ETH gas, relayer │
  │ to Ethereum   │ (delegate)   │ per batch│ pays upfront     │
  │               │              │          │ then REIMBURSED  │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Claim on ETH  │ User         │ ~$0.60   │ ETH gas for      │
  │               │              │          │ claimWithdrawal  │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ Withdrawal    │ User         │ max($5,  │ Deducted from    │
  │ fee           │              │ 0.1%)    │ withdrawal.      │
  │               │              │          │ 50% → relayer    │
  │               │              │          │ 30% → treasury   │
  │               │              │          │ 20% → reserve    │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ TOTAL USER    │ User         │ ~$0.70   │ + max($5, 0.1%)  │
  │ COST          │              │ + fee    │ Min withdrawal:  │
  │               │              │          │ $100             │
  ├───────────────┼──────────────┼──────────┼──────────────────┤
  │ TOTAL DELEGATE│ $0 net       │ earns $  │ 50% of all fees  │
  │ COST          │              │          │ go to relayer    │
  └───────────────┴──────────────┴──────────┴──────────────────┘

  With batching (50 withdrawals per batch):
  - Proof + submit cost: ~$4 ÷ 50 = $0.08 per user (paid by treasury)
  - User total: ~$0.70 + max($5, 0.1%) fee
```

### Component Architecture

```
                ETHEREUM                              IoTeX L1
┌──────────────────────────────┐    ┌──────────────────────────────────┐
│  BridgeVault.sol             │    │  BridgeManager.sol               │
│  - deposit(): lock tokens    │    │  - mintWrapped(): mint on attest │
│  - claimWithdrawal(): unlock │    │  - withdraw(): burn + emit event │
│                              │    │                                  │
│  IoTeXLightClient.sol        │    │  WrappedToken.sol (x4)           │
│  - verifyBlock(): ZK verify  │    │  - wUSDT, wUSDC, wWETH, wWBTC   │
│  - stores verified state     │    │                                  │
│                              │    │  Bridge Protocol (iotex-core)    │
│  SP1 Groth16 Verifier        │    │  - BridgeAttestation sys action  │
│  - 0x397A...deployed         │    │  - deposit handler (17/24 BFT)   │
└──────────────────────────────┘    │  - receipt proof API             │
                                    └──────────────────────────────────┘
                    ▲                              │
                    │          ┌────────────────────┘
                    │          ▼
              ┌─────────────────────────┐
              │  Relayer Service         │
              │  - watches IoTeX events  │
              │  - batches withdrawals   │
              │  - calls SP1 prover      │
              │  - submits to Ethereum   │
              │                          │
              │  Succinct Prover Network │
              │  - generates ZK proofs   │
              │  - ~30-90s per proof     │
              └─────────────────────────┘
```

### 1. Protocol-Level Changes (iotex-core)

#### 1.1 Hard Fork: Yosemite

A new hard fork height `YosemiteBlockHeight` activates the bridge protocol. All node operators must upgrade before this height.

**Genesis Configuration** (`blockchain/genesis/genesis.go`):

```go
type Blockchain struct {
    // ... existing fields ...
    YosemiteBlockHeight uint64 `yaml:"yosemiteHeight"`
}

type Bridge struct {
    EthereumChainID       uint64   `yaml:"ethereumChainID"`       // 1 for mainnet
    EthereumLockContract  string   `yaml:"ethereumLockContract"`  // BridgeVault address on ETH
    SupportedTokens       []string `yaml:"supportedTokens"`       // ETH token addresses
    WrappedTokenContracts []string `yaml:"wrappedTokenContracts"` // IoTeX wrapped token addresses
    MinAttestations       uint64   `yaml:"minAttestations"`       // 17 (BFT >2/3 of 24)
    BatchWindowBlocks     uint64   `yaml:"batchWindowBlocks"`     // blocks before relayer fallback
}

func (g *Blockchain) IsYosemite(height uint64) bool {
    return g.isPost(g.YosemiteBlockHeight, height)
}
```

**Feature Context** (`action/protocol/context.go`):

```go
type FeatureCtx struct {
    // ... existing fields ...
    EnableBridge bool
}
// Set via: EnableBridge: g.IsYosemite(height)
```

#### 1.2 System Action: BridgeAttestation

A new system action type for delegates to attest Ethereum deposit events. Follows the existing `PutPollResult` pattern: zero gas, zero nonce, included by block producer as part of block production.

**Protobuf Definition** (iotex-proto):

```protobuf
message BridgeDeposit {
    bytes   eth_tx_hash    = 1;  // 32-byte Ethereum transaction hash
    string  token          = 2;  // IoTeX wrapped token contract address
    string  recipient      = 3;  // IoTeX recipient address
    string  amount         = 4;  // Token amount as decimal string
    uint64  source_chain   = 5;  // Source chain ID (1 = Ethereum mainnet)
    uint64  deposit_nonce  = 6;  // Monotonic nonce from BridgeVault on ETH
}

message BridgeAttestation {
    uint64 height                    = 1;  // IoTeX block height
    repeated BridgeDeposit deposits  = 2;  // Attested deposits
}

// Added to ActionCore oneof:
message ActionCore {
    oneof action {
        // ... existing actions (field numbers 1-49) ...
        BridgeAttestation bridge_attestation = 50;
    }
}
```

**Go Implementation** (`action/bridgeattestation.go`):

```go
type BridgeAttestation struct {
    height   uint64
    deposits []*BridgeDeposit
}

type BridgeDeposit struct {
    EthTxHash    [32]byte       // Ethereum tx hash
    Token        string         // IoTeX wrapped token address
    Recipient    string         // IoTeX recipient address
    Amount       *big.Int       // Token amount
    SourceChain  uint64         // Source chain ID
    DepositNonce uint64         // Nonce from ETH lock contract
}

// Methods implementing actionPayload interface (following putpollresult.go):
func (a *BridgeAttestation) FillAction(core *iotextypes.ActionCore)
func (a *BridgeAttestation) Proto() *iotextypes.BridgeAttestation
func (a *BridgeAttestation) LoadProto(pb *iotextypes.BridgeAttestation) error
func (a *BridgeAttestation) Serialize() []byte
func (a *BridgeAttestation) IntrinsicGas() (uint64, error) { return 0, nil }
func (a *BridgeAttestation) SanityCheck() error { return nil }
```

#### 1.3 Bridge Protocol

New protocol registered in the protocol registry. Handles deposit attestation counting (ETH→IoTeX) and provides receipt proof generation for withdrawals (IoTeX→ETH).

**Protocol Interface** (`action/protocol/bridge/protocol.go`):

```go
const _protocolID = "bridge"

type Protocol struct {
    addr   address.Address
    cfg    genesis.Bridge
}

// Implements:
//   protocol.Protocol               — Register(), ForceRegister(), Name()
//   protocol.GenesisStateCreator    — CreateGenesisStates(): init nonce counters, token maps
//   protocol.PostSystemActionsCreator — CreatePostSystemActions(): create BridgeAttestation
//   protocol.ActionHandler          — Handle(): process BridgeAttestation, count attestations
//   protocol.Committer              — Commit(): finalize bridge state per block
```

**Deposit Processing Logic** (`action/protocol/bridge/deposit_handler.go`):

```
For each BridgeAttestation system action in a block:
  1. Identify the attesting delegate from the block producer context
  2. For each deposit in the attestation:
     a. Validate: deposit_nonce has not been fully processed
     b. Validate: this delegate has not already attested this nonce
     c. Record attestation: state key "deposit:attest:{nonce}:{delegate}" = true
     d. Increment attestation count for this nonce
     e. If attestation count >= MinAttestations (17):
        i.   Mark deposit as processed: state key "deposit:nonce:{nonce}" = ProcessedDeposit
        ii.  Execute EVM call to BridgeManager.mintWrapped(token, recipient, amount)
        iii. Emit DepositConfirmed log event
```

**Bridge State Keys** (stored in system namespace `"bridge"`):

| Key Pattern | Value Type | Purpose |
|-------------|-----------|---------|
| `deposit:nonce:{n}` | `ProcessedDeposit` | Tracks fully processed deposit nonces |
| `deposit:attest:{n}:{delegate}` | `bool` | Per-delegate attestation record |
| `deposit:count:{n}` | `uint64` | Attestation count per deposit nonce |
| `withdrawal:nonce` | `uint64` | Next withdrawal nonce counter |
| `config:tokens` | `[]TokenPair` | Supported token pair mappings |

#### 1.4 Receipt Merkle Proof Generation

New API endpoint that generates binary Merkle inclusion proofs for transaction receipts, enabling the SP1 ZK prover to prove receipt inclusion against the `receiptRoot` in block headers.

**Proof Structure** (`action/protocol/bridge/receipt_proof.go`):

```go
type ReceiptMerkleProof struct {
    LeafIndex  uint32           // Position of receipt in the block's receipt list
    LeafHash   hash.Hash256     // keccak256(receipt.Serialize())
    Siblings   []hash.Hash256   // Sibling hashes along the path from leaf to root
    Directions []bool           // Path direction: false=left sibling, true=right sibling
}

// GenerateReceiptProof creates a Merkle inclusion proof for the receipt at the given index
func GenerateReceiptProof(receipts []*action.Receipt, index int) (*ReceiptMerkleProof, error)
```

**Critical Implementation Note**: The proof generation MUST exactly replicate the binary Merkle tree construction in `crypto/merkle.go`:

1. Each leaf = `hash.Hash256b(receipt.Serialize())` (Keccak256 of protobuf-serialized receipt)
2. If leaf count is odd, the last leaf is duplicated
3. Internal nodes = `hash.Hash256b(leftChild[:] || rightChild[:])` (Keccak256 of 64-byte concatenation)
4. Tree is computed bottom-up, pairing adjacent nodes at each level
5. If a level has odd node count, the last node is duplicated

**RPC Endpoint**:

```go
// Added to CoreService interface (api/coreservice.go):
GetBridgeReceiptProof(height uint64, txIndex uint32) (*BridgeProofResponse, error)

// Response type:
type BridgeProofResponse struct {
    Header       *iotextypes.BlockHeader       // Full block header
    Endorsements []*iotextypes.Endorsement     // Block footer endorsements (17+ signatures)
    ReceiptProof *ReceiptMerkleProof           // Binary Merkle proof
    Receipt      *iotextypes.Receipt           // The receipt containing the withdrawal event
    DelegateSet  []DelegateInfo                // 24 delegate public keys for this epoch
}

type DelegateInfo struct {
    Address   string   // Delegate operator address
    PublicKey []byte   // Compressed secp256k1 public key (33 bytes)
}
```

Exposed via:
- **gRPC**: `GetBridgeReceiptProof` RPC method
- **JSON-RPC**: `iotx_getBridgeReceiptProof(blockHeight, txIndex)` method

#### 1.5 Protocol Registration

**File**: `chainservice/builder.go`

The bridge protocol is registered in the chain service builder, following the existing pattern for staking, account, execution, and rewarding protocols:

```go
func (builder *Builder) registerBridgeProtocol() error {
    if !builder.cfg.Genesis.IsYosemite(0) {
        return nil  // Bridge not activated
    }
    p := bridge.NewProtocol(builder.cfg.Genesis.Bridge)
    return p.Register(builder.cs.registry)
}

// Called in build() after registerRewardingProtocol() at line 876
```

#### 1.6 File Change Summary (iotex-core)

**New files**:

| File | Purpose |
|------|---------|
| `action/bridgeattestation.go` | BridgeAttestation system action type |
| `action/bridgeattestation_test.go` | Serialization round-trip tests |
| `action/protocol/bridge/protocol.go` | Bridge protocol: register, genesis, handle, system actions |
| `action/protocol/bridge/protocol_test.go` | Protocol unit tests |
| `action/protocol/bridge/config.go` | Bridge-specific configuration types |
| `action/protocol/bridge/deposit_handler.go` | ETH→IoTeX deposit attestation processing |
| `action/protocol/bridge/state.go` | Bridge state key management |
| `action/protocol/bridge/receipt_proof.go` | Receipt binary Merkle proof generation |
| `action/protocol/bridge/receipt_proof_test.go` | Proof generation/verification tests |

**Modified files**:

| File | Change |
|------|--------|
| `blockchain/genesis/genesis.go` | Add `YosemiteBlockHeight`, `Bridge` struct, `IsYosemite()` |
| `blockchain/config.go` | Add `EnableBridgeProtocol` flag |
| `action/protocol/context.go` | Add `EnableBridge` to `FeatureCtx` |
| `action/action_deserializer.go` | Add `BridgeAttestation` case to deserialization switch |
| `chainservice/builder.go` | Add `registerBridgeProtocol()`, call in `build()` |
| `api/coreservice.go` | Add `GetBridgeReceiptProof` interface method and implementation |
| `api/grpcserver.go` | Add gRPC handler for bridge proof endpoint |
| `api/web3server.go` | Add `iotx_getBridgeReceiptProof` JSON-RPC method |

**External dependency**:

| Repo | Change |
|------|--------|
| `iotex-proto` | Add `BridgeAttestation`, `BridgeDeposit` protobuf messages; add field 50 to `ActionCore` oneof; add `GetBridgeReceiptProof` gRPC service definition |

---

### 2. SP1 ZK Program (Rust)

New repository: `iotex-bridge-sp1`

The SP1 guest program cryptographically proves: *"These withdrawal events exist in a valid IoTeX block that was finalized by ≥17 of 24 known delegates via BFT consensus."*

#### 2.1 Repository Structure

```
iotex-bridge-sp1/
├── program/                        # SP1 guest program (compiled to RISC-V → ZK circuit)
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs                 # Entry point: read inputs, verify, commit outputs
│       ├── iotex_header.rs         # Block header protobuf deserialization + Keccak256 hashing
│       ├── consensus_vote.rs       # ConsensusVote construction + BLAKE2b hashing
│       ├── endorsement.rs          # Endorsement message hash + ECDSA verification
│       ├── receipt_merkle.rs       # Binary Merkle proof verification (matching crypto/merkle.go)
│       └── withdrawal.rs          # Withdrawal event log ABI decoding
├── script/                         # Host-side prover application
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs                 # CLI: fetch IoTeX data, generate SP1 proof, output Groth16
│       ├── iotex_client.rs         # Calls iotx_getBridgeReceiptProof RPC
│       └── input_builder.rs        # Constructs BridgeProofInput from RPC response
└── contracts/                      # Foundry project for on-chain verification tests
    ├── src/
    │   └── IoTeXBridgeVerifier.sol  # Integration test contract
    └── test/
        └── Verify.t.sol            # Forge tests: prove + verify cycle
```

#### 2.2 Guest Program Data Types

```rust
/// Input to the SP1 guest program (private witness + public data)
struct BridgeProofInput {
    /// Protobuf-serialized IoTeX BlockHeader (includes sig + pubkey)
    block_header_bytes: Vec<u8>,
    /// Protobuf-serialized IoTeX BlockHeaderCore (without sig + pubkey, for sig verification)
    block_header_core_bytes: Vec<u8>,
    /// 17+ endorsements from block footer
    endorsements: Vec<EndorsementData>,
    /// Full delegate set for this epoch (24 compressed secp256k1 pubkeys)
    delegate_set: Vec<[u8; 33]>,
    /// Merkle inclusion proofs for withdrawal receipts
    receipt_proofs: Vec<ReceiptMerkleProof>,
    /// Protobuf-serialized receipts containing withdrawal events
    withdrawal_receipts: Vec<Vec<u8>>,
}

struct EndorsementData {
    endorser_pubkey: [u8; 33],      // Compressed secp256k1 public key
    signature: [u8; 64],            // ECDSA signature bytes (r || s)
    recovery_id: u8,                // ECDSA recovery ID (v)
    timestamp_secs: u64,            // Endorsement timestamp (seconds)
    timestamp_nanos: u32,           // Endorsement timestamp (nanoseconds)
}

struct ReceiptMerkleProof {
    leaf_index: u32,                // Receipt position in block
    siblings: Vec<[u8; 32]>,        // Sibling hashes along the Merkle path
    directions: Vec<bool>,          // false = sibling is left, true = sibling is right
}

/// Public output committed by the guest program (verified on Ethereum)
struct BridgeProofOutput {
    block_height: u64,
    block_hash: [u8; 32],
    receipt_root: [u8; 32],
    delegate_set_hash: [u8; 32],    // keccak256(abi.encodePacked(sorted delegate pubkeys))
    withdrawals: Vec<WithdrawalClaim>,
}

struct WithdrawalClaim {
    recipient: [u8; 20],            // Ethereum recipient address
    token: [u8; 20],                // Ethereum token address
    amount: [u8; 32],               // uint256 amount
    nonce: u64,                     // Withdrawal nonce from IoTeX bridge contract
}
```

#### 2.3 Verification Algorithm

```
STEP 1: BLOCK HEADER VERIFICATION
  ─────────────────────────────────
  header_core_hash = keccak256(block_header_core_bytes)    // SP1 Keccak256 precompile
  block_hash       = keccak256(block_header_bytes)          // SP1 Keccak256 precompile
  receipt_root     = parse_receipt_root(block_header_bytes) // Extract from protobuf

  // Verify block producer signed the header core
  producer_pubkey  = parse_producer_pubkey(block_header_bytes)
  producer_sig     = parse_producer_sig(block_header_bytes)
  ASSERT ecdsa_verify(producer_pubkey, header_core_hash, producer_sig)
  // Uses SP1 native secp256k1 ECDSA precompile


STEP 2: BFT CONSENSUS VERIFICATION (≥17/24 delegate endorsements)
  ──────────────────────────────────────────────────────────────────
  valid_count    = 0
  seen_delegates = HashSet::new()

  FOR EACH endorsement IN endorsements:

    // 2a. Reconstruct the ConsensusVote that was signed
    //     IoTeX consensus votes are protobuf: { block_hash, topic: COMMIT(2) }
    vote_proto = protobuf_serialize(ConsensusVote {
        block_hash: block_hash,     // 32 bytes
        topic: 2                    // COMMIT
    })

    // 2b. Hash the vote with BLAKE2b-256
    //     NOTE: No SP1 native precompile for BLAKE2b; computed in software (~75K cycles)
    vote_hash = blake2b_256(vote_proto)

    // 2c. Combine vote hash with endorsement timestamp (IoTeX-specific scheme)
    ts_bytes = to_bytes_be(endorsement.timestamp_secs)       // 8 bytes, big-endian
              || to_bytes_be(endorsement.timestamp_nanos)     // 4 bytes, big-endian
    msg_hash = keccak256(vote_hash || ts_bytes)              // SP1 Keccak256 precompile

    // 2d. Verify ECDSA signature
    ASSERT ecdsa_verify(endorsement.endorser_pubkey, msg_hash, endorsement.signature)
    // Uses SP1 native secp256k1 ECDSA precompile

    // 2e. Verify endorser is in the known delegate set
    ASSERT delegate_set.contains(endorsement.endorser_pubkey)
    ASSERT NOT seen_delegates.contains(endorsement.endorser_pubkey)
    seen_delegates.insert(endorsement.endorser_pubkey)
    valid_count += 1

  // BFT threshold: strictly more than 2/3 (matching IoTeX consensus rule)
  ASSERT valid_count * 3 > delegate_set.len() * 2


STEP 3: RECEIPT MERKLE PROOF VERIFICATION
  ─────────────────────────────────────────
  FOR EACH (receipt_bytes, proof) IN zip(withdrawal_receipts, receipt_proofs):

    // 3a. Compute leaf hash (must match crypto/merkle.go in iotex-core)
    leaf_hash = keccak256(receipt_bytes)    // SP1 Keccak256 precompile

    // 3b. Walk binary Merkle tree from leaf to root
    current = leaf_hash
    FOR (sibling, direction) IN zip(proof.siblings, proof.directions):
      IF direction:     // sibling is on the right
        current = keccak256(current || sibling)
      ELSE:             // sibling is on the left
        current = keccak256(sibling || current)

    // 3c. Verify computed root matches the receiptRoot from the verified header
    ASSERT current == receipt_root


STEP 4: WITHDRAWAL EVENT EXTRACTION
  ──────────────────────────────────
  withdrawals = Vec::new()
  FOR receipt_bytes IN withdrawal_receipts:
    receipt = protobuf_deserialize(receipt_bytes)
    FOR log IN receipt.logs:
      // Match the Withdrawal event signature from BridgeManager.sol
      withdrawal_topic = keccak256("Withdrawal(address,address,uint256,uint256,bytes)")
      IF log.topics[0] == withdrawal_topic:
        (sender, token, amount, nonce, eth_recipient) = abi_decode(log)
        withdrawals.push(WithdrawalClaim {
            recipient: eth_recipient,
            token: token,
            amount: amount,
            nonce: nonce,
        })


STEP 5: COMMIT PUBLIC OUTPUTS
  ────────────────────────────
  delegate_set_hash = keccak256(abi.encodePacked(sort(delegate_set)))

  sp1_zkvm::io::commit(&block_height)
  sp1_zkvm::io::commit(&block_hash)
  sp1_zkvm::io::commit(&receipt_root)
  sp1_zkvm::io::commit(&delegate_set_hash)
  sp1_zkvm::io::commit(&withdrawals)
```

#### 2.4 Computational Cost Estimate

| Operation | Count | Cycles/Op | Total Cycles | Method |
|-----------|-------|-----------|-------------|--------|
| ECDSA secp256k1 verify | 18 (1 producer + 17 endorsers) | ~200,000 | ~3,600,000 | SP1 native precompile |
| BLAKE2b-256 hash | 17 (consensus votes) | ~75,000 | ~1,275,000 | Software (RISC-V) |
| Keccak256 hash | ~60 (headers, msgs, Merkle nodes) | ~5,000 | ~300,000 | SP1 native precompile |
| Protobuf deserialization | ~20 (header + receipts) | ~10,000 | ~200,000 | Software |
| Merkle proof verification | ~200 hash ops (10 receipts × ~20 depth) | ~5,000 | ~1,000,000 | SP1 native precompile |
| **TOTAL** | | | **~6,375,000** | |

**Performance estimates**:
- Proof generation (Succinct Prover Network): **~30-90 seconds**
- Groth16 proof size: **~256 bytes**
- On-chain verification gas (Ethereum): **~280,000 gas ≈ $2-5 at 30 gwei**

#### 2.5 BLAKE2b Optimization Path

BLAKE2b-256 is the most computationally expensive operation because SP1 lacks a native precompile for it. Three future optimizations are possible:

- **Option A (Recommended)**: Future IoTeX hard fork switches consensus vote hashing from BLAKE2b to Keccak256. SP1 has a native Keccak256 precompile, reducing per-vote hash cost from ~75K to ~5K cycles (15x improvement).
- **Option B**: Future IoTeX hard fork enables BLS aggregate signatures. A single BLS12-381 aggregate verify replaces 17 individual ECDSA verifications + 17 BLAKE2b hashes. SP1 has native BLS12-381 precompiles. IoTeX already stores `BLSPubKey` in the Candidate struct but does not use it in consensus yet.
- **Option C**: Succinct adds BLAKE2b as a native SP1 precompile (multiple projects have requested this).

---

### 3. Smart Contracts on Ethereum

New repository: `iotex-bridge-contracts`

#### 3.1 IoTeXLightClient.sol

Maintains a cryptographically verified view of IoTeX chain state on Ethereum, updated exclusively via SP1 ZK proofs.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ISP1Verifier} from "@sp1-contracts/ISP1Verifier.sol";

contract IoTeXLightClient {
    /// SP1 canonical Groth16 verifier gateway on Ethereum mainnet
    ISP1Verifier public immutable SP1_VERIFIER;
    // Deployed at: 0x397A5f7f3dBd538f23DE225B51f532c34448dA9B

    /// Verification key for the IoTeX bridge SP1 program
    bytes32 public immutable PROGRAM_VKEY;

    /// Verified IoTeX block state
    struct VerifiedBlock {
        uint64  height;
        bytes32 blockHash;
        bytes32 receiptRoot;
        bytes32 delegateSetHash;
    }

    /// Latest verified IoTeX block
    VerifiedBlock public latestVerified;

    /// Historical verified block hashes (height → blockHash)
    mapping(uint64 => bytes32) public verifiedBlockHashes;

    /// Initial trusted delegate set hash (set at deployment, immutable)
    bytes32 public immutable GENESIS_DELEGATE_SET_HASH;

    event BlockVerified(uint64 indexed height, bytes32 blockHash, bytes32 delegateSetHash);

    constructor(
        address _sp1Verifier,
        bytes32 _programVKey,
        bytes32 _genesisDelegateSetHash,
        uint64  _genesisHeight
    ) {
        SP1_VERIFIER = ISP1Verifier(_sp1Verifier);
        PROGRAM_VKEY = _programVKey;
        GENESIS_DELEGATE_SET_HASH = _genesisDelegateSetHash;
        latestVerified.height = _genesisHeight;
        latestVerified.delegateSetHash = _genesisDelegateSetHash;
    }

    /// @notice Verify an IoTeX block via SP1 ZK proof
    /// @param proof The Groth16 proof bytes
    /// @param publicValues ABI-encoded public outputs from the SP1 program
    function verifyBlock(
        bytes calldata proof,
        bytes calldata publicValues
    ) external returns (bool isNew) {
        // 1. Decode public outputs first (cheap) to check for duplicate submissions
        (
            uint64 height,
            bytes32 blockHash,
            bytes32 receiptRoot,
            bytes32 delegateSetHash
            // Withdrawal data is decoded separately by BridgeVault
        ) = abi.decode(publicValues, (uint64, bytes32, bytes32, bytes32));

        // 2. EARLY EXIT: If this block height is already verified, return false.
        //    This protects competing relayers from wasting gas on the expensive
        //    ZK proof verification step. The losing relayer's tx succeeds (no revert)
        //    but returns false and costs only ~30K gas instead of ~300K.
        if (height <= latestVerified.height) {
            return false;
        }

        // 3. Cryptographically verify the SP1 Groth16 proof (~280K gas)
        SP1_VERIFIER.verifyProof(PROGRAM_VKEY, publicValues, proof);

        // 4. Verify delegate set continuity
        require(
            delegateSetHash == latestVerified.delegateSetHash ||
            delegateSetHash == GENESIS_DELEGATE_SET_HASH,
            "IoTeXLC: unknown delegate set"
        );

        // 5. Store verified state
        latestVerified = VerifiedBlock(height, blockHash, receiptRoot, delegateSetHash);
        verifiedBlockHashes[height] = blockHash;

        emit BlockVerified(height, blockHash, delegateSetHash);
        return true;
    }

    /// @notice Update the accepted delegate set hash
    /// @dev Called when a proof at an epoch boundary introduces a new delegate set.
    ///      The proof itself was verified against the OLD delegate set's signatures,
    ///      so this is a trust-chained rotation.
    function updateDelegateSet(
        bytes calldata proof,
        bytes calldata publicValues,
        bytes32 newDelegateSetHash
    ) external {
        // Verify the proof (signed by old delegate set)
        SP1_VERIFIER.verifyProof(PROGRAM_VKEY, publicValues, proof);

        // Decode and verify the new delegate set hash is committed in the proof
        (, , , bytes32 provenDelegateSetHash) =
            abi.decode(publicValues, (uint64, bytes32, bytes32, bytes32));

        require(provenDelegateSetHash == newDelegateSetHash, "IoTeXLC: delegate set mismatch");

        // Update latest verified delegate set
        latestVerified.delegateSetHash = newDelegateSetHash;
    }
}
```

#### 3.2 BridgeVault.sol

Locks/unlocks tokens on the Ethereum side. Deposits lock tokens and emit events for IoTeX delegates to observe. Withdrawals verify ZK proofs and release locked tokens.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

struct WithdrawalData {
    address recipient;
    address token;
    uint256 amount;
    uint256 nonce;
}

contract BridgeVault {
    using SafeERC20 for IERC20;

    IoTeXLightClient public immutable LIGHT_CLIENT;

    /// Supported bridge tokens (USDT, USDC, WETH, WBTC)
    mapping(address => bool) public supportedTokens;

    /// Processed withdrawal nonces (prevents double-claims)
    mapping(uint256 => bool) public processedWithdrawals;

    /// Deposit nonce counter
    uint256 public depositNonce;

    /// Withdrawal fee: max(fixedFee[token], amount × feeRate / 10000)
    uint256 public withdrawalFeeRate = 10;       // 0.1% (10 basis points)

    /// Per-token fixed fee and minimum withdrawal (different decimals per token)
    /// Set via governance. Examples:
    ///   USDT (6 dec):  fixedFee = 5e6,       minWithdrawal = 100e6       ($5, $100)
    ///   USDC (6 dec):  fixedFee = 5e6,       minWithdrawal = 100e6       ($5, $100)
    ///   WETH (18 dec): fixedFee = 0.002e18,  minWithdrawal = 0.04e18     (~$5, ~$100 at $2500/ETH)
    ///   WBTC (8 dec):  fixedFee = 8000,      minWithdrawal = 160000      (~$5, ~$100 at $60K/BTC)
    mapping(address => uint256) public fixedFee;
    mapping(address => uint256) public minWithdrawal;

    /// Fee distribution addresses
    address public treasury;                      // 30% of fees
    address public securityReserve;               // 20% of fees
    // Remaining 50% goes to msg.sender (relayer)

    /// Per-epoch withdrawal cap (safety mechanism)
    uint256 public maxWithdrawalPerEpoch;

    /// Epoch withdrawal accumulator
    mapping(uint256 => uint256) public epochWithdrawals;

    /// Governance (timelock + multisig, NOT a single key)
    address public governance;

    event Deposit(
        address indexed sender,
        address indexed token,
        uint256 amount,
        bytes   iotexRecipient,
        uint256 nonce
    );

    event WithdrawalClaimed(
        address indexed recipient,
        address indexed token,
        uint256 amount,
        uint256 nonce
    );

    // ═══════════════════════════════════════════════════
    //  DEPOSIT: Ethereum → IoTeX
    // ═══════════════════════════════════════════════════

    /// @notice Lock tokens on Ethereum to bridge to IoTeX
    /// @param token ERC-20 token address (USDT, USDC, WETH, or WBTC)
    /// @param amount Amount of tokens to bridge
    /// @param iotexRecipient IoTeX destination address (as bytes)
    function deposit(
        address token,
        uint256 amount,
        bytes calldata iotexRecipient
    ) external {
        require(supportedTokens[token], "BV: unsupported token");
        require(amount > 0, "BV: zero amount");
        require(iotexRecipient.length > 0, "BV: empty recipient");

        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        emit Deposit(msg.sender, token, amount, iotexRecipient, depositNonce++);
    }

    // ═══════════════════════════════════════════════════
    //  WITHDRAWAL: IoTeX → Ethereum (ZK proof verified)
    // ═══════════════════════════════════════════════════

    /// @notice Claim tokens on Ethereum after ZK proof verification
    /// @param proof SP1 Groth16 proof bytes
    /// @param publicValues ABI-encoded public outputs from SP1 program
    /// @param withdrawalIndex Index of the withdrawal claim in the batch
    function claimWithdrawal(
        bytes calldata proof,
        bytes calldata publicValues,
        uint256 withdrawalIndex
    ) external {
        // 1. Verify the IoTeX block proof via light client
        //    verifyBlock returns false if already verified (saves gas for competing relayers)
        LIGHT_CLIENT.verifyBlock(proof, publicValues);

        // 2. Decode withdrawals from the verified public values
        (, , , , WithdrawalData[] memory withdrawals) =
            abi.decode(publicValues, (uint64, bytes32, bytes32, bytes32, WithdrawalData[]));

        require(withdrawalIndex < withdrawals.length, "BV: invalid index");
        WithdrawalData memory w = withdrawals[withdrawalIndex];

        // 3. Prevent double-claims
        require(!processedWithdrawals[w.nonce], "BV: already claimed");
        processedWithdrawals[w.nonce] = true;

        // 4. Enforce per-epoch withdrawal cap
        uint256 epoch = block.number / 7200;  // ~1 day at 12s blocks
        epochWithdrawals[epoch] += w.amount;
        require(epochWithdrawals[epoch] <= maxWithdrawalPerEpoch, "BV: epoch cap exceeded");

        // 5. Enforce minimum withdrawal (per-token, accounts for different decimals)
        require(w.amount >= minWithdrawal[w.token], "BV: below minimum");

        // 6. Calculate fee: max(fixedFee[token], 0.1% of amount)
        uint256 percentFee = (w.amount * withdrawalFeeRate) / 10000;
        uint256 tokenFixedFee = fixedFee[w.token];
        uint256 fee = percentFee > tokenFixedFee ? percentFee : tokenFixedFee;
        uint256 netAmount = w.amount - fee;

        // 7. Distribute fee: 50% relayer, 30% treasury, 20% reserve
        uint256 relayerShare = fee / 2;              // 50%
        uint256 treasuryShare = (fee * 30) / 100;    // 30%
        uint256 reserveShare = fee - relayerShare - treasuryShare;  // 20%

        IERC20(w.token).safeTransfer(w.recipient, netAmount);
        IERC20(w.token).safeTransfer(msg.sender, relayerShare);     // relayer reward
        IERC20(w.token).safeTransfer(treasury, treasuryShare);
        IERC20(w.token).safeTransfer(securityReserve, reserveShare);

        emit WithdrawalClaimed(w.recipient, w.token, netAmount, w.nonce);
    }

    // ═══════════════════════════════════════════════════
    //  GOVERNANCE (timelock + multisig protected)
    // ═══════════════════════════════════════════════════

    function setWithdrawalCap(uint256 newCap) external {
        require(msg.sender == governance, "BV: not governance");
        maxWithdrawalPerEpoch = newCap;
    }

    function addSupportedToken(
        address token,
        uint256 _fixedFee,
        uint256 _minWithdrawal
    ) external {
        require(msg.sender == governance, "BV: not governance");
        supportedTokens[token] = true;
        fixedFee[token] = _fixedFee;
        minWithdrawal[token] = _minWithdrawal;
    }

    function updateTokenFees(
        address token,
        uint256 _fixedFee,
        uint256 _minWithdrawal
    ) external {
        require(msg.sender == governance, "BV: not governance");
        require(supportedTokens[token], "BV: unsupported token");
        fixedFee[token] = _fixedFee;
        minWithdrawal[token] = _minWithdrawal;
    }
}
```

#### 3.3 Gas Cost Summary (Ethereum)

| Operation | Estimated Gas | USD at 30 gwei |
|-----------|--------------|----------------|
| `deposit()` (lock tokens) | ~80,000 | ~$0.60 |
| `verifyBlock()` (SP1 Groth16 proof + state update) | ~320,000 | ~$2.50 |
| `claimWithdrawal()` (after block is verified) | ~80,000 | ~$0.60 |
| **Full batch: verifyBlock + 10 claims** | **~1,120,000** | **~$8.50** |
| **Per-user cost (amortized over 100 withdrawals/batch)** | **~83,200** | **~$0.65** |

---

### 4. Smart Contracts on IoTeX

New repository: `iotex-bridge-contracts-iotex`

#### 4.1 BridgeManager.sol

Central bridge contract deployed on IoTeX. Handles wrapped token lifecycle.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BridgeManager {
    /// Mapping: Ethereum token address → IoTeX wrapped token address
    mapping(address => address) public wrappedTokens;

    /// Monotonic withdrawal nonce
    uint256 public withdrawalNonce;

    /// Bridge protocol address (system-level, set at deployment)
    address public immutable bridgeProtocol;

    event DepositConfirmed(
        address indexed recipient,
        address indexed wrappedToken,
        uint256 amount,
        uint256 depositNonce
    );

    event Withdrawal(
        address indexed sender,
        address indexed wrappedToken,
        uint256 amount,
        uint256 nonce,
        bytes   ethRecipient
    );

    modifier onlyBridgeProtocol() {
        require(msg.sender == bridgeProtocol, "BM: not bridge protocol");
        _;
    }

    /// @notice Mint wrapped tokens (called by bridge protocol when 17/24 attestations reached)
    function mintWrapped(
        address ethToken,
        address recipient,
        uint256 amount,
        uint256 depositNonce_
    ) external onlyBridgeProtocol {
        address wrapped = wrappedTokens[ethToken];
        require(wrapped != address(0), "BM: unsupported token");
        WrappedToken(wrapped).mint(recipient, amount);
        emit DepositConfirmed(recipient, wrapped, amount, depositNonce_);
    }

    /// @notice Burn wrapped tokens and initiate withdrawal to Ethereum
    /// @param wrappedToken The IoTeX wrapped token to burn
    /// @param amount Amount to withdraw
    /// @param ethRecipient Ethereum destination address (as bytes)
    function withdraw(
        address wrappedToken,
        uint256 amount,
        bytes calldata ethRecipient
    ) external {
        require(amount > 0, "BM: zero amount");
        require(ethRecipient.length == 20, "BM: invalid ETH address");

        WrappedToken(wrappedToken).burn(msg.sender, amount);

        emit Withdrawal(msg.sender, wrappedToken, amount, withdrawalNonce++, ethRecipient);
        // This event is picked up by the relayer, proven via SP1, and submitted to Ethereum
    }
}
```

#### 4.2 WrappedToken.sol

Standard ERC-20 with mint/burn restricted to BridgeManager. One instance per bridged asset.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract WrappedToken is ERC20 {
    address public immutable bridge;
    uint8 private immutable _decimals;

    constructor(
        string memory name_,
        string memory symbol_,
        uint8 decimals_,
        address bridge_
    ) ERC20(name_, symbol_) {
        _decimals = decimals_;
        bridge = bridge_;
    }

    function decimals() public view override returns (uint8) {
        return _decimals;
    }

    function mint(address to, uint256 amount) external {
        require(msg.sender == bridge, "WT: only bridge");
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        require(msg.sender == bridge, "WT: only bridge");
        _burn(from, amount);
    }
}
```

**Deployed instances**:

| Token | Name | Symbol | Decimals |
|-------|------|--------|----------|
| USDT | Wrapped USDT | wUSDT | 6 |
| USDC | Wrapped USDC | wUSDC | 6 |
| WETH | Wrapped WETH | wWETH | 18 |
| WBTC | Wrapped WBTC | wWBTC | 8 |

---

### 5. Relayer Service

New repository: `iotex-bridge-relayer` (Go)

#### 5.1 Architecture

```
iotex-bridge-relayer/
├── cmd/
│   └── relayer/main.go                 # Entry point and CLI
├── pkg/
│   ├── watcher/
│   │   ├── iotex_watcher.go            # Monitors IoTeX for Withdrawal events
│   │   └── eth_watcher.go              # Monitors Ethereum for Deposit events (delegate sidecar)
│   ├── prover/
│   │   ├── sp1_client.go               # HTTP client for Succinct Prover Network API
│   │   ├── input_builder.go            # Builds SP1 program inputs from iotx_getBridgeReceiptProof
│   │   └── batch.go                    # Accumulates withdrawals into proof batches
│   ├── submitter/
│   │   ├── eth_submitter.go            # Submits Groth16 proofs to IoTeXLightClient on Ethereum
│   │   └── gas_oracle.go               # ETH gas price monitoring and optimization
│   └── store/
│       └── db.go                       # Persistent state tracking (SQLite or PostgreSQL)
├── config/
│   └── config.yaml                     # Relayer configuration
└── Dockerfile
```

#### 5.2 Relayer Duty Model: Competitive Proving

**Core principle**: Any delegate can submit a valid ZK proof at any time. The first to submit wins 50% of the batch fees. This creates a **free market for proving** — delegates who invest in faster hardware (GPU) can consistently outcompete CPU-only delegates and earn more rewards.

```
═══════════════════════════════════════════════════════════════════
  COMPETITIVE PROVING: FIRST TO SUBMIT WINS
═══════════════════════════════════════════════════════════════════

  Batch window closes at t=10m. All 24 delegates can start proving.

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  Delegate A (GPU — RTX 4090):                               │
  │  t=10m: starts proving                                      │
  │  t=11m: proof done in ~1 minute ← SUBMITS FIRST, WINS 50% │
  │                                                             │
  │  Delegate B (CPU — 16 cores):                               │
  │  t=10m: starts proving                                      │
  │  t=18m: proof done in ~8 minutes ← too late, someone beat  │
  │         them. Proof not submitted (saves gas).              │
  │                                                             │
  │  Delegate C (Succinct Network API):                         │
  │  t=10m: sends to Succinct Network                           │
  │  t=11m: proof back in ~1 minute ← also fast, but A was     │
  │         first. Could win next time.                         │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

  RESULT: Natural selection for the fastest, most efficient provers.
          Protocol doesn't mandate hardware — the market decides.

  ┌─────────────────────────────────────────────────────────────┐
  │  WHY THIS IS GOOD:                                          │
  │                                                             │
  │  1. No hardware mandate — CPU delegates still participate   │
  │     in consensus and earn block rewards as usual            │
  │                                                             │
  │  2. GPU delegates earn MORE — natural incentive to invest   │
  │     in faster hardware without forcing anyone               │
  │                                                             │
  │  3. Competition drives speed — users get faster withdrawals │
  │                                                             │
  │  4. Redundancy — if the fastest prover goes offline,        │
  │     CPU delegates still submit (just slower)                │
  │                                                             │
  │  5. Permissionless — even non-delegates can submit after    │
  │     the fallback window (30 min)                            │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

**How it works on-chain**: The `IoTeXLightClient.verifyBlock()` and `BridgeVault.claimWithdrawal()` functions are callable by anyone. The first valid transaction to be mined wins. Ethereum's transaction ordering (gas price priority) naturally resolves races. The `msg.sender` of the successful `claimWithdrawal()` call receives 50% of the fees.

**Three tiers of participation**:

```
  ┌────────────────────┬──────────────┬────────────┬────────────────────┐
  │ Tier               │ Hardware     │ Proof Time │ Earning Potential  │
  ├────────────────────┼──────────────┼────────────┼────────────────────┤
  │ Tier 1: GPU Prover │ NVIDIA GPU   │ ~1 min     │ Wins most batches  │
  │ (competitive edge) │ ($200/mo)    │            │ = highest earnings │
  ├────────────────────┼──────────────┼────────────┼────────────────────┤
  │ Tier 2: API Prover │ No extra HW  │ ~1-2 min   │ Competitive, pays  │
  │ (Succinct Network) │ (~$1/proof)  │            │ per-proof fee      │
  ├────────────────────┼──────────────┼────────────┼────────────────────┤
  │ Tier 3: CPU Prover │ Existing     │ ~8-9 min   │ Wins when Tier 1/2 │
  │ (no extra cost)    │ server       │            │ are offline/busy   │
  ├────────────────────┼──────────────┼────────────┼────────────────────┤
  │ Tier 4: Fallback   │ Anyone       │ Any        │ After 30 min, earns│
  │ (permissionless)   │              │            │ 1.5x gas bounty    │
  └────────────────────┴──────────────┴────────────┴────────────────────┘
```

**Fallback guarantee**: If no delegate submits within `BatchWindowBlocks` (~30 minutes), the batch enters permissionless mode. Any Ethereum address can submit a valid proof and earn a bounty (1.5x gas cost) from the bridge treasury. This ensures withdrawals are never stuck.

```
Timeline for a withdrawal batch (fixed 10-minute window):

  t=0:    Batch window opens, withdrawal events accumulate on IoTeX
  t=10m:  Batch window closes — ALL delegates can start proving
          (competitive race begins)
  t=11m:  Fastest prover (GPU/API) submits proof to Ethereum
          → receives 50% of all fees in this batch ← WINNER
          Other delegates see on-chain submission, stop proving

  If nobody submits:
  t=40m:  Fallback window opens (BatchWindowBlocks elapsed)
  t=40m:  Anyone can submit the proof → earns 1.5x gas cost as bounty
```

#### 5.3 Batching Strategy

**Fixed 10-minute batch window** — every 10 minutes, the relayer submits a batch regardless of how many withdrawals are pending (even just 1).

```
═══════════════════════════════════════════════════════════════════
  BATCH WINDOW: FIXED 10 MINUTES
═══════════════════════════════════════════════════════════════════

  t=0min ──────────── t=10min ──────────── t=20min ──────────── t=30min
     │                   │                    │                    │
     │  Window 1         │  Window 2          │  Window 3          │
     │  Collect           │  Collect           │  Collect           │
     │  withdrawals      │  withdrawals       │  withdrawals       │
     │                   │                    │                    │
     ▼                   ▼                    ▼                    ▼
  Submit batch 1      Submit batch 2       Submit batch 3
  (even if 1 tx)      (even if 1 tx)       (even if 1 tx)

  LOW VOLUME SCENARIO (e.g., 5 withdrawals/day):

  ┌──────────────────────────────────────────────────────┐
  │  t=0:   Alice withdraws 500 USDT                     │
  │  t=10m: Batch #1 submitted (1 withdrawal)            │
  │         - SP1 proof: ~$0.50                          │
  │         - ETH gas: ~$3.00                            │
  │         - Total cost: ~$3.50                         │
  │         - Fee collected: $5.00 (fixed minimum)       │
  │         - Relayer earns: $2.50 (50%)                 │
  │         - NET: relayer profits ~$2.50 - $3.50 = -$1  │
  │           (treasury covers shortfall via reserve)     │
  │                                                      │
  │  t=45m: Bob withdraws 2,000 USDT                     │
  │  t=50m: Batch #2 submitted (1 withdrawal)            │
  │         - Fee collected: $5.00 (fixed > 0.1%×2000)   │
  │         - Relayer earns: $2.50 (50%)                 │
  │                                                      │
  │  Average user wait time: ~5 minutes (half of window) │
  └──────────────────────────────────────────────────────┘

  HIGH VOLUME SCENARIO (e.g., 200 withdrawals/day):

  ┌──────────────────────────────────────────────────────┐
  │  t=0-10m: 15 withdrawals accumulate                  │
  │           Total volume: $150,000                     │
  │                                                      │
  │  t=10m:  Batch #1 submitted (15 withdrawals)         │
  │          - SP1 proof: ~$1.00                         │
  │          - ETH gas: ~$5.00 (verify + batch claims)   │
  │          - Total cost: ~$6.00                        │
  │          - Fees collected: ~$150 (0.1% dominates)    │
  │          - Relayer earns: $75 (50%)                  │
  │          - NET: highly profitable                    │
  │                                                      │
  │  Batches per day: ~144                               │
  │  Gas cost/day: ~$864                                 │
  │  Fee revenue/day: ~$5,000+                           │
  │  Relayer share/day: ~$2,500 ÷ 24 = ~$104/delegate   │
  └──────────────────────────────────────────────────────┘
```

| Condition | Behavior |
|-----------|----------|
| Normal / Low volume | Fixed 10-minute window, submit even 1 withdrawal |
| High volume | Fixed 10-minute window, batches naturally larger |
| Emergency | Single withdrawal >$50K triggers immediate proof (skip window) |

#### 5.4 Proving Infrastructure: Why CPU Is Enough

Unlike ZK rollups (zkSync, Scroll, Polygon zkEVM) which must prove entire EVM execution for every block, the IoTeX ZK Bridge only proves that **17 delegates signed a block** — a fundamentally lighter workload.

```
═══════════════════════════════════════════════════════════════════
  ZK BRIDGE vs ZK ROLLUP: PROVING WORKLOAD
═══════════════════════════════════════════════════════════════════

  ┌────────────────────┬─────────────────┬──────────────────────┐
  │                    │ ZK Rollup       │ IoTeX ZK Bridge      │
  │                    │ (zkSync, Scroll)│ (this IIP)           │
  ├────────────────────┼─────────────────┼──────────────────────┤
  │ What to prove      │ Every EVM       │ 17 ECDSA signatures  │
  │                    │ opcode executed │ + 1 Merkle proof     │
  ├────────────────────┼─────────────────┼──────────────────────┤
  │ Computation        │ ~200M cycles    │ ~6.5M cycles         │
  │                    │                 │ (30x lighter)        │
  ├────────────────────┼─────────────────┼──────────────────────┤
  │ Proof frequency    │ Every block     │ Every 10 min         │
  │                    │ (continuous)    │ (only when needed)   │
  ├────────────────────┼─────────────────┼──────────────────────┤
  │ Proofs per day     │ Thousands       │ 5-144                │
  ├────────────────────┼─────────────────┼──────────────────────┤
  │ Hardware required  │ GPU cluster     │ Existing CPU server  │
  │                    │ ($10K-100K+/mo) │ ($0 extra)           │
  ├────────────────────┼─────────────────┼──────────────────────┤
  │ Proving cost/month │ $100K+          │ $50-500              │
  └────────────────────┴─────────────────┴──────────────────────┘

  This is why all ZK rollups need GPU clusters while we don't.
  We're not proving "the entire IoTeX state is correct" —
  we're only proving "17 delegates signed this specific block."
```

**Cycle count breakdown** for the IoTeX bridge SP1 program:

```
  ┌──────────────────────────────────────┬───────────────────────┐
  │ Operation                            │ RISC-V Cycles         │
  ├──────────────────────────────────────┼───────────────────────┤
  │ 18 × ECDSA secp256k1 verify          │ ~3,700,000            │
  │   (1 block producer + 17 endorsers)  │ (SP1 native precompile│
  │                                      │  ~220K cycles each)   │
  ├──────────────────────────────────────┼───────────────────────┤
  │ 17 × BLAKE2b-256 (consensus votes)   │ ~1,275,000            │
  │   (software, no SP1 precompile)      │ (~75K cycles each)    │
  ├──────────────────────────────────────┼───────────────────────┤
  │ ~60 × Keccak256 (headers, Merkle)    │ ~300,000              │
  │   (SP1 native precompile, ~5K each)  │                       │
  ├──────────────────────────────────────┼───────────────────────┤
  │ Merkle proof walks (10 withdrawals)  │ ~1,000,000            │
  ├──────────────────────────────────────┼───────────────────────┤
  │ Protobuf parsing (~20 messages)      │ ~200,000              │
  ├──────────────────────────────────────┼───────────────────────┤
  │ TOTAL                                │ ~6,475,000            │
  └──────────────────────────────────────┴───────────────────────┘
```

**CPU proving time** (based on SP1 official benchmarks, extrapolated for ~6.5M cycles):

```
═══════════════════════════════════════════════════════════════════
  CPU PROVING PERFORMANCE BY HARDWARE
═══════════════════════════════════════════════════════════════════

  SP1 Proving Pipeline:
  Execute → Core Prove → Compress → Groth16 Wrap
  (seconds)  (scales     (scales     (fixed ~144s
              w/ cycles)  sub-linear)  overhead)

  High-spec server (64 vCPU, 512GB RAM):
  ┌────────────────────┬────────────┐
  │ Execute            │ ~3 sec     │
  │ Core Prove         │ ~65 sec    │
  │ Compress           │ ~60 sec    │
  │ Groth16 Wrap       │ ~144 sec   │
  ├────────────────────┼────────────┤
  │ TOTAL              │ ~4.5 min   │
  └────────────────────┴────────────┘

  Typical delegate server (16 cores, 32GB RAM):
  ┌────────────────────┬────────────┐
  │ Execute            │ ~5 sec     │
  │ Core Prove         │ ~180 sec   │
  │ Compress           │ ~150 sec   │
  │ Groth16 Wrap       │ ~180 sec   │
  ├────────────────────┼────────────┤
  │ TOTAL              │ ~8-9 min   │
  └────────────────────┴────────────┘

  With GPU (NVIDIA RTX 4090 or better):
  ┌────────────────────┬────────────┐
  │ TOTAL              │ ~30-60 sec │
  │                    │ (10x+)     │
  └────────────────────┴────────────┘

  With Succinct Prover Network (API call):
  ┌────────────────────┬────────────┐
  │ TOTAL              │ ~30-90 sec │
  │ Cost               │ ~$0.10-1   │
  └────────────────────┴────────────┘
```

**End-to-end user wait time** (initial low volume, CPU only):

```
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  t=0:     User initiates withdrawal on IoTeX                │
  │  t=0-10m: Wait for batch window to close (~5 min average)  │
  │  t=10m:   Fastest delegate starts proving                   │
  │  t=11-19m: ZK proof generation (1 min GPU, 8 min CPU)      │
  │  t=19-20m: Submit to Ethereum + confirm                    │
  │                                                             │
  │  TOTAL USER WAIT (CPU): ~20 minutes                        │
  │  TOTAL USER WAIT (GPU): ~12 minutes                        │
  │                                                             │
  │  For comparison:                                            │
  │  - ioTube (before hack): 10-20 minutes                     │
  │  - Optimism L2 → L1: 7 DAYS                                │
  │  - Centralized exchange withdrawal: 10-60 minutes          │
  │  - Other cross-chain bridges: 15-30 minutes                │
  │                                                             │
  │  Conclusion: Both CPU and GPU times are competitive         │
  │  with existing bridges. CPU is perfectly acceptable.        │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

**Throughput analysis** — can a single CPU delegate keep up?

```
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  Batch interval:     10 minutes                             │
  │  CPU proving time:   ~8-9 minutes                           │
  │                                                             │
  │  → A single CPU delegate can prove 1 batch per 10 minutes  │
  │    (finishes just in time for the next batch)               │
  │                                                             │
  │  → At peak: if proving takes 9 min and batches arrive every│
  │    10 min, there's a 1-minute buffer — tight but workable  │
  │                                                             │
  │  → If volume outgrows CPU capacity, competitive GPU provers│
  │    will naturally step in (they earn more from 50% fees)    │
  │                                                             │
  │  The system self-regulates: more volume → more fees →      │
  │  more incentive for GPU provers → faster proofs            │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

**Industry context** — how do existing ZK rollups handle proving?

```
  ┌──────────────┬──────────────────┬───────────────────────────┐
  │ Project      │ Who runs prover? │ Hardware                  │
  ├──────────────┼──────────────────┼───────────────────────────┤
  │ zkSync Era   │ Matter Labs      │ GPU cluster (centralized) │
  │ Scroll       │ Scroll team      │ GPU cluster (centralized) │
  │ Polygon zkEVM│ Polygon Labs     │ CPU + GPU (centralized)   │
  │ Starknet     │ StarkWare        │ CPU + GPU (centralized)   │
  │ Linea        │ Consensys        │ CPU (centralized)         │
  ├──────────────┼──────────────────┼───────────────────────────┤
  │ Taiko        │ Free market      │ Outsourced to Succinct/   │
  │ (exception)  │ (proposer pays)  │ RISC Zero (decentralized) │
  ├──────────────┼──────────────────┼───────────────────────────┤
  │ IoTeX Bridge │ Competitive      │ CPU (any delegate) or     │
  │ (this IIP)   │ delegate market  │ GPU (competitive edge)    │
  │              │                  │ Fully decentralized       │
  └──────────────┴──────────────────┴───────────────────────────┘

  Key insight: Every ZK rollup runs centralized provers because
  proving entire EVM execution is too expensive to decentralize.

  IoTeX ZK Bridge can afford decentralized proving because our
  workload (~6.5M cycles) is 30x lighter than a ZK rollup's
  (~200M cycles). Even a commodity CPU can handle it.
```

#### 5.5 Ethereum Deposit Watcher (Delegate Sidecar)

Each IoTeX delegate runs a sidecar process that monitors Ethereum for deposit events:

1. Connect to Ethereum JSON-RPC endpoint (Infura, Alchemy, or self-hosted)
2. Subscribe to `BridgeVault.Deposit` events via `eth_getLogs`
3. Wait for Ethereum finality (~15 minutes / 64 blocks after Deposit event)
4. Verify deposit data matches on-chain state
5. Propose `BridgeAttestation` system action during next block production turn
6. IoTeX bridge protocol counts attestations; mints wrapped tokens when 17/24 threshold met

---

### 6. Delegate Set Rotation

The IoTeX delegate set changes every epoch (~1,440 blocks / ~72 minutes at 3s block time). The ZK light client contract on Ethereum must track these changes to continue accepting proofs.

**Mechanism**:

1. The SP1 program commits `delegateSetHash = keccak256(abi.encodePacked(sort(delegate_pubkeys)))` as a public output in every proof
2. The `IoTeXLightClient` contract enforces: each new proof's `delegateSetHash` must match the last accepted `delegateSetHash`
3. At epoch boundaries, the delegate set changes. The relayer submits a proof of a block at the epoch boundary:
   - The block is signed by the **old** delegate set (they produced it)
   - The block's state contains the **new** delegate set (elected for next epoch)
   - The SP1 program verifies old set's signatures and commits the new `delegateSetHash`
   - The light client accepts the rotation because the old (trusted) set vouched for it

This creates a **trust chain** from the genesis delegate set through every epoch rotation, each step cryptographically verified by ZK proof.

---

### 7. Fee Economics

#### Fee Model: Hybrid ($5 Fixed + 0.1%)

```
  Fee = max($5 fixed, 0.1% × withdrawal amount)
  Minimum withdrawal: $100

  ┌─────────────────────┬──────────┬──────────┬──────────────────┐
  │ Withdrawal Amount   │ Fee      │ Fee %    │ Which Applies    │
  ├─────────────────────┼──────────┼──────────┼──────────────────┤
  │ $100 (minimum)      │ $5.00    │ 5.0%     │ $5 fixed         │
  │ $500                │ $5.00    │ 1.0%     │ $5 fixed         │
  │ $1,000              │ $5.00    │ 0.5%     │ $5 fixed         │
  │ $5,000              │ $5.00    │ 0.1%     │ breakeven point  │
  │ $10,000             │ $10.00   │ 0.1%     │ 0.1% percentage  │
  │ $50,000             │ $50.00   │ 0.1%     │ 0.1% percentage  │
  │ $100,000            │ $100.00  │ 0.1%     │ 0.1% percentage  │
  └─────────────────────┴──────────┴──────────┴──────────────────┘

  Crossover point: $5,000 (below → $5 fixed; above → 0.1%)
```

#### Fee Distribution

```
  ┌─────────────────────────────────────────────────────────┐
  │                    Fee Distribution                      │
  │                                                          │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
  │  │  50% Relayer  │  │ 30% Treasury │  │ 20% Security │   │
  │  │   Delegate    │  │              │  │   Reserve    │   │
  │  │              │  │  Operations  │  │              │   │
  │  │  Reward for  │  │  SP1 costs   │  │  Emergency   │   │
  │  │  submitting  │  │  Gas backup  │  │  fund for    │   │
  │  │  ZK proof    │  │  Development │  │  exploits    │   │
  │  └──────────────┘  └──────────────┘  └──────────────┘   │
  └─────────────────────────────────────────────────────────┘
```

| Recipient | Share | Purpose |
|-----------|-------|---------|
| Relayer delegate (msg.sender) | 50% | Direct reward for submitting ZK proof to Ethereum |
| Bridge treasury | 30% | Operations, SP1 prover costs, gas backup |
| Security reserve | 20% | Emergency fund, capped withdrawal buffer |

#### Cost Structure

| Cost | Amount | Frequency |
|------|--------|-----------|
| SP1 proof generation | ~$0.10-1.00 per proof | Per batch (every 10 min) |
| Ethereum gas (verifyBlock) | ~$2.50 at 30 gwei | Per batch |
| Ethereum gas (per claim) | ~$0.60 at 30 gwei | Per withdrawal |
| **Total per batch (1 withdrawal)** | **~$4.10** | **Worst case** |
| **Total per batch (50 withdrawals)** | **~$33** | **High volume** |

#### Break-Even Analysis

```
  LOW VOLUME ($1M monthly, ~5 withdrawals/day):
  - Avg withdrawal: ~$6,600
  - Fee per withdrawal: ~$6.60 (0.1% applies)
  - Monthly fee revenue: ~$1,000
  - Monthly gas cost: ~$600 (144 batches/day × 30 days, most empty)
  - Monthly SP1 cost: ~$15 (5 proofs/day × $0.10 × 30)
  - Status: SUSTAINABLE ✓ (empty batches skipped, only submit when pending)

  HIGH VOLUME ($10M monthly, ~200 withdrawals/day):
  - Monthly fee revenue: ~$10,000+
  - Monthly gas cost: ~$3,000
  - Monthly SP1 cost: ~$450
  - Status: HIGHLY PROFITABLE ✓
  - Relayer share: ~$5,000/month ÷ 24 = ~$208/delegate/month
```

Note: In practice, the relayer skips empty 10-minute windows (no pending
withdrawals = no batch needed). The "fixed 10-minute window" means the
relayer checks every 10 minutes and submits if there are pending withdrawals.

---

## Rationale

### Why SP1 over other ZK frameworks?

| Framework | Pros | Cons |
|-----------|------|------|
| **SP1 (Succinct)** | Production-ready; native ECDSA/Keccak precompiles; Groth16 verifier deployed on ETH mainnet; decentralized Prover Network; write logic in Rust | BLAKE2b not native (software emulation) |
| Risc0 | Similar RISC-V zkVM approach | Smaller ecosystem, fewer crypto precompiles |
| Circom/Groth16 | Most efficient for bespoke circuits | Requires manual circuit design in DSL, not Rust |
| Halo2 | Flexible, no trusted setup | Complex API, steep learning curve |

SP1 is chosen because: (1) verification logic is written in standard Rust, not a specialized circuit DSL; (2) native secp256k1 ECDSA and Keccak256 precompiles exactly match IoTeX's cryptographic primitives; (3) canonical verifier contracts are already deployed and audited on Ethereum mainnet; (4) the Succinct Prover Network provides production-ready decentralized proof generation; (5) proven in production securing $40M+ TVL on Gnosis Chain bridge.

### Why delegate attestation for ETH→IoTeX deposits?

The deposit direction uses delegate BFT attestation (17/24 threshold) rather than ZK proofs of Ethereum consensus because:

1. **Same trust model**: Users who trust IoTeX consensus (17/24 delegates) already trust this mechanism
2. **Zero gas cost**: System actions are free on IoTeX — no gas burden on users or delegates
3. **Instant finality**: Deposits confirmed in one IoTeX block (~3 seconds after threshold reached)
4. **Simplicity**: Proving Ethereum's consensus in ZK requires verifying ~1M validator signatures — orders of magnitude more complex
5. **Upgrade path**: ZK proofs of Ethereum consensus can be added later via SP1 Helios without breaking changes

### Why not a simple multisig bridge (again)?

The ioTube hack demonstrated that multisig bridges have a fundamental architectural weakness: **keys can be stolen**. No amount of operational security (HSMs, MPC, key rotation) eliminates the attack surface of human-managed keys. A ZK bridge eliminates all key-dependent trust. The only assumptions are:

1. **ZK proof soundness** (mathematical, well-studied, audited)
2. **IoTeX BFT consensus security** (which users already trust by using IoTeX)

### Why CPU proving is sufficient (no mandatory GPU requirement)?

A common misconception is that ZK proofs require specialized GPU hardware. This is true for **ZK rollups** (zkSync, Scroll, Polygon zkEVM) which must prove entire EVM execution (~200M RISC-V cycles per block). The IoTeX ZK Bridge only proves **17 ECDSA signatures + 1 Merkle proof** (~6.5M cycles) — 30x lighter. At this scale, a standard 16-core CPU server generates a Groth16 proof in ~8-9 minutes, which is perfectly acceptable for a cross-chain bridge with a 10-minute batch window.

This design choice is critical for delegate accessibility:
- **No hardware barrier**: Delegates participate with existing servers, no GPU required
- **Voluntary GPU upgrade**: Delegates who want higher earnings can add a GPU (~$200/month cloud or ~$1,500 one-time purchase) to prove in ~1 minute instead of ~9 minutes
- **Self-regulating market**: As bridge volume grows, fee revenue increases, naturally attracting GPU-equipped provers without protocol-level mandates
- **Decentralization preserved**: Unlike ZK rollups (all centralized provers), IoTeX achieves decentralized proving because the workload is light enough for commodity hardware

### Why competitive proving (race-to-submit) instead of designated rotation?

A designated rotation model (delegate #N is the relayer for epoch #N) has a single point of failure: if that delegate is slow or offline, all withdrawals wait. Competitive proving — where any delegate can submit and the first valid submission wins — is superior because:

1. **Speed optimization**: GPU-equipped delegates naturally provide faster user experience without protocol mandates
2. **No single point of failure**: If the fastest prover goes offline, the next fastest takes over seamlessly
3. **Economic alignment**: 50% fee reward creates a genuine business opportunity for delegates who invest in proving infrastructure
4. **Permissionless fallback**: After 30 minutes, even non-delegates can submit, ensuring withdrawals are never permanently stuck
5. **Evolutionary pressure**: Over time, the proving market naturally optimizes — delegates find the most cost-effective setup (CPU, GPU, cloud GPU, or Succinct Network API)

This is similar to Taiko's "proposer pays prover" model — the only ZK rollup with decentralized proving in production.

### Why Hybrid fee model (max($5, 0.1%))?

A pure percentage fee (0.1%) fails for small withdrawals: a $200 withdrawal generates only $0.20, which doesn't cover the ~$3-5 ETH gas cost per batch. A pure fixed fee ($5) is disproportionately expensive for large withdrawals. The hybrid model `max($5, 0.1%)` ensures:

- **Small withdrawals ($100-$5,000)**: $5 fixed fee covers gas costs even in single-withdrawal batches
- **Large withdrawals (>$5,000)**: 0.1% scales proportionally, remaining competitive with centralized exchanges
- **Minimum withdrawal ($100)**: Prevents dust attacks and ensures fee economics are viable

The 50/30/20 split (relayer/treasury/reserve) directly incentivizes delegates to perform relayer duty — the relayer who submits the ZK proof receives 50% of all fees in that batch, making it economically rational to participate.

### Why permissionless relayer fallback?

A delegate-only relayer model creates a liveness risk: if the designated delegate goes offline, withdrawals could be stuck until the next epoch rotation. The permissionless fallback (with economic incentive) ensures:

1. **Liveness**: Withdrawals are never permanently stuck
2. **Decentralization**: No single entity can censor withdrawals
3. **Economic alignment**: Bounty (1.5x gas cost) attracts rational operators
4. **Simplicity**: No complex sequencer rotation protocol needed

---

## Backwards Compatibility

### Consensus Changes

The `BridgeAttestation` system action is a new action type activated at `YosemiteBlockHeight`. Blocks produced after this height may contain `BridgeAttestation` actions. **All node operators must upgrade to a Yosemite-compatible version before `YosemiteBlockHeight` is reached.** Nodes running older versions will reject blocks containing the new action type, causing a chain split.

### State Changes

New state keys are added under the `"bridge"` namespace in the protocol state factory. These do not conflict with existing namespaces (`"account"`, `"staking"`, `"poll"`, `"rewarding"`). No existing state is modified or migrated.

### API Changes

The new RPC method `iotx_getBridgeReceiptProof` is purely additive. All existing gRPC and JSON-RPC methods continue to function without modification.

### Action Serialization

The `ActionCore` protobuf oneof is extended with a new field number (50). Existing field numbers (1-49) are unchanged. Older clients will safely ignore the new field when deserializing. Newer clients can deserialize both old and new action types.

### Smart Contract Compatibility

All new contracts (BridgeManager, WrappedToken) are standard Solidity contracts deployed via EVM execution on IoTeX. They do not modify the EVM itself or any existing deployed contracts.

---

## Security Analysis

### Why This Bridge Is More Secure Than ioTube

```
═══════════════════════════════════════════════════════════════════
  SECURITY COMPARISON: ioTube vs ZK Light Client Bridge
═══════════════════════════════════════════════════════════════════

  ioTube (COMPROMISED)                   ZK Light Client Bridge
  ─────────────────────                  ──────────────────────────

  Trust model:                           Trust model:
  ┌───────────────────────┐              ┌───────────────────────┐
  │ Single validator key  │              │ Mathematics (ZK proof)│
  │ controls upgrades     │              │ + IoTeX BFT consensus │
  │                       │              │                       │
  │ ONE key compromised   │              │ No keys to steal      │
  │ = TOTAL bridge loss   │              │ No contract to        │
  │                       │              │ upgrade maliciously   │
  └───────────────────────┘              └───────────────────────┘

  Attack surface:                        Attack surface:
  ┌───────────────────────┐              ┌───────────────────────┐
  │ ✗ Private key theft   │              │ ✓ No private keys in  │
  │ ✗ Contract upgrade    │              │   the trust path      │
  │   to malicious code   │              │ ✓ Immutable verifier  │
  │ ✗ Single point of     │              │ ✓ 17/24 BFT threshold │
  │   failure             │              │ ✓ Math-based security │
  │ ✗ Social engineering  │              │ ✓ No admin override   │
  │   of key holder       │              │ ✓ On-chain withdrawal │
  │                       │              │   caps as safety net  │
  └───────────────────────┘              └───────────────────────┘

  What the ioTube attacker did:          Same attack on ZK bridge:
  ┌───────────────────────┐              ┌───────────────────────┐
  │ 1. Stole 1 private key│              │ 1. No key to steal    │
  │ 2. Called upgradeTo() │              │ 2. No upgradeTo()     │
  │    with malicious     │              │    (immutable verifier│
  │    contract           │              │    + timelock upgrade)│
  │ 3. Bypassed all       │              │ 3. ZK proof is either │
  │    signature checks   │              │    valid or not —     │
  │ 4. Drained $4.4M      │              │    cannot be forged   │
  │                       │              │ 4. Even if everything │
  │ Total time: minutes   │              │    else fails, caps   │
  │                       │              │    limit loss to $100K│
  └───────────────────────┘              └───────────────────────┘
```

### Security Assumptions

This bridge makes exactly **three** trust assumptions. All are explicit, auditable, and well-understood:

```
═══════════════════════════════════════════════════════════════════
  TRUST ASSUMPTION #1: ZK Proof Soundness (IoTeX → Ethereum)
═══════════════════════════════════════════════════════════════════

  What we trust: The SP1 Groth16 proof system is sound — a valid
  proof can only be generated from a valid witness (real IoTeX
  block data with real delegate signatures).

  Why this is safe:
  ┌─────────────────────────────────────────────────────────────┐
  │ • Groth16: 8+ years of academic study, used in Zcash since │
  │   2016, battle-tested in production                        │
  │ • SP1 verifier: audited by 4 independent firms             │
  │   (Veridise, Cantina, Zellic, KALOS)                       │
  │ • BN254 pairing: widely used, well-understood security     │
  │ • Trusted setup: SP1 uses universal setup (not per-circuit)│
  └─────────────────────────────────────────────────────────────┘

  What if this assumption breaks?
  ┌─────────────────────────────────────────────────────────────┐
  │ DEFENSE IN DEPTH:                                          │
  │ • Withdrawal cap: max $100K per epoch (~1 day)             │
  │ • Governance pause: timelock + multisig can freeze bridge  │
  │ • Gradual cap increase: community can react before caps    │
  │   are raised to dangerous levels                           │
  │ • Worst case: attacker drains $100K, bridge is paused,     │
  │   remaining TVL is safe                                    │
  └─────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════
  TRUST ASSUMPTION #2: IoTeX BFT Consensus (Ethereum → IoTeX)
═══════════════════════════════════════════════════════════════════

  What we trust: 17 of 24 IoTeX delegates will not collude to
  forge deposit attestations.

  Why this is safe:
  ┌─────────────────────────────────────────────────────────────┐
  │ • This is IDENTICAL to trusting IoTeX itself               │
  │ • If you hold IOTX, you already trust this assumption      │
  │ • 17/24 = 70.8% threshold (stricter than most PoS chains)  │
  │ • Delegates are elected by stakers — economic alignment    │
  │ • Collusion would destroy delegate reputation + staked IOTX│
  │ • No NEW trust assumption — just reuses existing consensus │
  └─────────────────────────────────────────────────────────────┘

  What if 17 delegates collude?
  ┌─────────────────────────────────────────────────────────────┐
  │ If 17/24 delegates collude, the ENTIRE IoTeX chain is      │
  │ compromised — not just the bridge. This is the fundamental │
  │ security model of IoTeX. The bridge adds ZERO additional   │
  │ trust beyond what the chain already requires.              │
  └─────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════
  TRUST ASSUMPTION #3: Smart Contract Correctness
═══════════════════════════════════════════════════════════════════

  What we trust: The Solidity contracts (BridgeVault, IoTeXLightClient,
  BridgeManager, WrappedToken) are free of exploitable bugs.

  How we ensure this:
  ┌─────────────────────────────────────────────────────────────┐
  │ • Independent security audit (Zellic / Trail of Bits /     │
  │   OpenZeppelin) before mainnet                             │
  │ • Formal verification of critical paths (fee calculation,  │
  │   withdrawal cap enforcement)                              │
  │ • Minimal contract surface area — each contract does one   │
  │   thing well                                               │
  │ • Immutable verification key and verifier address           │
  │ • No single-key admin — timelock + multisig governance     │
  │ • No upgradeTo() without governance vote + timelock delay  │
  └─────────────────────────────────────────────────────────────┘
```

### Security Guarantees

```
═══════════════════════════════════════════════════════════════════
  WHAT THIS BRIDGE GUARANTEES
═══════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────┬─────────┬─────────────────┐
  │ Property                       │ Status  │ How              │
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ No single point of failure     │ ✓       │ 17/24 BFT, no   │
  │                                │         │ single admin key │
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ No private key in trust path   │ ✓       │ ZK proof replaces│
  │ (IoTeX→ETH direction)         │         │ all signatures   │
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ Withdrawals cannot be censored │ ✓       │ Permissionless   │
  │                                │         │ fallback relayer │
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ Withdrawals cannot be forged   │ ✓       │ ZK proof of real │
  │                                │         │ IoTeX consensus  │
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ Double-spend impossible        │ ✓       │ On-chain nonce   │
  │                                │         │ tracking         │
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ Damage capped even if all      │ ✓       │ $100K per-epoch  │
  │ other assumptions fail         │         │ withdrawal cap   │
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ Bridge admin cannot steal funds│ ✓       │ No admin bypass, │
  │                                │         │ timelock upgrades│
  ├─────────────────────────────────┼─────────┼─────────────────┤
  │ Relayer cannot steal/censor    │ ✓       │ Relayer only     │
  │                                │         │ submits proofs,  │
  │                                │         │ cannot alter them│
  └─────────────────────────────────┴─────────┴─────────────────┘

  COMPARISON WITH COMMON BRIDGE MODELS:

  ┌──────────────────────┬────────┬────────┬────────┬────────────┐
  │ Property             │ ioTube │ Multi- │ MPC    │ ZK Light   │
  │                      │ (old)  │ sig    │ Bridge │ Client     │
  ├──────────────────────┼────────┼────────┼────────┼────────────┤
  │ Keys to compromise   │ 1      │ K of N │ T of N │ 0 (IoTeX→E)│
  │ for theft            │        │        │        │ 17 (E→IoTeX)│
  ├──────────────────────┼────────┼────────┼────────┼────────────┤
  │ Admin can drain?     │ YES    │ Maybe  │ Maybe  │ NO         │
  ├──────────────────────┼────────┼────────┼────────┼────────────┤
  │ Math-verified?       │ No     │ No     │ No     │ YES        │
  ├──────────────────────┼────────┼────────┼────────┼────────────┤
  │ Damage cap?          │ No     │ No     │ No     │ YES ($100K)│
  ├──────────────────────┼────────┼────────┼────────┼────────────┤
  │ Censorship-resistant?│ No     │ Maybe  │ Maybe  │ YES        │
  ├──────────────────────┼────────┼────────┼────────┼────────────┤
  │ Trustless?           │ No     │ No     │ No     │ YES        │
  │ (IoTeX→ETH direction)│        │        │        │ (ZK proof) │
  └──────────────────────┴────────┴────────┴────────┴────────────┘
```

---

## IoTeX L1 Sovereignty

This IIP is specifically designed to preserve IoTeX's sovereignty as an independent Layer 1 blockchain. IoTeX is **NOT** becoming an Ethereum Layer 2 — this must be clearly understood.

### What Makes IoTeX a Sovereign L1 (Unchanged by This IIP)

```
═══════════════════════════════════════════════════════════════════
  IoTeX SOVEREIGNTY: WHAT STAYS THE SAME
═══════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  1. OWN CONSENSUS                                          │
  │     IoTeX uses Roll-DPoS with 24 elected delegates         │
  │     NOT Ethereum validators, NOT a sequencer               │
  │     Block time: 3 seconds (independent of Ethereum)        │
  │                                                             │
  │  2. OWN GOVERNANCE                                         │
  │     IOTX stakers elect delegates                            │
  │     Protocol upgrades decided by IoTeX community            │
  │     NOT governed by Ethereum Foundation                    │
  │                                                             │
  │  3. OWN EXECUTION                                          │
  │     IoTeX runs its own EVM instance                         │
  │     Transactions settle on IoTeX L1 — NOT posted to ETH    │
  │     State root is NOT submitted to any Ethereum contract   │
  │                                                             │
  │  4. OWN TOKEN ECONOMICS                                    │
  │     IOTX is the native gas token                            │
  │     Block rewards, staking, burning — all independent      │
  │     NOT paying gas to Ethereum for settlement              │
  │                                                             │
  │  5. OWN DATA AVAILABILITY                                  │
  │     Transaction data lives on IoTeX nodes                   │
  │     NOT posted as calldata/blobs to Ethereum               │
  │     No dependency on Ethereum DA layer                      │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

### How This Differs From a Layer 2

```
═══════════════════════════════════════════════════════════════════
  IoTeX + ZK BRIDGE  vs  Ethereum Layer 2 (Rollup)
═══════════════════════════════════════════════════════════════════

  ┌────────────────────┬──────────────────┬─────────────────────┐
  │ Property           │ IoTeX + ZK Bridge│ Ethereum L2 Rollup  │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ Consensus          │ Own (Roll-DPoS)  │ None (uses ETH      │
  │                    │                  │ consensus)           │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ Finality source    │ IoTeX delegates  │ Ethereum L1          │
  │                    │ (3s blocks)      │ (12min+ for L2)      │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ State root posted  │ NO — only when   │ YES — every batch    │
  │ to Ethereum?       │ bridging assets  │ must post state root │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ Tx data posted     │ NO               │ YES — all tx data    │
  │ to Ethereum?       │                  │ as calldata/blobs    │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ Gas token          │ IOTX             │ ETH                  │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ Can operate if     │ YES — fully      │ NO — settlement      │
  │ Ethereum is down?  │ independent      │ halts                │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ Governance         │ IOTX stakers     │ Rollup team / ETH    │
  │                    │                  │ governance            │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ ZK proof purpose   │ Verify bridge    │ Verify ALL state     │
  │                    │ withdrawals ONLY │ transitions          │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ ETH gas cost       │ Only for bridge  │ Continuous: every    │
  │                    │ txns (~$4/batch) │ batch costs $100s+   │
  ├────────────────────┼──────────────────┼─────────────────────┤
  │ Sovereignty        │ FULL             │ NONE (derived from   │
  │                    │                  │ Ethereum)            │
  └────────────────────┴──────────────────┴─────────────────────┘

  KEY INSIGHT: IoTeX uses ZK proofs ONLY for cross-chain asset
  bridging — not for settlement, not for state verification,
  not for data availability. This is fundamentally different
  from being a ZK rollup.

  ANALOGY:
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  ZK Rollup = you LIVE in Ethereum's house, follow their    │
  │              rules, pay their rent (gas), and your security │
  │              depends entirely on them                       │
  │                                                             │
  │  IoTeX + ZK Bridge = you own your OWN house, but you have  │
  │                      a mathematically verified secure       │
  │                      tunnel to Ethereum's house for moving  │
  │                      assets back and forth                  │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

### DePIN Sovereignty Rationale

IoTeX's mission is DePIN (Decentralized Physical Infrastructure Networks). DePIN requires:
- **Low latency**: 3-second block times for real-time device data (vs 12s+ on Ethereum L2s)
- **Low fees**: Sub-cent gas costs for high-frequency IoT transactions
- **Custom consensus**: Domain-specific validator requirements for DePIN
- **Independent governance**: Protocol upgrades driven by DePIN ecosystem needs, not Ethereum politics

Becoming an Ethereum L2 would compromise all of these. The ZK bridge preserves full DePIN sovereignty while enabling seamless Ethereum liquidity access.

---

## Migration Path to Ethereum Native Rollup (EIP-8079)

### Current Status of EIP-8079

As of March 2026, Ethereum's Native Rollup proposal (EIP-8079) is in **Draft** stage:

```
  ┌─────────────────────────────────────────────────────────────┐
  │  EIP-8079 Timeline (estimated):                             │
  │                                                             │
  │  2025 Q4:  EIP draft published                              │
  │  2026 H1:  Prototype in Glamsterdam fork (optimistic)       │
  │  2026-27:  Testnet, audits, iteration                       │
  │  2027+:    Mainnet (full ZK EXECUTE precompile)             │
  │                                                             │
  │  Current: NOT production-ready                              │
  └─────────────────────────────────────────────────────────────┘
```

### How IIP-57 Prepares for Native Rollup Migration

The ZK Light Client Bridge is designed as a **stepping stone**, not a dead end. If/when Ethereum's Native Rollup infrastructure matures, IoTeX can migrate the bridge verification with minimal changes:

```
═══════════════════════════════════════════════════════════════════
  MIGRATION PATH: ZK BRIDGE → NATIVE ROLLUP VERIFICATION
═══════════════════════════════════════════════════════════════════

  TODAY (IIP-57):
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  IoTeX Block                                                 │
  │      │                                                       │
  │      ▼                                                       │
  │  SP1 Program (our Rust code)                                 │
  │      │ generates                                             │
  │      ▼                                                       │
  │  Groth16 Proof                                               │
  │      │ verified by                                           │
  │      ▼                                                       │
  │  IoTeXLightClient.sol (our contract on Ethereum)             │
  │      │ calls                                                 │
  │      ▼                                                       │
  │  SP1 Verifier Contract (Succinct's contract on Ethereum)     │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

  FUTURE (with EIP-8079 Native Rollup):
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  IoTeX Block                                                 │
  │      │                                                       │
  │      ▼                                                       │
  │  SP1 Program (SAME Rust code, reused)                        │
  │      │ generates                                             │
  │      ▼                                                       │
  │  Groth16 Proof                                               │
  │      │ verified by                                           │
  │      ▼                                                       │
  │  EXECUTE precompile (Ethereum L1 native, ~10x cheaper gas)   │
  │      │                                                       │
  │      ▼                                                       │
  │  IoTeXLightClient.sol (our contract, minimal changes)        │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

  WHAT CHANGES:
  ┌──────────────────────┬──────────────────┬────────────────────┐
  │ Component            │ Today            │ With EIP-8079      │
  ├──────────────────────┼──────────────────┼────────────────────┤
  │ SP1 Rust program     │ Our code         │ SAME (reused)      │
  │ ZK proof format      │ Groth16/BN254    │ SAME               │
  │ Verification         │ SP1 Verifier     │ EXECUTE precompile │
  │                      │ contract         │ (Ethereum-native)  │
  │ IoTeXLightClient     │ Calls external   │ Calls precompile   │
  │                      │ verifier         │ (1 line change)    │
  │ Verification gas     │ ~280K gas        │ ~28K gas (est.)    │
  │ Prover               │ Succinct Network │ SAME               │
  │ IoTeX L1 changes     │ None needed      │ None needed        │
  │ IoTeX sovereignty    │ FULL             │ FULL (still L1)    │
  └──────────────────────┴──────────────────┴────────────────────┘

  KEY POINT: The migration is a 1-line contract change:

  // Before (IIP-57):
  SP1_VERIFIER.verifyProof(PROGRAM_VKEY, publicValues, proof);

  // After (EIP-8079):
  EXECUTE_PRECOMPILE.verify(PROGRAM_VKEY, publicValues, proof);
```

### Why Not Wait for EIP-8079?

```
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. EIP-8079 is 12-18+ months away from production          │
  │ 2. IoTeX needs a secure bridge NOW (ioTube was hacked)     │
  │ 3. IIP-57 work is NOT wasted — SP1 program is reused       │
  │ 4. IIP-57 gives IoTeX production ZK bridge experience      │
  │ 5. Even with EIP-8079, IoTeX remains a sovereign L1        │
  │    — it uses EXECUTE for bridge verification only, not      │
  │    for settlement (still not a rollup)                      │
  └─────────────────────────────────────────────────────────────┘
```

### Long-Term Architecture Options

```
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  Option A: Stay on IIP-57 (SP1 verifier contract)           │
  │  - Works today, proven, audited                             │
  │  - ~280K gas per verification                               │
  │  - No dependency on Ethereum upgrades                       │
  │                                                             │
  │  Option B: Migrate to EIP-8079 EXECUTE precompile           │
  │  - ~10x gas savings on verification                         │
  │  - Ethereum-native security (L1 precompile)                 │
  │  - Requires Ethereum hard fork (not in IoTeX's control)     │
  │  - IoTeX STILL remains sovereign L1                         │
  │                                                             │
  │  Option C: Hybrid — use both                                │
  │  - SP1 verifier as fallback                                 │
  │  - EXECUTE precompile as primary (when available)           │
  │  - Maximum resilience                                       │
  │                                                             │
  │  All options preserve IoTeX L1 sovereignty.                 │
  │  The choice is purely about gas cost optimization.          │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### ZK Proof Soundness

The security of the IoTeX→Ethereum withdrawal direction relies entirely on the soundness of the SP1 proof system (Groth16 over BN254). A soundness break would allow an attacker to forge withdrawal proofs and drain the BridgeVault.

**Mitigations**:
- SP1 verifier contracts are audited by four independent firms: Veridise, Cantina, Zellic, and KALOS
- Groth16 is a well-studied proof system with over 8 years of academic and production use
- Per-epoch withdrawal caps ($100K initial) limit maximum loss from any exploit, including a hypothetical soundness break
- Timelock on cap increases provides response time for the community to react
- The bridge can be paused via governance (timelock + multisig) in an emergency

### Delegate Collusion (ETH→IoTeX Direction)

The deposit direction has identical security to IoTeX consensus itself: 17 of 24 delegates must collude to mint unauthorized wrapped tokens. This is already the fundamental trust assumption for all IoTeX state transitions, including token transfers, staking, and smart contract execution.

### Smart Contract Risks

All Solidity contracts (BridgeVault, IoTeXLightClient, BridgeManager, WrappedToken) must undergo independent security audits before mainnet deployment. Critical design choices to prevent ioTube-class vulnerabilities:

- **No single-owner upgradability**: Contract upgrades require timelock + multisig governance (not a single key — the exact vulnerability that caused the ioTube hack)
- **Immutable verification logic**: The SP1 verifier address and program verification key are `immutable` in `IoTeXLightClient`, preventing unauthorized replacement
- **No admin bypass**: No function allows minting or unlocking tokens without a valid ZK proof or BFT attestation

### Withdrawal Caps

Per-epoch withdrawal caps ($100K initial, gradually increased via governance) enforce an on-chain upper bound on damage from any exploit. The cap is enforced in `BridgeVault.sol` and cannot be bypassed by the relayer, prover, or any external party. Cap increases require governance approval with a timelock delay.

### Delegate Set Rotation Security

The `IoTeXLightClient` contract enforces strict delegate set continuity. An attacker cannot submit proofs with an arbitrary delegate set — the `delegateSetHash` must form an unbroken chain from the genesis trusted set through each epoch transition. Each link in this chain is a ZK proof verified against the previous delegate set's signatures.

### Relayer Liveness and Censorship

If no competing relayer submits a proof within 30 minutes, the permissionless fallback ensures withdrawals are never permanently stuck. Any Ethereum address can submit a valid proof after the batch window expires, earning a gas bounty. This prevents both liveness failures and censorship attacks.

### Front-Running Protection

Withdrawal claims on Ethereum use a nonce-based system. Each withdrawal has a unique `nonce` assigned at burn time on IoTeX. The nonce is committed inside the ZK proof as a public output. The `BridgeVault` contract marks each nonce as processed after claim, preventing double-claims regardless of transaction ordering.

---

## Test Cases

### Unit Tests (Go — iotex-core)

1. `BridgeAttestation` protobuf serialization round-trip: Go → proto → Go
2. Receipt Merkle proof generation for edge cases: 1 receipt, 2 receipts, 3 (odd), 100 (large), 0 (empty)
3. Receipt Merkle proof verification: generated proof verified against `crypto.NewMerkleTree().HashTree()`
4. Bridge state: attestation counting, BFT threshold detection (16 vs 17), duplicate delegate rejection
5. Deposit processing: first attestation, threshold reached at 17, duplicate nonce rejection, cross-epoch nonce tracking

### Unit Tests (Rust — SP1 program)

1. IoTeX block header protobuf parsing and Keccak256 hash (cross-validated against Go `header.HashHeader()` output)
2. ConsensusVote protobuf construction and BLAKE2b-256 hash (cross-validated against Go `consensusvote.Hash()` output)
3. Endorsement message hash: `keccak256(blake2b(vote) || timestamp_bytes)` (cross-validated against Go `hashDocWithTime()`)
4. ECDSA secp256k1 signature verification with IoTeX test vectors
5. Binary Merkle proof verification (cross-validated against Go `crypto/merkle.go`)
6. Full SP1 program execution with mock 24-delegate data: valid proof generation and Groth16 wrapping

### Integration Tests (Solidity — Foundry)

1. `IoTeXLightClient.verifyBlock()`: accept valid SP1 proof, reject invalid proof, reject tampered public values
2. Delegate set rotation: consecutive proofs with different delegate sets
3. `BridgeVault.deposit()`: successful lock, unsupported token rejection, zero amount rejection
4. `BridgeVault.claimWithdrawal()`: successful claim, double-claim rejection, epoch cap enforcement
5. Fee calculation: verify `max(fixedFee, 0.1%)` and 50/30/20 split accuracy across token decimals (6, 8, 18)
6. Governance: timelock enforcement on cap changes, multisig requirement

### End-to-End Tests

1. **Local testnet** (4 delegates + Anvil): complete deposit → attest → mint → burn → prove → claim cycle
2. **IoTeX testnet + Ethereum Sepolia**: multi-token bridge test with all 4 supported assets
3. **Relayer failover**: primary delegate offline → permissionless relayer claims bounty
4. **Delegate set rotation**: bridge operation continuity across epoch boundary with delegate set change
5. **Adversarial**: invalid proof submission, insufficient attestations, double-spend attempts

---

## Implementation

### Team Structure (Parallel Development)

| Team | Scope | Timeline |
|------|-------|----------|
| **Team A**: ZK & Contracts | SP1 Rust program, Solidity contracts (ETH + IoTeX), Foundry tests | Weeks 1-10 |
| **Team B**: iotex-core Protocol | System action, bridge protocol, proof API, integration tests | Weeks 1-8 |
| **Team C**: Relayer & Infrastructure | Relayer service, delegate sidecar, batching, monitoring, DevOps | Weeks 5-14 |

### Phase Timeline

| Phase | Weeks | Deliverables |
|-------|-------|-------------|
| **1. Foundation** | 1-4 | `BridgeAttestation` action type, bridge protocol skeleton, receipt proof generation API, SP1 program: header parsing + Merkle verification |
| **2. ZK Core** | 3-8 | SP1 program: full consensus verification (ECDSA + BLAKE2b), Solidity contracts deployed on testnet, Go↔Rust cross-validation tests |
| **3. Bridge Logic** | 5-12 | Deposit handler (17/24 attestation), withdrawal handler, relayer service, delegate Ethereum watcher sidecar, integration tests |
| **4. Hardening** | 9-16 | E2E testing on IoTeX testnet + Ethereum Sepolia, security audit (SP1 program + Solidity contracts), gas optimization, frontend SDK |
| **5. Mainnet Launch** | 15-20 | Yosemite hard fork activation, Ethereum contract deployment, gradual token rollout: USDT → USDC → WETH → WBTC (1 week intervals), monitoring and cap adjustment |

### External Dependencies

| Dependency | Action Required | Contact |
|------------|----------------|---------|
| **Succinct Labs** | SP1 partnership, Prover Network access, integration support | Uma Roy (`@pumatheuma`), `succinct.xyz` |
| **iotex-proto** | Add `BridgeAttestation` protobuf definitions | Internal team |
| **Security Auditor** | Audit SP1 program + all Solidity contracts | Engage at week 10 (recommended: Zellic, Trail of Bits, or OpenZeppelin) |
| **EF Platform Team** | EIL participation, Native Rollup alignment (long-term) | `platform@ethereum.org`, Justin Drake (`justin@ethereum.org`) |

### Future Upgrade Path

| Timeline | Upgrade | Impact |
|----------|---------|--------|
| Post-launch | Switch consensus vote hash BLAKE2b → Keccak256 | 15x reduction in SP1 proving cost |
| 6-12 months | Enable BLS aggregate signatures in consensus | Single BLS verify replaces 17 ECDSA + 17 BLAKE2b |
| 12-18 months | Add ZK proofs of Ethereum consensus (SP1 Helios) | ETH→IoTeX direction becomes fully trustless |
| 18-24 months | Evaluate EIP-8079 Native Rollup integration | Potentially replace custom ZK bridge with Ethereum-native verification |

---

## References

- [IIP-55: Dynamic Witness Committee for ioTube](https://github.com/iotexproject/iips/blob/master/iip-55.md)
- [Succinct SP1 Documentation](https://docs.succinct.xyz/)
- [SP1 Helios: Ethereum ZK Light Client](https://github.com/succinctlabs/sp1-helios)
- [SP1 Verifier Contract Addresses](https://docs.succinct.xyz/docs/sp1/verification/contract-addresses)
- [Succinct Prover Network](https://docs.succinct.xyz/docs/protocol/what-is-succinct)
- [Gnosis Chain ZK Light Client Bridge](https://www.gnosis.io/blog/succincts-ethereum-zk-light-client-and-the-road-to-trust-minimzed-bridges-with-hashi)
- [EIP-8079: Native Rollups](https://eips.ethereum.org/EIPS/eip-8079)
- [Ethereum Interoperability Layer](https://ethresear.ch/t/eil-trust-minimized-cross-l2-interop/23437)
- [Ethereum Foundation Platform Team Announcement](https://blog.ethereum.org/2026/02/17/platform)
- [Vitalik Buterin: Scaling Ethereum L1 and L2s in 2025 and Beyond](https://vitalik.eth.limo/general/2025/01/23/l1l2future.html)
- [Vitalik Buterin: The Math of Stage 1 and Stage 2](https://vitalik.eth.limo/general/2025/05/06/stages.html)
- [IoTeX ioTube Hack Post-Mortem — Halborn](https://www.halborn.com/blog/post/explained-the-iotex-hack-february-2026)
- [Bridge Hacks History — HackenProof](https://hackenproof.com/blog/for-hackers/web3-bridge-hacks)
- [IoTeX iotex-core Repository](https://github.com/iotexproject/iotex-core)
- [IoTeX Improvement Proposals Repository](https://github.com/iotexproject/iips)

---

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
