```
IIP: 30
Title: Deploy Circle Standard Token to ioTube (USDC.e) and Migrate ioUSDC to USDC.e
Author: Qevan & Giuseppe
Status: WIP
Type: Standards Track
Category: Core
Created: 2024-05-16
```

### Background
ioTube, the official bridge of IoTeX, introduced ioUSDC, a bridged token from Ethereum, on 9/14//2021. Since its launch, ioUSDC has been integrated with over 10 DeFi protocols and is held by over 5,000 wallet addresses. Recently, Circle proposed the [Bridged USDC Standard](https://github.com/circlefin/stablecoin-evm/blob/master/doc/bridged_USDC_standard.md), a specification and process for deploying a bridged form of USDC on EVM blockchains. This standard includes the optionality for Circle to seamlessly upgrade to native USDC issuance in the future. The Bridged USDC Standard provides a secure and standardized method for any EVM blockchain and rollup team to transfer ownership of a bridged USDC token contract to Circle, facilitating an upgrade to native USDC.

### Proposal

1. **Deployment of Circle Standard Token (USDC.e)**
   - Deploy the Circle standard token on IoTeX, using the symbol USDC.e as per Circle's recommendation.

2. **Migration from ioUSDC to USDC.e**
   - Enable users to convert their ioUSDC tokens to USDC.e seamlessly.

3. **Interoperability between USDC.e and ioUSDC**
   - Allow users to convert USDC.e back to ioUSDC to maintain compatibility with existing DeFi protocols that support ioUSDC.

4. **Bridge Support Enhancement**
   - Update ioTube to support bridging between USDC on Ethereum and USDC.e, replacing the current support for USDC on Ethereum and ioUSDC.

### Implementation Details

1. **Smart Contract Deployment**
   - Deploy the smart contract for USDC.e as specified by Circle.

2. **Wrapper Smart Contract**
   - Develop and deploy a wrapper smart contract that facilitates the conversion between ioUSDC and USDC.e.

3. **Validator Upgrades**
   - Upgrade all validators on ioTube to handle the new bridge functionality between USDC on Ethereum and USDC.e.

4. **DeFi Protocol Integration**
   - Recommend all DeFi protocols on IoTeX to support the new USDC.e token.

### Conclusion
By implementing the proposed deployment and migration strategy, IoTeX will enhance its DeFi ecosystem's compatibility and ensure seamless token transactions for users. This initiative will leverage Circle's standard token format, positioning IoTeX for future integrations and improvements.
