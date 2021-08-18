```
IIP: 11
Title: Prevent replay attack by enabling chainID in IoTeX transaction
Author: Dustin Xie (dustin.xie@iotex.io)
Status: WIP
Type: Standards Track
Created: 2021-08-17
```

## Abstract
This document proposed a solution to prevent replay attack on the IoTeX blockchain

## Proposal
A [`chainID`](https://github.com/iotexproject/iotex-proto/blob/master/proto/types/action.proto#L210) 
field is actually reserved in the IoTeX transaction structure, we could activate
this field to mitigate potential replay attack by:

1. Use a different chain ID for mainnet and testnet when signing transactions
2. Enforce chain ID check at block producing, transaction with chain ID that is
different from target network will be rejected

So far the default `chainID` = 0, this change will take place in 2 phases:
1. A transitional period with a mix of the default and new chain ID, and
transactions with `chainID` = 0 will still be accepted
2. At next hard-fork, chain ID check enforcement is activated. Only those
transactions with new chain ID can be accepted, any transaction that carries
`chainID` = 0 will be rejected
> Chain ID for native transaction

| Chain ID | Network | Endpoint |
| --- | --- | --- |
| 1 | Mainnet | api.iotex.one:443, api.iotex.one:80 |
| 2 | Testnet | api.testnet.iotex.one:443, api.testnet.iotex.one:80 |

## Impact
This change will impact all products and services that involve transaction
processing on our mainnet and testnet, including:
- Product/service that use antenna SDK: ioPay desktop/mobile, mimo/iotube,
hermes, airdrop/drip
- Product/service that integrates IoTeX into their own SDK: trustwallet
- Crytpo exchanges: they might use our antenna or their own SDK, need to 
carefully understand each one's situation
- Other components that I may miss

## Upgrade plan
1. Implement the chain ID in antenna SDK and iotex-core
2. Rollout to testnet, use ioctl to test and verify
3. Start transitional phase:
   1. Rollout to mainnet (with hard-fork disabled)
   2. Notify all impacted products/service/exchange to upgrade to new antenna
   SDK
   3. Verify new transaction does have correct value for chain ID
4. Final enabling
   1. Activate the hard-fork on testnet
   2. Verify transaction process on testnet still working normally when chain
   ID check is enforced
   3. Activate the hard-fork on mainnet

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).