```
IIP: 8
Title: Delegated Actions
Author: Raullen Chai (raullen@iotex.io)
Status: Draft
Type: Standards Track
Category: Core
Created: 2020-07-23
```

## Abstract
TBD

## Motivation
In many IoT scenarios, devices usually don't have initial balance in their wallets to initiate actions with IoTeX blockchain. To setup the initial balances on these devices requires extra work and is not scalable (think about one million devices deploying to the field). 

We need a "delegation scheme" to address this problem at the protocol level, meaning all 0-balance accounts can delegate their gas fees to a non-0-balance account if the latter one agrees. This is practical and useful in the IoT sceanrio, e.g., the account of a controller of devices (which could be a person, an app or a device) covers all gas cost for the devices managed.

At a high level, we require the delegation scheme to be flexible (i.e., support innovative ways for delegation) and safe (i.e., support rate-limit policies to protect the malicious consumption of another account's balance).

## Specification
TBD

## Backwards Compatibility
The existent gas model stays the same while the new model is added. Theerefore, there is no backward compatability issue. 

## Test Cases
TBD

## Implementation
TBD

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).

## Reference
- https://www.freecodecamp.org/news/universal-ethereum-delegated-transactions-no-more-ethereum-fees/
