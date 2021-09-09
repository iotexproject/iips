```
IIP: 12
Title: Support staking action in Web3
Author: Haixiang Liu(), Dustin Xie (dustin.xie@iotex.io)
Status: Draft
Type: Standards Track
Category: Core
Created: 2021-08-23
```

## Abstract

TBD

## Motivation

During the growth of eco-system of IoTeX, the demand for supporting staking action via Web3 is increasing. However, the nature of native ethereum transaction is incompatible with our staking action transaction. This is because the data struction of native ethereum transaction only contains six data fields(`AccountNonce`, `Price`, `GasLimit`, `Recipient`, `Amount`, `Payload`)(https://github.com/ethereum/go-ethereum/blob/release/1.9/core/types/transaction.go), whereas our staking actions includes some extra data field. So it is hard to wrap our staking action into native ethereum transaction when transmitting the transaction via Web3.

## Specification

The discussion will be divided into two part: 

1. How are staking actions sent to IoTeX blockchain via Web3?

2. How are staking actions verified?

### Part I: Transaction Transportation

#### Transaction Creation(Staking action encoding)

To send native staking action via Web3, the staking action is serialized into Protobuf data types, which is packed into `Payload` field of native transaction `tx.payload = Proto.Marshal(stakingAction.Proto())`. To differentiate the special transaction from normal ones, the `Recipient` field is marked with special address. To conclude, the modified transactions of staking actions via Web3 are different from normal transactions(transfer and execution) in three fields:

```
{
Payload : Proto.Marshal(stakingAction.Proto()),
Recipient : (Pre-defined special address),
Amount : 0,
} 
```



#### Transaction Transportation(Staking action decoding)

IoTeX blockchain has its own Web3 API known as `Babel`. When `Babel` receives eth_sendRawTransaction() request, it  uses IoTeX `Antenna`API to process such request, and send the result onto the chain. In the `Antenna`, staking action decoding includes three Steps:

1. Decoding raw transaction data

   The six data fields of native transaction are extracted from the raw transaction

2. Judge whether the recipient address belongs to the special address pool

3. Decoding data field into native staking action

   Construct native staking action by deserializing the data in `Payload` field

   ```js
   // construct a stake create action for example
   const stakeAct = StakeCreate.deserializeBinary(data); 
   sendActionReq.action.core.stakeCreate = {
           candidateName: stakeAct.getCandidatename(),
           stakedAmount: stakeAct.getStakedamount(),
           stakedDuration: stakeAct.getStakedduration(),
           autoStake: stakeAct.getAutostake(),
           payload: stakeAct.getPayload()
   };
   ```


### Part II: Action Verification

When IoTeX delegates received transaction requests, It will use the signature of the action in the request to verify the action. However, the signature of raw tx can't be directly used to verify native staking action.  We reconstruct the native staking action transaction using the same method mentioned in Part I. Then the hash calculated from the generated raw tx can be used to verfify the signature. 

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
