```
Title: DePIN Flywheel I: IoTeX ioID Tokenomics
Author(s): IoTeX Core Team
Status: Community Discussion
Type: Standards
Created: 11/12/2024
```


### Abstract

This IIP proposes a sustainable tokenomics framework for ioID, **the world's most advanced on-chain identity solution for smart devices.** ioID enables secure, verifiable identities for devices, users, and nodes while integrating seamlessly with DePIN modular infrastructure. The proposed model introduces **a free DID issuance process**, **a flat ioID registration fee denominated in IOTX**, and **a staking mechanism for DePIN projects** for registering with the IoTeX blockchain. These mechanisms ensure broad adoption, contribute to Layer 1 (L1) gas revenue, and sustain the IoTeX ecosystem by aligning with its mission to support scalable, decentralized DePIN applications.

---

### Motivation

The ioID tokenomics model addresses critical needs within the IoTeX ecosystem by:

1. **Establishing Sustainable Protocol Revenue:** The one time registration fee in IOTX and IOTX staking requirements create a self-sustaining protocol revenue while enhancing network security.

2. **Driving Decentralized Identity Adoption:** Free DID issuance and manageable registration fees encourage user onboarding and DePIN project participation.

3. **Empowering Comprehensive Identity Management:** ioID enables seamless identity verification and management for DePIN projects, device manufacturers, and users, unlocking real-world applications with verifiable trust.

By balancing accessibility, financial sustainability, and incentive mechanisms, the proposal supports IoTeX’s vision for scalable decentralized device identity solutions being the sector standard adopted among DePIN applications.

---

### Overview of the ioID Module

