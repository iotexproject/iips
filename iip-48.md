```
- Title: "IIP-48: CIOTX – A Unified Cross-Chain Token Standard for the IoTeX Network"
- Author: Qevan Guo, Chen Chen, Seedlet
- Status: Draft
- Type: Standards Track
- Category: Token / Governance
- Created: 2025-02-12
- Updated: 2025-06-05
```

---

## **Abstract**

The IoTeX ecosystem currently features multiple representations of the IOTX token, leading to user confusion and integration complexity. This proposal aims to unify IOTX into a single, canonical token across major Layer 1 / Layer 2 blockchains, including Ethereum mainnet, Base and Solana, to name a few.

This proposal formalizes **CIOTX** as the standard cross-chain representation of IOTX. CIOTX has been in use across multiple chains and functions effectively as a unified token, differing primarily in name. It is already deployed via trusted bridging infrastructure such as ioTube and Wormhole.

IIP-48 will serve as **Phase 1** of the unification. A future IIP will introduce **Phase 2** which will involve the introduction of a new unified token to consolidate all IOTX variants across chains.

---

## **Motivation**

Multiple versions of the IOTX token currently exist within the ecosystem:

* **Native IOTX**: The native token on IoTeX L1, required to pay gas for mainnet transactions, widely traded on major exchanges (Binance, KuCoin, Gate, MEXC, etc.).

* **WIOTX**: The wrapped IOTX token (XRC20 format) used for DeFi and dApps on the IoTeX L1 blockchain.

* **ERC20 IOTX**: The legacy ERC20 IOTX token on the Ethereum blockchain, listed on Coinbase & Gemini exchanges. While 87% of the total supply has been burned during mainnet launch, it remains 1:1 convertible to native IOTX, but price discrepancies arise due to its limited availability on Ethereum.

* **CIOTX (Crosschain IOTX)**: A bridge-based version of IOTX deployed on multiple chains (Polygon, BSC, Ethereum) for cross-chain functionality.

This fragmented structure creates market inefficiencies, complicates liquidity distribution, and increases the technical burden for developers and users. A unified token standard will enhance ecosystem clarity, improve liquidity, and streamline user experience.

---

## **Token Unification Strategy**

##### **A. Formal Adoption of CIOTX as the Cross-Chain Token Standard**

CIOTX has been actively used to enable cross-chain IOTX transfers across ecosystems like Ethereum, BSC, Polygon, and Solana. This proposal formalizes CIOTX as the **canonical cross-chain representation** of IOTX.

##### **B.** **dApp** **and Exchange Coordination**

**Action:** Coordinate with major exchanges, wallet providers, indexers, and dApp developers to adopt CIOTX as the primary multichain representation of IOTX. **Rationale:** Standardizing CIOTX across platforms ensures a unified user experience and reduces the complexity of managing multiple IOTX variants.

##### **C. Expand and Rebalance CIOTX Liquidity**

**Action:** Collaborate with liquidity providers, DeFi protocols, and bridge operators to expand and rebalance CIOTX liquidity on supported chains, including Solana (Raydium), Base (Uniswap), and Polygon (Quickswap). **Rationale:** Consolidated liquidity around CIOTX improves price discovery, reduces slippage, and promotes seamless multichain DeFi participation.

##### **D. Legacy ERC20 IOTX Token (Phase 2 Outlook)**

**Action:** While ERC20 IOTX remains widely held (e.g., on Coinbase), its long-term future should be discussed with the community and exchange partners. **Rationale:** ERC20 IOTX lacks a consistent 1:1 peg to native IOTX, leading to pricing discrepancies and market confusion. A potential retirement or migration path may be proposed in a future phase, pending consensus.

<!--br {mso-data-placement:same-cell;}--> td {white-space:nowrap;border:0.5pt solid #dee0e3;font-size:10pt;font-style:normal;font-weight:normal;vertical-align:middle;word-break:normal;word-wrap:normal;}

|Chain|Token|DEX|Bridge|Explorer|
| --- | --- | --- | --- | --- |
|Ethereum|CIOTX|Uniswap|ioTube|https://etherscan.io/token/0x9F90B457Dea25eF802E38D470ddA7343691D8FE1|
|Polygon|CIOTX|Quickswap|ioTube|https://polygonscan.com/token/0x300211Def2a644b036A9bdd3e58159bb2074d388|
|Solana|CIOTX|Raydium|Wormhole|https://solscan.io/token/QUUzqeiXHxjs9Yxm33tvugvUsKr5T8vjeyV4XhVsAfZ|
|BSC|CIOTX|PancakeSwap|ioTube|https://bscscan.com/token/0x9678E42ceBEb63F23197D726B29b1CB20d0064E5|
|Base (proposed)|CIOTX|Uniswap|Superbridge|–|
|Unichain (proposed)|CIOTX|TBD|Superbridge|–|

---

## **Design Principles**

Our approach prioritizes the use of **official and native bridges** for each target chain, as they are generally the most trusted, sustainable, and well-integrated within their ecosystems:

* **Wormhole** for bridging to **Solana**

* **Superbridge** (the standard for L2 rollups) for **Base** and **Unichain**

* **ioTube** for bridging from/to **IoTeX**

* **Binance CEX** as a bridge to **BSC** (Binance Smart Chain)

These choices aim to maximize compatibility with existing dApps while ensuring long-term reliability and user trust.

![whiteboard_exported_image (2)](https://github.com/user-attachments/assets/dbf9c875-f53d-4d59-b6f5-286f7acfdaf5)



---

# User Experience and Security Considerations

This proposal prioritizes both user safety and simplicity. By leveraging the existing CIOTX architecture, users and developers benefit from a streamlined experience without introducing unnecessary migration steps or token confusion.

#### **User Experience**

* **No Migration Required**: Users are not required to swap tokens or move funds. CIOTX is already active on multiple chains, and its role is being formalized—not replaced.

* **Improved Discoverability**: A unified token standard enables easier tracking on portfolio tools, DEX aggregators, and market data platforms.

* **DeFi Compatibility**: Standardizing on CIOTX simplifies onboarding for users participating in DeFi protocols across Solana (Raydium), Base (Uniswap), Polygon (Quickswap), and more.

#### **Security**

* **Audits**: All smart contracts used in new CIOTX deployments (e.g., on Base, Unichain) will undergo comprehensive audits from reputable security firms before launch.

* **Bridge Reliability**: CIOTX is only deployed through trusted, ecosystem-native bridges:

  * **Wormhole** (Solana)

  * **Superbridge** (L2s like Base and Unichain)

  * **ioTube** (Ethereum, BSC, Polygon)

---

## **Conclusion**

Adopting **CIOTX** as the unified cross-chain representation of IOTX is a practical step toward reducing fragmentation, improving liquidity, and simplifying the user experience.

By building on existing infrastructure and coordinating with exchanges, dApps, and bridge providers, we can strengthen IoTeX’s multichain presence with minimal disruption.

Future decisions regarding other token variants, such as ERC20 IOTX, will be guided by community discussion and adoption trends.

---

## **Copyright**

This document and its contents are made available under the CC0 public domain dedication.
