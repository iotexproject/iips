```
  IIP: 2
  Title: Increasing Daily Epoch Reward Amount to 350K IOTX
  Author: Zhijie Shen (zhijie@iotex.io)
  Discussions-To: 
  Status: Draft
  Type: Standards Track
  Created: 2019-06-08
```

## Abstract

When IoTeX MainNet was launched, only 12 out of 36 delegates came from the community, while the remaining ones are the
bots. Now the number of real delegates have grown to 18, and will grow to 24 very soon. It's reasonable to motivate the
community on operating the network in a further decentralized way, so that we propose to raise the epoch reward amount
from 300K IOTX per day (24 epochs) to 350K.

## Implementation

The per epoch epoch reward is 12,500 defined in the genesis config now. The number will be adjusted to 14,500, which
will make it 348,000 totally for every 24 epochs. A new block height needs to be defined, from which the new epoch
reward number will be used.

## Timeline

The epoch reward amount adjustment will be rolled out with v0.7.x. The exact date is still TBD.

## Voting Process

We will collect the opinion from the community to decide if we want to increase the epoch reward amount. As the on-chain voting is not ready yet, we will vote in the discord channel: https://discord.gg/NxMKT5A. The voting process is defined here: https://docs.google.com/document/d/1qAcZtNeX6vadLTXp6k1CEADVJwNv7BMZQrtQSLhgpqQ/edit.

## Changelog

2019-06-08: Created the issue
2019-06-10: Added the details
2019-06-17: Added the voting details
