"""Ranked Choice Budgeting.

This module implements a method of selecting projects to fund based on the ranked
preferences of funders.

Each project has a fixed budget. The budgets of the projects can differ from each other.
In order to be selected a project must be fully funded.

Each funder has a fixed budget to allocate. The budgets of the funders can differ from
each other.

The total budget of all the projects is assumed to be larger than the sum of the budgets
of the funders -- otherwise all projects would simply be funded regardless of funder
preferences.

The only input required from the funders is to rank the projects in order of preference.

"""

from typing import TypedDict

import pandas as pd
from pydantic import BaseModel

# Class defining a set of projects and their budgets.
# A typed dictionary with string keys and decimal values.

Projects = TypedDict("Projects", {str: float})

# Class defining a set of participants and their contributions.

Funders = TypedDict("Participants", {str: float})


class RankedPreferences(BaseModel):
    """A class defining the ranked preferences of participants for projects."""

    projects: Projects
    participants: Funders
    rankings: pd.DataFrame
    """A DataFrame with participants as rows and projects as columns."""
