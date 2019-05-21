```
  IIP: 1
  Title: Improving slashing policy enforced on underperforming delegates
  Author: Zhijie Shen (zhijie@iotex.io)
  Status: Draft
  Type: Standards Track
  Created: 2019-05-20
```

## Abstract

Currently, a delegate will lose all the epoch reward for the epoch where it misses 85% productivity threshold. We
propose to replace this slashing policy with excluding the delegate for the next 3 epochs' block production and all
kinds of reward to reduce the impact on IoTeX's quality of service (QoS) and motivate delegates to provide robust
infrastructure.

## Motivation

Sometimes we saw some delegate nodes were in unhealthy status (e.g., block height is no longer growing), so that it
can't produce blocks if they are chosen as active consensus delegates in a certain epoch. This prolongs the confirmation
latency for those transactions sent during the time slot of unhealthy delegates' block proposal rounds. Moreover, the
unhealthy nodes would take more than one epoch's time to recover due to communication delay, diagnostics process and etc.

Meanwhile, we have quite a few other good delegate nodes in the pool, which is ready to produce blocks but just doesn't
have enough votes yet.

Given the observations above, we are looking for the good mechanism to improve IoTeX's QoS as well as motivate delegates
to provide robust infrastructure.

## Approach

We propose to achieve this by using a new slashing policy. When a delegate misses 85% productivity threshold (aka misses
3+ out of 15 blocks), it will 1) be excluded from the consensus delegate pool for the next 3 epochs and 2) it will miss
all kinds of rewards during this 3 epochs.
 
Alternatively, the `X+1`-th delegate, where `X` is the number of consensus delegates, will be moved into consensus
delegate pool, and have the change to be rolled as the active consensus delegate.

Note that we have an existing slashing policy, which is skipping the epoch reward for the current epoch where 85%
productivity threshold is missed. This policy will be removed once the new policy is enabled to keep the policy concise.

By doing this, we could make that 1) IoTeX QoS could be less impacted while a delegate is repairing the node, and 2) the
resource of the standby delegates could be leveraged.

Last but not least, we propose 3 epochs because it seems to a reasonably enough time for a responsive delegate to
recover the node. However, this number could be debatable.

## Implementation

It needs to change [iotex-core](https://github.com/iotexproject/iotex-core/) to implement the new policy:

- At the end of each epoch, a new productivity summary action should be processed so that all delegates should reach the
consensus on the final productivity in the current epoch, and the productivity metrics will be written into the state DB.

- When polling the consensus delegates for `X`-th epoch, check the productivity from `X-3`-th to `X-1`-th epochs. If a
delegate misses the productivity threshold in anyone of these epochs, it will be remove from the list.

- The current slashing policy implemented in the rewarding protocol needs to be removed.

This is protocol level change, so that it will result in a hard fork.

In addition to the protocol level change, we may also need to:

- Provide API for delegates to check if they are slashed for some epochs;

- Reflect the slashing results on the member portal so that the voters could be notified. 

## Changelog

2019-05-20: Drafted the proposal of new productivity slashing policy