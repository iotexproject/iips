```
- Title: IIP-48: A Unified Token Standard for the IoTeX Network
- Author: Qevan Guo & Giuseppe De Luca
- Status: Draft
- Type: Standards Track
- Category: Token / Governance
- Created: 2025-02-12
```


# Abstract
The IoTeX ecosystem currently features multiple representations of the IOTX token, leading to user confusion and integration complexity. This proposal aims to unify IOTX into a single, canonical token across major Layer 1 / Layer 2 (L1/L2) blockchains, including Ethereum mainnet. The plan involves retiring CIOTX, retiring the ERC20 IOTX on Ethereum, and introducing a unified IOTX token that will be interconnected via the IoTeX bridge (iotube) to all supported chains. The total supply of the IOTX Unified Token will be based on the native IOTX on the IoTeX network, which has a total supply of 10 billion.

To ensure a smooth transition, IoTeX will collaborate with exchanges and dApps to migrate existing tokens to the unified standard over six months. Following this period, the legacy ERC20 IOTX token will be retired, with all ERC20 IOTX convertible to the unified IOTX token at a 1:1 ratio.

---

# Motivation
Multiple versions of the IOTX token currently exist within the ecosystem:

- **Native IOTX**: The primary token on IoTeX L1, widely traded on major exchanges (Binance, KuCoin, Gate, MEXC, etc.).
- **WIOTX**: The wrapped IOTX token (XRC20 format) used for DeFi and on-chain applications.
- **Legacy ERC20 IOTX**: An older Ethereum-based IOTX token, listed on Coinbase & Gemini. While 87% of the total supply has been burned and it remains 1:1 convertible to native IOTX, price discrepancies arise due to its limited availability on Ethereum.
- **CIOTX (Crosschain IOTX)**: A bridge-based version of IOTX deployed on multiple chains (Polygon, BSC, Ethereum) for cross-chain functionality.

This fragmented structure creates market inefficiencies, complicates liquidity distribution, and increases the technical burden for developers and users. A unified token standard will enhance ecosystem clarity, improve liquidity, and streamline user experience.

---

# Specification

## 1. Token Unification Strategy

### 1.1 CIOTX Replacement with a Unified IOTX Token
- CIOTX, while enabling cross-chain transfers, introduces unnecessary complexity and liquidity fragmentation.
- It will be replaced by a unified IOTX token deployed on major L1s/L2s, including Ethereum mainnet, Base, Polygon, and Solana.
- The unified token will have the following properties:
  - **Symbol/Ticker**: IOTX
  - **Name**: IoTeX Network Token (Unified)

### 1.2 Migration Plan with Exchanges and dApps
- **Action**: Coordinate with major exchanges, wallet providers, and dApp developers to integrate the unified IOTX token.
- **Rationale**: A structured migration will ensure minimal disruption while consolidating liquidity.

### 1.3 Replenish Liquidity for IOTX on Mainstream L1s
- **Action**: Partner with liquidity providers and cross-chain bridge operators to maintain deep liquidity for the unified IOTX token on Ethereum, Solana, Base, Polygon, and BSC.
- **Rationale**: Strong liquidity will drive adoption, enable efficient price discovery, and reduce slippage.

### 1.4 Retire Legacy ERC20 IOTX
- **Action**: Once migration is complete, deprecate the ERC20 IOTX token.
- **Rationale**: The legacy ERC20 IOTX, due to its reduced supply and deviation from a 1:1 peg, causes confusion and inefficiencies. Retiring it will streamline the token ecosystem.

---

## 2. Implementation Details

### 2.1 Smart Contract and Bridge Adjustments
- Deploy the IOTX unified token on Ethereum mainnet and facilitate CIOTX conversions.
- Expand deployments to popular Ethereum Layer 2 solutions via L2 bridges.
- Deploy the IOTX unified token on Solana using the Wormhole bridge.
- Work with major cross-chain bridges to ensure broad compatibility.

### 2.2 Migration Tools
- **User Interface**:
  - Develop a migration dApp allowing CIOTX and legacy ERC20 IOTX holders to swap to the unified IOTX token at a 1:1 ratio.

---

# Backward Compatibility
- **Legacy Integrations**:
  - CIOTX and ERC20 IOTX will remain operational during the six-month migration period but will be clearly marked as deprecated.
  - Legacy smart contracts and bridges will provide temporary support before full deprecation.

---

# Security Considerations
- **Smart Contract Audits**:
  - All new contracts related to token unification and migration will undergo comprehensive security audits using reputable security vendors.

---

# Conclusion
The unification of IOTX into a single, standardized token is a crucial step toward streamlining the IoTeX ecosystem. By consolidating various representations of IOTX, we eliminate market fragmentation, enhance liquidity, and simplify user experience. This proposal outlines a structured migration plan, ensuring seamless adoption across exchanges, dApps, and major L1/L2 blockchains.

Through coordinated efforts with key stakeholders, including liquidity providers and bridge operators, we will ensure a smooth transition over six months. The retirement of CIOTX and the legacy ERC20 IOTX will mark a significant milestone in IoTeX’s evolution, reinforcing the integrity and accessibility of IOTX as a unified, interoperable asset.

By adopting this unified token standard, IoTeX strengthens its position as a leading blockchain platform, fostering broader adoption and long-term sustainability.
