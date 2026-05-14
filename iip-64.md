
```
IIP: 64
Title: Post-Quantum Cryptographic Migration for IoTeX
Author: Xinxin Fan (@cryptoxfan)
Discussions-to: https://community.iotex.io/c/governance-proposals
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-05-14
Replaces: N/A
```
 
## Abstract

This IoTeX Improvement Proposal specifies a comprehensive, phased migration of the IoTeX blockchain from quantum-vulnerable elliptic-curve cryptography (secp256k1/ECDSA) to NIST-standardized post-quantum cryptographic (PQC) algorithms. The proposal draws on published research and migration frameworks from Ethereum, Bitcoin (BIP-361 and Chaincode Labs), Sui, the Quantum Resistant Ledger (QRL), Google Quantum AI, the Coinbase Independent Advisory Board, Meta, and Paradigm, synthesizing their findings into a specification tailored to IoTeX's Roll-DPoS consensus, 5-second block time, 24-delegate architecture, DePIN device ecosystem, and EVM compatibility.

The migration proceeds across five phases (2026–2033) and introduces a PQ signature verification precompile, a new hybrid transaction type, a PQ Key Registry, consensus-layer dual-signing with PQ checkpoint attestations, zkSTARK-based migration proofs for hidden-key accounts, a five-level PQC Maturity Model with on-chain metrics, guardrails to prevent new quantum-vulnerable deployments, and a quantum-milestone-triggered acceleration mechanism. Upon completion, all IoTeX transactions, consensus attestations, and DePIN device identities will be secured exclusively by post-quantum algorithms, achieving the highest maturity level (PQ-Enabled) before the projected arrival of cryptographically-relevant quantum computers (CRQCs).

## 1. Motivation

### 1.1 The Quantum Threat to the IoTeX Blockchain

IoTeX derives all account security from the secp256k1 elliptic curve. Every externally-owned account (EOA) generates a private key, derives a public key via the secp256k1 curve, and produces an IoTeX address by hashing the public key. Transaction authorization relies on ECDSA signatures over secp256k1. This is the same cryptographic foundation used by Bitcoin and Ethereum, and it is vulnerable to quantum attack.

[Google Quantum AI's whitepaper](https://quantumai.google/static/site-assets/downloads/cryptocurrency-whitepaper.pdf) (April 2026) demonstrates that the resource estimates for breaking ECDLP-256 have decreased by approximately 20× compared to prior literature. The paper presents two optimized Shor-based circuits: one requiring fewer than 1,200 logical qubits and 90 million Toffoli gates, and another requiring fewer than 1,450 logical qubits and 70 million Toffoli gates. These circuits could be executed on a superconducting CRQC with fewer than 500,000 physical qubits, completing within minutes. This places the threat horizon within the plausible engineering trajectory of the next 10–15 years.

### 1.2 Classification of IoTeX Quantum Vulnerabilities

Following the taxonomy from Google Quantum AI's whitepaper and the Chaincode Labs Bitcoin report, we identify IoTeX's attack surfaces in order of severity:

* **At-Rest Attacks:&#x20;**&#x54;hese attacks target accounts whose public keys are already exposed on-chain (any EOA that has ever signed a transaction). Since IoTeX addresses are derived from a Keccak-256 hash of the public key, but the key is recoverable from any signed transaction, the set of exposed accounts grows monotonically with network activity. A quantum adversary with a slow-clock CRQC (days of compute) can drain any such account.

* **On-Spend Attacks:** These attacks target transactions in the mempool. IoTeX's 2.5-second block time is significantly shorter than Bitcoin's 10 minutes but still vulnerable to fast-clock CRQCs capable of solving ECDLP in minutes, particularly if the attacker has precomputed the "primed" state (halving the attack time to \~9 minutes per Google's estimates). Delegate collusion or adversarial delegate replacement could extend the effective attack window.

* **On-Setup Attacks:&#x20;**&#x54;hese attacks target fixed public parameters. IoTeX's current protocol does not use trusted setups or pairing-based data availability sampling, making this vector less relevant at present. However, future integration with zk-rollup Layer-2 solutions or verifiable compute systems introduces this risk.

* **Consensus-Layer Attacks:** These attacks target the 24 Roll-DPoS delegates. If a CRQC can derive delegate signing keys, it can produce valid block proposals, attestations, and governance votes, enabling chain reorganizations or protocol manipulation.

* **DePIN-Specific Attacks:** These attacks target long-lived device identities and data provenance proofs. IoT devices may remain operational for 10–20 years, well into the CRQC era. Device key compromise enables data falsification, unauthorized device impersonation, and fraudulent machine-to-machine payments.

### 1.3 Why Act Now?

[NIST](https://nvlpubs.nist.gov/nistpubs/ir/2024/NIST.IR.8547.ipd.pdf) mandates the deprecation of quantum-vulnerable algorithms by 2030 and their disallowance by 2035. Google has announced a 2029 target for complete internal PQC migration. [Meta](https://engineering.fb.com/2026/04/16/security/post-quantum-cryptography-migration-at-meta-framework-lessons-and-takeaways/) has begun deploying PQ-TLS internally and published a detailed migration framework. The [Coinbase Independent Advisory Board](https://assets.ctfassets.net/sygt3q11s4a9/6EjYavuGdtJDYCqaJrASj9/9f464a8bf26f44bd6c85710fe7e4a29f/Quantum_Computing_and_Blockchain_v10.3_15April2026.pdf) urges all blockchain ecosystems to begin migration now, warning that "wallets that never upgrade may leave assets exposed." [Ethereum](https://pq.ethereum.org/) targets L1 PQ upgrades by approximately 2029. [Bitcoin's BIP-361](https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki) proposes a two-phase soft-fork migration. IoTeX must act in concert with this industry-wide transition.

## 2. Threat Model and Risk Assessment

### 2.1 Adversary Model

This proposal considers three classes of quantum adversary, ordered by increasing capability.

* **Class 1: Harvest-Now-Decrypt-Later (HNDL).** A classical adversary records all on-chain public keys and transaction data today, intending to extract private keys once a CRQC becomes available. This is the most immediate threat because the adversary requires no quantum hardware today.

* **Class 2: Offline CRQC.** An adversary with access to a CRQC, but not with real-time capability. This adversary can break any exposed secp256k1 public key given hours to days of quantum computation. All at-rest keys with prior on-chain exposure are vulnerable.

* **Class 3: Real-Time CRQC.** An adversary with a CRQC capable of solving ECDLP-256 within the network's block confirmation window (5 seconds for IoTeX). This adversary can intercept transactions in the mempool, extract the signing key from the revealed public key, and broadcast a competing transaction before the original is finalized. This is the most severe threat and the one that requires the network to have fully completed migration.

### 2.2 IoTeX-Specific Risk Matrix

The IoTeX-specific components that are vulnerable to quantum computers are analyzed in the table below.

| **Component**                 | **Vulnerability**      | **Attack Type**    | **Likelyhood (15 Years)** | **Impact** | **Risk** |
| ----------------------------- | ---------------------- | ------------------ | ------------------------- | ---------- | -------- |
| **EOA keys (secp256k1)**      | ECDLP via Shor's       | At-rest / On-spend | High                      | High       | **High** |
| **Delegate signing keys**     | ECDLP via Shor's       | At-rest            | High                      | High       | **High** |
| **Keccak-256 addresses**      | Grover's (preimage)    | Brute-force        | Low                       | High       | Low      |
| **SHA-256 (Merkle trees)**    | Grover's (collision)   | BHT collision      | Medium                    | Medium     | Medium   |
| **Smart contract admin keys** | ECDLP via Shor's       | At-rest            | High                      | High       | **High** |
| **TLS/P2P networking**        | ECDH key exchange      | Harvest-now        | Medium                    | Medium     | Medium   |
| **DePIN device keys**         | ECDLP via Shor's<br /> | At-rest<br />      | High                      | High       | **High** |

### 2.3 Quantitative Exposure Analysis

IoTeX addresses that have initiated at least one transaction have an on-chain-recoverable public key. Based on IoTeX mainnet state, the majority of active accounts fall into this category. The proportion of value secured by exposed public keys represents the primary risk surface. Accounts that have never transacted (receive-only) retain hash-hiding protection, analogous to Bitcoin's P2PKH. However, as noted in the [Kiraz–Kardas framework](https://eprint.iacr.org/2026/352.pdf), this protection is reduced (not eliminated) in the quantum setting: Grover's algorithm reduces the effective preimage security of Keccak-256(pubkey) from 256 bits to approximately 128 bits — still substantial but warranting proactive migration rather than reliance on hash security alone.

### 2.4 What Is NOT Threatened

Hash functions (Keccak-256, SHA-256) used in address derivation, Merkle trees, and block hashing provide 128-bit quantum security via Grover's algorithm (which only halves the effective security bits of symmetric primitives). These do not require immediate replacement but should use ≥256-bit outputs for 128-bit post-quantum pre-image resistance and ≥384-bit outputs for 128-bit collision resistance. IoTeX's existing Keccak-256 usage meets the pre-image requirement.

## 3. Comparative Analysis of Existing Proposals

### 3.1 Ethereum Foundation PQ Roadmap (pq.ethereum.org)

The Ethereum Foundation's Post-Quantum team defines a multi-layer, multi-fork migration:

* **Execution Layer:** The execution layer will evolve through three stages, namely PQ signature precompiles (Fork J\*), PQ transactions (longer-term), and PQ signature aggregation (Fork M\*). The strategy relies on account abstraction (ERC-4337 / EIP-8141) as the central upgrade mechanism, allowing smart contract accounts to define custom PQ verification logic without protocol changes. Signature candidates under evaluation include Falcon (FN-DSA/FIPS 206), ML-DSA (FIPS 204), and SPHINCS+ (SLH-DSA/FIPS 205).

* **Consensus Layer:** The consensus layer will evolve through three stages, namely PQ key registry (Fork I\*), PQ attestations with real-time CL proofs using leanXMSS and leanVM (Fork L\*), and full PQ consensus (longer-term). The approach replaces BLS with hash-based signatures (leanXMSS) and uses SNARK-based aggregation via a minimal zkVM (leanMultisig) to restore the aggregation properties lost by abandoning BLS.

* **Data Layer:** The data layer will evolve through two stages, namely leanVM (Fork L\*) and PQ blobs (Fork M\*). PQ-safe data availability is an emerging research area.

The Ethereum L1 protocol upgrades could be completed by 2029 and full execution-layer migration extends years beyond.

### 3.2 Google Quantum AI Whitepaper (April 2026)

The Google whitepaper introduces a critical architectural distinction between "fast-clock" CRQCs (superconducting, photonic, silicon — minutes for ECDLP) and "slow-clock" CRQCs (neutral atom, ion trap — days for ECDLP). The key findings include: 1) The updated resource estimates (≤500K physical qubits) represent a \~20x reduction over prior work; 2) The zero-knowledge proof methodology for responsible disclosure sets a new standard for the field; 3)  The whitepaper identifies five distinct Ethereum vulnerability categories: Account, Admin, Code, Consensus, and Data Availability; 4) The "digital salvage" policy framework for dormant assets introduces public-policy dimensions relevant to any chain's migration planning.

