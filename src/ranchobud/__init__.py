"""ranchobud: An algorithm for ranked-choice co-budgeting.

The ranchobud package implements a ranked-choice budgeting algorithm that allows funders
to allocate funding based on their ranked preferences for projects. It is a
generalization of the single transferable vote (STV) ranked-choice voting system, in
which projects under consideration are analogous to candidates, and funders are
analogous to voters. The budget for each project is analogous to the election quota
required for a candidate to be elected.

The algorithm allows funders with unequal budgets to collaboratively prioritize the
funding of a number of different projects. Each project has a fixed budget required for
completion, but the budgets of projects can vary.
"""
