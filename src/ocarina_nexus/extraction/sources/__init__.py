"""One module per data source. Each exposes an `extract(**kwargs) -> int` entry
point returning the number of rows written, registered in `extraction/cli.py`."""
