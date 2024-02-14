```
IIP: 29
Title: Bridge Bitcoin to IoTeX via ioTube
Author: Haixiang (haixiang@iotex.io)
Status: WIP
Type: Standards Track
Created: 2024-02-13
```

## Abstract

This IIP proposes a bridge to facilitate the transfer of Bitcoin assets to the IoTeX network, enhancing the network's value and interoperability. It utilizes a multi-signature wallet managed by off-chain witnesses for securing asset on the Bitcoin network. The designed transactions on Bitcoin ensure compatibility with existing IoTeX contracts.

## Motivation

The motivation for this proposal is twofold. First, by bridging Bitcoin to IoTeX, we aim to significantly increase IoTeX's Total Value Locked (TVL) by tapping into the vast assets of the Bitcoin market. This move is expected to enhance the utility and attractiveness of the IoTeX ecosystem to users and depin projects alike. Second, the unique challenges presented by Bitcoin's limited programmability and the lack of open-source bridging solutions necessitate the development of a custom solution. This effort will not only provide IoTeX with a direct link to Bitcoin market but also demonstrate our capability to innovate and expand the blockchain's functionality.


## Specification

### Legit BTC Transaction format 

#### From sender to mulsig wallet

The `output` Field should be exquisitely constructed for assets bridged to IoTex via ioTube: 

1. Output 1

PkScript: A taproot Address held by multiple signers.

Amount: the amount to be bridged from the user

2. Output 2

PkScript: OP_RETURN + (BINARY DATA)

Amount: 0

- Notes: 

The ETH ADDR of receiver is encoded in the binary data:

|                   | Content                        | Type        | Data Length (in Bytes) |
|-------------------|--------------------------------|-------------|------------------------|
| Opcode            | OP_DATA_31                     |      -      | 1                      |
| Protocol Name     | "iotube"                       | String      | 6                      |
| Data byte         | 1                              | Uint8       | 1                      |
| Index of Transfer | index in LittleEndian          | Uint32      | 4                      |
| Token Recipient   | Address of wrapped btc mint to | ETH Address | 20                     |
| Total             |                                |             | 32                     |


The expected length of PkScript is 33.

3. Output 3

PkScript: the taproot Address same as output 1

Amount: A tip to the bridge

4. Output 4 (Optional)

Change back to the sender

#### From mulsig wallet to BTC recipient

It is a P2TR transaction from mulsig wallet to BTC recipient


## Rationale

### Workflow

![whiteboard_exported_image](https://github.com/iotexproject/iips/assets/55118568/da1c1a40-9897-4473-9392-a4fb0d903949)

### Signature Scheme

MuSig2 is a multi-signature scheme that allows multiple signers to create a single aggregate public key and cooperatively create ordinary Schnorr signatures valid under the aggregate public key. Signing requires interaction between all signers involved in key aggregation. (MuSig2 is a n-of-n multi-signature scheme and not a t-of-n threshold-signature scheme.)

More details could be found in [BIP 327](https://github.com/bitcoin/bips/blob/master/bip-0327.mediawiki) and [Musig2 paper](https://eprint.iacr.org/2020/1261.pdf)

### Bitcoin Script

With the support of aggregated schnorr signature, Pay-to-Taproot (P2TR) script is used to transfer assets from custody wallet to bridged wallet. Other benefits P2TR scripts bring include cheaper output spending and security upgrade.


## Example

Examples of transactions bridging Satoshi between the Bitcoin testnet and the IoTeX testnet are provided to illustrate the bridge's functionality:

 - 600 satoshis are bridged from bitcoin testnet to iotex testnet

https://mempool.space/testnet/tx/f7475c55b20babcf8e506f87b3d15e06660435a4116a4b76b911208a2e6177b4

 - 200 satoshis are bridged back to the wallet on bitcoin testnet 

https://mempool.space/testnet/tx/84105c89eb65f236984dcc4f9781304276099672155f1596b4c8004a12046b58

## Backward Compatibility

The change will ensure seamless integration with existing infrastructure, including UI/UX enhancements to include a Bitcoin option and compatibility with  the smart contracts on IoTeX.

## Security Considerations

There is no security concern.

## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).