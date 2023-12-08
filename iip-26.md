```
IIP: 26
Title: Use VersionedDB to reduce CandidateBucket index DB size
Author: Dustin Xie
Status: WIP
Type: Standards Track
Category: Core
Created: 2023-12-04
```
## Abstract
This IIP introduced the concept of VersionedDB and utilized it to reduce the size of CandidateBucket index DB. It also discussed several techniques to optimize the DB operation

## Motivation
CandidateBucket index DB is an auxiliary DB needed by API node. It stores the candidates and buckets at each epoch, and serves requests for API and analyser queries.  API retrieves this data for query of each epoch's delegate list. Analyser polls this data for calculation of bucket rewards.
As of now, this DB size has reached a whopping 110GB. This has caused a heavy burden on storage and the rate of size increase is not sustainable for the future.  A solution is needed to reduce the DB size and better manage the file size increase.

## Proposal
TBA

## Specification
TBA

## Rationale
TBA
