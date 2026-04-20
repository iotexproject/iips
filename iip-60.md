```
IIP: 60
Title: Enable Ethereum Pectra Upgrade
Author: ChenChen (chenchen@iotex.me)
Status: Draft
Type: Standards Track
Category: Core
Created: 2026-01-08
```

## Abstract

This proposal introduces support for the Ethereum Pectra upgrade on the IoTeX network. The Pectra upgrade includes several EIPs that enhance the EVM capabilities, improve user experience, and strengthen cryptographic operations. Specifically, this IIP implements EIP-7702 (Set EOA Account Code), EIP-7623 (Increase Calldata Cost), EIP-2935 (Serve Historical Block Hashes from State), and EIP-2537 (Precompile for BLS12-381 Curve Operations).

## Motivation

Maintaining EVM compatibility is crucial for the IoTeX ecosystem. By adopting the Ethereum Pectra upgrade, IoTeX ensures that developers can seamlessly deploy and interact with smart contracts using the latest Ethereum tooling and standards. The key benefits of this upgrade include:

1. **Enhanced Account Abstraction (EIP-7702)**: Allows EOAs to temporarily delegate to smart contract code, enabling batching, gas sponsorship, and privilege de-escalation without requiring users to migrate to smart contract wallets.

2. **Reduced Maximum Block Size (EIP-7623)**: Increases calldata costs for data-heavy transactions, reducing the maximum possible block size and improving network stability.

3. **Extended Block Hash History (EIP-2935)**: Stores historical block hashes in state, providing extended block hash history access (8191 blocks vs. 256 blocks) for applications and rollups. This change ensures compatibility with Ethereum's Pectra upgrade.

4. **Enhanced Cryptographic Capabilities (EIP-2537)**: Adds BLS12-381 curve operations as precompiles, providing 120+ bits of security for pairing-based cryptographic operations such as BLS signature verification.

## Specification

### Implement EIP-7702: Set EOA Account Code

#### Overview
EIP-7702 introduces a new transaction type (`0x04`) that allows EOAs to set code in their account by attaching authorization tuples to the transaction.

#### Parameters
| Parameter | Value |
|-----------|-------|
| SET_CODE_TX_TYPE | 0x04 |
| MAGIC | 0x05 |
| PER_AUTH_BASE_COST (TxAuthTupleGas) | 12500 |
| PER_EMPTY_ACCOUNT_COST (CallNewAccountGas) | 25000 |

#### Transaction Format
```
rlp([chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit,
destination, value, data, access_list, authorization_list, signature_y_parity,
signature_r, signature_s])

authorization_list = [[chain_id, address, nonce, y_parity, r, s], ...]
```

#### Implementation Details
1. **Authorization Processing**: For each authorization tuple `[chain_id, address, nonce, y_parity, r, s]`:
   - Verify the chain ID is 0 or the current chain ID
   - Recover the authority address using `ecrecover(keccak(MAGIC || rlp([chain_id, address, nonce])), y_parity, r, s)`
   - Verify the authority's code is empty or already delegated
   - Set the authority's code to `0xef0100 || address` (delegation indicator)
   - Increment the authority's nonce

2. **Delegation Indicator**: The `0xef0100 || address` prefix uses the banned opcode `0xef` to indicate delegated code. All code executing operations (`CALL`, `CALLCODE`, `DELEGATECALL`, `STATICCALL`) must follow the delegation pointer.

3. **Gas Costs**: 
   - Intrinsic cost includes `PER_EMPTY_ACCOUNT_COST * authorization_list_length` initially
   - If the authority account already exists, refund `PER_EMPTY_ACCOUNT_COST - PER_AUTH_BASE_COST` (25000 - 12500 = 12500)

4. **Supported Action Types**: SetCodeTx only supports `execution` and `transfer` action types. Native staking and rewarding actions are not supported.

### Implement EIP-7623: Increase Calldata Cost

#### Overview
EIP-7623 increases calldata costs for data-heavy transactions to reduce maximum block size while maintaining low costs for regular transactions.

#### Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| TX_BASE_GAS | 10000 | Base intrinsic gas for execution transactions |
| TX_TOKEN_PER_NONZERO_BYTE | 1 | Token per non-zero byte |
| TX_COST_FLOOR_PER_TOKEN | 250 | Cost floor per token |


#### Implementation Details
1. **Token Calculation**: 
```go
tokens = nonzero_bytes * TX_TOKEN_PER_NONZERO_BYTE + zero_bytes
```

2. **Floor Data Gas Calculation**:
```go
floorDataGas = TX_BASE_GAS + tokens * TX_COST_FLOOR_PER_TOKEN
```

3. **Gas Usage**: After EVM execution completes, the actual gas used is:
```go
gasUsed = max(normalGasUsed, floorDataGas)
```

4. **Transaction Validity**: Transactions must have gas limit >= `floorDataGas`

5. **Impact**: Regular transactions (IOTX transfers, DeFi, etc.) remain unaffected as they have significant EVM execution. Data-heavy transactions (primarily using calldata for DA) will see increased costs, with floor gas around 250 gas per byte.

### Implement EIP-2935: Save Historical Block Hashes in State

#### Overview
EIP-2935 stores the last 8191 block hashes in a system contract's storage, enabling stateless execution and extended history access.

