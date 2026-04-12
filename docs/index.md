# Ranked Choice Contests

RanChoVote is a framework for experimenting with ranked-choice counting methods derived from [Single Transferable Vote](https://opavote.com/methods/single-transferable-vote).
Its core abstractions are intentionally neutral so the same machinery can support classical STV elections, participatory budgeting, committee selection, and other contests in which participants rank options and the system must allocate limited support among them.

The current framework centers on three ideas:

- participants may have different voting weights or contribution levels.
- options may require different support thresholds to be selected.
- the count should leave behind a structured trace that can be audited, visualized, and used to explain the result.

One important application is participatory budgeting, where participants contribute different amounts of funding and options require different budgets.
Another is weighted or otherwise non-standard STV-style elections, where the same ranked-ballot mechanics apply even though the resource being allocated is voting power rather than money.

The project grew out of work on collaborative funding methods to support [Catalyst Cooperative](https://github.com/catalyst-cooperative)'s [Public Utility Data Liberation](https://github.com/catalyst-cooperative/pudl) (PUDL) Project.
The repository now aims to serve the broader study and demonstration of ranked-choice contest methods.

## Single Transferable Vote Resources

### References

- [Single Transferable Vote](https://en.wikipedia.org/wiki/Single_transferable_vote) from Wikipedia
- [Single Transferable Vote](https://opavote.com/methods/single-transferable-vote) from OpaVote
- [Counting Single Transferable Votes](https://en.wikipedia.org/wiki/Counting_single_transferable_votes) from Wikipedia
- [Meek Single Transferable Vote](https://blog.opavote.com/2017/04/meek-stv-explained.html) from OpaVote

### Existing Implementations

- [blackgreen100/meek-stv](https://github.com/blackgreen100/meek-stv) (Go)
- [jontingvold/pyrankvote](https://github.com/jontingvold/pyrankvote) (Python)
- [ikluft/prefvote](https://github.com/ikluft/prefvote) (Perl)
- [denismollison/pref](https://github.com/denismollison/pref) (R)

## Development Roadmap

The package should be usable in a variety of different cases, including:

- Running a classical Single Transferable Vote election, where all options have the same threshold and all participants have the same voting weight.
- Running a weighted STV-style election where participants have different voting power, but all options have the same threshold for selection.
- Running a generalized resource-allocation contest where participants have different weights and options have different required support values.

The package should allow the use of different STV algorithms. Our ultimate goal is to generalize the Meek STV algorithm to the case of unequal voting power and unequal option thresholds.
However, first we should be able to use a simpler STV algorithm that is easier to implement and understand, even if it is less fair than Meek's method.
This will allow us to test the data model and the overall contest process before implementing the more complex Meek algorithm.
It will also help when onboarding new users to the system, as they can start with a simpler algorithm and then move on to the more complex one once they are familiar with the overall process.

- [ ] Implement a conceptually simple STV algorithm.
- [ ] Enable auditing of contest process and results, including detailed logging of the contest process and final vote counts for each option.
- [ ] Create a visualization of the contest process, showing how votes are transferred and options are selected at each step.

### Data Model

There are two primary data classes, Options and Participants.
Participants submit Ballots that rank the Options in order of priority, and the algorithm selects a subset of Options based on the ballots and each option's required support.
A Contest consists of a set of Options, Participants, and Ballots.
Ballots need to be validated as only containing option identifiers that exist in the Options set, and only one ballot per participant_id.
Contests need to be validated as only containing option identifiers that exist in the Options set, and only participant_id values that exist in the Participants set.
The data model should work with a variety of different single transferable vote algorithms, not just our generalization.

#### Options

- `option_id`: primary key
- `required_support`: fixed support threshold for selecting the option
- `title`: short, human-readable option title, 50 chars or less
- `description`: full-length, human-readable option description, many lines of text

#### Participants

- `participant_id`: primary key
- `name`: short, human-readable identifier
- `weight`: their voting weight, contribution amount, or other unit of support

#### Ballots

- `participant_id`: whose ballot is it
- `ranking`: ordered list of `option_id` values, with the first one being the highest priority for the participant and the last one being the lowest priority. May include as few as one `option_id` or as many as all `option_id` values.

#### Contest

Given a set of mutually consistent Options, Participants, and Ballots, the core contest object should be able to run the STV algorithm and return a list of selected option identifiers.
In addition to returning the final result of the contest, it should also be able to return a detailed log of the process, including the state of the contest at each step of the algorithm, and the final vote counts for each option.
This will aid in debugging, auditing, visualization, and user education about how the algorithm works.
In addition to the input data, the contest runner will be defined by several parameters that control the behavior of the process.
This will allow us to run different types of contests using the same underlying data model and algorithm, and also allow us to experiment with different parameters to see how they affect the results.
The parameters include:

### Data Serialization

- Data classes should be representable with simple, human-readable text files, using YAML, JSON, CSV, or other common formats.
- This will allow users to easily create and edit the data using a simple text editor and also facilitate version control of test data.
- When reading data from files, the system should validate that the data is consistent and meets the requirements outlined in the data model section.

### Testing

- Unit tests should be implemented for each component of the system, including the data model, the counting algorithm, and the data validation and serialization functions.
- Test data should be created to cover a variety of scenarios, including edge cases and potential failure modes.
- Tests should be automated and run as part of the development process to ensure that changes to the codebase do not introduce regressions or break existing functionality.
- Integration tests should be implemented to test the system as a whole, including the interaction between different components and the overall functionality of the contest process.
- In the case where each option has the same threshold, and each participant has the same weight, the algorithm should produce the same results as a standard Single Transferable Vote implementation.
- In the case where the total available support of all participants exceeds the total required support of all options, all options should be selected.
- In the case where the total available support of all participants is less than the required support of even the smallest option, no options should be selected.
- In the case where the total available support of all participants lies between the smallest option threshold and the total required support of all options, the algorithm should select only a subset of options.
- In the case where a participant ranks only one option, and that option is selected, the algorithm should ensure that the participant's entire weight is allocated to that option.
