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
   4. pack all into an IoTeX tx (transfer or execution depending on iii) using decoded data + signature in step 1 and 2
   5. send the IoTeX transaction to the corresponding IoTeX blockchain endpoint
   
2. Protobuf support
   1. A new field `uint32 encoding` is added to IoTeX transaction's protobuf definition to identify which network the transaction is targeting
   2. `encoding = 1` indicates the transaction is encoded in RLP format, while `encoding = 0` (default value) is used by IoTeX native transaction  

3. iotex-core support for transaction with `encoding = 1`
   1. decode the transaction, extract (nonce, gas price, gas limit, recipient, amount, payload)
   2. use these + node's external chain ID to reconstruct the raw transaction and compute the corresponding raw hash
   3. verify signature from the transaction against the raw hash
   4. reject the tx if verification fails
   
4. iotex-core support for global external chain ID
   1. at the start-up of an IoTeX node/server, it will need to bind to an external chain ID to indicate which network this node is on. See table below
   2. this global ID is used to compare against `externChainID` in the IoTeX transaction. A transaction with the wrong external chain ID will be rejected.

> External chain ID

| Chain ID | Network | Endpoint |
| --- | --- | --- |
| 4689 | Mainnet | api.iotex.one:443, api.iotex.one:80 |
| 4690 | Testnet | api.testnet.iotex.one:443, api.testnet.iotex.one:80 |

## Replay Attack Immunity
We require that the received raw tx (usually sent by Metamask) must be conforming
to EIP-155 rules, and we registered distinct chain ID for IoTeX mainnet (4689)
and testnet (4690). According to [EIP155](https://github.com/ethereum/EIPs/blob/master/EIPS/eip-155.md#specification),
same tx will have different raw hash values when signing with different chainid.
Hence the proposed solution is immune to replay attack targeted between the IoTeX
and Ethereum blockchain.

If a raw tx does not conform to EIP-155, the corresponding raw hash won't be able
to pass signature verification and the tx will simply be rejected.
 
## Backwards Compatibility
This IIP introduces a new compatible type of on-chain transaction that does not exist before. Hence it is back-compatible with existing data on the chain; no hard-fork is needed. 

## Implementation
- The new proxy service - https://github.com/iotexproject/babel-api 
- iotex-core support - https://github.com/iotexproject/iotex-core/commit/6348f251bcc57b675cc97a660b0c795156be04df
- External chain IDs registreation - https://github.com/ethereum-lists/chains/commit/5f49c91806717479ac72cbbc0fd0028c24c69239

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
