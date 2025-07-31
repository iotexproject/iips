```
IIP: 53
Title: Dynamic Scaling of Consensus Delegates for Decentralization
Author: Seedlet (zhi@iotex.io)
Discussions-to: TBD
Status: Draft
Type: Core
Category: Core
Created: 2025-07-28
Requires: 51, 52
```

## Simple Summary
This proposal enhances IoTeX’s decentralization and security by increasing the number of consensus delegates dynamically based on network participation. It introduces an interval-based scaling rule (in steps of 12), enforces a minimum of 24 consensus delegates, and adds an **exit queue** mechanism to ensure delegate set stability. Simulations will test scalability and P2P traffic resilience.


## Abstract
IoTeX currently selects 24 consensus delegates from the top 36 by voting power. This static model limits scalability. We propose a dynamic mechanism where the number of consensus delegates grows proportionally to the total number of qualified delegates, in **multiples of 12**, capped at **144**.  
A **minimum of 24** consensus delegates is always enforced, and an **exit queue** is added to prevent frequent delegate set churn.
This design builds on IIP-51 and IIP-52 to ensure scalability:
- IIP-51 prevents centralization by aligning consensus power with voting stake.
- IIP-52 reduces block size through BLS signature aggregation.
It enhances decentralization while maintaining PBFT security thresholds and system performance.

## Motivation
This proposal will enhance decentralization by allowing more stakeholders to participate in consensus. It prevents centralization risk by breaking the ceiling of 24 consensus delegates, and improves delegate stability via exit queue logic, reducing volatility and maintaining peer connectivity.

## Specification

### Delegate Scaling
Let:
- `Q` = number of qualified delegates in an epoch
- `C_max` = max number of consensus delegates
- `C_min` = min number of consensus delegates
- `I` = scaling interval
Then:
> `C = min(C_max, max(C_min, ceil(Q * 2 / 3 / I) * I))`

`C_min` is fixed at 24, preserving current consensus security. `C_max` will be gradually increased to 144.
The number of consensus delegates `C` in an epoch adjusts based on the number of qualified delegates `Q`. `C` delegates are randomly selected from the top `Q`, weighted by voting power as consensus delegates.  

### Exit Queue
To maintain stability of the consensus delegate set, an exit queue mechanism will be introduced:
- A delegate wishing to exit consensus must first enter the exit queue.
- Only one delegate may be in the active exit phase at any time.
- Delegates in the queue wait their turn, and are processed in the order they entered the queue.
- A delegate in the queue may voluntarily cancel their request and remove themselves from the queue at any time before entering the active exit phase.
- The exiting delegate must continue participation during a cooldown period of `X` epochs before final removal. `X` will be set to 24, which is one day period.
- Only after the cooldown will the delegate be removed from delegate list.
This mechanism prevents sudden mass exits and ensures gradual, predictable turnover.


## Rationale
- Scaling in **multiples of 12** ensures uniform committee sizes compatible with existing PBFT thresholds.
- Maintaining a **minimum of 24** consensus delegates preserves legacy compatibility and security.
- Exit queue prevents instability and P2P churn.
- Prior proposals (BLS and voting power–based finality) enable seamless scaling without compromising performance or security.

## Backwards Compatibility
This is a consensus-level change and will require a hardfork upgrade.  
The legacy model of fixed 24 consensus delegates will be retired after transition.

## Test Cases

### Consensus Scaling Tests  
To validate the robustness of the consensus protocol under increasing delegate sizes, we will simulate the scaling of qualified delegates in controlled testnet environments. These simulations will observe:
- Effects on consensus finality time.
- Block propagation and orphan rate.
- Overall system performance and stability.
Simulations will incrementally increase the number of qualified delegates and monitor system behavior, ensuring readiness before each scheduled C_max increase.

## Implementation
- Implement `C` calculation in consensus component.
- Update consensus delegate selection logic.
- The value of `C_max` will be increased in stages via a series of planned hardforks, eventually reaching 144.
An exit queue mechanism will be added:
- Delegates wishing to exit consensus participation must enter a queue.
- Only one delegate can be in the active exit phase at a time.
- Delegates may cancel their request and remove themselves from the queue before reaching the front.
- Until processed, queued delegates must continue to participate in consensus.
The frontend, ioctl, and explorer will be updated to:
- Display real-time consensus delegate count.
- Show exit queue status.
- Reflect changes in consensus delegate eligibility.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).