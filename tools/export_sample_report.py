#!/usr/bin/env python3
"""Export the sample SwitchItUp style plan."""

from pathlib import Path

from src.style_reports import export_sample_report


def main() -> None:
    print(export_sample_report(Path("reports/sample_style_report.csv")))


if __name__ == "__main__":
    main()
