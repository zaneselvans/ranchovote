# Glossary

This glossary records the vocabulary used by the framework and maps it onto two
important application domains:

- classical STV and election administration terminology
- participatory budgeting terminology

The core library aims to use neutral language so the same mechanics can be
applied across elections, budgeting, committee selection, and related ranked
collective decision processes.

## Core Terminology Mapping

| STV (electoral) | Budgeting                          | Neutral        |
| --------------- | ---------------------------------- | -------------- |
| Election        | Budgeting process                  | Contest        |
| Election result | Budgeting outcome                  | Contest result |
| Candidate       | Project                            | Option         |
| Voter           | Funder, Resident, or Budget Holder | Participant    |
| elect           | fund or approve                    | select         |
| elected         | funded or approved                 | selected       |
| eliminate       | reject or defund                   | exclude        |
| eliminated      | rejected or unfunded               | excluded       |

## Notes

- `Ballot` is already sufficiently neutral and is used across all three vocabularies.
- Neutral framework terms are preferred in the codebase unless a module is specifically documenting classical STV concepts or a budgeting specialization.
- This page is intended to accumulate additional definitions over time as the framework grows.
