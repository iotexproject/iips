```
IIP: 22
Title: IoTeX Domain Name Service
Author: Leo (leo@iotex.io)
Status: WIP
Type: Standards Track
Category: Core
Created: 2023-05-30
```

## Abstract

This draft IIP describes the details of the IoTeX Name Service (INS), which is similar to the ENS (Ethereum Name Service). The INS aims to be a protocol and ABI definition that provides flexible resolution of short, human-readable names to service and resource identifiers. This enables users to register and manage human-readable domain names for their IoTeX addresses, smart contracts, decentralized websites, and other IoTeX-based resources. INS will simplify the user experience by replacing long and complex IoTeX addresses with easy-to-remember names.

If cryptocurrencies become mainstream, there will be a substantial market for Web3 domains. As "everyone" eventually adopts a Web3 wallet, human-readable digital wallet addresses will be as commonplace as email addresses.

This proposal suggests using .io as the IoTeX L1 network's TLD.

## Motivation

INS can offer many benefits for IoTeX blockchains:

1. Simplified Address System and enhanced user experience: INS replaces complex and lengthy cryptocurrency addresses with human-readable domain names, making it easier for users to interact with blockchain addresses and decentralized applications.

2. Interoperability: INS provides a unified namespace across multiple decentralized applications and blockchain platforms. Users can use the same INS domain name for various services, eliminating the need to remember different addresses for different applications.

3. Branding and Identity: INS supports various top-level domains (TLDs) beyond the traditional ".io" extension. This enables organizations and communities to establish their unique identities on blockchain, promoting branding and fostering a sense of trust and recognition.

4. Decentralization and Security: INS operates on the IoTeX blockchain, leveraging the decentralized nature of blockchain technology. This ensures that domain ownership and control are in the hands of the users themselves, reducing the risk of censorship or manipulation.

5. Integration with Existing Systems: INS can be integrated into popular wallets, exchanges, and decentralized applications, allowing seamless use of domain names across various platforms and services.

6. User Empowerment: INS gives users ownership and control over their domain names and associated cryptocurrency addresses. Users have the flexibility to update or transfer their domains as needed, providing a sense of empowerment and autonomy.

7. Improved Discoverability: INS facilitates the discovery of decentralized services and applications by providing human-readable domain names. Users can easily search and navigate the blockchain ecosystem, promoting the adoption and usage of decentralized platforms.

8. Future-Proofing: INS is designed to be compatible with evolving blockchain technologies and standards. It can adapt to changes and upgrades in the IoTeX network, ensuring its longevity and relevance in the ever-changing blockchain landscape.

9. Community and Innovation: INS fosters a community-driven ecosystem where developers, organizations, and individuals can collaborate, build upon, and innovate using the INS infrastructure. This drives creativity and the development of new decentralized applications and services.
Based on the multiple advantages of INS mentioned above, it is an imminent task to deploy a mature, flexible, and stable domain name system on the IoTeX network.

## Specification

### Overview

The INS system comprises four main parts:
  - The INS registry
  - Resolvers
  - Registrars
  - Name Wrapper

The registry is a single contract that serves as the core infrastructure of the IoTeX Name Service. It functions as a decentralized database that maintains the mapping between domain names and their corresponding IoTeX addresses or resources. The Registry is implemented as a smart contract on the IoTeX blockchain, ensuring security, immutability, and censorship resistance. It acts as a single source of truth for all registered INS names and is responsible for handling the resolution of these names to their respective resources.

Resolvers are smart contracts associated with individual INS names. They play a crucial role in enabling INS names to resolve to specific resources such as IoTeX addresses, decentralized websites, or content hashes. Resolvers allow users to configure and update the settings associated with their INS names, providing flexibility and adaptability. By interacting with the Resolver contract, users can define various records, such as address records (for IoTeX addresses), content records (for decentralized websites), and text records (for arbitrary metadata). These records allow users to attach additional information to their INS names and enable decentralized applications to utilize INS in a more versatile manner.

Registrars act as intermediaries between users and the INS Registry. They facilitate the process of registering and managing INS names by allowing users to reserve, release, and transfer names securely. Registrars typically implement additional rules, policies, and pricing structures that govern the registration of names within their specific TLD (Top-Level Domain). Each TLD on INS has its own registrar, which defines the requirements for registering names under that TLD. Registrars play a vital role in ensuring the availability and integrity of the INS namespace by enforcing the registration rules and policies in a fair and transparent manner.

Name Wrapper is a smart contract that will allow issuing subdomains (such as sub.domain.io) as separate Non-Fungible Tokens (NFTs). It is already possible to make and use subdomains, but they are not created as separate NFTs and can not be transferred between wallets, rented, or sold. On top of that, it will be possible to customize subdomains by revoking sets of permissions (burning fuses) to change the degree of ownership.

Together, the INS Registry, Resolvers, Registrars, and Name Wrapper form a robust infrastructure that powers the IoTeX Name Service ecosystem. INS provides a decentralized and user-friendly approach to interacting with blockchain resources by offering human-readable names instead of long and complex addresses. Whether it's simplifying transactions, enhancing user experiences, or supporting the growth of decentralized applications, INS plays a vital role in making the IoTeX ecosystem more accessible and intuitive for users worldwide.

### Name syntax

INS names must conform to the following syntax:

```
<domain> ::= <label> | <domain> "." <label>
<label> ::= any valid string label per [UTS46](https://unicode.org/reports/tr46/)
```

Below are valid names for INS:

- iopay.io
- cool.iopay.io

### namehash algorithm

Before being used in INS, names are hashed using the ‘namehash’ algorithm. This algorithm recursively hashes components of the name, producing a unique, fixed-length string for any valid input domain. The output of namehash is referred to as a ‘node’.
Pseudocode for the namehash algorithm is as follows:

```
def namehash(name):
  if name == '':
    return '\0' * 32
  else:
    label, _, remainder = name.partition('.')
    return sha3(namehash(remainder) + sha3(label))
```

## Rationale

The basic principle of INS implementation is basically the same as that of ENS. In ENS, zero-width character names are allowed to register domain names, but in INS, such domain names are prohibited from being registered.

## Backward Compatibility

There is no backward compatibility concern.

## Security Considerations

There is no security concern.

## Copyright

Copyright and related rights waived via CC0.