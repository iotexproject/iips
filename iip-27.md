```
IIP: 27
Title: Collaborative Reward Claiming
Author: Chen Chen (chenchen@iotex.me)
Status: WIP
Type: Standards Track
Category: Core
Created: 2024-02-01
```

## Abstract
The Collaborative Reward Claiming Proposal aims to introduce a new method for claiming rewards by allowing proxies to conduct claiming operations on their behalf. This approach enables increased flexibility and convenience in the reward claiming process. 

## Motivation
Currently, due to the limitation of only being able to claim rewards by themself, nodes have to set the reward address to an Externally Owned Account (EOA), leading to potential security risks. By enabling reward address to be set to a contract account, the security of these rewards can be significantly enhanced. Introducing a reward proxy strategy would make it feasible to designate node rewards to contract accounts, providing a more secure option. This advancement not only mitigates security vulnerabilities associated with EOAs but also paves the way for a more robust and secure reward distribution system.

## Specification
### Claim Params
Building upon the existing "ClaimFromRewardingFund" action, an "address" field is added to represent the account address where rewards should be claimed from and to.
```
type ClaimFromRewardingFund struct {
    amount *big.Int
    address string // newly added field
}
```
The new account address can be an:
- EOA/CA: Representing the rewards claiming from and to
- Empty: Denoting account is the transaction sender, for backward compatibility.

### Procedure
1. Determine the account for reward claim:
  1. If the "address" field is not empty, consider it as the reward account.
  2. Otherwise, consider the transaction sender as the reward account.
2. Verify that the account has a sufficient balance of rewards.
3. Deduct the specified reward balance from the reward pool and transfer it to the reward account.

## Rationale

## Backwards Compatibility
The updated action is backward compatible, and not setting the "address" field will result in the claim of rewards for the sender's account.

## Security Considerations
Post-update, any EOA account is allowed to initiate reward extraction for account A. However, since rewards are only disbursed to A, malicious actors can, at most, affect the timing of others' reward claiming but cannot steal the rewards. This is deemed acceptable.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).