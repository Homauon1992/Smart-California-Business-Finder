from __future__ import annotations

import argparse
import logging

from lead_scraper.exporters import export_to_csv, export_to_excel
from lead_scraper.maps_scraper import GoogleMapsLeadScraper, SearchTarget


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape California churches and hospitals from Google Maps."
    )
    parser.add_argument(
        "--total-leads",
        type=int,
        default=100,
        help="Total number of leads requested (default: 100).",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run browser in visible mode for debugging.",
    )
    parser.add_argument(
        "--csv-output",
        type=str,
        default="output/leads.csv",
        help="Path for CSV export.",
    )
    parser.add_argument(
        "--excel-output",
        type=str,
        default="output/leads.xlsx",
        help="Path for Excel export.",
    )
    return parser.parse_args()


def build_targets(total: int) -> list[SearchTarget]:
    # Split target between both lead categories.
    church_count = total // 2
    hospital_count = total - church_count
    return [
        SearchTarget(
            query="Churches in California",
            org_type="Church",
            max_items=church_count,
        ),
        SearchTarget(
            query="Hospitals in California",
            org_type="Hospital",
            max_items=hospital_count,
        ),
    ]


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    scraper = GoogleMapsLeadScraper(headless=not args.headful)
    targets = build_targets(args.total_leads)
    leads = scraper.scrape(targets)

    export_to_csv(leads, args.csv_output)
    export_to_excel(leads, args.excel_output)

    logging.info("Saved %s leads.", len(leads))
    logging.info("CSV: %s", args.csv_output)
    logging.info("Excel: %s", args.excel_output)


if __name__ == "__main__":
    main()
