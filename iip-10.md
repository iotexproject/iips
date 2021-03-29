```
IIP: 10
Title: Enable IoTeX blockchain to process transaction sent in web3js format
Author: Dustin Xie (dustin.xie@iotex.io)
Status: WIP
Type: Standards Track
Created: 2021-03-29
```

## Abstract
This document proposed a method to enable IoTeX blockchain process transaction sent in web3js format

## Motivation
TDB

## Specification
4 components are required to make this feature work:

1. A relayer service to receive raw transaction and translate it to IoTeX transaction, and broadcast to IoTeX blockchain endpoint. Upon receiving a raw transaction, the relayer performs the following tasks:
   1. decode the raw transaction, extract (nonce, gas price, gas limit, recipient, amount, payload)
   2. also extract the signature from transaction
   3. call IoTeX endpoint API to determine if the recipient is a regular address or contract
   4. pack an IoTeX transaction (transfer or execution depending on 3) using decoded data + signature in step 1 and 2
   5. also set the corresponding external chain ID in the transaction (see table below)
   6. send the IoTeX transaction to corresponding IoTeX blockchain endpoint
   
2. Protobuf support
   1. A new field `uint32 externChainID` is added to IoTeX transaction's protobuf definition to identify which network the transaction is targeting

3. iotex-core support for transaction with `externChainID`
   1. upon receiving transfer and execution transaction, if the `externChainID` field equals the network's external chain ID, do following additional checks:
   2. decode the transaction, extract (nonce, gas price, gas limit, recipient, amount, payload)
   3. use these to reconstruct the raw transaction, and compute the corresponding raw hash
   4. extract signature bytes from the transaction, and compute the signed hash
   
4. iotex-core support for global external chain ID
   1. at the start-up of an IoTeX node/server, it will need to bind to an external chain ID to indicate which network this node is on. See table below
   2. this global ID is used to compare against `externChainID` in the IoTeX transaction. A transaction with wrong ID will be rejected

> External chain ID

| Chain ID | Network | Endpoint |
| --- | --- | --- |
| 4689 | Mainnet | api.iotex.one:443, api.iotex.one:80 |
| 4690 | Testnet | api.testnet.iotex.one:443, api.testnet.iotex.one:80 |
 
## Backwards Compatibility
This IIP introduces a new compatible type of transaction that does not exist before on the chain. Hence it is back-compatible with existing data on the chain, no hard-fork is needed to activate this. 

## Implementation
iotex-core support is enabled in [TBD](https://github.com/iotexproject/iotex-core/commits/master/)

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
