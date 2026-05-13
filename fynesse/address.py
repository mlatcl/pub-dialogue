"""
Address module for a Fynesse data science project.

This module is responsible for ANSWERING THE ANALYSIS QUESTION using data
that has already been accessed and assessed. This is where statistical
modelling, machine learning, visualisation, and dashboarding live.

WHAT BELONGS HERE
==================
- Analysis functions specific to the research or business question
- Statistical modelling and machine learning pipelines
- Visualisations intended to communicate results (not just data quality)
- Question-specific feature engineering and cleaning
- Dashboard generation and report production

WHAT DOES NOT BELONG HERE
==========================
- Direct data access: do not call pd.read_csv() or API functions here.
  Call assess.data() to get the pre-assessed dataset.
- General data quality work: that belongs in assess.py.
- Logic that is not specific to the analysis question.

CALLING CONVENTION
==================
Address functions receive assessed data as input:

    assessed_df = assess.data()
    results = address.analyze_data(assessed_df)

Do not call access.data() from address.py except in exceptional
circumstances that must be documented with a comment explaining why.

EXAMPLE ANALYSIS TYPES
========================
- Confirmatory statistics: hypothesis tests, confidence intervals
- Predictive modelling: regression, classification, time series
- Causal inference: difference-in-differences, regression discontinuity
- Visualisation: maps, dashboards, summary charts for decision-makers
- Descriptive analysis: cohort summaries, segment comparisons
"""

from typing import Any, Union
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def analyze_data(data: Union[pd.DataFrame, Any]) -> dict:
    """Answer the analysis question using assessed data.

    IMPLEMENTATION GUIDE
    ====================
    Replace this stub with your actual analysis code. Your implementation
    should:

    1. Receive assessed data as input (do not fetch data here)
    2. Apply question-specific feature engineering or cleaning
    3. Fit models, run statistical tests, or generate visualisations
    4. Return results in a structured format

    Parameters
    ----------
    data : pd.DataFrame
        Assessed data returned by assess.data(). Should not be None.

    Returns
    -------
    dict
        Analysis results. Structure depends on your analysis question.
        At minimum, document what keys the returned dict contains.
    """
    if data is None:
        logger.error("No data provided to address.analyze_data()")
        return {"error": "No data provided"}

    if hasattr(data, '__len__') and len(data) == 0:
        logger.error("Empty dataset provided to address.analyze_data()")
        return {"error": "Empty dataset"}

    logger.info(f"Addressing question with {len(data)} rows of assessed data")

    # REPLACE: add your actual analysis code below
    # Examples of what might go here:
    #
    # # Question-specific feature engineering
    # data = data.copy()
    # data['log_price'] = np.log(data['price'])
    #
    # # Fit a model
    # from sklearn.linear_model import LinearRegression
    # model = LinearRegression()
    # model.fit(X_train, y_train)
    #
    # # Return structured results
    # return {
    #     "model": model,
    #     "r_squared": model.score(X_test, y_test),
    #     "coefficients": dict(zip(features, model.coef_))
    # }

    logger.warning(
        "address.analyze_data() is using a stub implementation. "
        "Implement this function to answer your analysis question."
    )

    return {
        "sample_size": len(data),
        "columns": list(data.columns) if hasattr(data, 'columns') else [],
        "note": "Stub implementation — replace with actual analysis"
    }
