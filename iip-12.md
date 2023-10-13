```
IIP: 12
Title: Support staking transactions via JSON-RPC
Author: Haixiang Liu(haixiang@iotex.io), Dustin Xie (dustin.xie@iotex.io)
Status: Final
Type: Standards Track
Category: Core
Created: 2022-05-25
```

## Abstract

This proposal explains the mechanism of supporting staking transactions via JSON-RPC 

## Motivation

With the growth of eco-system of IoTeX, the demand for staking via `Ethereum-compatible way` is increasing, so we decided to support it in `web3.js` for our API node. Currently, staking-related features are only available in IoTeX `Antenna` SDK, who sends native staking transactions to the API nodes via gRPC protocol. However, transaction transmission via JRPC(ethereum-based) is incompatible with our staking transaction transmission via gRPC. This is because the data structure of native ethereum transaction only contains six data fields(`AccountNonce`, `Price`, `GasLimit`, `Recipient`, `Amount`, `Payload`), whereas our staking transactions include some extra data fields(e.g. `staking candidate`, `staking amount`, etc.). So it is hard to send our native staking transactions directly via JSON-RPC.

## Specification

The discussion will be divided into two parts: 

1. How are staking transactions sent to IoTeX blockchain via JSON-RPC?

2. How are staking transactions via JSON-RPC verified?

### Part I: Transaction Transmission

#### Transaction Creation (Encode Staking Transaction)

To send native staking transactions via JSON-RPC, RLP encoding is used for serializing staking transactions into binary data, which is packed into `Payload` field of native transaction `tx.payload = ABI.Pack(stakingAction)`. To differentiate special staking transactions from normal ethereum transactions, the special `Recipient` address `0x04C22AfaE6a03438b8FED74cb1Cf441168DF3F12` is reserved for this special treatment. To conclude, the modified transactions from staking transactions via JSON-RPC are different in three fields:

```
{
Payload : ABI.Pack(stakingAction),
Recipient : "0x04C22AfaE6a03438b8FED74cb1Cf441168DF3F12",
Amount : 0,
} 
```



#### Transaction Forwarding (Decode Staking Transaction)

IoTeX blockchain has its own JSON-RPC API service. When staking transactions are sent via `eth_sendRawTransaction` method, the API service will translate staking transactions in three steps:

1. Decoding raw transaction data

   The six data fields of the native transaction are extracted from the raw transaction

2. Check whether the recipient address is the special staking address `0x04C22AfaE6a03438b8FED74cb1Cf441168DF3F12`

3. Reconstruct native staking transactions by deserializing the data in `Payload` field with pre-defined `ABI`


   ```js
   // Example (pseudocode)
   // reconstruct a stake create transaction for binary data
   data := ABI.Unpack(rawData); 
   CreateStake := CreateStake{
           candidateName: data["candName"],
           stakedAmount: data["amount"],
           stakedDuration: data["duration"],
           autoStake: data["autoStake"],
           payload: data["data"],
   };
   ```

4. Send generated native staking transactions to the p2p network.

### Part II: Transaction Verification

When IoTeX delegates receive the special staking transaction, It will use the signature in the transaction for verification. However, the hash of the staking transaction can't be directly used to verify the signature of the raw transaction. The staking transaction has to be encoded into the ethereum transaction using the same method mentioned in Part I. Then the hash calculated from the generated raw transaction can be used to verify the signature. 

## Reference Implementation

Since the `Recipient` address `0x04C22AfaE6a03438b8FED74cb1Cf441168DF3F12` is a virtual contract address, native staking actions aren’t supported when interacting from other contracts. However, Ethereum-compatible transactions to API nodes from clients can be translated into native staking actions under this proposal.

Fristly, virtual contract setup:

```jsx

const ethers = require('ethers');

// The Contract interface
const abi = require("./iip-12-abi.json");

// Connect to the network
const provider = new ethers.JsonRpcProvider('https://babel-api.mainnet.iotex.io');

// The virtual contract address for native staking
let contractAddress = "0x04c22afae6a03438b8fed74cb1cf441168df3f12";

// A Signer from a private key
let privateKey = '';
let wallet = new ethers.Wallet(privateKey, provider);

// Contract Setup
let contract = new ethers.Contract(contractAddress, abi, provider);
```

A list of examples to stake natively:

- Creating a native staking bucket

```jsx

async function createStake() {
    let tx = await contract.createStake(
      "",  // Candidate's Name
      BigInt("100000000000000000000"),  // Stake amount:  Minimum 100 IOTX
      100, // Number of days 
      true, // Autostake
      [] // null
    );
    console.log(tx.hash);
}

createStake();
```

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).

## Appendix

ABI (iip-12-abi.json) is provided under [assets folder](assets/iip-12-abi.json)