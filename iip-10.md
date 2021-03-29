```
IIP: 10
Title: Support Web3.js APIs
Author: Dustin Xie (dustin.xie@iotex.io)
Status: WIP
Type: Standards Track
Created: 2021-03-29
```

## Abstract
This document proposed an improvement for IoTeX blockchain to support Web3.js APIs and integrate seamlessly with standard tools and dapps.

## Motivation
Since its launch, IoTeX blockchain has its definition of APIs known as `Antenna`. As time goes by, we receive more and more requirements to have IoTeX blockchain to support commonly used tools and dapps such as metamask, truffle, remix, subgraph, etc..

## Specification
Four components are required to make this work:

1. A new proxy service that receives raw transaction encoded in RLP, translates it to IoTeX tx format and relays to IoTeX blockchain endpoint. Upon receiving the raw transaction, the proxy performs the following tasks:
   1. decode the raw transaction, extract (nonce, gas price, gas limit, recipient, amount, payload)
   2. extract the signature from the transaction
   3. call IoTeX endpoint API to determine if the recipient is a regular address or contract
   4. pack all into an IoTeX tx (transfer or execution depending on 3) using decoded data + signature in step 1 and 2
   5. set the corresponding external chain ID in the transaction (see table below)
   6. send the IoTeX transaction to the corresponding IoTeX blockchain endpoint
   
2. Protobuf support
   1. A new field `uint32 externChainID` is added to IoTeX transaction's protobuf definition to identify which network the transaction is targeting

3. iotex-core support for transaction with `externChainID`
   1. upon receiving transfer and execution transaction, if the `externChainID` field equals the network's external chain ID, do the following additional checks:
   2. decode the transaction, extract (nonce, gas price, gas limit, recipient, amount, payload)
   3. use these to reconstruct the raw transaction and compute the corresponding the raw hash
   4. extract signature bytes from the transaction, and compute the signed hash
   
4. iotex-core support for global external chain ID
   1. at the start-up of an IoTeX node/server, it will need to bind to an external chain ID to indicate which network this node is on. See table below
   2. this global ID is used to compare against `externChainID` in the IoTeX transaction. A transaction with the wrong external chain ID will be rejected.

> External chain ID

| Chain ID | Network | Endpoint |
| --- | --- | --- |
| 4689 | Mainnet | api.iotex.one:443, api.iotex.one:80 |
| 4690 | Testnet | api.testnet.iotex.one:443, api.testnet.iotex.one:80 |
 
## Backwards Compatibility
This IIP introduces a new compatible type of on-chain transaction that does not exist before. Hence it is back-compatible with existing data on the chain; no hard-fork is needed. 

## Implementation
- The new proxy service - https://github.com/iotexproject/babel-api 
- iotex-core support - https://github.com/iotexproject/iotex-core/pull/2586
- External chain IDs registreation - https://github.com/ethereum-lists/chains/pull/194

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
