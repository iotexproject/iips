```
IIP: 31
Title: Bridge Solana to IoTeX via ioTube
Author: Haixiang (haixiang@iotex.io), Leo (leo@iotex.io)
Status: WIP
Type: Standards Track
Created: 2024-05-21
```

## Abstract
The proposal details the integration of Solana with the ioTube bridge, enhancing DEPIN interoperability. It specifies on-chain contracts for sending and receiving assets, the ioTube Message Protocol for event communication, and off-chain witness consensus using secp256k1 and ed25519 elliptic curves, optimizing cost and performance.

## Motivation

After integrating into EVM and Bitcoin ecosystem, Solana ecosystem is the next milestone for ioTube bridge. Bridging Solana and IoTeX chains will enhance interoperability between two leading DEPIN ecosystems, enabling seamless transfer of assets, data, and services. Enhanced interoperability will attract a broader user base, driving adoption and network effects while promoting the overall growth of the DEPIN sector. Additionally, as one of the public goods of IoTeX ecosystem, ioTube bridge is evolving to create a more interconnected and impactful DEPIN ecosystem, aligning with our mission of "DePIN for Everyone."


## Specification

## Onchain Contracts

### Methods of Sending Assets
These methods enable blockchain clients to bridge assets from the source chain to the destination chain. User assets are locked in a token safe within the contract by the bridge, which can only be withdrawn by burning the wrapped assets on the destination chain.

 - Method on Solana Chain:
 
```rust
pub fn process_bridge(program_id: &Pubkey, accounts: &[AccountInfo], amount: u64, to: &[u8]) -> ProgramResult
```

 - Method on IoTex Chain:
 
```solidity
function depositTo(address _token, address _to, uint256 _amount) public whenNotPaused payable`
```

### Methods of Receiving Assets
These methods allow off-chain relayers of the bridge to submit proofs, confirmed by witnesses (oracles) regarding events emitted on the source chain, to the contract on the destination chain. Proofs are submitted automatically by relayers. Once verified, bridged assets are issued to the user's wallet (assets will be sent to users' associated token account on Solana).

 - Method on Solana Chain:

```rust
 pub fn process_settle(program_id: &Pubkey, accounts: &[AccountInfo], amount: u64) -> ProgramResult`
```

 - Method on IoTex Chain:

```solidity
function submit(address cashier, address tokenAddr, uint256 index, address from, address to, uint256 amount, bytes memory signatures) public whenNotPaused` 
```

## ioTube Message Protocol 
The ioTube Message Protocol is adopted by on-chain contracts of ioTube bridge as the format of emitted events to ensure interoperability between the IoTeX chain, the Solana chain, and off-chain witnesses:

```
Receipt struct {
    token Address, 
    id Number, 
    sender Address,
    recipient Address, 
    amount Number, 
    fee Number,
}
```

## Offchain witnesses concensus
Solana-IoTeX bridge, leveraged on the [ioTube Bridge architecture](https://docs.iotube.org/introduction/overview-and-architecture), operates on the existing witnesses network with Solana client support. Once two-thirds of witnesses sign the event, a consensus is reached, and the relayer submits the data and signatures to the contract. When bridging assets from Solana to IoTeX, witnesses use the `secp256k1` elliptic curve to sign the data, which can be verified in EVM smart contracts; in the opposite direction, the `ed25519` elliptic curve is used.


## Rationale

### Workflow

WIP

### Ed25519 Elliptic Curve

The address of a Solana account is a public key lies on the `ed25519` curve. Therefore, to be seamlessly managed in the Solana program of the bridge, each off-chain witness possesses an `ed25519` private key as their identity. Additionally, Ed25519 signatures can be natively verified by the [system program](https://docs.solanalabs.com/runtime/programs#ed25519-program) `Ed25519SigVerify111111111111111111111111111`, significantly reducing the bridge's operational costs.



## Backward Compatibility

The change will ensure seamless integration with existing infrastructure, including UI/UX enhancements to include a Solana option and compatibility with the smart contracts on IoTeX.

## Security Considerations

There is no security concern.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).