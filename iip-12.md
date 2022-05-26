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

With the growth of eco-system of IoTeX, the demand for staking via JSON-RPC is increasing. Currently, staking-related features are only available in IoTeX `Antenna` SDK, who sends native staking transactions to the API nodes via gRPC protocol. However, transaction transmission via JRPC(ethereum-based) is incompatible with our staking transaction transmission via gRPC. This is because the data structure of native ethereum transaction only contains six data fields(`AccountNonce`, `Price`, `GasLimit`, `Recipient`, `Amount`, `Payload`), whereas our staking transactions include some extra data fields(e.g. `staking candidate`, `staking amount`, etc.). So it is hard to send our native staking transactions directly via JSON-RPC.

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

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).

## Appendix


`Web3Staking.abi`
```
[
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "operatorAddress",
				"type": "address"
			},
			{
				"internalType": "address",
				"name": "rewardAddress",
				"type": "address"
			},
			{
				"internalType": "address",
				"name": "ownerAddress",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			},
			{
				"internalType": "uint32",
				"name": "duration",
				"type": "uint32"
			},
			{
				"internalType": "bool",
				"name": "autoStake",
				"type": "bool"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "candidateRegister",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "operatorAddress",
				"type": "address"
			},
			{
				"internalType": "address",
				"name": "rewardAddress",
				"type": "address"
			}
		],
		"name": "candidateUpdate",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "candName",
				"type": "string"
			},
			{
				"internalType": "uint64",
				"name": "bucketIndex",
				"type": "uint64"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "changeCandidate",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "candName",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			},
			{
				"internalType": "uint32",
				"name": "duration",
				"type": "uint32"
			},
			{
				"internalType": "bool",
				"name": "autoStake",
				"type": "bool"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "createStake",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint64",
				"name": "bucketIndex",
				"type": "uint64"
			},
			{
				"internalType": "uint256",
				"name": "amount",
				"type": "uint256"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "depositToStake",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint64",
				"name": "bucketIndex",
				"type": "uint64"
			},
			{
				"internalType": "uint32",
				"name": "duration",
				"type": "uint32"
			},
			{
				"internalType": "bool",
				"name": "autoStake",
				"type": "bool"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "restake",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "voterAddress",
				"type": "address"
			},
			{
				"internalType": "uint64",
				"name": "bucketIndex",
				"type": "uint64"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "transferStake",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint64",
				"name": "bucketIndex",
				"type": "uint64"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "unstake",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint64",
				"name": "bucketIndex",
				"type": "uint64"
			},
			{
				"internalType": "uint8[]",
				"name": "data",
				"type": "uint8[]"
			}
		],
		"name": "withdrawStake",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	}
]
```
