```
IIP: 6
Title: Exclude delegate nodes with lower-than-expected chain version
Author: Zhi (@CoderZhi)
Status: Draft
Type: Standard Track
Category: Core
Created: 2019-10-31
```

## Simple Summary
Delegate nodes, with a lower-than-expected chain version, may cause empty consensus rounds (productivity issue) or even stuck the whole chain. This IIP will address this problem and improve the productivity and the stability of IoTeX blockchain.

## Abstract
If a delegate node does not adopt a mandatory upgrade, the node will not be able to contribute in the future consensus. As a result, the corresponding proposal round of the delegate node will not produce any valid block. The current poll protocol expects voters to downvote this kind of delegate nodes to exclude them in follow up epochs. However, the productivity of IoTeX blockchain has been hurt if it happens.

It could be even worse if 1/3 or more delegates fail to adopt mandatory upgrades, that the whole chain will get stuck according to the consensus strategy we are using now. Nothing we can do, as what happened in https://github.com/iotexproject/iotex-bootstrap/blob/master/postmortem/2019-10-30.md, but waiting for these delegate nodes to upgrade themselves.

## Motivation
The problem can be concurred by enforcing all delegate nodes to be up-to-date, however, the communication cost could be very high for a decentralized system like us. To prevent similar problems, we are proposing a new delegate election strategy to exclude delegate nodes who fail to adopt a mandatory upgrade. With this new strategy, these delegate nodes will be replaced by qualified backup delegate nodes until they adopt all mandatory upgrades.

## Specification
A system level contract will be deployed onto IoTeX blockchain to register the chain versions of all delegate nodes. When starting a blockchain node, a version checking will be performed to update the version registered in the contract if necessary. In poll protocol, a delegate node will be filtered if its chain version registered in the contract is lower than expected, which means it has not adopted the latest version of mandatory upgrade.

## Backwards Compatibility
This IIP will be a mandatory upgrade, so the backwards compatibility is not a concern.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).