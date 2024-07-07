```
IIP: 32
Title: A new NFT based staking buckets
Author: Coder Zhi (@CoderZhi)
Discussions-to: <URL>
Status: WIP
Type: Standards Track
Category Core
Created: 2024-06-01
```

## Abstract
This IIP proposes a new system staking contract, which is an ERC721 contract. Each bucket will be represented as an NFT token and the buckets created in the new contract are of the same features as the native staking buckets. It will overcome the limitations of the current native staking protocol and enable the seamless integration of various DeFi projects, enhancing liquidity and flexibility for investors.

## Motivation
The most commonly used buckets in IoTeX blockchain are native staking buckets. The native staking buckets are restricted in terms of tradability, as the native protocol does not support very complicated operations. This limitation reduces liquidity and restricts the potential use cases of staked assets in the DeFi ecosystem.

Different from the previous version of system staking contract, in which investors could only choose some specific staking amounts and durations, this version allows investors to create buckets of any amount and any duration. We are able to implement a very straightforward migration from the native staking buckets to the new NFT based buckets. 

The new staking contract will:
* Improve accessibility: The ability to trade staking buckets lowers the entry barriers for new investors and allows for more efficient capital allocation within the ecosystem.
* Enhance liquidity: By making staking buckets tradable, investors can easily buy, sell, and transfer their staked assets, increasing overall market liquidity.
* Increase flexibility: NFT-based staking buckets can be used as collateral, integrated into DeFi platforms, and utilized in various financial products, providing greater flexibility and opportunities for investors.

## Specification
The proposed smart contract will include the following key components:

1. Bucket creation
When an investor stakes their coins, a corresponding NFT will be minted, representing the staked amount and duration. Similar to the native buckets, the staked amount should be larger than 100 IOTX and the maximum duration is 3 years.

2. Bucket modification
Investors could transfer the ownership, lock/unlock the staking duration, expand a bucket by increasing staked amount and/or duration, merge multiple buckets into one, and unstake/withdraw buckets.

3. Staking rewards
Staking rewards will continue to accrue to the holder of the NFT, ensuring that the rightful owner receives the benefits. The amount of rewards are the same as native staking buckets.

4. Donation
Bucket owners could donate the staked amount to the beneficiary specified in the contract.

5. Security and Compliance
Audit and Verification: The smart contract will undergo thorough security audits to ensure its robustness and reliability.
Compliance: The system will adhere to relevant regulatory requirements, ensuring that it operates within legal frameworks.

6. Migration
In the native protocol, migration from a native staking bucket to an NFT-based bucket will be supported.


## Backwards Compatibility
The new system staking contract has no conflict with the existing staking system, thus it will be backwards compatible.

## Implementation
The implemenation of this new system staking contract could be found in [github](https://github.com/iotexproject/iip13-contracts/blob/main/src/SystemStaking2.sol).

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).