"""
Assess module for a Fynesse data science project.

This module is responsible for UNDERSTANDING THE DATA returned by the access
module. It examines data properties and quality WITHOUT reference to the
specific analysis question.

CRITICAL RULE: ASSESS WITHOUT THE QUESTION
===========================================
Everything in this module must be performable without knowing what question
the data will be used to answer. This means:

- DO document how missing values are encoded
- DO check data types and flag unexpected values
- DO visualise distributions and flag outliers
- DO perform cleaning that is always justified (e.g. drop completely empty rows)
- DON'T impute values using a method chosen for a specific model
- DON'T drop columns because they are irrelevant to a specific question
- DON'T filter rows to match a cohort definition from the analysis question

WHY THIS MATTERS
================
Question-agnostic assessment is a public good. Another analyst working on
the same dataset for a different question should be able to use this module
directly, without repeating quality assessment work.

WHAT BELONGS HERE
==================
- Functions that check data quality and structure
- Visualisations of data properties (distributions, missing values)
- Light cleaning that is always justified by the data properties
- Summary statistics and metadata about the dataset

WHAT DOES NOT BELONG HERE
==========================
- Question-specific feature engineering (that goes in address.py)
- Imputation decisions motivated by a downstream model (that goes in address.py)
- Direct data access (use access.data() — do not read files here)
"""

from typing import Any, Optional, Union
import pandas as pd
import logging

from . import access

logger = logging.getLogger(__name__)


def data() -> Optional[pd.DataFrame]:
    """Load data via access and return an assessed, quality-checked version.

    This function calls access.data(), examines the data's properties,
    performs question-agnostic quality checks, and returns a cleaned
    DataFrame ready for use in address.py.

    IMPLEMENTATION GUIDE
    ====================
    Replace this stub with your actual assessment code. Your implementation
    should:

    1. Call access.data() to get the raw data
    2. Examine and document: missing value patterns, data types, value ranges,
       outlier counts, and any encoding surprises
    3. Perform only cleaning that is justified by data properties alone:
       - Correcting data type mismatches (e.g. dates stored as strings)
       - Dropping rows that are entirely empty
       - Standardising known encodings (e.g. -999 → NaN if documented)
    4. Log what you found so collaborators can understand the data quality

    Returns
    -------
    pd.DataFrame or None
        Assessed data ready for use in address.py, or None if access failed.
    """
    logger.info("Starting data assessment")

    df = access.data()
    if df is None:
        logger.error("No data returned from access.data() — cannot assess")
        return None

    logger.info(f"Received data: {len(df)} rows, {len(df.columns)} columns")

    # REPLACE: add your actual quality assessment code below
    # Example checks you might want to implement:
    #
    # missing = df.isnull().sum()
    # logger.info(f"Missing values per column: {missing[missing > 0].to_dict()}")
    #
    # logger.info(f"Data types: {df.dtypes.to_dict()}")
    #
    # # Question-agnostic cleaning — always justified
    # rows_before = len(df)
    # df = df.dropna(how='all')
    # if len(df) < rows_before:
    #     logger.info(f"Dropped {rows_before - len(df)} completely empty rows")

    logger.warning(
        "assess.data() is using a stub implementation. "
        "Implement this function to assess your data quality."
    )
    return df


def query(data: Union[pd.DataFrame, Any]) -> str:
    """Request user input to clarify some aspect of the data.

    Use this for human-in-the-loop quality checks where automated
    assessment is not sufficient.

    Parameters
    ----------
    data : DataFrame
        The data to query about.

    Returns
    -------
    str
        User response.
    """
    raise NotImplementedError(
        "Implement query() to ask a human to verify a data quality aspect"
    )


def view(data: Union[pd.DataFrame, Any]) -> None:
    """Produce a visualisation to verify some aspect of data quality.

    Parameters
    ----------
    data : DataFrame
        The data to visualise.
    """
    raise NotImplementedError(
        "Implement view() to visualise a data quality property "
        "(e.g. missing value map, distribution plot)"
    )


def labelled(data: Union[pd.DataFrame, Any]) -> Union[pd.DataFrame, Any]:
    """Return a labelled subset of the data for supervised learning.

    Labelling is a property of the data (ground truth labels exist or
    can be derived from the data itself), not a question-specific operation.
    This is distinct from address-level feature engineering.

    Parameters
    ----------
    data : DataFrame
        The assessed data.

    Returns
    -------
    DataFrame
        A subset of the data with labels attached.
    """
    raise NotImplementedError(
        "Implement labelled() to return a labelled subset "
        "for supervised learning tasks"
    )
