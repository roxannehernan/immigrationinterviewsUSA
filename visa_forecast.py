#!/usr/bin/env python3
"""
Department of State Immigration Case & Consulate Interview Forecaster
=====================================================================
Fetches visa bulletin data, NVC processing times, and CEAC case status
from the U.S. Department of State, then forecasts likely consulate
interview scheduling windows.

Requirements:
    pip install requests beautifulsoup4 pandas numpy matplotlib

Usage:
    python visa_forecast.py --category F2B --country mexico
    python visa_forecast.py --category EB3 --chargeability all
    python visa_forecast.py --list-categories
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
    import numpy as np
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install requests beautifulsoup4 pandas numpy matplotlib")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://travel.state.gov"

VISA_BULLETIN_INDEX = (
    f"{BASE_URL}/content/travel/en/legal/visa-law0/"
    "visa-bulletin.html"
)

# Family-based and employment-based preference categories
FAMILY_CATEGORIES = ["F1", "F2A", "F2B", "F3", "F4"]
EMPLOYMENT_CATEGORIES = ["EB1", "EB2", "EB3", "EB4", "EB5", "EB5_RURAL",
                          "EB5_INFRA", "EB5_HIGH_UNEMPLOY"]

ALL_CATEGORIES = FAMILY_CATEGORIES + EMPLOYMENT_CATEGORIES

CHARGEABILITY_REGIONS = [
    "all", "china_mainland", "india", "mexico", "philippines"
]

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

class StateDeptScraper:
    """Scrapes visa bulletin and processing time data from travel.state.gov."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; VisaForecast/1.0; "
                "educational research tool)"
            )
        })

    # -- Visa Bulletin --------------------------------------------------

    def get_bulletin_links(self, count: int = 13) -> list[dict]:
        """
        Fetch the visa bulletin index page and return links to the most
        recent `count` monthly bulletins.
        Returns list of {"month": str, "year": int, "url": str}.
        """
        print(f"[*] Fetching visa bulletin index from {VISA_BULLETIN_INDEX}")
        resp = self.session.get(VISA_BULLETIN_INDEX, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        bulletins = []
        # Bulletin links follow pattern: visa-bulletin-for-<month>-<year>.html
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            match = re.search(
                r"visa-bulletin-for-(\w+)-(\d{4})", href, re.IGNORECASE
            )
            if match:
                month_name = match.group(1).lower()
                year = int(match.group(2))
                if month_name in MONTH_MAP:
                    url = href if href.startswith("http") else BASE_URL + href
                    bulletins.append({
                        "month": month_name,
                        "month_num": MONTH_MAP[month_name],
                        "year": year,
                        "url": url,
                    })

        # Deduplicate and sort descending
        seen = set()
        unique = []
        for b in bulletins:
            key = (b["year"], b["month_num"])
            if key not in seen:
                seen.add(key)
                unique.append(b)
        unique.sort(key=lambda x: (x["year"], x["month_num"]), reverse=True)
        return unique[:count]

    def parse_bulletin_page(self, url: str) -> dict:
        """
        Parse a single visa bulletin page and extract cutoff dates for
        both Final Action and Dates for Filing charts.
        Returns nested dict: {table_type: {category: {region: date_str}}}.
        """
        print(f"  [>] Parsing bulletin: {url}")
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tables = soup.find_all("table")
        result = {"final_action": {}, "dates_for_filing": {}}

        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            headers = [th.get_text(strip=True).lower()
                       for th in rows[0].find_all(["th", "td"])]

            # Determine which chart this table belongs to
            preceding_text = ""
            prev = table.find_previous(["h2", "h3", "h4", "p", "strong"])
            if prev:
                preceding_text = prev.get_text(strip=True).lower()

            if "filing" in preceding_text or "dates for filing" in preceding_text:
                target = result["dates_for_filing"]
            else:
                target = result["final_action"]

            # Map header columns to chargeability regions
            col_map = {}
            for i, h in enumerate(headers):
                if i == 0:
                    continue  # category column
                if "china" in h:
                    col_map[i] = "china_mainland"
                elif "india" in h:
                    col_map[i] = "india"
                elif "mexico" in h:
                    col_map[i] = "mexico"
                elif "philippines" in h:
                    col_map[i] = "philippines"
                elif "all" in h or "world" in h or "other" in h:
                    col_map[i] = "all"

            if not col_map:
                continue

            for row in rows[1:]:
                cells = row.find_all(["th", "td"])
                if not cells:
                    continue
                cat_text = cells[0].get_text(strip=True).upper()
                cat_text = re.sub(r"[^A-Z0-9_]", "", cat_text)

                # Normalize category names
                cat_key = None
                for cat in ALL_CATEGORIES:
                    if cat.replace("_", "") in cat_text.replace("_", ""):
                        cat_key = cat
                        break
                if cat_key is None:
                    # Try partial match
                    for cat in ALL_CATEGORIES:
                        if cat_text.startswith(cat.replace("_", "")):
                            cat_key = cat
                            break
                if cat_key is None:
                    continue

                if cat_key not in target:
                    target[cat_key] = {}

                for col_idx, region in col_map.items():
                    if col_idx < len(cells):
                        val = cells[col_idx].get_text(strip=True)
                        target[cat_key][region] = val

        return result

    def fetch_bulletin_history(self, months: int = 13) -> pd.DataFrame:
        """
        Fetch multiple months of visa bulletin data and return a DataFrame
        with columns: bulletin_date, table_type, category, region, cutoff_raw,
        cutoff_date.
        """
        links = self.get_bulletin_links(count=months)
        if not links:
            print("[!] No bulletin links found. The page structure may have changed.")
            return pd.DataFrame()

        records = []
        for link in links:
            bulletin_date = datetime(link["year"], link["month_num"], 1)
            try:
                data = self.parse_bulletin_page(link["url"])
            except Exception as exc:
                print(f"  [!] Error parsing {link['url']}: {exc}")
                continue

            for table_type, categories in data.items():
                for category, regions in categories.items():
                    for region, date_str in regions.items():
                        parsed = self._parse_cutoff_date(date_str)
                        records.append({
                            "bulletin_date": bulletin_date,
                            "table_type": table_type,
                            "category": category,
                            "region": region,
                            "cutoff_raw": date_str,
                            "cutoff_date": parsed,
                        })

        df = pd.DataFrame(records)
        if not df.empty:
            df.sort_values(["category", "region", "bulletin_date"],
                           inplace=True)
            df.reset_index(drop=True, inplace=True)
        return df

    @staticmethod
    def _parse_cutoff_date(raw: str) -> Optional[datetime]:
        """Parse a cutoff date string like '01JAN23' or 'C' (current)."""
        raw = raw.strip().upper()
        if raw in ("C", "CURRENT", ""):
            return datetime.today()
        if raw in ("U", "UNAVAILABLE"):
            return None

        # Patterns: 01JAN23, 01JAN2023, 01-Jan-2023, Jan 01 2023, etc.
        for fmt in ("%d%b%y", "%d%b%Y", "%d-%b-%y", "%d-%b-%Y",
                     "%b %d, %Y", "%B %d, %Y", "%d %b %Y"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None


# ---------------------------------------------------------------------------
# Forecasting Engine
# ---------------------------------------------------------------------------

class InterviewForecaster:
    """
    Forecasts future consulate interview windows based on historical
    visa bulletin cutoff date movement.
    """

    def __init__(self, bulletin_df: pd.DataFrame):
        self.df = bulletin_df

    def movement_analysis(
        self, category: str, region: str,
        table_type: str = "final_action"
    ) -> pd.DataFrame:
        """
        Compute month-over-month cutoff date movement (in days) for a
        given category and region.
        """
        mask = (
            (self.df["category"] == category.upper())
            & (self.df["region"] == region.lower())
            & (self.df["table_type"] == table_type)
            & (self.df["cutoff_date"].notna())
        )
        subset = self.df.loc[mask].copy()
        if subset.empty:
            return pd.DataFrame()

        subset.sort_values("bulletin_date", inplace=True)
        subset["prev_cutoff"] = subset["cutoff_date"].shift(1)
        subset["movement_days"] = (
            subset["cutoff_date"] - subset["prev_cutoff"]
        ).dt.days
        subset.dropna(subset=["movement_days"], inplace=True)
        return subset

    def forecast_interview_date(
        self,
        category: str,
        region: str,
        priority_date: datetime,
        table_type: str = "final_action",
        confidence: float = 0.80,
    ) -> dict:
        """
        Given a priority date, forecast when the cutoff date will reach
        it — i.e., when a consulate interview is likely to be scheduled.

        Uses historical movement rates with a simple linear projection
        plus variance-based confidence intervals.

        Returns dict with projected date range and statistics.
        """
        movement = self.movement_analysis(category, region, table_type)
        if movement.empty:
            return {"error": "Insufficient data for this category/region."}

        # Latest cutoff
        latest = movement.iloc[-1]
        latest_cutoff = latest["cutoff_date"]
        latest_bulletin = latest["bulletin_date"]

        # Days remaining until priority date becomes current
        days_remaining = (priority_date - latest_cutoff).days
        if days_remaining <= 0:
            return {
                "status": "CURRENT",
                "message": (
                    "Your priority date is already current. You should "
                    "expect NVC processing and interview scheduling soon."
                ),
                "latest_cutoff": latest_cutoff,
                "priority_date": priority_date,
            }

        # Movement statistics
        moves = movement["movement_days"].values
        avg_move = float(np.mean(moves))
        std_move = float(np.std(moves, ddof=1)) if len(moves) > 1 else 0
        median_move = float(np.median(moves))

        if avg_move <= 0:
            return {
                "status": "RETROGRESSED",
                "message": (
                    "This category/region is currently retrogressing or "
                    "stalled. Forecasting is unreliable."
                ),
                "avg_monthly_movement_days": round(avg_move, 1),
                "latest_cutoff": latest_cutoff,
            }

        # Months until current (point estimate)
        months_est = days_remaining / avg_move
        projected_date = latest_bulletin + timedelta(days=months_est * 30.44)

        # Confidence interval using z-score approximation
        from scipy.stats import norm
        z = norm.ppf(1 - (1 - confidence) / 2) if 'norm' in dir() else 1.28

        # Fallback if scipy not available
        try:
            from scipy.stats import norm as sp_norm
            z = sp_norm.ppf(1 - (1 - confidence) / 2)
        except ImportError:
            z_map = {0.80: 1.28, 0.90: 1.645, 0.95: 1.96}
            z = z_map.get(confidence, 1.28)

        if std_move > 0 and avg_move > 0:
            # Optimistic: faster movement -> sooner
            opt_move = avg_move + z * std_move
            months_opt = days_remaining / opt_move
            date_early = latest_bulletin + timedelta(days=months_opt * 30.44)

            # Pessimistic: slower movement -> later
            pess_move = max(avg_move - z * std_move, avg_move * 0.25)
            months_pess = days_remaining / pess_move
            date_late = latest_bulletin + timedelta(days=months_pess * 30.44)
        else:
            date_early = projected_date - timedelta(days=60)
            date_late = projected_date + timedelta(days=120)

        # NVC processing buffer (typically 2-6 months after becoming current)
        nvc_buffer_min = 60
        nvc_buffer_max = 180
        interview_early = date_early + timedelta(days=nvc_buffer_min)
        interview_late = date_late + timedelta(days=nvc_buffer_max)

        return {
            "status": "PROJECTED",
            "priority_date": priority_date.strftime("%Y-%m-%d"),
            "latest_cutoff": latest_cutoff.strftime("%Y-%m-%d"),
            "latest_bulletin": latest_bulletin.strftime("%Y-%m-%d"),
            "days_remaining": days_remaining,
            "avg_monthly_movement_days": round(avg_move, 1),
            "median_monthly_movement_days": round(median_move, 1),
            "std_monthly_movement_days": round(std_move, 1),
            "months_data_points": len(moves),
            "estimated_current_date": projected_date.strftime("%Y-%m-%d"),
            "confidence_level": f"{confidence:.0%}",
            "current_date_range": {
                "earliest": date_early.strftime("%Y-%m-%d"),
                "latest": date_late.strftime("%Y-%m-%d"),
            },
            "interview_window": {
                "earliest": interview_early.strftime("%Y-%m-%d"),
                "latest": interview_late.strftime("%Y-%m-%d"),
                "note": (
                    "Includes estimated NVC processing time of "
                    f"{nvc_buffer_min}-{nvc_buffer_max} days after becoming "
                    "current."
                ),
            },
        }

    def summary_table(
        self, category: str, region: str,
        table_type: str = "final_action"
    ) -> pd.DataFrame:
        """Return a readable summary of recent cutoff movements."""
        movement = self.movement_analysis(category, region, table_type)
        if movement.empty:
            return pd.DataFrame()

        summary = movement[[
            "bulletin_date", "cutoff_date", "cutoff_raw", "movement_days"
        ]].copy()
        summary["bulletin_date"] = summary["bulletin_date"].dt.strftime("%b %Y")
        summary["cutoff_date"] = summary["cutoff_date"].dt.strftime("%Y-%m-%d")
        summary.rename(columns={
            "bulletin_date": "Bulletin",
            "cutoff_date": "Cutoff Date",
            "cutoff_raw": "Raw",
            "movement_days": "Movement (days)",
        }, inplace=True)
        return summary


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_forecast(movement_df: pd.DataFrame, forecast: dict,
                  category: str, region: str):
    """Generate a matplotlib chart of cutoff movement and forecast."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("[!] matplotlib not installed — skipping chart.")
        return

    if movement_df.empty or forecast.get("status") != "PROJECTED":
        return

    fig, ax = plt.subplots(figsize=(12, 5))

    # Historical cutoff dates
    ax.plot(
        movement_df["bulletin_date"],
        movement_df["cutoff_date"],
        "o-", color="#2563eb", linewidth=2, markersize=5,
        label="Historical cutoff",
    )

    # Projected point
    proj_date = datetime.strptime(forecast["estimated_current_date"], "%Y-%m-%d")
    priority_date = datetime.strptime(forecast["priority_date"], "%Y-%m-%d")
    ax.axhline(y=priority_date, color="#dc2626", linestyle="--",
               linewidth=1, label=f"Your priority date ({forecast['priority_date']})")

    # Interview window shading
    iv_early = datetime.strptime(
        forecast["interview_window"]["earliest"], "%Y-%m-%d")
    iv_late = datetime.strptime(
        forecast["interview_window"]["latest"], "%Y-%m-%d")
    ax.axvspan(iv_early, iv_late, alpha=0.15, color="#16a34a",
               label="Estimated interview window")

    ax.set_title(
        f"Visa Bulletin Cutoff Trend & Interview Forecast\n"
        f"Category: {category.upper()} | Region: {region.title()}",
        fontsize=13, fontweight="bold",
    )
    ax.set_xlabel("Bulletin Month")
    ax.set_ylabel("Cutoff / Priority Date")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = f"visa_forecast_{category}_{region}.png"
    plt.savefig(out_path, dpi=150)
    print(f"[✓] Chart saved to {out_path}")
    plt.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Forecast U.S. consulate interview dates from DoS visa bulletin data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --category EB2 --country india --priority-date 2020-06-15
  %(prog)s --category F2B --country mexico --months 24
  %(prog)s --list-categories
  %(prog)s --category EB3 --country all --priority-date 2022-01-01 --chart
        """,
    )
    parser.add_argument(
        "--category", "-c",
        choices=[c.lower() for c in ALL_CATEGORIES],
        help="Visa preference category (e.g. EB2, F2B).",
    )
    parser.add_argument(
        "--country", "-r",
        choices=CHARGEABILITY_REGIONS,
        default="all",
        help="Chargeability region (default: all/rest-of-world).",
    )
    parser.add_argument(
        "--priority-date", "-p",
        help="Your priority date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--table-type", "-t",
        choices=["final_action", "dates_for_filing"],
        default="final_action",
        help="Which chart to use (default: final_action).",
    )
    parser.add_argument(
        "--months", "-m", type=int, default=13,
        help="Number of months of bulletin history to fetch (default: 13).",
    )
    parser.add_argument(
        "--confidence", type=float, default=0.80,
        help="Confidence level for interval (default: 0.80).",
    )
    parser.add_argument(
        "--chart", action="store_true",
        help="Generate a matplotlib chart of the forecast.",
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Output forecast result as JSON.",
    )
    parser.add_argument(
        "--list-categories", action="store_true",
        help="List all supported visa categories and exit.",
    )
    parser.add_argument(
        "--save-csv", metavar="PATH",
        help="Save raw bulletin data to a CSV file.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list_categories:
        print("Family-based:     ", ", ".join(FAMILY_CATEGORIES))
        print("Employment-based: ", ", ".join(EMPLOYMENT_CATEGORIES))
        print("Regions:          ", ", ".join(CHARGEABILITY_REGIONS))
        return

    if not args.category:
        parser.error("--category is required (use --list-categories to see options).")

    category = args.category.upper()
    region = args.country.lower()

    # --- Fetch data ---
    scraper = StateDeptScraper()
    print(f"\n{'='*60}")
    print(f"  Visa Bulletin Forecast Tool")
    print(f"  Category: {category} | Region: {region}")
    print(f"  Fetching {args.months} months of bulletin data...")
    print(f"{'='*60}\n")

    df = scraper.fetch_bulletin_history(months=args.months)
    if df.empty:
        print("[!] No data retrieved. Check your internet connection and try again.")
        sys.exit(1)

    print(f"\n[✓] Retrieved {len(df)} data points across "
          f"{df['bulletin_date'].nunique()} bulletins.\n")

    if args.save_csv:
        df.to_csv(args.save_csv, index=False)
        print(f"[✓] Raw data saved to {args.save_csv}\n")

    # --- Analysis ---
    forecaster = InterviewForecaster(df)

    # Show movement summary
    summary = forecaster.summary_table(category, region, args.table_type)
    if summary.empty:
        print(f"[!] No data found for {category} / {region} / {args.table_type}.")
        print("    Try a different category or region.")
        sys.exit(1)

    print(f"--- Recent Cutoff Movements ({args.table_type}) ---")
    print(summary.to_string(index=False))
    print()

    # --- Forecast ---
    if args.priority_date:
        try:
            pd_date = datetime.strptime(args.priority_date, "%Y-%m-%d")
        except ValueError:
            print("[!] Invalid date format. Use YYYY-MM-DD.")
            sys.exit(1)

        forecast = forecaster.forecast_interview_date(
            category=category,
            region=region,
            priority_date=pd_date,
            table_type=args.table_type,
            confidence=args.confidence,
        )

        if args.output_json:
            print(json.dumps(forecast, indent=2, default=str))
        else:
            print("--- Interview Forecast ---")
            for key, val in forecast.items():
                if isinstance(val, dict):
                    print(f"  {key}:")
                    for k2, v2 in val.items():
                        print(f"    {k2}: {v2}")
                else:
                    print(f"  {key}: {val}")

        # Chart
        if args.chart and forecast.get("status") == "PROJECTED":
            movement = forecaster.movement_analysis(
                category, region, args.table_type)
            plot_forecast(movement, forecast, category, region)
    else:
        print(
            "Tip: Add --priority-date YYYY-MM-DD to get a personalized "
            "interview forecast."
        )


if __name__ == "__main__":
    main()
