# What is a IIP?

IIP stands for IoTeX Improvement Proposal. An IIP is a design document providing information to the IoTeX community, or
describing a new feature for IoTeX or its processes or environment. The IIP should provide a concise technical
specification of the feature and a rationale for the feature.

We intend IIPs to be the primary mechanisms for proposing new features, for collecting community input on an issue, and
for documenting the design decisions that have gone into IoTeX. The IIP author is responsible for building consensus
within the community and documenting dissenting opinions.

Because the IIPs are maintained as text files in a versioned repository, their revision history is the historical record
of the feature proposal.

# IIP Types

There are three kinds of IIP:

- A Standards Track IIP describes any change that affects most or all IoTeX implementations, such as a change to the
network protocol, a change in block or transaction validity rules, or any change or addition that affects the
interoperability of applications using IoTeX.

- An Informational IIP describes an IoTeX design issue, or provides general guidelines or information to the IoTeX
community, but does not propose a new feature. Informational IIPs do not necessarily represent an IoTeX community
consensus or recommendation, so users and implementors are free to ignore Informational IIPs or follow their advice.

- A Process IIP describes a process surrounding IoTeX, or proposes a change to (or an event in) a process. Process IIPs
are like Standards Track IIPs but apply to areas other than the IoTeX protocol itself. They may propose an
implementation, but not to IoTeX's codebase; they often require community consensus; unlike Informational IIPs, they are
more than recommendations, and users are typically not free to ignore them. Examples include procedures, guidelines,
changes to the decision-making process, and changes to the tools or environment used in IoTeX development. Any meta-IIP
is also considered a Process IIP.

## IIP Status

There are four kinds of status:

- **Draft**: an IIP that is open for consideration.

- **Accepted**: an IIP that is planned for immediate adoption.

- **Final**: an IIP that has been adopted previously.
 
- **Deferred**: an IIP that is not being considered for immediate adoption. May be reconsidered in the future.

- **Closed**: an IIP that is no longer considered for adoption.

## IIP Formats and Templates

IIPs should be written in markdown format, and the file should be named `iip-X.md`, where `X` is IIP number. Image files
should be included `assets/iip-X` folder. When linking to an image in the IIP, use relative links such as
`assets/iip-X/image.png`.

Each IIP must begin with an RFC 822 style header preamble. The headers must appear in the following order. Headers
marked with `*` are optional and are described below. All other headers are required.
 
```
  IIP: <IIP number>
  Title: <IIP title>
  Author: <list of authors' real names and optionally, email addrs>
* Discussions-To: <URL to the discussion thread>
  Status: <Draft | Accepted | Final | Deferred | Closed>
  Type: <Standards Track | Informational | Process>
  Created: <date created on, in ISO 8601 (yyyy-mm-dd) format>
* Replaces: <IIP number>
* Superseded-By: <IIP number>
* Resolution: <url>
```

Refer to the [example](iip-X.md) for details.

## Process of creating a new IIP

1) Review the IIPs public repo
This will help you ensure that your idea is unique and has not already been proposed or discussed. It will also give you an idea of the standard of other successful proposals. 

2) Determine the next IIP number: To avoid conflicts, find the current latest IIP and use the next number for your proposal (don't forget to check any PRs with pending proposals).

3) Draft your proposal: Try using the same format as the existing IIP documents you find the repository to draft yours. When in doubt, feel free to reach out to any IoTeX team member on Discord, on X,  Telegram, or on the community forum. Not sure where to look? 
Start here:  https://iotex.io

4) Submit for discussion: Once your proposal is ready, post it to the IoTeX Community Forum for discussion under the Governance Proposals category: https://community.iotex.io/c/governance-proposals

5) Voting and implementation: Based on the feedback received, you may need to make revisions to your proposal. Once the IIP is finalized, it will go through community voting on the IoTeX snapshot: 
 https://snapshot.org/#/iotex.eth

6) Implementation: Once the voting is passed, it will be implemented into the relevant IoTeX ecosystem protocol.



## Acknowledgement

Thanks for those who contribute to [BIPs](https://github.com/bitcoin/bips), [EIPs](https://github.com/ethereum/EIPs)
and [EEPs](https://eeps.io/), where we have learned and borrowed clauses heavily.

## Changelog

2019-05-20: Drafted the initial version of IIP guideline.

2019-06-11: Added the IIP sample file.
