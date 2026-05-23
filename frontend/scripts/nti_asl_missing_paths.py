"""
Deprecated: missing letters now come from Wikimedia line-art (see extract_asl_from_wikimedia.py).
This module re-exports the Wikimedia pipeline for backwards compatibility.
"""
from extract_asl_from_wikimedia import main

if __name__ == "__main__":
    main()
