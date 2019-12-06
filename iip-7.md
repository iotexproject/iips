```
IIP: 7
Title: Decentralized Mobile Auth
Author: Tian Pan (@puncsky) tian@iotex.io
Discussions-to: <URL>
Status: Draft
Type: Application Track
Created: 2019-12-05 18:22
Requires (*optional): <IIP number(s)>
Replaces (*optional): <IIP number(s)>
```

## Simple Summary

This documentation describes why we need decentralized mobile App login, its challenges, and how to implement it with DID, IoTeX blockchain account, and smart contracts. 

## Abstract

IoT devices usually function in the intranet or at the edge of the Internet. And, in the spirits of the decentralized system, we do not trust the centralized identity provider and want to have full control over our own identities. 

In this design, we leverage the DID and IoTeX account to provide the login solution at the edge, as an alternative to OAuth2 but without external user-agents such as the user's browser. 

When the user wants to log in with IoPay in the App, we use deep-link to redirect the user to the ioPay. The user chooses the intended identity in the wallet and consent, and finally, loop back to the original App with self-sovereign credentials (JWT and DID). 

We realize that the deep link is not ideally secured, and we lose the power of the browser and HTTPs in a traditional OAuth2 flow. To compensate for the security issues, we introduce smart contracts to verify extra information but still keeps the process open for any DApps, with the assumption that the user and the user's Phone can be trusted to be self-responsible.

## Motivation
Mobile apps usually rely on the user’s PIIs like email, name, and phone number to identify the user, and a centralized identity provider plays a vital role in both the first-party and second-party login. Combined, they lead to security breaches and privacy abuses, if the trusted centralized services are not able to fully protect the users’ data and fully comply with the law. 

Thus, we need a decentralized mobile login, that is 

1. Decentralized. It should not rely on a single identity provider.
2. Self-sovereign. The credentials given by the user can prove identity by itself.
3. Decoupled with PIIs. It should not mandatorily contain PIIs or upload PIIs to the server without the permission of the user. Any PII should be used under the user’s grants and can be deleted at will.
4. Server-agnostic. It should be functioning in the edge, with minimal network connection or even without the connection.

## Specification
### Workflow

