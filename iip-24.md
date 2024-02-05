```
IIP: 25
Title: Raise Block Gas Limit to 50 Million
Author: Dustin Xie (dustin.xie@iotex.io)
Forum discussions: https://community.iotex.io/t/iip-24-raise-block-gas-limit-to-50m/11352
Status: WIP
Type: Standards Track
Category: Core
Created: 2024-01-23
```

## Abstract
This IIP proposes to raise the block gas limit of IoTeX blockchain to 50 million.

## Background
The block gas limit is a crucial parameter for a blockchain network. It represents the maximum amount of gas, a unit of computational effort, that can be consumed in a single block. Gas is used to measure and allocate resources like computation and storage on the network. The block gas limit serves as a mechanism to control the overall capacity of a block, preventing it from becoming too large and ensuring the network's stability.

Block gas limit directly impacts the blockchain's scalability and throughput. A higher gas limit allows more transactions and smart contract computations to be included in a single block, enhancing the network's throughput. However, setting the limit too high may lead to slower block time (too many txs in a block) and potential network congestion. Conversely, a lower gas limit can result in fewer transactions in each block and wasting the blockchain's capacity to handle a larger volume of transactions. Therefore, striking a balance in setting the block gas limit is crucial for maintaining a well-functioning and secure blockchain network.

## Motivation
Currently, the IoTeX blockchain's gas limit is at 20 million. Given that the minimum gas for a standard transfer equals 10000, this means that the maximum number of transactions in a block is capped at 2000, which amounts to only 400TPS at 5-second block time.

This TPS is not high enough to sustain use-cases where it is desired to accommodate a large number of transactions in a single block. For instance, periods of increased network activity, such as token sales, DeFi protocols experiencing high demand, special promotion or airdrop, complex smart contract calls requiring more gas to execute, etc. In particular, the recent inscription event has caused a large volume of transactions waiting in line to be executed and included into the IoTeX blockchain. A higher TPS would definitely help alleviate the situation.

In all these scenarios, a higher gas limit is preferred to prevent network congestion and ensures timely execution of large amounts of transactions rushing into the blockchain.

## Specification
The change will be introduced in the upcoming hard-fork. After the hard-fork block number, the block gas limit will be raised to 50 million. And with that, we'll have these new performance specs:
```
Max number of transactions in a block = 5000
Max TPS = 1000
```
During the recent inscription event, our performance monitoring data show that most delegate nodes have a very low CPU and memory usage number of between 5-10% for a regular 8CPU and 16GB memory hardware configuration. So raising block gas limit to 50M would allow us to lift the IoTeX blockchain's processing capability to the next level, while not jeopardizing the entire network's stability.

## Rationale
The change aims to boost the IoTeX network's processing capacity. It will be implemented in the upcoming hard-fork.

## Backwards Compatibility
This feature will be enabled in the upcoming hard-fork, so backward compatibility is maintained.

## Security Considerations
This IIP will elevate the IoTeX network's processing capacity to maximum TPS=1000. As discussed above, that number is well in the reach of most delegate's hardware configuration. The entire network's stability is not affected by introducing this IIP.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).