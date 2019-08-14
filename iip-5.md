```
IIP: 5
Title: Classifying EVM Error Status
Author: Dorothy Ko (dorothy@iotex.io)
Status: Draft
Type: Standards Track
Created: 2019-08-14
```


## Abstract
Currently every execution of smart contracts on IoTeX Blockchain doesn't show any information of error if it fails to execute or deploy the smart contract. In order to give an information of error to the end-user, this standard outlines a common set of EVM Error Status Code. Therefore, we classify the possible EVM error and define EVM error status code. And we propose to give the EVM Error Code to the Receipt Status, so that it is visible to users/developers and accordingly it enhances UX(User Experience) and DX(Developer Experience). 

## Motivation
Sometimes, we failed to execute or deploy a smart contract. However, currently its status gives us just simple status such as Success(1) or Failure(0) in receipt and it doesn't give us any information of the reason of failure. In terms of user and developer experience, it makes us difficult to utilize the smart contract execution.  

## Specification

> General Status 

| code | Description  |
|------|--------------|
| 0    | Failure      |
| 1    | Success      |


> 1xx for EVM Execution Error Status 

| code | 			Description               |
|------|--------------------------------------|
| 100  | Unknown 	                          |
| 101  | Execution out of Gas                 |
| 102  | Deployment out of gas (store code)   |
| 103  | Max call depth exceeded              |
| 104  | Contract address collision           |
| 105  | No compatible interpreter            |
| 106  | Execution reverted                   |
| 107  | Max code size exceeded               |
| 108  | Write protection                     |



## Backwards Compatibility
This IIP may cause breaking chain because it changes the receipt status. Therefore, it needs a hard fork, such as height upgrade(Bering). So we propose to apply this modification of receipt status to blocks after Bering-Height and it'll prevent from the potential incompatibility issue. 


## Implementation
The status of receipt in the block after Bering-Height will include EVM Error Status code. 


## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).