#### Parameters
| Parameter | Value |
|-----------|-------|
| BLOCKHASH_SERVE_WINDOW | 256 |
| HISTORY_SERVE_WINDOW | 8191 |
| SYSTEM_ADDRESS | 0xfffffffffffffffffffffffffffffffffffffffe |
| HISTORY_STORAGE_ADDRESS | 0x0000F90827F1C53a10cb7A02335B175320002935 |

#### Implementation Details
1. **Block Processing**: At the start of each block (before transactions), invoke a system call to `HISTORY_STORAGE_ADDRESS` with:
   - Caller: `SYSTEM_ADDRESS`
   - Input: 32-byte `block.parent.hash`
   - Gas limit: 30,000,000
   - Value: 0

2. **Contract Operations**:
   - `set`: Stores `block.parent.hash` at slot `(block.number - 1) % HISTORY_SERVE_WINDOW`
   - `get`: Returns the block hash for a given block number within the serve window

3. **Contract Deployment**: Deploy the history contract at the fork activation block using the predefined deployment transaction.

4. **BLOCKHASH Opcode**: Semantics remain unchanged; the contract provides extended history access via direct calls.

### Implement EIP-2537: Precompile for BLS12-381 Curve Operations

#### Overview
EIP-2537 adds seven precompiles for BLS12-381 curve operations, enabling efficient BLS signature verification with 120+ bits of security.

#### Precompile Addresses and Gas Costs
| Precompile | Address | Gas Cost |
|------------|---------|----------|
| BLS12_G1ADD | 0x0b | 375 |
| BLS12_G1MSM | 0x0c | Variable (see MSM formula) |
| BLS12_G2ADD | 0x0d | 600 |
| BLS12_G2MSM | 0x0e | Variable (see MSM formula) |
| BLS12_PAIRING_CHECK | 0x0f | 32600*k + 37700 |
| BLS12_MAP_FP_TO_G1 | 0x10 | 5500 |
| BLS12_MAP_FP2_TO_G2 | 0x11 | 23800 |

#### Implementation Details
The implementation follows the Ethereum EIP-2537 specification exactly. For detailed encoding formats, gas formulas, and subgroup check requirements, refer to [EIP-2537](https://eips.ethereum.org/EIPS/eip-2537).

## Rationale

### EIP Selection
The selected EIPs represent the core functionality of the Ethereum Pectra upgrade that is most relevant to IoTeX:

- **EIP-7702** provides significant UX improvements for EOA users without requiring migration to smart contract wallets
- **EIP-7623** helps control block size, which is important for network stability
- **EIP-2935** provides extended block hash history access for applications and ensures Ethereum compatibility
- **EIP-2537** enables efficient BLS signature verification, important for bridges and cross-chain applications

### IoTeX-Specific Adaptations
- **EIP-7623 Parameters**: IoTeX's base calldata gas cost differs from Ethereum (100 gas/byte vs 16 gas/byte). EIP-7623 aims to increase the floor cost to approximately 2.5x the original calldata cost. To maintain the same multiplier, IoTeX uses `TX_COST_FLOOR_PER_TOKEN = 250` (100 × 2.5) instead of Ethereum's `TOTAL_COST_FLOOR_PER_TOKEN = 40` (16 × 2.5). The relative increase ratio is consistent; only the absolute values differ due to IoTeX's different base gas parameters.

### Compatibility Considerations
The implementation follows Ethereum specifications exactly to ensure maximum compatibility with existing tooling and contracts deployed on Ethereum.

## Backwards Compatibility

This IIP is NOT backwards compatible and requires a hard fork. The following changes break existing invariants:

1. **EIP-7702**:
   - Account balance can decrease from calls to delegated EOAs
   - EOA nonce may increase during transaction execution (via CREATE operations)
   - `tx.origin == msg.sender` is no longer guaranteed to be true only in the topmost frame

2. **EIP-7623**:
   - Data-heavy transactions will require more gas
   - Wallet and RPC implementations must update gas estimation logic

3. **EIP-2935**:
   - New system contract deployed at `HISTORY_STORAGE_ADDRESS`
   - Block processing logic modified to include system calls

4. **EIP-2537**:
   - New precompile addresses (0x0b - 0x11) are now reserved

## Security Considerations

### EIP-7702
- Delegation indicators persist after transaction failure; users must understand the implications of signing authorizations
- Front-running initialization is possible if delegation and initialization are performed in separate transactions; implementations should combine delegation and initialization calls in a single atomic transaction
- Storage collision risks when changing delegations; contracts should use ERC-7201 namespaced storage

## Test Cases

Test cases will be adapted from the Ethereum execution-spec-tests repository:
- [EIP-7702 Tests](https://github.com/ethereum/execution-spec-tests/tree/main/tests/prague/eip7702_set_code_tx)
- [EIP-7623 Tests](https://github.com/ethereum/execution-spec-tests/tree/main/tests/prague/eip7623_increase_calldata_cost)
- [EIP-2935 Tests](https://github.com/ethereum/execution-spec-tests/tree/main/tests/prague/eip2935_historical_block_hashes_from_state)
- [EIP-2537 Tests](https://github.com/ethereum/EIPs/tree/master/assets/eip-2537)


## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
