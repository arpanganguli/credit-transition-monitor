"""Transparent prototype calculations, independent of Streamlit."""
__version__ = "0.1.0"
from .pipeline import analyse_portfolio, rank_borrowers
__all__ = ["analyse_portfolio", "rank_borrowers"]
