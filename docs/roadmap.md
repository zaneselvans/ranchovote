# Development Roadmap

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
