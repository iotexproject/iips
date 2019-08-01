```
  IIP: 3
  Title: Removing the per action gas limit
  Author: Zhijie Shen (zhijie@iotex.io)
  Status: Final
  Type: Standards Track
  Created: 2019-06-17
```

## Abstract

Currently every action on IoTeX blockchain cannot consume more than 5 million gas. Even if user specifies the gas limit
to a number greater than 5M, it will be capped to 5M by the system. This prevents developers from deploying some big
contracts. Therefore, we propose to remove this per action gas limit, and let the action consume as much gas as possible
until the block gas limit (20M now) is hit, as long as the action executor has enough IOTX for the gas fee.

## Rationales

There are following rationales behind this proposal:

- When launching the mainnet, the per action gas limit is introduced to prevent the risk of a big action overwhelming
the block processing. After about 2 months running production, monitoring and testing, the blockchain platform turns
out to be mature enough to execute big actions. As long as, the executor has enough IOTX for the gas fee, the action
should be allowed to consume the whole block gas capacity.

- Ethereum's current block gas limit is 8M, and it doesn't have per transaction gas limit cap. Therefore, there are smart
contracts that are deployable on Ethereum, but not IoTeX yet. Making per action gas limit go beyond 8M will avoid the
potential gas risk of migrating Ethereum dapps onto IoTeX.

- Moreover, after removing the per action gas limit, the action can consume as much as 20M gas. It will even enable
developers to deploy the contracts that are not deployable on Ethereum.

## Implementation

We need to adjust the following things of the blockchain protocol:

- Remove the per action gas limit from action execution context;
- Remove the logic of capping action gas limit to the per action gas limit;
- Define the read gas limit config, and replace the per action gas limit with it when restricting a state/contract read
API call.

Note that the read gas limit is a node/system config, which could vary from node to node.

Note that the per action gas limit can't be removed from the genesis for the backward compatibility.

## Updates

The per action gas limit is removed in the release `v0.7.2`, and will be activated from block 864,001.

The per action gas limit removal was activated on 2019-07-31.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