The paper recommends two contingency scenarios: 1) Fast-clock first: On-spend and at-rest attacks arrive simultaneously; and 2) Slow-clock first: At-rest attacks precede on-spend by years.&#x20;

### 3.3 ZKP-Augmented Ethereum Transaction Migration (pQCee/IoTeX)

The researchers from IoTeX and pQCee propose two migration paths specifically targeting Ethereum-compatible chains:

* **Proposal 1 (Layer-1 Hard Fork):** A new transaction type augments legacy transactions with a `proofUri` parameter linking to an off-chain quantum-safe zero-knowledge proof (zkSTARK or MPCitH). The proof demonstrates that the sender knows a secret (e.g., mnemonic phrase) that deterministically generates the transaction's signing address. Validators verify both the ECDSA signature and the PQ ZKP.

* **Proposal 2 (Layer-2 zk-Rollups):** Off-chain rollup nodes aggregate individual zkSTARK proofs into a single recursive proof via a tree-based aggregation process, submitting the batch with a final compressed proof via blob transactions (EIP-4844).

* **Initial Benchmarks on Azure F32s v2:** Individual proof generation takes \~304 seconds with \~42 GB memory for SP1 and the proof size is \~5.3 MB at 100-bit security. With recursive aggregation of 10 proofs via SP1, per-proof size drops to \~177 KB and per-proof time to \~80 seconds.

### 3.4 Dual Mode Signatures for EdDSA Chains (Mysten Labs/Sui)

This work formalizes the "Dual Mode Signature" (DMS) security model and demonstrates a structural advantage of EdDSA-based chains (Sui, Solana, Near): EdDSA's deterministic seed-based key derivation (RFC 8032) allows the seed to serve as a witness in a PQ-NIZK proof, enabling post-quantum authentication without address changes or asset transfers, even for accounts with already-exposed public keys.

The Core Protocol works as follows: The EdDSA seed (sk₂) is used as a private witness in a STARK proof that: (1) pk = HashToScalar(SHA-512(seed)\[:32]) · G, and (2) hx = Hash(msg, seed, rx). This "one-time proof certification" binds a PQ public key (pqpk) to the legacy address, after which all subsequent signatures use standard PQ signature verification. The Benchmarks on MacBook Pro M4 show that it takes 6.2 seconds for proof generation and 2.3 seconds for proof verification. Moreover, the proof size is 5.4 MB using Ligetron zkVM.

The authors demonstrate that ECDSA-based chains (Bitcoin, Ethereum, IoTeX) lack this structural property because ECDSA keys are sampled without deterministic structure from a seed. BIP-32 hardened derivation provides a partial workaround but introduces domain separation issues and doesn't achieve quantum safety without modifying the BIP-32 standard itself.

Sui's strategy leverages EdDSA's structural advantage, proposes proactive strategies (PQ-sign PreQ key at account creation, 1-of-2 multisig with PQ expiration) and adaptive strategies (ownership transition, PQ key pair from same seed randomness with ZK proof). Sui provides comprehensive analysis of hash function security, ZK proof system transitions, public key encryption, and DKG protocol migration.

### 3.5 zkSTARK-Based Bitcoin/Ethereum Address Migration

