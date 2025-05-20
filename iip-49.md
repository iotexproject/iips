# IIP-49: Enhancing Block Rewards Allocation with EIP-1559 Priority Fees

**Title:** Enhancing Block Rewards Allocation with EIP-1559 Priority Fees  
**Author:** Dustin Xie  
**Last update:** 2025/4/3  
**Discussion Link:** TBD  
**Github Link:** TBD

---

## Abstract

Starting from IoTeX v2.1.0, the blockchain has integrated EIP-1559 transactions, introducing priority fees that are awarded to block producers. Currently, block producers receive a fixed block reward of 8 IOTX plus any additional priority fees included in transactions.

To improve the sustainability of the rewarding pool, this proposal modifies block reward allocation by incorporating priority fees into the fixed 8 IOTX reward mechanism. Specifically:

1. If the total priority fee is below 8 IOTX, the rewarding pool contributes the difference (8 - priority fee) to maintain an 8 IOTX total block reward.
2. If the priority fee exceeds 8 IOTX, the rewarding pool does not contribute more, and the block producer receives the full priority fee amount.

This ensures that higher network activity reduces reliance on the rewarding pool, slowing its depletion over time.

---

## Motivation

The IoTeX blockchain currently distributes a fixed 8 IOTX per block from the rewarding pool, regardless of network activity. However, the integration of EIP-1559 priority fees in recent v2.1.0 hard-fork introduces an opportunity to adjust block rewards dynamically, reducing unnecessary token emissions.

By using priority fees as part of the block reward, we achieve the following benefits:

- Extend the lifespan of the rewarding pool by reducing the amount withdrawn per block when network activity is high.
- Encourage validator participation by ensuring block producers receive fair compensation, especially during periods of high transaction volume.
- Maintain network security by preserving an incentive structure that rewards active validators.

---

## Specification

### Current Block Reward Mechanism

- Block producers receive a fixed 8 IOTX reward from the rewarding pool.
- Priority fees from EIP-1559 transactions are added on top of this fixed reward.
- No adjustments are made based on network activity.

### Proposed Block Reward Mechanism

1. Total block reward remains capped at 8 IOTX, unless the priority fee exceeds 8 IOTX.
2. If the priority fee is below 8 IOTX, the rewarding pool contributes the difference (8 - priority fee) to make a total of 8 IOTX block reward.
3. If the priority fee is 8 IOTX or more, the rewarding pool does not contribute more, and the block producer receives the full priority fee amount instead.

### Example Scenarios

| Priority Fee (IOTX) | Rewarding Pool Contribution (IOTX) | Total Block Reward (IOTX) | Notes                                   |
|---------------------|-------------------------------------|----------------------------|-----------------------------------------|
| 0                   | 8                                   | 8                          | Full reward from pool                   |
| 3                   | 5                                   | 8                          | Partial priority fee + pool top-up      |
| 7.5                 | 0.5                                 | 8                          | Minimal pool contribution               |
| 8                   | 0                                   | 8                          | All reward from priority fee            |
| 10                  | 0                                   | 10                         | Priority fee exceeds 8, no pool needed  |

---

## Rationale

- **Sustainability:** The rewarding pool depletes at a slower rate, ensuring long-term economic viability.
- **Fair Compensation:** Block producers receive the same minimum reward (8 IOTX), but can earn more when network activity is high.
- **Scalability:** As more transactions generate priority fees, the need for direct token emissions decreases.

---

## Implementation

This will be implemented as a hard-fork, with changes activated at the next hard-fork height:

- Modify the block reward calculation logic to adjust the rewarding pool allocation dynamically based on priority fees.
- Update IoTeX consensus nodes to enforce the new reward distribution model.
- Ensure backward compatibility with existing reward structures for a smooth transition.

---

## Backward Compatibility

This proposal does not affect existing transactions or smart contracts. It solely modifies how block rewards are allocated starting at the next hard-fork height, ensuring backward-compatible integration into the current IoTeX economic model.

---

## Security Considerations

- The proposal does not introduce new attack vectors or affect existing consensus mechanisms.
- Block producers continue to receive fair rewards, maintaining network security.
- As a result of this change, the rewarding pool will be depleting at a slower rate, ensuring long-term economic sustainability.

---

## Conclusion

By incorporating priority fees into block rewards, this proposal enhances IoTeX’s economic sustainability while maintaining strong incentives for block producers. The rewarding pool depletes at a slower rate, allowing IoTeX to sustain validator rewards for a longer period, even as transaction volume grows.
