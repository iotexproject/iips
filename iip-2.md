```
  IIP: 2
  Title: Increasing Daily Epoch Reward Amount to 450K IOTX
  Author: Zhijie Shen (zhijie@iotex.io)
  Discussions-To: https://discord.gg/NxMKT5A
  Status: Accepted
  Type: Standards Track
  Created: 2019-06-08
```

## Abstract

When IoTeX MainNet was launched, only 12 out of 36 delegates came from the community, while the remaining ones are the
bots. Now the number of real delegates have grown to 36. It's reasonable to motivate the community on operating the network
in a further decentralized way, so that we propose to raise the epoch reward amount from 300K IOTX per day (24 epochs) to 450K.

## Implementation

The per epoch epoch reward is 12,500 defined in the genesis config now. The number will be adjusted to 18,750, which
will make it 450,000 totally for every 24 epochs. A new block height needs to be defined, from which the new epoch
reward number will be used.

## Timeline

The epoch reward amount adjustment will be rolled out with v0.7.2, and the hard fork will happen on 864,001-st block.

## Voting Process

We will collect the opinion from the community to decide if we want to increase the epoch reward amount. As the on-chain voting is not ready yet, we will vote in the discord channel: https://discord.gg/NxMKT5A. The voting process is defined here: https://docs.google.com/document/d/1qAcZtNeX6vadLTXp6k1CEADVJwNv7BMZQrtQSLhgpqQ/edit.

## Update

We originally planed to increase epoch reward to 350K per day, but after discussion, we decided to increase to 450K per day
directly. Another uber proposal vote that propose for this is https://member.iotex.io/polls.

## Changelog

2019-07-19: Update the progress
2019-06-08: Created the issue
2019-06-10: Added the details
2019-06-17: Added the voting details