![](https://res.cloudinary.com/dohtidfqh/image/upload/v1575598621/web-guiguio/iopay_1.png)

*Architecture (see descriptions below for details)*

#### Step 1: Login Redirect

App implements a button with deep-link to `io.iotex.iopay://sign/?type=login&nonce=:nonce&next=:next&did=:userDid`

Specifically, those query parameters are

1. `type`: required field. It states what kinds of signature request it is. Here it is `login`.
2. `nonce`: required field. It is a randomly-generated UUID to identify this login intention. It will be used later as the `jti` of the final access token. The App has to keep this for later verification when it receives the loopback JWT.
3. `next`: required field. It is a deep link composed of the package ID of the mobile App and the path, e.g. `io.iotex.ucam://loginCallback`.
4. `userDid`: not required field. It is the intended user’s DID, if you do not specify the DID then the user has to choose one by herself; Otherwise, the indented one is suggested as the default choice.

#### Step 2: Consent, Select, and Sign

We suggest users separate identity keys from token keys. Users or developers can generate their private keys with SDK  `iotex-antenna`. 

Once ioPay App launched by the deep link, it recognizes the `login` sign type and prompts the login screen. In the login screen, the user sees the consent and choose an account to continue with or abort. If it is a re-auth scenario and the `userDid` parameter is present, then we set that address as the default choice. 

We fetch the App signature of the `source` package ID, along with other metadata, and present to the user to know what App is requesting login.

Optionally, for security, we verify the App signature and package ID against registration in the smart contracts and App staking. 

Once the user read through the App consent and the verification information, and continue with a specific account, ioPay will sign a JWT with the `EK256K` algorithm, and then generate the access token in the following format.

Header:

``` json
{“alg”: “EK256K”, “typ”: “JWT”}
```

Payload Type:

```json
{
  'type': 'object',
  'properties': {
    'iss': { 'type': 'string' },
    'exp': { 'type': 'IntDate' },
    'iat': { 'type': 'IntDate' },
    'associationToken': { 'type': 'string' },
    'salt': { 'type': 'string' }
  }
  'required': [ 'iss' ]
}
```

Signature:

See the implementation section below.

#### Step 3: Loopback and verify the self-sovereign JWT

After the success of step 2, the control flow loops back with the redirect deep link in the format of `io.iotex.ucam://loginCallback?token=:token`.

The mobile App verifies the token and uses it as the access token or in exchange of their own tokens. The app verify the token in four steps

1. `nonce` is the one this App initially designated.  
2. `iss`: pubKey signed the signature.
3. `sub` is the DID of the pubkey.
4. `exp` is not expired yet.

## Rationale
### Threat Modeling

* Replay attack and Session fixation attack: We use nonce to prevent these issues.
* Deep link hijacking and phishing
    * First-party App is hijacked. TBD.
    * `ioPay` is hijacked. TBD.
* Open redirect: TBD.
* Impersonalization: TBD.

## Backwards Compatibility
It with reuse the design of IoTeX accounts via what iotex-antenna currently have. And we will add a new JSON web token with a new algorithm “EK256K” to the SDK family.

## Test Cases
We will implement unit tests In the SDKs. The integration in the mobile apps is out of the scope of this spec.

## Implementation

```ts
import { Account } from "iotex-antenna/lib/account/account";
import { fromUtf8 } from "iotex-antenna/lib/account/utils";
import { publicKeyToAddress } from "iotex-antenna/lib/crypto/crypto";

function base64url(str: string, encoding: BufferEncoding): string {
  return Buffer.*from*(str, encoding)
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function toString(obj: object): string {
  if (typeof obj === "string") {
    return obj;
  }
  if (typeof obj === "number" || Buffer.*isBuffer*(obj)) {
    return obj.toString();
  }
  return JSON.stringify(obj);
}

// tslint:disable-next-line:no-any
function isObject(thing: any): boolean {
  return Object.prototype.toString.call(thing) === "[object Object]";
}

// tslint:disable-next-line:no-any
function safeJsonParse(thing: string | object): Record<string, any> {
  if (isObject(thing)) {
    // @ts-ignore
    return thing;
  }
  try {
    // @ts-ignore
    return JSON.parse(thing);
  } catch (e) {
    return {};
  }
}

function jwsSecuredInput(
  header: object,
  payload: object,
  encoding: BufferEncoding = "utf8"
): string {
  const encodedHeader = base64url(toString(header), "binary");
  const encodedPayload = base64url(toString(payload), encoding);
  return `${encodedHeader}.${encodedPayload}`;
}

// tslint:disable-next-line:no-any
function headerFromJWS(jwsSig: string): Record<string, any> {
  const encodedHeader = jwsSig.split(".", 1)[0];
  return safeJsonParse(Buffer.*from*(encodedHeader, "base64").toString("binary"));
}

// tslint:disable-next-line:no-any
function payloadFromJWS(jwsSig: string): Record<string, any> {
  const encodedHeader = jwsSig.split(".")[1];
  return safeJsonParse(Buffer.*from*(encodedHeader, "base64").toString("binary"));
}

function securedInputFromJWS(jwsSig: string): string {
  return jwsSig.split(".", 2).join(".");
}

function signatureFromJWS(jwsSig: string): string {
  return jwsSig.split(".")[2];
}

const ALG = "EK256K";

export async function sign(
  payload: object,
  secretOrPrivateKey: string
): Promise<string> {
  const securedInput = jwsSecuredInput(
    {
      alg: ALG,
      typ: "JWT"
    },
    payload
  );
  const acct = Account.*fromPrivateKey*(secretOrPrivateKey);
  const sigHex = acct.sign(fromUtf8(securedInput));
  const signature = base64url(sigHex.toString("hex"), "hex");
  return `${securedInput}.${signature}`;
}

export async function verify(
  token: string
  // tslint:disable-next-line:no-any
): Promise<Record<string, any>> {
  const header = headerFromJWS(token);
  if (!header) {
    throw new Error("header is empty or does not have alg");
  }
  if (header.alg !== ALG) {
    throw new Error(`alg should be ${ALG} but got ${header.alg}`);
  }

  const securedInput = securedInputFromJWS(token);
  const signature = signatureFromJWS(token);
  const empty = new Account();
  const recoveredAddress = empty.recover(
    fromUtf8(`${securedInput}`),
    Buffer.*from*(signature, "base64"),
    false
  );
  const securedInputObject = payloadFromJWS(token);
  const secretOrPublicKey = securedInputObject.iss;
  const expectedAddress = publicKeyToAddress(secretOrPublicKey);
  if (recoveredAddress !== expectedAddress) {
    throw new Error(
      `${recoveredAddress} signed the signature but we are expecting ${expectedAddress}`
    );
  }

  if (!securedInputObject.iss || securedInputObject.iss !== secretOrPublicKey) {
    throw new Error(`issuer of the token does not match ${secretOrPublicKey}`);
  }
  return securedInputObject;
}

```



## Copyright
Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).

## References

* [Measuring the Insecurity of Mobile Deep Links of Android](https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/liu)
* [OAuth 2.0 for Native Apps](https://www.usenix.org/sites/default/files/conference/protected-files/usenixsecurity17_slides_gang_wang.pdf)
* [Understanding decentralized identity (DID and DIF)](https://tianpan.co/notes/159-did)
