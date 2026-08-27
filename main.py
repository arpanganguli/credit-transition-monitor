from pathlib import Path
import os
import sys

PROJECT_DIR = Path(__file__).resolve().parent
SRC_DIR = PROJECT_DIR / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))

from data.synthetic_portfolio_generator import create_synthetic_portfolio

def find_project_root(marker: str = "pyproject.toml") -> Path:
    path = Path(__file__).resolve().parent.parent.parent

    for parent in [path, *path.parents]:
        if (parent / marker).exists():
            return parent

    raise FileNotFoundError(
        f"Could not find project root containing {marker}"
    )


if __name__ == "__main__":
    PROJECT_ROOT = find_project_root()
    os.chdir(PROJECT_ROOT)
    print(f"Current working directory: {os.getcwd()}")

    portfolio = create_synthetic_portfolio()

    portfolio.to_csv(
        "data/synthetic_credit_portfolio.csv",
        index=False
    )

    print(portfolio.head(10))
    print()
    print(f"Rows: {len(portfolio)}")
    print(f"Borrowers: {portfolio['borrower_id'].nunique()}")