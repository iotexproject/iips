```
IIP: 40
Title: Deprecate io1 Address Format
Author: IoTeX Lab 
Type: Standards Track
Category Core
Created: 2024-10-22
``` 

## Abstract

This IIP proposes deprecating the native `io1...` address format in favor of the widely recognized Ethereum-compatible `0x...` format across the IoTeX ecosystem. After evaluating the pros and cons, we recommend a phased transition to enhance user experience, reduce confusion, and align with industry standards.

## Motivation

In 2020, IoTeX added support for the Ethereum-compatible `0x...` address format along with support for the Ethereum API, facilitating interactions with users, developers, and third-party tools familiar with Ethereum. Currently, IoTeX supports both `io1...` and `0x...` address formats. While existing community members are accustomed to this duality, new users often face confusion, leading to errors and support issues.

## Proposal

After evaluating the advantages and disadvantages of maintaining both address formats, to promote mass adoption and simplify onboarding, we propose deprecating the `io1...` format.

### Cons of Maintaining Both Formats

1. **User Confusion**: New users risk sending tokens to the wrong chain or are unsure how to proceed when withdrawing to wallets like MetaMask.

2. **Ledger App Issues**: Users must adapt between `io1...` and `0x...` formats, causing confusion about the destination network.

3. **Perceived Unauthorized Transfers**: Discrepancies between input and displayed addresses lead users to suspect unauthorized activities.

4. **Wallet Inconsistencies**: Different wallets using different formats hinder user migration and create confusion.

5. **ioPay Complexity**: Requiring users to select address formats adds unnecessary complexity.

6. **Inconsistent Address Display**: Seeing different address formats in explorers and tools degrades user experience.

7. **Complex Documentation**: Supporting both formats complicates guides and onboarding materials (both internal and external).

## Proposed Actions

We propose that the IoTeX team takes the following actions to actively deprecate the use of the `io1` address format:

1. **Notify Existing Exchanges**: Request all exchanges that already support IOTX to update their withdrawal and deposit flows to use `0x...` addresses first when users select IoTeX as the destination chain. The `io1` option should be removed, or provided as an alternative only.

2. **Standardize New Exchanges**: Encourage new exchanges to adopt `0x...` addresses for deposits and withdrawals.

3. **Wallet Compatibility**: Advise new and existing wallets to treat IoTeX as an Ethereum-compatible chain from the outset.


## Impact

Deprecating the `io1...` address format will streamline the user experience, reduce confusion, and lower the risk of errors. It aligns IoTeX with the broader blockchain ecosystem, making it more accessible to users familiar with Ethereum. While some legacy systems may require updates, the long-term benefits outweigh temporary inconveniences.

**NOTE**: NO action is required for all `io1...` users, as these addresses are 100% interchangeable and share the exact same private key. If needed, the official address converter is available in the IoTeX Hub's tools tab, [here](https://hub.iotex.io/tools). Additionally, the `io1...` address format will remain available solely as an alternative for backward compatibility. 

## Conclusion

After careful evaluation, we propose deprecating the `io1...` address format in favor of the Ethereum-compatible `0x...` format in all IoTeX ecosystem tools and exchanges. This transition will enhance usability, promote adoption, and align IoTeX with industry standards.

## References

Address Conversion Topic on the docs: [https://docs.iotex.io/builders/reference-docs/native-iotex-development/address-conversion](https://docs.iotex.io/the-iotex-stack/basic-concepts/address-conversion)
