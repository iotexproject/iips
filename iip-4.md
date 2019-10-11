```
  IIP: 4
  Title: Lowering the block interval time
  Author: Dustin Xie (dustin.xie@iotex.io)
  Status: Implementing
  Type: Standards Track
  Created: 2019-08-01
```

## Abstract

Currently the IoTeX blockchain is producing a block at every 10 seconds. As a result, the transaction confirmation time lies in the range of 10~20 seconds with an average of 15 seconds. We are doing engineering study to investigate the feasibility to lower the block interval time.

## Implementation

We need to adjust the following things of the blockchain protocol:

- Adjust timing configuration in consensus module;
- Adjust block reward and epoch reward setting to keep the same payout yield;

## Updates

Once we finish the feasibility study, the new block interval time and activation timeline/plan will be announced.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