In overview, ioID not only provides DePIN builders with a suite of tools to register and manage device identities on-chain and off-chain, but also equips devices with their own smart contract wallet and private key to **sign data on-device and verify their real world activities**. Furthermore, ioID serves as a gateway for devices to interact with the rest of the IoTeX 2.0 tech stack including **[DePIN Infrastructure Modules (DIMs)](https://docs.iotex.io/depin-infra-modules-dim/dims-overview?ref=iotex.io)** for connectivity, storage, compute, and more. With ioID, we are bringing devices on-chain as self-sovereign assets and introducing a new universe of use cases for the DePIN sector.

### ioID Architecture at Glance

ioID is a universal identity system that creates on-chain identities for devices that are then verifiably bound via smart contracts to devices' off-chain identities and owners' on-chain identities. In the architecture of ioID, the on-chain identity of a device is represented as an **ioID NFT** (i.e., [ERC-6551 NFT](https://eips.ethereum.org/EIPS/eip-6551?ref=iotex.io)) while the device's off-chain identity is represented as a **[decentralized identity (DID)](https://www.w3.org/TR/did-core/?ref=iotex.io)**. The issuance and binding of a device's ioID NFT and DID is facilitated by the [IoTeX Hub](https://hub.iotex.io/?ref=iotex.io) web portal and a [suite of smart contracts](https://github.com/iotexproject/ioID-contracts?ref=iotex.io) on the IoTeX L1 blockchain. In the diagram below, we provide a high-level overview of the ioID architecture.

![](https://iotex.larksuite.com/space/api/box/stream/download/asynccode/?code=NjQ4NjFiZDI1ZjgyMjY5MmRlNmJhODlkNjIzZjA0Y2FfYm1IM3FvaEpDZjkxVDlWQnRkMTNENTlBUzg4c1VoRHBfVG9rZW46TEZiaGJ0c0g0b2UyU0d4OHBMcHVkajhPc0tkXzE3MzI3NDM3Nzk6MTczMjc0NzM3OV9WNA)

* **ioID SDK:**

IoTeX’s **ioID Software Development Kit (SDK)** allows devices to register Decentralized Identities (DIDs) and enable secure communications. It integrates with popular hardware like Raspberry Pi, ESP32, Arduino, and Linux. DIDs are created automatically on devices, with private keys stored securely. For simpler devices, hosted servers can issue DIDs and link them to device identifiers like serial numbers.

* **IoTeX Hub (hub.iotex.io):**

A web portal lets users bind their DIDs to on-chain wallets, pay registration fees, and register ioIDs. Device data is uploaded to IPFS and submitted to smart contracts for minting ioID NFTs.

* **On-Chain Identity:**

Devices receive **ioID NFTs** (ERC-6551), representing ownership and enabling actions like managing data, earning rewards, and interacting on-chain.

* **Smart Contracts:**

  * **ioID Registry:** Registers and verifies device identities for each project.

  * **Project Registry:** Manages DePIN projects with unique project IDs.

  * **ioID NFT:** Mints and assigns ioID NFTs to devices.

  * **ioID Store:** Handles ioID activation and device lifecycle.

---

### ioID Tokenomics Specification

![](https://iotex.larksuite.com/space/api/box/stream/download/asynccode/?code=MWViMGFjYTM0MmZjM2M3Nzc3ZmI2N2M4N2MyMjBmN2Jfa2pFTGQzQjhIRkxhb2ptNEpOeTdaM254QllKYXpVcjhfVG9rZW46VDUzemJiZDg4b0RhMHN4TWEyMnV2SVAxc1NjXzE3MzI3NDM3Nzk6MTczMjc0NzM3OV9WNA)

#### DePIN Team Registration Flow

* **Requirement to Register:**

  * Projects must register with the **Project Registry smart contract**, providing their project name and linking to a unique **Device Registry smart contract** tailored for the project.

  * Projects are required to stake a specific amount of **IOTX** **on Modular Security Pool (MSP)** as a prerequisite, ensuring a stake-for-services model to incentivize honest participation and enhance security.

#### DePIN Device Registration Flow

* **ioID Allocation and Binding:**

  * Devices are issued DID through their associated Device Registry.

  * Device owners must register ioIDs with a one-time registration fee, binding them securely to the owners' wallets and enabling interaction across DePIN infrastructure.

#### Minting and Registration Fees

* **Free DID Issuance:** DePIN teams can issue off-chain DIDs at no cost.

* **ioID Registration Fee:** Users registering their DID on-chain (via the ioID smart contract) incur a flat fee of 1000 IOTX, justified by the interaction costs:

  * **On-Chain Fees:**

    1. Gas costs for submitting DID data to the **Device Registry smart contract**.

    2. Minting an ioID NFT through the **ioID NFT smart contract**, which is then dropped into the user’s wallet.
  * **ioID Features:**

    1. Access to **DIMs (** **DePIN** **Infrastructure Modules)**, including storage (IPFS), connectivity, distributed analytics, W3bstream Zero-Knowledge Proofs, and more.

    2. Access to **Reward Mining Pool** that emitss IOTX and project rewards.

#### Revenue Utilization

Registering a decentralized identity (DID) for a device is free, while activating an ioID on-chain will require a registration fee in IOTX, where a portion of ioID fees collected will be burnt, added to the IoTeX DAO, and/or re-distributed back to ioID-equipped device owners. Registration fees collected are allocated as follows:

1. **Burn (25%):** Ensures token deflation and value appreciation for IOTX.

2. **IoTeX DAO (75%):** Further distributed to support ecosystem growth:

  1. Rewards for **users/devices** contributing data or services.

  2. Grants for **DePIN** **projects** to foster innovation and expansion.

  3. Support for the **Roll-DPoS pool**, enhancing consensus security and scalability.

---

### Rationale

The ioID tokenomics model balances accessibility, scalability, and financial sustainability by:

* Lowering entry barriers through free minting for off-chain identities.

* Supporting network sustainability with registration fees and staking models.

* Allocating fees to both deflationary mechanisms and community incentives, ensuring long-term ecosystem health.

Alternative models, such as higher registration fees or subscription-based pricing, were evaluated but deemed less effective for achieving IoTeX’s goals of rapid adoption and trust-building.

---

### Backward Compatibility

As a new addition, the ioID tokenomics model introduces no backward compatibility concerns.

---

### Security Considerations

ioID leverages IoTeX’s robust smart contract architecture to ensure secure identity management. The DID-based communication protocol strengthens security by replacing centralized IoT models reliant on private certificates. Staking mechanisms further enhance the integrity of participating DePIN projects.

---

### Conclusion

The ioID tokenomics proposal provides a sustainable model to support decentralized device identity solutions within the DePIN ecosystem. By enabling free minting, scalable registration-based revenue, and integration with DIM bundles, the model promotes adoption while ensuring the protocol remains self-sustaining. ioID empowers users, DePIN builders, and device manufacturers to seamlessly integrate decentralized device identities into their applications, driving the growth of secure, blockchain-powered DePIN solutions.
