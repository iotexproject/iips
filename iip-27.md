```
IIP: 27
Title: Claim Reward for Contract Account
Author: Chen Chen (chenchen@iotex.me)
Status: WIP
Type: Standards Track
Category: Core
Created: 2024-02-01
```

## Abstract
This IIP enables an Externally Owned Account (EOA) to claim rewards for a specified account (EOA or Contract Account) by initiating the "Claim Reward" action.

## Motivation
Currently, the Hermes account is an EOA, and EOAs are susceptible to the risk of private key theft. Many delegates currently entrust their rewards to Hermes, and if the private key of Hermes is compromised, it can have significant consequences.

Transferring all rewards to a Contract Account (CA) eliminates this security risk. Delegates can directly extract their rewards through contract calls. 

However, the current system only supports the rewards claiming for EOA accounts,  through the initiation of transactions of type "ClaimFromRewardingFund." This does not support Contract Accounts, hence the need for this IIP to claim rewards for contract accounts.

## Specification
### Claim Params
Building upon the existing "ClaimFromRewardingFund" action, an "address" field is added to represent the account address where rewards should be claimed to.
```
type ClaimFromRewardingFund struct {
    amount *big.Int
    address string // newly added field
}
```
The specified account can be:
- EOA/CA: Representing the claim of rewards for the specified account.
- Empty: Denoting the claim of rewards for the sender's account, for backward compatibility.

### Procedure
1. Determine the account for reward claim:
  a. If the "address" field is not empty, consider it as the reward account.
  b. Otherwise, consider the transaction sender as the reward account.
2. Verify that the account has a sufficient balance of rewards.
3. Deduct the specified reward balance from the reward pool and transfer it to the reward account.

## Rationale

## Backwards Compatibility
The updated action is backward compatible, and not setting the "address" field will result in the claim of rewards for the sender's account.

## Security Considerations
Post-update, any EOA account is allowed to initiate reward extraction for account A. However, since rewards are only disbursed to A, malicious actors can, at most, affect the timing of others' reward claiming but cannot steal the rewards. This is deemed acceptable.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).