[Kiraz and Kardas](https://eprint.iacr.org/2026/352.pdf) present an end-to-end migration framework with dual paths based on key exposure status:

* **Scenario A (Revealed Public Keys):** Hybrid dual-signature migration combining ECDSA attestation of the PQ key with ML-DSA counter-attestation, followed by one-way transition to PQ-only authorization.

* **Scenario B (Hidden Public Keys):** zkSTARK-based migration proofs that bind legacy addresses to PQ keys without revealing the legacy EC public key on-chain. The STARK circuit verifies: (1) address derivation (RIPEMD-160(SHA-256(Q)) = h160 for Bitcoin; Keccak-256(Qu\[1:65])\[12:32] = aeth for Ethereum), and (2) ECDSA ownership proof.

The above two scenarios can be implemented based on two new on-chain primitives proposed: `OP_CHECKQUANTUMSIG` and `OP_CHECKSTARKPROOF`.

### 3.6 BIP-361 — Post-Quantum Migration and Legacy Signature Sunset (Bitcoin)

BIP-361 introduces a pre-announced sunset of ECDSA/Schnorr signatures in two phases:

* **Phase A (160,000 blocks ≈ 3 years after activation):** Disallows sending funds to quantum-vulnerable address types, forcing adoption of PQ address types.

* **Phase B (2 years after Phase A):** Restricts ECDSA/Schnorr spends by encumbering them with a quantum-safe rescue protocol (e.g., proving knowledge of parent XPriv via zkSTARK for BIP-32 HD wallets).

The proposal estimates that over 34% of Bitcoin's supply has exposed public keys.

### 3.7 Chaincode Labs — Bitcoin Post-Quantum Report (May 2025)

The Chaincode report proposes a dual-track strategy: short-term contingency measures (\~2 years) deployable as emergency response, and a long-term comprehensive path (\~7 years) for optimal quantum resistance. Key technical elements include Lamport signatures via OP\_CAT, quantum-secure Taproot scripts, pay-to-quantum-resistant-hash (P2QRH), and commit-delay-reveal migration mechanisms. The report estimates \~6.26 million BTC (\~US$650 billion) as vulnerable and frames the "burn vs. steal" dilemma for dormant assets.

### 3.8 Paradigm — Provable Address-Control Timestamps (May 2026)

Paradigm proposed Provable Address-Control Timestamps (PACTs), a privacy-preserving rescue mechanism for dormant Bitcoin holders. PACTs allow holders to secretly timestamp their knowledge of private keys using Bitcoin itself (via OpenTimestamps and OP\_RETURN outputs) before CRQCs arrive. A future sunset fork could accept STARK proofs of these timestamps as an alternative spending path, enabling dormant holders to prove ownership without publicly moving coins. The protocol exploits the temporal asymmetry between current private-key knowledge and future quantum key derivation, creating unforgeable evidence that a quantum attacker fundamentally cannot produce. This mechanism is adapted for IoTeX as iPACTs.

### 3.9 QRL (Quantum Resistant Ledger)

QRL is the only production blockchain that launched (2018) with NIST-approved post-quantum signature XMSS, a stateful hash-based scheme. It is now migrating to SPHINCS+ (SLH-DSA, stateless, NIST FIPS 205) to eliminate the state-management complexity of XMSS. Project Zond introduces Proof-of-Stake consensus with EVM compatibility, enabling Solidity developers to deploy on a natively PQ-secure chain. QRL represents the existence proof that post-quantum blockchain operation is practical, with seven years of uninterrupted PQ-secured operation.

### 3.9 Coinbase Independent Advisory Board

The position paper by the Coinbase Independent Advisory Board provides the most authoritative current threat assessment. The board concludes that large-scale fault-tolerant quantum computers are "not imminent but could arrive by 2035+." They define four quantum milestones: (1) fault-tolerant two-qubit gates, (2) fault-tolerant Shor's factoring, (3) indefinitely stable logical qubits, and (4) verifiable quantum-simulation advantage. The paper rates PQC signature schemes by confidence and size, including ML-DSA-44 (1312-byte pubkey, 2420-byte sig), FN-DSA-512 (897-byte pubkey, 666-byte sig, 3× signing cost), SLH-DSA-128s (32-byte pubkey, 7856-byte sig, 14,000× signing), and SLH-DSA-128f (32-byte pubkey, 17,088-byte sig, 720× signing). Confidence is highest for hash-based SLH-DSA and aggregation remains research-intensive.

For consensus, the paper recommends periodic PQ checkpoints: a super-majority of delegates signs block metadata (block\_hash, state\_root, tx\_root) with ML-DSA-65 signatures (\~3,293 bytes each), providing PQ integrity without full execution-layer migration. IoTeX's 24-delegate Roll-DPoS can adopt full PQ signing per block, eliminating the need for aggregation optimizations. The paper also urges early governance decisions on dormant wallets and recommends public decisions on freeze, burn, or other policies before they become market-impacting.

### 3.10 Coinbase Independent Advisory Board

Meta's April 2026 engineering blog post outlines a six-step PQC migration strategy: (1) prioritize high-risk applications (offline-attack vectors first), (2) build a cryptographic inventory through automated discovery and developer reporting, (3) address external dependencies (NIST standards, hardware vendor support, production-level implementations), (4) select algorithms (ML-KEM, ML-DSA, upcoming HQC), (5) implement guardrails to block new quantum-vulnerable keys and APIs, and (6) integrate PQC components via replacement or hybrid schemes. Meta introduces PQC Migration Levels: PQ-Unaware, PQ-Aware, PQ-Ready, PQ-Hardened, and PQ-Enabled. This framework provides the organizational maturity model adopted by this IIP.

### 3.11 Key Insight for IoTeX

The previous work brings the following key insight for IoTeX:

* Ethereum's account abstraction approach is directly applicable to IoTeX given EVM compatibility. However, IoTeX's Roll-DPoS consensus with 24 delegates is simpler than Ethereum's PoS with hundreds of thousands of validators, dramatically simplifying consensus-layer PQ migration.

* IoTeX's 2.5-second block time makes on-spend attacks more challenging but not impossible (an attacker could collude with or replace delegates). The DePIN use case amplifies the at-rest risk because device keys are long-lived. The Google's dual-scenario planning framework directly informs IoTeX's phased migration.

* IoTeX uses secp256k1/ECDSA, not EdDSA, so the seed-based DMS approach is not directly applicable. However, the mnemonic-based approach (proving knowledge of BIP-39 mnemonic) remains viable for wallets that use HD derivation, following the IoTeX/pqCee's construction. For non-mnemonic accounts (e.g., HSM-based institutional custody), the Kiraz–Kardas dual-path framework is more appropriate.

* The dual-path approach proposed by Kiraz and Kardas is directly applicable. IoTeX accounts that have transacted (revealed keys) follow Scenario A and accounts that have only received (hidden keys) follow Scenario B. The Ethereum-specific STARK circuit design can be adopted with minimal modification for IoTeX's Keccak-256 address derivation.

* The "private incentive" model in BIP-361 — creating a clear deadline to motivate migration — is applicable to IoTeX but must be calibrated to IoTeX's governance model (24 delegates, community voting) and the DePIN device lifecycle. The rescue protocol concept using BIP-32 hardened derivation knowledge asymmetry is directly relevant.

### 3.11 Comparative Summary&#x20;

We provide a comparative summary in the table below.

| **Dimension**              | **Ethereum (EF)**                     | **Bitcoin (BIP-361)**     | **IoTeX\&pQCee**              | **Sui**                 | **Kiraz-Kardas**            | **QRL**               | **This IIP**                    |
| -------------------------- | ------------------------------------- | ------------------------- | ----------------------------- | ----------------------- | --------------------------- | --------------------- | ------------------------------- |
| **Signature Scheme**       | Falcon, ML-DSA, SPHINCS+ (evaluating) | ML-DSA                    | Scheme-agnostic (ZKP-based)   | EdDSA DMS + PQ-NIZK     | ML-DSA + zkSTARK            | XMSS → SPHINCS+       | ML-DSA + SLH-DSA + zkSTARK      |
| **Migration Model**        | Account abstraction (opt-in)          | Flag-day sunset (forced)  | New tx type + off-chain proof | Seed-based DMS (opt-in) | Dual-path (revealed/hidden) | Hard fork (PQ-native) | Phased hybrid (incentivized)    |
| **Consensus Layer**        | leanXMSS + SNARK aggregation          | N/A (PoW unchanged)       | Not addressed                 | Not addressed           | Not addressed               | XMSS/SPHINCS+ native  | ML-DSA delegate keys + registry |
| **Backward Compatability** | High (AA-based)                       | Moderate (soft fork)      | High (new tx type)            | High (same address)     | High (one-way transition)   | Low (new chain)       | High (phased, incentivized)     |
| **Aggregation**            | SNARK-based (leanVM)                  | N/A                       | Recursive zkSTARK             | One-time proof          | Not addressed               | N/A                   | Recursive zkSTARK + precompile  |
| **ZK Proof System**        | General-purpose                       | zkSTARK (proposed)        | SP1/RISC0 zkVM                | Ligetron zkVM           | SP1 zkVM (STARK-native)     | N/A                   | SP1 zkVM (STARK-native)         |
| **IoT/DePIN**              | Not addressed                         | Not addressed             | Partially (IoTeX context)     | Not addressed           | Not addressed               | Not addressed         | Fully addressed                 |
| **Timeline**               | L1 by 2029 & full migration 2032+     | \~5 years post-activation | Not specified                 | Not specified           | Not specified               | Already deployed      | 2026–2033 (7-year plan)         |

## 4. Specification

### 4.1 Post-Quantum Signature Algorithms

This proposal standardizes support for two NIST-approved post-quantum digital signature algorithms:&#x20;

* **ML-DSA (FIPS 204, Module-Lattice Digital Signature Algorithm):** Recommended as the primary PQ signature scheme. ML-DSA-44 (NIST Security Level 2) is selected for user transactions, offering public key size of 1,312 bytes, signature size of 2,420 bytes, and verification performance approximately 0.5x that of ECDSA (i.e., faster). ML-DSA-65 (NIST Security Level 3) is recommended for delegate/consensus keys and high-value smart contract admin keys.

* **SLH-DSA (FIPS 205, Stateless Hash-Based Digital Signature Algorithm):** Recommended as the conservative fallback. SLH-DSA relies solely on the security of hash functions (no lattice assumptions), providing a hedge against potential future cryptanalysis of lattice problems. SLH-DSA-SHA2-128s provides public key size of 32 bytes but signature size of 7,856 bytes. SLH-DSA is recommended for long-lived device identities in DePIN applications where signature size is less critical than long-term security assurance.

The rationale for excluding other candidates is due to the following considerations:

* FALCON (FN-DSA/FIPS 206 draft) requires complex floating-point arithmetic for Gaussian sampling, making it unsuitable for IoT devices.

* SQIsign, while offering compact signatures, remains too immature and computationally expensive.&#x20;

* XMSS, while battle-tested (QRL), is stateful and operationally complex for a general-purpose blockchain.

The signature algorithm identifiers are shown in table below.

| **Algorithm** | **Identifier (uint8)** | **OID**                 |
| ------------- | ---------------------- | ----------------------- |
| ML-DSA-44     | 0x01                   | 2.16.840.1.101.3.4.3.17 |
| ML-DSA-65     | 0x02                   | 2.16.840.1.101.3.4.3.18 |
| ML-DSA-87     | 0x03                   | 2.16.840.1.101.3.4.3.19 |
| SLH-DSA-128s  | 0x10                   | 2.16.840.1.101.3.4.3.20 |
| SLH-DSA-128f  | 0x11                   | 2.16.840.1.101.3.4.3.21 |
| FN-DSA-512    | 0x20                   | (pending FIPS 206)      |

### 4.2 PQ Signature Verification Precompile

A new precompiled contract is deployed at a designated address (proposed: `0x0B`) implementing PQ signature verification:

```java
// Precompile interface (pseudocode)
// Input format: [algorithm_id (1 byte)] [public_key] [message] [signature]
// algorithm_id: 0x01 = ML-DSA-44, 0x02 = ML-DSA-65, 0x03 = ML-DSA-87
//               0x04 = SLH-DSA-SHA2-128s, 0x05 = SLH-DSA-SHA2-128f
// Output: 0x01 (valid) or 0x00 (invalid)

function pqVerify(bytes calldata input) external view returns (bytes1 result);
```

The verification gas cost is set to reflect actual computational cost relative to `ecrecover`. Based on benchmark data:

* ML-DSA-44 verification is approximately 0.9x the cost of ECDSA verification;&#x20;

* ML-DSA-65 is approximately 1.5x.&#x20;

* SLH-DSA-SHA2-128s verification is approximately 37x ECDSA verification cost.&#x20;

As a result, the proposed gas costs: ML-DSA-44: 2,700 gas; ML-DSA-65: 4,500 gas;  and SLH-DSA-SHA2-128s: 111,000 gas. These costs are set conservatively and should be adjusted based on client benchmarks.

### 4.3 New Transaction Type: PQ-Authenticated Transaction (Type `0x05`)

Following EIP-2718 (Typed Transaction Envelope), a new transaction type `0x05` is introduced:

```json
0x05 || rlp([chain_id, nonce,       max_priority_fee_per_gas, max_fee_per_gas, 
gas_limit, to, value, data, access_list,
pq_algorithm_id, pq_public_key, pq_signature,
legacy_v, legacy_r, legacy_s])
```

During Phase 2 (Hybrid Mode), both `pq_signature` and legacy ECDSA signature (`v, r, s`) MUST be present and valid. During Phase 4 (PQ-Only Mode), the legacy fields MAY be zero-filled.&#x20;

The Validation is conducted in the following steps:

1. Recover the sender address from the legacy ECDSA signature (if present) using standard `ecrecover`.

2. Verify the PQ signature using the precompile against `pq_public_key` and the transaction hash.

3. Look up `pq_public_key` in the PQ Key Registry (Section 5.4). The registered PQ key MUST match the key in the transaction, and the registered address MUST match the recovered sender address.

4. If both verifications pass, the transaction is valid.

### 4.4 PQ Key Registry

A singleton smart contract deployed at a protocol-designated address maintains the mapping between IoTeX addresses and their registered PQ public keys:

```javascript
contract PQKeyRegistry {
    struct PQKey {
        uint8 algorithmId;      // ML-DSA-44, ML-DSA-65, SLH-DSA, etc.
        bytes publicKey;         // The PQ public key
        uint256 registeredBlock; // Block at which registration was confirmed
        bool active;             // Whether PQ-only mode is activated
    }
    
    mapping(address => PQKey) public registry;
    
    // Registration: prove ownership via ECDSA signature + PQ signature
    function register(
        uint8 algorithmId,
        bytes calldata pqPublicKey,
        bytes calldata pqSignature,   // ML-DSA signature over registration message
        bytes calldata ecdsaSignature // ECDSA signature over registration message
    ) external;
    
    // Optional: ZKP-based registration for accounts that wish to
    // avoid revealing their ECDSA public key
    function registerWithProof(
        uint8 algorithmId,
        bytes calldata pqPublicKey,
        bytes calldata starkProof,    // zkSTARK proof per Kiraz-Kardas framework
        bytes32 addressHash           // Keccak-256 address binding
    ) external;
    
    // Activate PQ-only mode (irreversible during Phases 2-3)
    function activatePQOnly() external;
    
    // Key rotation: replace PQ key (requires existing PQ signature)
    function rotateKey(
        uint8 newAlgorithmId,
        bytes calldata newPqPublicKey,
        bytes calldata rotationSignature // Signed with current PQ key
    ) external;
}
```

The registration message has the following format:

```json
registration_msg = keccak256(
    "IOTEX_PQ_REGISTER" ||
    chain_id ||
    sender_address ||
    algorithm_id ||
    keccak256(pq_public_key) ||
    registration_nonce
)
```

The dual-signature registration (ECDSA + PQ) follows the Kiraz–Kardas Scenario A (revealed public key) hybrid dual-signature protocol. The zkSTARK-based registration follows Scenario B (hidden public key), using the circuit specification from Section 6.2 of their framework.

### 4.5 Consensus Layer: Delegate PQ Key Migration

IoTeX's Roll-DPoS consensus with 24 delegates simplifies consensus PQ migration compared to Ethereum's hundreds of thousands of validators:

* **Phase 1 — PQ Key Registry for Delegates:** Each delegate registers a PQ public key (ML-DSA-65 recommended for consensus security) in a dedicated delegate PQ registry contract. Registration requires both the delegate's current secp256k1 signing key and the new PQ key.

* **Phase 2 — Dual-Signed Blocks:** Block proposals include both ECDSA and PQ signatures from the proposing delegate. Attestations from other delegates include both signature types. Clients verify both.

* **Phase 3 — PQ-Only Consensus:** After a governance-approved activation block height, only PQ-signed block proposals and attestations are accepted. ECDSA-only delegates are excluded from the active set.

With only 24 delegates, native BLS-style aggregation is not required. Individual ML-DSA-65 signatures (3,293 bytes each) for all 24 delegates total \~79 KB per block — manageable within IoTeX's block. For future scalability (if delegate count increases), STARK-based aggregation following the Ethereum Foundation's leanMultisig approach can be adopted.

### 4.6 DePIN Device Identity Migration

A specialized migration path for IoT device identities in the DePIN ecosystem:

* **Device PQ Key Provisioning:** New devices are provisioned with ML-DSA-44 or SLH-DSA-SHA2-128s key pairs at manufacture. SLH-DSA is preferred for devices where a long operational lifetime (10–20 years) warrants the most conservative security assumptions.

* **Legacy Device Migration:** Existing devices with secp256k1 keys register PQ keys via a TEE-assisted proving service. The device authenticates to the TEE via its legacy key, the TEE generates a PQ key pair and a zkSTARK migration proof, and the proof is submitted to the PQ Key Registry on behalf of the device.

* **Lightweight Verification:** Resource-constrained IoT devices that cannot perform PQ signature verification locally can delegate verification to trusted gateway nodes that hold PQ-verified certificates. This follows the IoTeX W3bstream off-chain compute model.

### 4.7 zkSTARK Proof System for Migration

Following the IoTeX/pqCee and Kiraz–Kardas frameworks, the migration proof system uses SP1 (Succinct's STARK-native zkVM) to generate proofs that remain entirely within the STARK domain (avoiding the quantum-vulnerable Groth16 final recursion step). There are two options to bind an IoTeX address with a PQ one.

* **IoTeX Address Binding Circuit (adapted from Kiraz–Kardas Section 6.2)**

```json
Public inputs: IoTeX address a_iotex (20 bytes), PQ public key pk_pq

Private inputs: Uncompressed secp256k1 public key Q_u (65 bytes), ECDSA signature σ

Constraints:
1. Address binding: Keccak-256(Q_u[1:65])[12:32] == a_iotex
2. Ownership proof: ECDSA.Verify(Q_u, Keccak-256(a_iotex || pk_pq), σ) == 1
```

* **Mnemonic-Based Alternative (adapted from IoTeX/pqCee)**

For wallets using BIP-39/BIP-32 HD derivation, the circuit can alternatively prove knowledge of the mnemonic/seed.

```json
Public inputs: IoTeX address a_iotex, PQ public key pk_pq

Private inputs: Pre-image ρ (mnemonic-derived seed or intermediate hash)

Constraints:
1. Hash(ρ) yields the private key sk
2. sk · G = Q (secp256k1 point multiplication)
3. Keccak-256(Q_uncompressed[1:65])[12:32] == a_iotex
```

Following IoTeX/pqCee's Proposal 2, multiple individual migration proofs can be aggregated via tree-based recursive STARK aggregation, reducing on-chain verification cost. A batch of N migration proofs is aggregated into a single proof of approximately constant size (\~1.8 MB for SP1 compressed), amortizing per-account verification cost. A STARK verification contract is deployed on IoTeX for on-chain verification of migration proofs. This contract accepts the proof, public inputs, and verification key, and returns a boolean. The verification gas cost is estimated at approximately 200,000–500,000 gas depending on proof parameters.

### 4.8 iPACT: IoTeX Provable Address-Control Timestamps

Adapted from Paradigm's PACTs proposal (May 2026), iPACTs allow holders of quantum-vulnerable IoTeX addresses to silently and costlessly prove, before CRQCs arrive, that they control their private keys. The mechanism exploits the temporal asymmetry between current private-key knowledge and future quantum key derivation: by creating a timestamped commitment now, the holder produces unforgeable evidence that a future quantum adversary fundamentally cannot produce.

#### 4.8.1 **Commitment Generation**

The holder generates:

```json
salt = random(32 bytes)
msg = Encode("iPACT/v1", "iotex-mainnet", ioAddr, salt)
control_proof = ECDSA.sign(secp256k1_privkey, keccak256(msg))
commitment = keccak256("iPACT/v1 commitment" || salt || keccak256(control_proof))
```

where `ioAddr` is the IoTeX address (20 bytes, derived from `keccak256(secp256k1_pubkey)[12:32]`), and `Encode` is a canonical ABI-encoding function. The holder stores the salt, the ECDSA control proof, and the timestamp proof file in a secure location. This requires no on-chain transaction by the holder (when using Method A) and is entirely off-chain. The commitment reveals nothing about the control proof, salt, public key, address, or which coins the holder owns.

#### 4.8.2 **Timestamping Methods**

The commitment is timestamped using one or more of the following methods, in order of preference.

* **Method A: OpenTimestamps via Bitcoin.** The commitment hash is submitted to the OpenTimestamps calendar server, which aggregates it into a Merkle tree and embeds the root in a Bitcoin OP\_RETURN output. This provides the strongest timestamp guarantee (Bitcoin's proof-of-work security). The holder retains the `.ots` proof file. No IoTeX transaction is required.

* **Method B: IoTeX On-Chain Commitment.** The commitment hash is submitted to a `PACTRegistry` contract on IoTeX, which stores `mapping(bytes32 => uint64)` mapping commitment hashes to block numbers. This provides IoTeX-native timestamping but requires one on-chain transaction (which does not reveal address ownership since the commitment is opaque). Gas cost is minimal (\~41,000 gas).

```solidity
contract PACTRegistry {
    mapping(bytes32 => uint64) public commitments;

    event CommitmentRegistered(bytes32 indexed commitment, uint64 blockNumber);

    function register(bytes32 commitment) external {
        require(commitments[commitment] == 0, "Already registered");
        commitments[commitment] = uint64(block.number);
        emit CommitmentRegistered(commitment, uint64(block.number));
    }

    function getTimestamp(bytes32 commitment) external view returns (uint64) {
        return commitments[commitment];
    }
}
```

* **Method C: Ethereum On-Chain Commitment.** The commitment hash is submitted to an Ethereum contract, providing an independent timestamp anchored to Ethereum's security.

Holders are encouraged to use multiple methods for redundancy. The rescue protocol accepts any method whose timestamp predates the governance-defined cutoff.

#### 4.8.3 **Cutoff Date**

The governance-defined cutoff date is the timestamp before which an iPACT must have been created to be accepted by the rescue protocol. The cutoff MUST be set conservatively early—before any credible evidence that CRQCs could derive secp256k1 private keys. The Phase 2 governance vote will determine the cutoff date. The recommended default is the activation block of Phase 2 (hybrid mandatory), which represents the point at which the IoTeX protocol formally acknowledges the quantum threat as operationally relevant.

#### 4.8.4 **iPACT Rescue Protocol**

Upon activation of the legacy sunset (Phase 3), a `PACTRescue` contract is deployed alongside the `PQRescue` contract (Section 6.6.1). To rescue funds, the claimant submits a STARK proof demonstrating, in zero knowledge, the following statement:

"I know values `salt`, `control_proof`, and `secp256k1_privkey` such that: (1)`pk = secp256k1.pubkey(secp256k1_privkey)`; (2)`ioAddr = keccak256(pk)[12:32]`; (3) `ioAddr == claimed_address`; (4) `msg = Encode("iPACT/v1", "iotex-mainnet", ioAddr, salt)`; (5)`ECDSA.verify(pk, keccak256(msg), control_proof) == true`; (6)`commitment = keccak256("iPACT/v1 commitment" || salt || keccak256(control_proof)); (7) commitment` was timestamped before `cutoff_date` (verified against the OpenTimestamps proof or on-chain registry); and (8)`pq_destination` is the post-quantum address to which rescued funds should be sent".&#x20;

The public inputs are `(claimed_address, commitment, timestamp_proof_root, cutoff_block, pq_destination, pq_algorithm_id)`, whereas the private inputs are `(secp256k1_privkey, pk, salt, control_proof)`. The STARK proof is post-quantum secure. Upon successful verification, the `PACTRescue` contract transfers the account's balance to `pq_destination`, which must have a registered PQ key in the PQ Key Registry. The rescue transaction is bound to prevent replay.

#### 4.8.5 **iPACT-DePIN Extension**

For DePIN devices, an extended iPACT format is defined:

```solidity
msg = Encode("iPACT-DePIN/v1", "iotex-mainnet", deviceAddr, deviceType, salt)
```

where `deviceType` is a standardized identifier for the device category (e.g., "obd-dongle", "pebble-tracker"). Device manufacturers SHOULD generate iPACTs for all deployed devices during firmware updates or during device provisioning, storing the salt and proof files in secure enclaves or manufacturer key management systems.

## 5. Technology Stack

### 5.1 Cryptographic Libraries

The following cryptographic libraries are essential for a secure PQC migration.

| **Component**               | **Library**                  | **Justification**                                                                    |
| --------------------------- | ---------------------------- | ------------------------------------------------------------------------------------ |
| ML-DSA                      | liboqs (Open Quantum Safe)   | NIST-compliant, audited, C with Go/Rust bindings                                     |
| SLH-DSA                     | liboqs                       | Same library for consistency                                                         |
| zkSTARK prover              | SP1 (Succinct)               | STARK-native, Rust, WASM-compatible, no quantum-vulnerable final recursion           |
| zkSTARK verifier (on-chain) | SP1 Solidity verifier        | Deployable on EVM-compatible chains                                                  |
| Hash functions              | SHA-256, SHA-512, Keccak-256 | Existing IoTeX hash functions; 256-bit output provides ≥128-bit PQ preimage security |
| Formal verification         | Lean4 / Coq                  | Following EF's formal verification approach                                          |

### 5.2 Client Modifications

IoTeX's Go-based client (iotex-core) requires the following modifications:

* **Transaction pool:** Accept and propagate Type `0x05` transactions. Validate both PQ and legacy signatures before mempool admission.

* **Block validation:** Verify PQ signatures on block proposals and attestations (Phase 2+). Reject ECDSA-only blocks after Phase 3 activation.

* **State management:** Integrate PQ Key Registry state lookups into transaction validation pipeline.

* **P2P networking:** Upgrade to PQ-TLS (using ML-KEM for key encapsulation) for peer-to-peer connections. This follows the Open Quantum Safe (OQS) provider for OpenSSL 3 integration.

* **RPC endpoints:** Expose new RPC methods for PQ key registration, migration proof submission, and PQ key lookup.

### 5.3 Wallet and SDK Modifications

The following wallet and SDK need to be modified to support PQC migration.

* **iotex-antenna (JavaScript/TypeScript SDK):** Add ML-DSA key generation, signing, and verification. Support Type `0x05` transaction construction. Integrate SP1 WASM prover for client-side migration proof generation (desktop/browser wallets).

* **ioPay (mobile wallet):** Add PQ key generation and storage (secure enclave). For migration proof generation, connect to a TEE-based proving service (following Fan et al.'s architecture) due to mobile hardware constraints.

* **Hardware wallet integration:** Work with hardware wallet manufacturers to add ML-DSA support. In the interim, use a hybrid approach where the hardware wallet signs the ECDSA component and a software companion generates the PQ signature.

## 6. Migration Roadmap

### 6.1 Five-Phase Migration Plan

<table><colgroup><col width="118"><col width="100"><col width="156"><col width="507"></colgroup>
<thead>
<tr>
<th><strong>Phase</strong></th>
<th><strong>Time Period</strong></th>
<th><strong>Objective</strong></th>
<th><strong>Key Deliverables</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Phase 0: Foundation</strong></td>
<td>2026 Q3 – 2027 Q2<br /></td>
<td>Deploy infrastructure without protocol changes</td>
<td><ul>
<li>Publish this IIP and complete community review process</li>
<li>Implement ML-DSA and SLH-DSA in <code>iotex-core</code> as an optional module</li>
<li>Deploy PQ Key Registry smart contract on IoTeX mainnet (no protocol enforcement, purely voluntary registration)</li>
<li>Deploy STARK verifier contract on IoTeX mainnet</li>
<li>Launch TEE-based PQ proving service for mobile/IoT device migration</li>
<li>Integrate PQ key generation into ioPay wallet (opt-in)</li>
<li>Perform formal verification of PQ precompile implementation</li>
<li>Upgrade P2P networking to support hybrid PQ-TLS alongside classical TLS</li>
<li>Publish DePIN PQ Device Identity Standard for new device provisioning</li>
</ul></td>
</tr>
<tr>
<td><strong>Phase 1: Precompile Deployment</strong></td>
<td>2027 Q3 – 2028 Q2</td>
<td>Deploy PQ signature verification as a native protocol capability</td>
<td><ul>
<li>Hard fork to deploy PQ signature verification precompile (<code>0x0B</code>)</li>
<li>Enable Type <code>0x05</code> transaction processing (PQ signature required alongside ECDSA)</li>
<li>Activate protocol-level PQ Key Registry enforcement (registered PQ key required for Type <code>0x05</code> transactions)</li>
<li>All 24 delegates MUST register PQ keys (governance mandate)</li>
<li>Begin dual-signed block production (ECDSA + PQ attestations)</li>
<li>Gas subsidy program for PQ migration transactions (reduced gas for Type <code>0x05</code> for the first 12 months)</li>
<li>Launch ecosystem migration toolkit for DApp developers</li>
</ul></td>
</tr>
<tr>
<td><strong>Phase 2: Hybrid Enforcement</strong></td>
<td>2028 Q3 – 2030 Q2</td>
<td>Establish PQ signatures as the primary authentication mechanism while maintaining backward compatibility</td>
<td><ul>
<li>Soft deadline (2028 Q3): All new account creation in official wallets defaults to PQ-capable accounts (PQ key generated alongside ECDSA key)</li>
<li>Hard deadline (2029 Q3): New transactions to PQ-registered accounts MUST use Type <code>0x05</code> (analogous to BIP-361 Phase A for the IoTeX context, restricting sends to registered accounts)</li>
<li>Consensus transition (2030 Q1): PQ-only consensus activation — delegates produce and attest blocks using only PQ signatures. ECDSA-only delegates are excluded from the active set</li>
<li>Deploy recursive STARK aggregation for batch migration proofs</li>
<li>Expand DePIN device migration program with manufacturer partnerships</li>
<li>Publish formal security audit of full PQ implementation</li>
</ul></td>
</tr>
<tr>
<td><strong>Phase 3: Legacy Sunset</strong></td>
<td>2030 Q3 – 2031 Q4</td>
<td>Restrict and eventually eliminate classical ECDSA authentication</td>
<td><ul>
<li>Soft fork (2030 Q3): Type <code>0x00</code>, <code>0x01</code>, <code>0x02</code> transactions (legacy ECDSA-only) are accepted only if the sender has NOT registered a PQ key. Accounts with registered PQ keys MUST use Type <code>0x05</code></li>
<li>Grace period (18 months): Aggressive outreach campaign for remaining un-migrated accounts, including automated migration services, exchange partnerships, and device OTA update programs</li>
<li>zkSTARK rescue protocol: For accounts whose owners can prove knowledge of the BIP-32 derivation seed or mnemonic, a rescue path remains open via zkSTARK proof submission, even after the ECDSA sunset</li>
<li>Policy determination on unmigrated accounts (community governance vote): options include indefinite preservation (do nothing), time-locked freeze, or permanent burn</li>
</ul></td>
</tr>
<tr>
<td><strong>Phase 4: PQ-Native</strong></td>
<td>2032 Q1 – 2033</td>
<td>Complete the transition to post-quantum-only operation</td>
<td><ul>
<li>Hard fork (2032 Q1): Legacy ECDSA-only transactions are no longer processed at the protocol level. All transaction types require PQ authentication. The rescue protocol via zkSTARK remains available for late migrants</li>
<li>Remove ECDSA verification from the critical consensus path (retain <code>ecrecover</code> precompile for smart contract compatibility)</li>
<li>Evaluate and potentially deploy STARK-based PQ signature aggregation for execution-layer transaction verification (following Ethereum's Fork M* approach if research matures)</li>
<li>Evaluate emerging PQ algorithms (e.g., SQIsign improvements, new NIST round selections) for potential inclusion via the cryptographic agility framework</li>
<li>Publish final migration report and post-mortem analysis</li>
</ul></td>
</tr>
</tbody>
</table>

### 6.2 Emergency Track

If credible evidence of a CRQC capable of at-rest attacks emerges before Phase 3 completion.

* **Immediate actions (within 48 hours):**

  * Issue emergency advisory to all IoTeX ecosystem participants

  * Activate "PQ-only" transaction processing for all PQ-registered accounts (skip to Phase 3 enforcement)

  * Coordinate with exchanges and custodians for emergency key rotation

* **Short-term actions (within 2 weeks):**

  * Emergency hard fork to require PQ authentication for all high-value transactions (>10,000 IOTX)

  * Freeze accounts with exposed public keys that have not registered PQ keys (time-locked, unfreezes upon PQ registration)

  * Deploy commit-delay-reveal protocol for legacy transactions (sender commits to a transaction hash, waits for N blocks, then reveals — preventing on-spend attacks even for non-migrated accounts)

* **Medium-term actions (within 3 months):**

  * Accelerate Phase 4 deployment

  * Implement the BIP-361-style rescue protocol for all accounts with provable ownership

## 7. Backward Compatibility

This IIP is designed for maximum backward compatibility, following the lessons from every analyzed framework:

* **EVM Compatibility:** The PQ signature verification precompile extends the EVM precompile set without modifying existing opcodes. Existing smart contracts continue to function unchanged. The `ecrecover` precompile is retained permanently for backward compatibility.

* **Transaction Format:** Type `0x05` is additive under EIP-2718. Existing transaction types (`0x00`, `0x01`, `0x02`) remain valid through Phase 3. Wallets and infrastructure that do not support Type `0x05` can continue to interact with the network during the transition period.

* **Address Format:** Following the approach of Fan et al., Baldimtsi et al., and Kiraz–Kardas, no address changes are required. PQ keys are bound to existing addresses via the PQ Key Registry. Users retain their existing addresses, balances, and smart contract interactions.

* **Smart Contract Compatibility:** Existing smart contracts do not require redeployment. Contracts that perform on-chain signature verification (e.g., multisig wallets, governance contracts) should be upgraded to support PQ verification via the precompile, but this is at the discretion of contract owners. A migration library (`PQVerifierLib.sol`) is provided for easy integration.

* **Delegate Compatibility:** Non-upgraded delegates can continue to produce blocks through Phase 2 using ECDSA-only signatures. After Phase 2 consensus transition, only PQ-capable delegates are included in the active set.

## 8. Security Considerations

### 8.1 Cryptographic Agility

This IIP embeds cryptographic agility as a first-class design principle, following the Ethereum Foundation's approach. The precompile supports multiple algorithm identifiers, and the PQ Key Registry supports key rotation. If ML-DSA is weakened by future cryptanalysis (as happened with isogeny-based SIKE in 2022), accounts can rotate to SLH-DSA or future NIST-approved algorithms without protocol changes.

### 8.2 Hash Function Security in the Quantum Setting

Following the Kiraz–Kardas analysis, we distinguish collision resistance (BHT-style, \~2^(n/3)) from preimage resistance (Grover-style, \~2^(n/2)):

* **Keccak-256 (address derivation):** Provides \~128-bit preimage security and \~85-bit collision security in the quantum setting. The 128-bit preimage security is sufficient for address hiding (Scenario B accounts). For migration-era commitments and registry leaves, domain-separated hash suites with at least 256-bit outputs are used, following the Kiraz–Kardas hash agility guidance.

* **SHA-256 (Merkle trees, transaction IDs):** Provides \~128-bit preimage security and \~85-bit collision security. Sufficient for current use cases but should be evaluated for upgrade to SHA-384 or SHA3-256 in future protocol revisions if collision resistance becomes critical.

### 8.3 Side-Channel Attacks

NIST PQC algorithms are known to be susceptible to side-channel attacks (power analysis, electromagnetic analysis, fault injection) as documented in the Baseri et al. STRIDE analysis. Mitigations include masked implementations in the client, constant-time code, and hardware-backed key storage. The IoTeX client MUST use constant-time ML-DSA implementations from liboqs. Hardware wallet implementations MUST include side-channel protections.

### 8.4 Migration Proof Security

The zkSTARK-based migration proofs rely on the soundness of the STARK proof system and the quantum preimage resistance of the underlying hash functions. STARKs use no trusted setup and rely only on collision-resistant hash functions, making them plausibly post-quantum secure. The SP1 zkVM is STARK-native end-to-end, avoiding the quantum-vulnerable Groth16 final recursion step used by some other systems.

### 8.5 Mempool Privacy

During the transition period, Type `0x05` transactions that include ECDSA signatures still reveal the public key in the mempool. For maximum security during the quantum-proximity period, a commit-delay-reveal scheme is recommended for high-value transactions: the sender first commits to a hash of the transaction, waits for N blocks, then reveals the full transaction. This prevents on-spend attacks even for accounts that have not completed PQ migration. Integration with IoTeX's existing infrastructure for private mempools (if available) or encrypted mempool solutions is recommended.

### 8.6 Quantum-Safe Consensus Integrity

With 24 delegates, the Roll-DPoS consensus is vulnerable if a CRQC can compromise multiple delegate keys simultaneously. The PQ migration of all 24 delegate keys in Phase 2 eliminates this risk. During the hybrid period (Phases 1–2), the dual-signature requirement ensures that an attacker must compromise both the ECDSA and PQ keys of a delegate to produce valid attestations.

### 8.7 DePIN Device Security

IoT devices often have limited computational resources and long operational lifetimes. SLH-DSA-SHA2-128s is recommended for devices due to its reliance solely on hash function security (most conservative assumption) despite its larger signature size (7,856 bytes). For extremely constrained devices, a gateway-mediated verification model is specified where the device signs with its PQ key and a trusted gateway verifies and attests to the validity.

## 9. Performance Analysis and Gas Economics

### 9.1 Transaction Size Impact

The translation size of the current, hybrid, PQ signatures is summarized in the table below.

| **Transaction Type** | **Current (ECDSA)** | **Type 0x05 (ML-DSA-44 + ECDSA)** | **Type 0x05 (ML-DSA-44 only)** |
| -------------------- | ------------------- | --------------------------------- | ------------------------------ |
| Signature size       | \~65 bytes          | \~2,485 bytes (2,420 + 65)        | \~2,420 bytes                  |
| Public key size      | 0 (recovered)       | \~1,312 bytes                     | \~1,312 bytes                  |
| Total overhead       | \~65 bytes          | \~3,797 bytes                     | \~3,732 bytes                  |
| Increase factor      | 1x                  | \~58x                             | \~57x                          |

### 9.2 Block Size and Throughput Impact

At IoTeX's current parameters, the increase in transaction size will reduce the number of transactions per block by approximately 40–60% if block size limits remain unchanged. Mitigations include increasing the block size limit (straightforward given IoTeX's 5-second block time and delegate-based consensus), introducing blob-style data availability (following EIP-4844) for PQ signature data, and implementing STARK-based signature aggregation in later phases.

### 9.3 Gas Cost Comparison

| **Operation**                  | **Current Gas** | **PQ Gas (Phase 1-2)**              | **PQ Gas (Phase 4)** |
| ------------------------------ | --------------- | ----------------------------------- | -------------------- |
| Simple transfer (ECDSA)        | \~21,000        | N/A                                 | Deprecated           |
| Simple transfer (ML-DSA-44)    | N/A             | \~23,700 (21,000 + 2,700 verify)    | \~23,700             |
| Simple transfer (SLH-DSA-128s) | N/A             | \~132,000 (21,000 + 111,000 verify) | \~132,000            |
| PQ Key Registration            | N/A             | \~100,000 (one-time)                | N/A                  |
| zkSTARK Migration Proof        | N/A             | \~300,000–500,000 (one-time)        | N/A                  |

### 9.4 Migration Incentives

To accelerate migration, the following economic incentives are proposed:

* **Gas subsidy (Phase 1, 12 months):** PQ key registration transactions receive a 50% gas discount, funded by a protocol-level migration subsidy pool.

* **Priority inclusion:** Type `0x05` transactions receive priority ordering in the block (above same-fee legacy transactions) during Phases 1–2.

* **Delegate rewards:** Delegates that complete PQ migration before the Phase 2 deadline receive a bonus reward multiplier for 6 months.

## 10. Reference Implementation

The reference implementation consists of the following components, to be developed as open-source public goods:

* **`iotex-core` modifications:** Go implementation of PQ precompile, Type `0x05` transaction processing, and dual-signed consensus

* **`iotex-pq-registry`:** Solidity smart contract for PQ Key Registry, including zkSTARK verifier integration

* **`iotex-pq-sdk`:** TypeScript/Go SDK extensions for PQ key management, Type `0x05` transaction construction, and migration proof generation

* **`iotex-pq-prover`:** Rust-based SP1 zkVM circuits for IoTeX address binding and mnemonic-based migration proofs

* **`iotex-pq-tee-service`:** TEE-based proving service for mobile/IoT device migration

* **`iotex-pq-depin-sdk`:** DePIN device identity SDK with ML-DSA/SLH-DSA support

## References

1. **pq.ethereum.org** — Ethereum Foundation Post-Quantum Team. "Post-Quantum Ethereum." <https://pq.ethereum.org/>

2. **Google Quantum AI (2026).** Babbush, R. and Neven, H. "Quantum Vulnerability of ECDLP-256." arXiv:2603.28846. <https://quantumai.google/static/site-assets/downloads/cryptocurrency-whitepaper.pdf>

3. **PQCEE (2025).** "Enabling a Smooth Migration towards Post-Quantum Security for Ethereum." <https://pqcee.github.io/Enabling_a_Smooth_Migration_towards_Post_Quantum_Security_for_Ethereum.pdf>

4. **eprint 2025/1368.** "Post-Quantum Migration Framework for EdDSA-Based Blockchains." <https://eprint.iacr.org/2025/1368.pdf>

5. **Sui Blog.** "Post-Quantum Computing Cryptography Security." <https://blog.sui.io/post-quantum-computing-cryptography-security/>

6. **Google Research Blog.** "Safeguarding Cryptocurrency by Disclosing Quantum Vulnerabilities Responsibly." <https://research.google/blog/safeguarding-cryptocurrency-by-disclosing-quantum-vulnerabilities-responsibly/>

7. **BIP-361.** Lopp, J. et al. "Post-Quantum Migration and Legacy Signature Sunset." <https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki>

8. **Chaincode Labs.** "Bitcoin Post-Quantum." <https://chaincode.com/bitcoin-post-quantum.pdf>

9. **eprint 2026/352.** "End-to-End Post-Quantum Migration Framework for Bitcoin and Ethereum." <https://eprint.iacr.org/2026/352.pdf>

10. **arXiv 2501.11798.** "Quantum-Safe Risk Assessment of Blockchain Systems." <https://arxiv.org/pdf/2501.11798>

11. **QRL.** "The Definitive Guide to Post-Quantum Blockchain Security." <https://www.theqrl.org/the-definitive-guide-to-post-quantum-blockchain-security/>

12. **Meta Engineering (2026).** "Post-Quantum Cryptography Migration at Meta: Framework, Lessons, and Takeaways." <https://engineering.fb.com/2026/04/16/security/post-quantum-cryptography-migration-at-meta-framework-lessons-and-takeaways/>

13. **Coinbase Independent Advisory Board (2026).** Aaronson, S., Boneh, D., Drake, J., Kannan, S., Lindell, Y., Malkhi, D. "Quantum Computing and Blockchain." <https://assets.ctfassets.net/sygt3q11s4a9/6EjYavuGdtJDYCqaJrASj9/9f464a8bf26f44bd6c85710fe7e4a29f/Quantum_Computing_and_Blockchain_v10.3_15April2026.pdf>

14. **Robinson, D. (2026).** "PACTs: Protecting Your Bitcoin From a Quantum Sunset." Paradigm Research, May 1, 2026. <https://www.paradigm.xyz/2026/05/pacts-protecting-your-bitcoin-from-a-quantum-sunset>

15. **NIST FIPS 203.** "Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM)." 2024.

16. **NIST FIPS 204.** "Module-Lattice-Based Digital Signature Standard (ML-DSA)." 2024.

17. **NIST FIPS 205.** "Stateless Hash-Based Digital Signature Standard (SLH-DSA)." 2024.

18. **NIST FIPS 206 (Draft).** "FFT over NTRU Lattice–Based Digital Signature Standard (FN-DSA)." 2025.

19. **EIP-2718.** "Typed Transaction Envelope." <https://eips.ethereum.org/EIPS/eip-2718>

20. **EIP-8141.** "Frame Transactions." <https://eips.ethereum.org/EIPS/eip-8141>

21. **EIP-7619.** "Precompile Falcon512 Generic Verifier." <https://eipsinsight.com/eips/7619>

22. **ERC-4337.** "Account Abstraction Using Alt Mempool." <https://eips.ethereum.org/EIPS/eip-4337>

23. **IoTeX Core.** <https://github.com/iotexproject/iotex-core>

24. **IoTeX Documentation.** "Account Cryptography." <https://docs.iotex.io/blockchain/build/reference-docs/native-iotex-development/account-cryptography>

25. **Open Quantum Safe (liboqs).** <https://openquantumsafe.org/>

26. **Ethereum Strawmap.** <https://strawmap.org/>

27. **OpenTimestamps.** Open-source timestamping protocol. <https://opentimestamps.org/>

28. **BIP-322.** "Generic Signed Message Format." <https://github.com/bitcoin/bips/blob/master/bip-0322.mediawiki>

29. **Narula, N. (2026).** "Bitcoin and Quantum: A Roadmap." <https://nehanarula.org/2026/04/20/bitcoin-and-quantum-a-roadmap.html>

30. **Aaronson, S. (2026).** Blog post on quantum computing advances. <https://scottaaronson.blog/?p=9665>

31. **Coinbase Blog.** "Coinbase Quantum Advisory Council Publishes Position Paper on Quantum Computing and Blockchain." <https://www.coinbase.com/blog/coinbase-quantum-advisory-council-publishes-position-paper-on-quantum-computing-and-blockchain>
