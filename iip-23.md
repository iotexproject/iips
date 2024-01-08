```
IIP: 23
Title: The Marshall DAO
Author: iotex-core
Status: WIP
Type: Standards Track
Category: Core
Created: 2023-12-05
```

# Summary

This IIP proposes the creation of **The Marshall DAO**, a Decentralized Autonomous Organization (DAO) that will employ a vote-escrow on-chain governance model. The purpose of The Marshall DAO is to enable IoTeX stakeholders to make proposals regarding how to allocate $IOTX incentives to grow the IoTeX ecosystem, including onboarding reputable DePIN projects and funding network-wide initiatives. Additionally, this IIP suggests that The Marshall DAO be formed by merging previously passed IIPs (e.g., [IIP-15](https://community.iotex.io/t/iip-15-sharing-of-gas-fee-with-dapps-sgd/10742)) and IoTeX programs (e.g., [Burn-Drop](https://community.iotex.io/t/passed-burn-drop-tokenomics-updates/9127)), as well as making use of newly available network tools (e.g., [IOTX staking via NFT buckets](https://iotex.io/blog/staking-bucket-as-nfts/)). It is important to note that The Marshall DAO is an upgrade / extension of the original **MachineFi DAO** concept, which was originally proposed and discussed in [August 2022](https://community.iotex.io/t/passed-burn-drop-tokenomics-updates/9127). As such, this proposal gives MachineFi DAO NFT holders the ability to boost their voting power by 0.1% for each MFI NFT owned, up to a maximum of 100 NFTs per wallet, adding up to a potential maximum boost of 10%. 

# Motivation

Over the past year, the DePIN (Decentralized Physical Infrastructure Networks) sector has come to life with many promising projects being bootstrapped across several industries. However, there is a lack of transparent and effective incentive programs that align projects, investors, and community members with the goal of funding new DePIN projects/initiatives and growing the DePIN sector as a whole in a concerted fashion. As a market leader in DePIN, IoTeX is motivated to launch a world-class incentives program that will be governed by DePIN stakeholders via a transparent and fair [vote-escrow on-chain governance](https://coinmarketcap.com/academy/article/what-is-vote-escrow) format.

We believe that by establishing The Marshall DAO (named after [The Marshall Plan](https://history.state.gov/milestones/1945-1952/marshall-plan) of 1948), we can effectively allocate $IOTX incentives to projects and teams that wish to utilize IoTeX's various product offerings (e.g., L1, W3bstream, DePINscan, ioTube, ioPay, device SDKs), contribute new technologies to the IoTeX Network (e.g., wallets, DEX, identity), or even launch new initiatives (e.g., liquidity boost, launchpads, integrations). By putting decision-making power regarding which initiative and projects receive funding/incentives into the hands of $IOTX "true believers", we believe a transparent and meritocratic incentives program can be created to drive the IoTeX Network and DePIN sector forward.

# Typical Scenarios To Support

Here are five typical scenarios that The Marshall DAO aims to unlock. We will enable IoTeX community members who are passionate about on-chain governance to create, discuss, and approve proposals that determine how to allocate $IOTX from the DAO to various projects (specifically, "gauges") periodically.

* **Scenario 1 (Liquidity Boost):** utilize $IOTX from the DAO to incentive liquidity of $XYZ-$IOTX pair on a DEX such as mimo (i.e.,[ liquidity mining](https://www.nansen.ai/guides/the-complete-guide-to-liquidity-mining)), where $XYZ is the token of a community-approved DePIN project

* **Scenario 2 (Launch):** allocate $IOTX from the DAO to sponsor an early-stage DePIN project to help them get started (from 0 to 1). Ultimately, this will increase the velocity of new DePIN project creation and potentially grow the treasury in the DAO.

* **Scenario 3 (Grow):** allocate $IOTX from the DAO to accelerate the growth of a DePIN project that already has its devices or machines launched (from 1 to 100). For example, this can be done by allowing devices or machines to "dual-mine" $IOTX in addition to their tokens.

* **Scenario 4 (Grant):** allocate $IOTX from the DAO to sponsor a project that creates a public good (e.g., blog post series or documentary on DePIN or even something more meme-like such as inscription) or offers network-wide tooling/utilities (e.g., covering gas fees for a public oracle, bug bounties for network tools).

* **Scenario** **5** **(Donate)**: one wants to donate assets such as $IOTX, $USDT, $BTC, $ETH or other DEPIN assets to build a flourishing DePIN ecosystem and encourage the use of IoTeX technologies. They should be able to send the tokens directly to the smart contract address of the Marshall DAO and optionally have their name displayed on a "Hall of Fame".

Other scenarios and ideas for how $IOTX should be allocated to grow the IoTeX Network and DePIN sector may also be facilitated by The Marshall DAO -- the scenarios above are simply illustrative. The goal is to enable long-term "true believers" to propose their own ideas for how $IOTX should be allocated.

# Terminology

**Off-chain Governance vs** **.** **On-chain Governance**

|                       | Off-chain governance (Existent)                                                                                      | On-chain governance (This IIP)                                                  |
|-----------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| **where**             | [https://gov.iotex.io/](https://gov.iotex.io/)                                                                       | [https://dao.iotex.io/ (to come)](https://dao.iotex.io/)                        |
| **who**               | - People who stake $IOTX via staking portal to vote for Delegates / secure the network                               | - People who stake $IOTX to the vote-escrow smart contract to participate in Marshall DAO |
| **why**               | - Protocol-level changes<br>- Smart contract or parameter-level changes<br>- Network policies, processes, and rules | - Spend DAO treasury via specifically scoped projects<br>- Creation of new gauges (see below) |
| **process difference**| - Propose+vote on snapshot                                                                                           | - Propose+vote on dao.iotex.io                                                  |


**Project vs** **.** **Proposal vs** **.** **Gauge**

* A project, as its name implies, refers to a specific initiative.

* A proposal is what is submitted to the DAO for potential acceptance or rejection.

* A gauge (following the convention of curve.fi) is a smart contract that belongs to the project team and is a component of the proposal. It receives the allocated $IOTX tokens.

**Staking** **$IOTX** **Options**

There are currently two ways to stake $IOTX: Native Staking and Staking-as-NFT (more details [here](https://stake.iotex.io/stake)). The Marshall DAO will first support "Staking-as-NFT" upon launch. An initiative to convert "Native Staking" buckets to "Staking-as-NFT" buckets is being planned for late 2024 / early 2025, as protocol-level changes are needed to complete the conversion. After the conversion is completed, existing "Native Staking" buckets will be eligible to participate in The Marshall DAO.

# **Specification**

## Who Governs

Governance of The Marshall DAO will be centered around a new vote-escrowed version of $IOTX called $veIOTX. This can be obtained by staking $IOTX via the ["Staking-as-NFT"](https://stake.iotex.io/stake) method (options include 10K, 100K, 1M $IOTX increments with mandatory 91-day stake lock) and receiving an NFT that represents your staking bucket. These NFTs can then be deposited into The Marshall DAO smart contract to produce **$veIOTX** **,** **which is a non-transferable** **and** **non-tradable token.** $veIOTX grants its holder three benefits:

1. Voting power for on-chain governance (as detailed in this IIP)

2. Obtaining incentives/rewards from projects such as portion of transaction fees and/or new tokens.

3. Boosted $IOTX staking yield by either having vote escrow contract to stake part of its NFT buckets to a liquid staking protocol or tune the DPoS parameters to grant a boost factor to $veIOTX holders (potentially covered by a future IIP)

Since all "Staking-as-NFT" buckets are required to have a 91-day stake lock duration, one's voting power is proportional to the actual $IOTX staked. For example, if Alice has two NFT buckets (10K $IOTX + 100K $IOTX) then Alice's voting power is 110K. If the total $IOTX locked in the vote escrow contract is 10M $IOTX, Alice accounts for 0.11% of all voting power.

![iip23-1](https://github.com/iotexproject/iips/assets/77351244/d8097ee0-70db-4eda-b74d-3d717f7ac579)




## Funding and Allocations

![iip23-2](https://github.com/iotexproject/iips/assets/77351244/aafecf4a-9be1-4423-81f8-7eff27f6aa6e)


This section explains the source of funds for The Marshall DAO, as well as the destination of funds. It is worth noting that The Marshall DAO merges existing IoTeX programs (e.g., [Burn-Drop](https://community.iotex.io/t/passed-burn-drop-tokenomics-updates/9127)) and previously passed IIPs (e.g., [IIP-15](https://community.iotex.io/t/iip-15-sharing-of-gas-fee-with-dapps-sgd/10742)) in an effort to create one holistic program.

* **Foundation:** The IoTeX Foundation will allocate initial funds into the Marshall DAO, as well as replenishments over time.

* **Protocol** **Revenue:** various forms of network revenues, including L1 revenues, gas fees, and potentially W3bstream revenues will be added to the Marshall DAO Treasury. This can be considered merging [IIP-15](https://community.iotex.io/t/iip-15-sharing-of-gas-fee-with-dapps-sgd/10742) into the Marshall DAO design.

* **Donation** **:** in multiple assets such as $USDT, $ETH, $BTC, $ETH and DePIN assets in addition to $IOTX.

* **Burn-Drop:** Additionally, we propose that funds allocated to the [Burn-Drop](https://community.iotex.io/t/passed-burn-drop-tokenomics-updates/9127) program be re-allocated to the Marshall DAO. Specifically, 300M $IOTX from the "MachineFi DAO" allocation of Burn-Drop will be added to the Marshall DAO immediately at launch. After Phase 5 (i.e., 31,000 devices), the remaining "Burn" and "Drop" allocations, comprising a total of 250M $IOTX, will be added to the Marshall DAO -- *note that Phase 5 is expected to be completed by end of 2024 based on the current rate of Ucam/Pebble registrations.* More details on the remaining Burn-Drop allocations can be found [here](https://community.iotex.io/t/passed-burn-drop-tokenomics-updates/9127).

* **Other:** additional sources of funding for Marshall DAO may be added by community vote later.

The destinations of the funds will be **gauges contracts** **,** including one-time gauges (i.e., receives emission once as a lump sum) and continuous gauges (i.e., receives emission every block). The table below illustrates how gauges will be applied to the example scenarios explained earlier:

| Voting Mechanism | Emission | Supported Scenarios |
|------------------|----------|---------------------|
| **One-time Gauge** | | |
| - No weight, one-time vote for pass or reject lasting for N days specified by the proposer. | Lump sum, e.g. 100K IOTX | - Scenario 2: Launch<br>- Scenario 4: Grant<br>- Scenario 5: Donation |
| - Quorum Reached: The total number of votes cast must exceed the dynamic quorum. We start with 10% of participating voting power. | | |
| - Majority Vote: The proposal must receive a majority of the votes cast, i.e., 50% of participating voting power | | |
| **Continuous Gauge** | | |
| - Weight is proportional to votes received | Per-block basis, i.e., 2 IOTX / block initially, adjustable through off-chain governance | - Scenario 1: Liquidity Boost<br>- Scenario 3: Grow |
| - Higher gauge weights receive a larger share of the per-block $IOTX emission | | |
| - Periodic voting, every for 14 days | | |

## The Process

Since on-chain governance aims to facilitate well-scoped projects with specific goals and enable rapid, community-curated decision-making, we do not expect the need for temperature checks or heavy pre-discussion as is required by off-chain governance. We envision the high-level process below:

1. **Create a Proposal**: a new portal at https://dao.iotex.io will be built enabling anyone with more than 100K $veIOTX to create a new funding proposal, which must include:

  1. Title, summary, and actionable proposal

  2. Smart contract address to receive emission, e.g., $XYZ-$IOTX pool contract

  3. Gauge type: One-time vs Continuous

  4. Any specific parameters e.g., voting duration
2. **Vote for a Proposal**: the voting mechanism has been described in the table above

3. **Apply the Results**: The Marshall DAO autonomously applies the proposal once its passed, as part of our vision for decentralized governance and permissionless participation.

# What this IIP Implies

This passing of this IIP implies the community will give the green light to begin development of the Marshall DAO from a technology and process design perspective. It also implies the below action items:

1. The initial governance parameters are as listed below. Any future adjustments of these parameters are possible via new IIPs:

   i. Minimum to propose: 100,000 $veIOTX

   ii. Continuous Gauge:

    * Voting period: 7 days

    * The initial emission rate is 2 $IOTX per block

   iii. One-time Gauge:

    * Quorum: 10% of participating voting power

    * Pass threshold: 50% of participating voting power
2. "MachineFi DAO" allocation of Burn-Drop (300M $IOTX) will be moved immediately into The Marshall DAO as initial funding -- note that the MachineFi DAO and Marshall DAO are ideologically similar, but the Marshall DAO includes more features like decentralized governance. After Phase 5 of Burn-Drop (i.e., >31,000 devices), the remaining "Burn" and "Drop" allocations (250M $IOTX) will be added to the Marshall DAO and Burn-Drop will be halted. *Note that new forms of deflationary burn and/or airdrop mechanisms can be introduced via Marshall DAO -- this enables the community to create several Burn-Drop like programs that are based on different metrics, not only # of devices registered.*

3. A portion of L1 revenues will be allocated to The Marshall DAO upon launch. Specifically, the 30% of L1 revenues approved as part of [IIP-15](https://community.iotex.io/t/iip-15-sharing-of-gas-fee-with-dapps-sgd/10742) to be shared with Dapps will now be added to the Marshall DAO instead. The rationale is that a new gauge can be created via the Marshall DAO that mimics the "sharing of gas fees with top Dapps" goals of IIP-15.

## Copyright

Copyright and related rights waived via CC0.
