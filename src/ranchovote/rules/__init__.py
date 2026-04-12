"""Reusable rule components used to assemble counting methods.

Rather than baking every decision into one monolithic algorithm, ranchovote separates
threshold calculation, ballot allocation, option selection, exclusion, tie-breaking,
and surplus transfer into smaller rule objects. That decomposition makes method
behavior easier to reason about and easier to swap during experimentation.
"""
