```
IIP: 28
Title: Transfer Delegate Ownership
Author: Simone Romano (simone@iotex.me), Dustin (dustin.xie@iotex.me), Chen Chen (chenchen@iotex.me)
Status: WIP
Type: Standards Track
Category: Core
Created: 2024-06-01
```

## Abstract

This IIP introduces the "Transfer Delegate Ownership" feature to the IoTeX L1. The feature allows delegate owners to change a delegate's profile address to a new one. This offers several benefits, including the ability to transfer their delegate business to another entity, switch between wallet setups, and improve security by addressing potential account compromises.

## Motivation

The motivation behind this feature is to offer increased flexibility and security to delegate owners of the IoTeX L1. Currently, there is no way to update a delegate's profile address once it is set. This limitation hinders adapting to changing circumstances, such as transferring a delegate to a new owner, switching between wallet setups (e.g., Ledger native app to Metamask), or addressing security concerns from a compromised profile account.

## Overview

The "Transfer Delegate Ownership" feature will allow delegate owners to change the profile address associated with their delegate. This feature will provide the following benefits:
1. Delegate Ownership Transition: Delegate owners can easily transfer entire ownership of their delegate to another entity or individual by updating the profile address.
2. Wallet Setup Flexibility: Delegate owners who initially set up their profiles using specific wallet configurations, such as Ledger + ioPay desktop, can now transition to different setups, such as Metamask, or Metamask+Ledger.
3. Security Enhancement: In cases where a delegate owner suspects their profile address has been compromised, they can promptly change it to mitigate potential risks.

## Specification

The ownership transfer will be implemented by sending a new type of transaction to the IoTeX L1. This will validate the transaction and apply the state change it indicates. For the delegate who intends to transfer ownership, they first construct a message that articulates their intention:

### Delegate ID
We introduce a new field ID as the unique identifier for delegate. It is determined when the node is created (equal to the owner address) and remains unchanged thereafter. The voting address for the stake bucket needs to be set to the ID, rather than the owner.
```
type Delegate {
    Name string
    Owner address.Address
    Operator address.Address
    Rewarding address.Address
    // newly added fields
    ID address.Address
}
```

### Ownership Transfer Transaction
We also introduce a new type of transaction that allows node owners to transfer ownership through this transaction.
```
type transferOwner struct {
    NewOwner address.Address // the new owner address
}
```

### Owner Limitation
- Can only be registered once: Once an address has been registered, it cannot be used as a new owner for other nodes. 
- Can be transferred multiple times: If an address has not been registered, it can be transferred multiple times, but cannot simultaneously be the owner of multiple nodes.

### Self-Stake & Endorsement Inheritance
- If the delegate is self-staked, after transferring ownership, the self-staked bucket will then convert to a regular bucket, and the delegate will no longer be self-staked. 
- If the delegate is endorsed, the endorsement remains valid after the ownership transferred.

### Votes counting
Initially, we used the delegate's owner as the voting address, but now we have switched to using the ID as the voting address. This change maintains compatibility as the default value of ID is the owner. The reasons for this can be explained in the following two scenarios: 
- For existing nodes and stake buckets, this change does not affect the votes counting because the ID defaults to being equal to the owner address. 
- For nodes that have transferred ownership, since the ID remains unchanged and still equals the old owner, all previous bucket voting remains accurate.

## Rationale

### Difference between ID and Owner
- The ID serves as the unique identifier for the delegate, it will never change, and is used to as identification of bucket voting. (This replaces the role previously held by the owner)
- Owner now only denotes ownership, meaning only the owner has authority over delegate-related operations. It is modifiable.

### Why cann't the owner register multiple times although ownership transferred?
This is to prevent user confusion. If allowing the same owner to re-register after a transfer, it could lead to a situation where the owner of one delegate is the ID of another delegate node, causing users to be confused about which delegate they are voting for.

### Impact
The introduction of the "Transfer Delegate Ownership" feature will have a positive impact on the IoTeX community. It will empower delegate owners with greater control and flexibility over their delegate profiles, potentially encourage more participation in the network, and enhance the overall security of delegate operations.

## Backwards Compatibility
We ensure backward compatibility at the protocol level by setting the default value of the delegate ID to be equal to the owner address.

## Security Considerations
There is no security concern.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
