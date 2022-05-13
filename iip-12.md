```
IIP: 12
Title: Support staking action via Web3
Author: Haixiang Liu(haixiang@iotex.io), Dustin Xie (dustin.xie@iotex.io)
Status: Draft
Type: Standards Track
Category: Core
Created: 2021-08-23
```

## Abstract

TBD

## Motivation

With the growth of eco-system of IoTeX, the demands for staking via Web3 is increasing. Currently, staking-related features are avilable in IoTeX `Antenna` API, which sends native staking actions to the API nodes via gRPC protocol. However, transaction transmission via JRPC(ethereum-based) is incompatible with our staking transaction transmission via gRPC. This is because the data structure of native ethereum transaction only contains six data fields(`AccountNonce`, `Price`, `GasLimit`, `Recipient`, `Amount`, `Payload`), whereas our staking actions includes some extra data fields(e.g. `staking candidate`, `staking amount`, etc.). So it is hard to send our native staking action directly via Web3.

## Specification

The discussion will be divided into two part: 

1. How are staking actions sent to IoTeX blockchain via Web3?

2. How are staking actions via Web3 verified?

### Part I: Transaction Transportation

#### Transaction Creation(Staking action encoding)

To send native staking action via Web3, RLP encoding is used for serializing the staking action into binary data, which is packed into `Payload` field of native transaction `tx.payload = ABI.Pack(stakingAction)`. To differentiate the special staking transaction from normal ethereum transaction, the special `Recipient` address `0x04C22AfaE6a03438b8FED74cb1Cf441168DF3F12` is reserved for this special treatment. To conclude, the modified transactions from staking actions via Web3 are different in three fields:

```
{
Payload : ABI.Pack(stakingAction),
Recipient : "0x04C22AfaE6a03438b8FED74cb1Cf441168DF3F12",
Amount : 0,
} 
```



#### Transaction Transportation(Staking action decoding)

IoTeX blockchain has its own Web3 API service known as `Babel`. When `Babel` receives the web3 staking action via `eth_sendRawTransaction` method, it will translate the staking action in three steps:

1. Decoding raw transaction data

   The six data fields of native transaction are extracted from the raw transaction

2. Check whether the recipient address is the special staking address `0x04C22AfaE6a03438b8FED74cb1Cf441168DF3F12`

3. Reconstruct native staking action by deserializing the data in `Payload` field with pre-defined `ABI`


   ```js
   // Example (pseudocode)
   // reconstruct a stake create action for binary data
   data := ABI.Unpack(rawData); 
   CreateStake := CreateStake{
           candidateName: data["candName"],
           stakedAmount: data["amount"],
           stakedDuration: data["duration"],
           autoStake: data["autoStake"],
           payload: data["data"],
   };
   ```

4. Send generated native staking action to the p2p network.

### Part II: Action Verification

When IoTeX delegates receive the special staking action, It will use the signature in the action for verification. However, the hash of native action can't be directly used to verify the signature of raw tx. The staking action has to be encoded into ethereum transaction using the same method mentioned in Part I. Then the hash calculated from the generated raw tx can be used to verfify the signature. 

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
