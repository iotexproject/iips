```
IIP: 56
Title: Deprecation of CIOTX Across All Networks
Author: Qevan Guo
Status: Draft
Type: Standards Track
Category: Token / Governance
Created: 2026-02-26
Requires: IIP-48
```

## Abstract

On February 20, 2026, the ioTube cross-chain bridge was exploited, resulting in unauthorized minting of CIOTX tokens on Ethereum. This proposal deprecates CIOTX across all networks — Ethereum, Base, Solana, BSC, Polygon, and IoTeX — and establishes differentiated wind-down procedures based on whether each network was affected by the exploit.

For Ethereum, Base, and Solana, where the attacker minted illegitimate CIOTX (Base and Solana CIOTX are bridged from Ethereum and equally affected), the bridge is permanently shut down. Attacker-minted tokens are disregarded. Legitimate holders can submit claims through a dedicated claims portal to receive equivalent IOTX on the IoTeX Network.

For BSC and Polygon, which were not affected by unauthorized minting, the bridges will be unpaused in the future so users can self-serve bridge their CIOTX back to IOTX on the IoTeX Network. CIOTX on these networks will be deprecated over time as users complete their migrations.

All CEX, DEX, and DeFi partners will be contacted to deprecate CIOTX listings and integrations across all networks.

---

## Motivation

**IIP-48** formalized CIOTX as the canonical cross-chain representation of IOTX, deployed across Ethereum, BSC, Polygon, and other chains via the ioTube bridge.

On February 20, 2026, the ioTube bridge was exploited, and unauthorized CIOTX tokens were minted on Ethereum. As a result:

- **Tainted supply on Ethereum, Base, and Solana**: The attacker-minted CIOTX is indistinguishable from legitimately bridged CIOTX on-chain. CIOTX on Base and Solana is bridged from Ethereum (via Superbridge and Wormhole respectively), so the tainted supply propagates to these chains as well. The attacker may have already sold, transferred, or distributed these tokens, contaminating the circulating supply.

- **Protecting the IOTX token economy**: Each CIOTX in circulation was originally backed 1:1 by IOTX locked on the IoTeX Network. The exploit broke this backing for Ethereum, Base, and Solana by injecting unbacked CIOTX into the supply. To preserve the integrity of the IOTX economy, CIOTX on affected chains must be deprecated, and only verified legitimate holders will be allowed to reclaim their equivalent IOTX through a managed claims process.

BSC, Polygon, and IoTeX were not affected by unauthorized minting. The bridges on these chains were paused as a precautionary measure and can be safely resumed to allow users to migrate their CIOTX back to IOTX before the full deprecation takes effect.

