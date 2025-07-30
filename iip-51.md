```
IIP: 51
Title: Switch Consensus Voting from Delegate Count to Voting Power
Author: Seedlet <zhi@iotex.io>
Discussions-to: TBD
Status: Draft
Type: Core
Category: Core
Created: 2025-07-24
```

## Simple Summary
This proposal changes IoTeX's consensus logic from a simple majority of delegates to a majority based on total voting power". This shift ensures that governance outcomes reflect actual stake-weighted consensus and improves the representiveness and security of IoTeX.

## Abstract
Currently, consensus on the IoTeX blockchain is determined by the NUMBER of supporting delegates, regardless of their individual voting powers. This can allow low-stake delegate to control consensus and underrepreseting high-voting-power delegates. It leads to governance decisions that do not reflect the true economic stake of the community. This proposal replaces the delegate-count-based majority with a stake-weighted rule: consensus will require support from delegates representing more than two-thirds of the total voting power. This change enhances fairness, improves security, and incentivizes greater voter engagement.

## Specification
In each epoch, N delegates are randomly selected from the top T candidates by voting power. Under the current consensus algorithm, more than 2/3 * N delegates must sign off to finalize a block. In the current protocol, T is set to 36, and N is set to 24.

With this proposal, consensus will instead require that the sum of voting power from the supporting delegates exceeds 2/3 of the total voting power of the selected N delegates. Block rewards and epoch rewards will remain unchanged.

## Rationale
The current delegate-count rule enables adversarial behavior such as bribing many low-power delegates to approve a block which potentially leads to attacks.

By switching to stake-weighted consensus, the system better aligns incentives, improves resistance to collusion, and reflects the true will of voters.

## Backwards Compatibility
This is a consensus-level change. It is not backwards compatible and will require a hardfork upgrade.

## Test Cases
| Voting Power       | Delegate Count        | Consensus Reached |
|--------------------|-----------------------|-------------------|
| Sufficient (> 2/3) | Sufficient (> 2/3 N)   | ✅ Yes             |
| Sufficient         | Insufficient          | ✅ Yes             |
| Insufficient       | Sufficient            | ❌ No              |
| Insufficient       | Insufficient          | ❌ No              |

Simulation tests on testnet will cover cases with various voting power and delegate participation combinations.

Only cases where the voting power exceeds two thirds of the total voting power among N selected delegates will result in successful consensus.

Additionally, performance tests will be conducted to ensure that replacing delegate-count-based consensus with voting-power-weighted consensus does not degrade:
- block finality time
- overall consensus responsiveness

## Implementation
This change will require modifications to the consensus module and validator vote-counting logic. We also recommend updating frontend and explorer interfaces to display voting power per block, enabling more transparent validation of consensus decisions.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).