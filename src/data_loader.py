"""
data_loader.py

Purpose:
Provides a reusable function to read the large e-commerce dataset
in manageable chunks instead of loading the complete CSV into memory.

Why:
The raw dataset contains more than 42 million rows, so chunk-based
loading is required for memory-efficient processing.
"""


import pandas as pd
from pathlib import Path


DATA_PATH = Path("../data/raw/2019-Oct.csv")


def load_data_chunk(file_path=DATA_PATH, chunk_size=500_000):
    """
    Read the e-commerce dataset in chunks.

    Parameters
    ----------
    file_path : Path or str
        Location of the raw CSV file.
    chunk_size : int
        Number of rows to read at a time.

    Returns
    -------
    TextFileReader
        Pandas chunk iterator.
    """

    return pd.read_csv(
        file_path,
        chunksize=chunk_size
    )

