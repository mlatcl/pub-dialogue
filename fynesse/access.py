"""
Access module for a Fynesse data science project.

This module is responsible for OBTAINING DATA from its source. It handles:
- Fetching data from APIs, databases, files, or web sources
- Authentication and connection management
- Documenting the legal and ethical basis for each data source
- Error handling for access failures

LEGAL AND ETHICAL REQUIREMENTS
================================
Every data source accessed here must have an accompanying note documenting:
- The license or terms of service under which the data is used
- Any privacy or GDPR considerations
- The provenance of the data (where it came from, who collected it)

WHAT BELONGS HERE
==================
- Functions that fetch or load raw data
- Connection setup for databases or APIs
- Documentation of data sources and their legal basis

WHAT DOES NOT BELONG HERE
==========================
- Data quality checks (those go in assess.py)
- Analysis or modelling (that goes in address.py)
- Logic that depends on the specific analysis question

EXAMPLE IMPLEMENTATION GUIDE
==============================
Replace the stub below with your actual data loading code:

    # Source: [name], License: [license], URL: [url]
    # Accessed: [date], Privacy: [any PII or consent notes]
    def data():
        try:
            df = pd.read_csv("https://example.com/data.csv")
            logger.info(f"Loaded {len(df)} rows from [source name]")
            return df
        except Exception as e:
            logger.error(f"Failed to access data: {e}")
            return None
"""

from typing import Optional
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def data() -> Optional[pd.DataFrame]:
    """Fetch and return the raw data from its source.

    IMPLEMENTATION GUIDE
    ====================
    Replace this function with code that loads your actual data source.

    Before writing any access code, document:
    1. Where the data comes from (URL, database name, file path pattern)
    2. The license or terms under which you are using it
    3. Any personally identifiable information and the applicable privacy framework
    4. The access date and data version if the source changes over time

    Returns
    -------
    pd.DataFrame or None
        The raw data as a DataFrame, or None if access failed.
    """
    # Source: [REPLACE — name and URL of data source]
    # License: [REPLACE — e.g. "OGL v3", "CC BY 4.0", "Proprietary, licensed for research"]
    # Provenance: [REPLACE — who collected it, how, when]
    # Privacy: [REPLACE — "No PII" or describe PII and applicable framework]

    logger.info("Starting data access — replace this stub with your data source")

    # REPLACE the code below with your actual data access logic
    logger.warning(
        "access.data() is using a stub implementation. "
        "Implement this function to load your data source."
    )
    return None