**Note:** IOTX-ERC20 on Ethereum ([`0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69`](https://etherscan.io/token/0x6fB3e0A217407EFFf7Ca062D46c26E5d60a14d69)) and Binance-Pegged IOTX on BSC ([`0x9678E42ceBEb63F23197D726B29b1CB20d0064E5`](https://bscscan.com/token/0x9678E42ceBEb63F23197D726B29b1CB20d0064E5)) were **not affected** by this exploit. These are separate tokens from CIOTX with independent contracts and are not part of the ioTube bridge system. They continue to function normally. No action is required for their holders under this proposal.

---

## Specification

### 1. Immediate Deprecation: Ethereum, Base, and Solana

- **CIOTX Bridge Shutdown**: The ioTube bridge for CIOTX between Ethereum and IoTeX is permanently shut down. CIOTX on Base (bridged from Ethereum via Superbridge) and Solana (bridged from Ethereum via Wormhole) are equally affected. No further bridging of CIOTX from Ethereum, Base, or Solana to the IoTeX Network or any other chain will be supported.

- **Attacker Tokens Disregarded**: All CIOTX minted by the attacker on Ethereum, Base, and Solana is considered invalid. These tokens have no claim to IOTX and will not be honored through any conversion or claims process.

- **Contract Status**: The CIOTX token contracts on Ethereum ([`0x9F90B457Dea25eF802E38D470ddA7343691D8FE1`](https://etherscan.io/token/0x9F90B457Dea25eF802E38D470ddA7343691D8FE1)), Base ([`0x819233aa703a19e434e6dd965493b6081a3fc3aa`](https://basescan.org/token/0x819233aa703a19e434e6dd965493b6081a3fc3aa)), and Solana ([`QUUzqeiXHxjs9Yxm33tvugvUsKr5T8vjeyV4XhVsAfZ`](https://solscan.io/token/QUUzqeiXHxjs9Yxm33tvugvUsKr5T8vjeyV4XhVsAfZ)) are no longer recognized as valid representations of IOTX by the IoTeX Foundation or the ioTube bridge.

### 2. Claims Portal for Legitimate Ethereum, Base, and Solana Holders

Legitimate users who held CIOTX on Ethereum, Base, or Solana **before the exploit** are eligible for reimbursement through a dedicated claims portal:

- **Claims Portal**: The IoTeX Foundation will launch a claims portal where affected users can submit and track their claims.

- **Claim Submission**: Users must:
    - Send their CIOTX to the designated IoTeX Foundation wallet on Ethereum.
    - Submit the transaction hash of the transfer through the claims portal.

- **Verification**: The IoTeX Foundation will verify each claim against on-chain data, including:
    - Confirmation that the submitted CIOTX was received at the Foundation wallet
    - Transaction history to confirm tokens were not minted by the attacker or acquired from attacker-controlled addresses
    - Cross-referencing with ioTube bridge records of legitimate cross-chain transfers

- **Distribution**: Upon successful verification, equivalent IOTX will be sent to the claimant's wallet on the IoTeX Network. Distributions will be processed in batches.

### 3. Gradual Deprecation: BSC, Polygon, and IoTeX

These networks were not affected by unauthorized minting. CIOTX on these chains will be deprecated over time through the following process:

- **Bridge Resumption**: The ioTube bridge for CIOTX on BSC ([`0x2aaF50869739e317AB80A57Bf87cAA35F5b60598`](https://bscscan.com/token/0x2aaF50869739e317AB80A57Bf87cAA35F5b60598)), Polygon ([`0x300211Def2a644b036A9bdd3e58159bb2074d388`](https://polygonscan.com/token/0x300211Def2a644b036A9bdd3e58159bb2074d388)), and IoTeX will be unpaused after a full security review of the bridge infrastructure is completed.

- **Self-Service Migration**: Users holding CIOTX on BSC, Polygon, or IoTeX can bridge their tokens back to IOTX on the IoTeX Network through the standard ioTube interface. No manual claims process is needed for these chains.

- **Deprecation Timeline**: After a sufficient migration window (duration to be announced), the bridges for CIOTX on BSC, Polygon, and IoTeX will be permanently shut down. Users are encouraged to migrate their CIOTX to IOTX as soon as the bridges reopen.

### 4. Partner Coordination

- **Centralized Exchanges (CEX)**: All CEX partners supporting CIOTX deposits or withdrawals will be contacted to migrate away from CIOTX.

- **Decentralized Exchanges (DEX)**: DEX protocols with CIOTX liquidity pools (Uniswap, PancakeSwap, QuickSwap, and others) will be notified. Liquidity providers will be advised to withdraw their liquidity.

- **DeFi Protocols**: Any DeFi protocols that accept CIOTX as collateral, staking, or in any other capacity will be contacted to remove CIOTX support.

- **Data Aggregators and Wallets**: Market data platforms (CoinGecko, CoinMarketCap, etc.) and wallet providers will be notified to flag CIOTX as deprecated across all networks.

---

## Backward Compatibility

This proposal is a **breaking change** for all CIOTX holders across all networks:

- **Ethereum, Base, and Solana**: CIOTX is immediately non-bridgeable to IoTeX Network. Legitimate holders must use the claims portal to receive IOTX on the IoTeX Network. Attacker-minted tokens are disregarded.

- **BSC, Polygon, and IoTeX**: CIOTX remains bridgeable during the migration window after bridges are unpaused. After the deprecation deadline, CIOTX on these chains will no longer be convertible to IOTX.

This proposal fully supersedes IIP-48's cross-chain token unification strategy for CIOTX. A future IIP will define the replacement cross-chain approach.

---

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
