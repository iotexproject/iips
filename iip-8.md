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
In many IoT scenarios, devices usually don't have initial balance in their wallets to initiate actions with IoTeX blockchain. To set up the initial balances on these devices requires extra work and is not scalable (think about one million devices deploying to the field). This pain point applies to human beings who want to interact with the blockchain/DAO.

We need some kind of "delegation" to address this problem at the protocol level, i.e., all 0-balance accounts can delegate their gas fees to a non-0-balance account if the latter agrees. This is practical and useful in many scenarios, e.g., the account of a controller of devices (which could be a person, an app, or a device) covers all gas costs for the devices managed.

At a high level, we require the delegation scheme to be **flexible** (i.e., support different delegation policies) and **safe** (i.e., rate-limit and revoke to mitigate the malicious consumption of another account's balance). 

## Specification
Since all transactions within the IoTeX network is termed as `Actions`, we call such a delegate `Delegated Actions`, and we call regular actions `Normal Actions`. Note that `delegate` here should not be confused with a delegate in the context of Roll-DPoS.

At a high level, there are three key differences for a delegated action, comparing to a normal action:
- Bind: a delegate agrees to cover a delegatee's transaction cost  
- Consume: when a delegatee initiate an action, the protocol charges its delegate for the gas fee; if the delegate has not enough balance, the action fails
- Unbind: a delegate terminates the contract for covering the delegatee's transaction cost

### Bind
Delegate initiates an action (bearing with a policy) to notify the protocol its willingness to cover the gas cost for certain delegatee addresses. The policy at least specifis the following:
```
- Delegatee address or adresses
- Number of actions
- Total gas consumed in IOTX
- Start at block height
- End at block height
- Whitelist/blacklist, e.g., delegatee can/cannot initiate action with certain addresses
- Rate limit, e.g., delegatee can consume at most X IOTX in Y blocks.
```

### Consume


### Unbind


## Backwards Compatibility
- The existent gas model stays the same while the new model is added. Therefore, there is no backward compatibility issue. 
- May not even require a custom UI/tools if standardized

## Test Cases
TBD

## Implementation
No implementation yet.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).

## Reference
- https://www.freecodecamp.org/news/universal-ethereum-delegated-transactions-no-more-ethereum-fees/
- https://www.cs.princeton.edu/~arvindn/publications/mining_CCS.pdf
