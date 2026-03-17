"""Main entry point for running the Argo data pipeline."""

import argparse
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floatchat.pipeline.client import ArgoAPIClient
from floatchat.pipeline.processor import ArgoStreamProcessor
from floatchat.pipeline.runner import stream_multiple_floats

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def query_data_example(db_url: str = "sqlite:///data/databases/argo_data.db"):
    """Print data summary for quick verification."""
    engine = create_engine(db_url)

    print("\n=== Data Summary ===")

    query = "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name='profiles'"
    table_exists = pd.read_sql(query, engine)["count"].values[0] > 0
    if not table_exists:
        print("No profiles table found yet (no qualifying floats ingested).")
        return

    query = "SELECT COUNT(*) as count FROM profiles"
    result = pd.read_sql(query, engine)
    print(f"Total profiles: {result['count'].values[0]}")

    query = "SELECT COUNT(*) as count FROM measurements"
    result = pd.read_sql(query, engine)
    print(f"Total measurements: {result['count'].values[0]}")

    query = """
    SELECT
        MIN(latitude) as min_lat, MAX(latitude) as max_lat,
        MIN(longitude) as min_lon, MAX(longitude) as max_lon,
        COUNT(DISTINCT float_id) as num_floats
    FROM profiles
    """
    result = pd.read_sql(query, engine)
    print("\nGeographic coverage:")
    print(result)

    query = """
    SELECT float_id, datetime, latitude, longitude, cycle_number
    FROM profiles
    WHERE datetime IS NOT NULL
    ORDER BY datetime DESC
    LIMIT 5
    """
    result = pd.read_sql(query, engine)
    print("\nRecent profiles:")
    print(result)


def clear_sqlite_db(db_file: Path):
    """Reset local SQLite database for a clean targeted ingest."""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    if db_file.exists():
        db_file.unlink()
        logger.info("Removed existing DB file: %s", db_file)


def matches_demo_window(profiles_df: pd.DataFrame, mode: str = "strict") -> bool:
    """Return True when dataset contains demo-window profiles under given mode."""
    if profiles_df.empty:
        return False

    timestamps = pd.to_datetime(profiles_df["datetime"], errors="coerce")

    if mode == "strict":
        mask = (
            (timestamps >= pd.Timestamp("2023-03-01"))
            & (timestamps < pd.Timestamp("2023-04-01"))
            & (profiles_df["latitude"].between(-5, 5, inclusive="both"))
            & (profiles_df["longitude"].between(50, 100, inclusive="both"))
        )
    else:
        mask = (
            timestamps.notna()
            & (profiles_df["latitude"].between(-30, 30, inclusive="both"))
            & (profiles_df["longitude"].between(30, 120, inclusive="both"))
        )

    return bool(mask.any())


def ingest_targeted_demo_data(
    db_url: str = "sqlite:///data/databases/argo_data.db",
    centers: list[str] | None = None,
    target_floats: int = 5,
    max_scan_per_center: int = 200,
    max_no_match_per_center: int = 60,
    match_mode: str = "strict",
    max_runtime_minutes: int = 8,
):
    """Ingest only floats that satisfy the March 2023 equatorial Indian Ocean criteria."""
    if centers is None:
        centers = ["incois", "csio", "jma", "coriolis"]

    api = ArgoAPIClient()
    processor = ArgoStreamProcessor()
    selected = []
    start_time = time.time()

    def runtime_exceeded() -> bool:
        return (time.time() - start_time) > (max_runtime_minutes * 60)

    for center in centers:
        if runtime_exceeded():
            logger.info("Stopping targeted ingest: runtime budget (%s min) reached", max_runtime_minutes)
            break

        if len(selected) >= target_floats:
            break

        logger.info("Scanning center: %s", center)
        float_ids = api.list_floats(center, max_floats=None)
        float_ids = [fid for fid in float_ids if fid.isdigit() and len(fid) >= 4]
        float_ids = sorted(float_ids, key=int, reverse=True)[:max_scan_per_center]
        logger.info("Scanning %s candidate float IDs in %s", len(float_ids), center)
        skipped_count = 0
        fetched_count = 0

        for float_id in float_ids:
            if runtime_exceeded():
                logger.info("Stopping center %s: runtime budget reached", center)
                break

            if len(selected) >= target_floats:
                break

            ds, local_file = api.fetch_float_data(center, float_id)
            if ds is None:
                continue
            fetched_count += 1

            try:
                profiles_df = processor.extract_profiles(ds, float_id, center)
                if matches_demo_window(profiles_df, mode=match_mode):
                    logger.info(
                        "Selected float %s from %s (matches %s demo window)",
                        float_id,
                        center,
                        match_mode,
                    )
                    processor.stream_to_sql(ds, float_id, center, db_url=db_url)
                    selected.append((center, float_id))
                else:
                    skipped_count += 1
                    if skipped_count % 25 == 0:
                        logger.info(
                            "Skipped %s float(s) in %s with no %s match so far",
                            skipped_count,
                            center,
                            match_mode,
                        )
                    if skipped_count >= max_no_match_per_center:
                        logger.info(
                            "Stopping center %s early after %s no-match floats (fast-fail threshold reached)",
                            center,
                            skipped_count,
                        )
                        break
            except Exception as exc:
                logger.warning("Failed while evaluating float %s/%s: %s", center, float_id, exc)
            finally:
                try:
                    ds.close()
                except Exception:
                    pass

                if local_file and os.path.exists(local_file):
                    os.remove(local_file)

        logger.info(
            "Center %s scan summary: fetched=%s, skipped_no_match=%s, selected_total=%s",
            center,
            fetched_count,
            skipped_count,
            len(selected),
        )

    if selected:
        processor.create_indexes(db_url=db_url)

    logger.info("Targeted ingest complete. Selected %s float(s).", len(selected))
    for center, float_id in selected:
        logger.info("  - %s/%s", center, float_id)

    if not selected:
        logger.warning(
            "No qualifying floats were found for mode=%s. "
            "Try increasing --max-scan-per-center or widening the latitude/longitude window temporarily "
            "for data bootstrap.",
            match_mode,
        )

    return selected


def validate_demo_window(db_file: Path):
        """Run Phase 1 validation SQL and print a data-driven golden-query suggestion."""
        if not db_file.exists():
                print("Validation skipped: database file does not exist.")
                return

        conn = sqlite3.connect(str(db_file))
        try:
                table_exists = conn.execute(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='profiles'"
                ).fetchone()[0]
                if not table_exists:
                        print("\nPhase 1 validation skipped: profiles table does not exist yet.")
                        return

                strict_query = """
                SELECT COUNT(*) AS n
                FROM profiles
                WHERE datetime >= '2023-03-01'
                    AND datetime < '2023-04-01'
                    AND latitude BETWEEN -5 AND 5
                    AND longitude BETWEEN 50 AND 100;
                """
                strict_n = conn.execute(strict_query).fetchone()[0]
                print(f"\nPhase 1 strict count (March 2023 equatorial Indian Ocean): {strict_n}")

                broad_query = """
                SELECT COUNT(*) AS n
                FROM profiles
                WHERE datetime IS NOT NULL
                    AND latitude BETWEEN -30 AND 30
                    AND longitude BETWEEN 30 AND 120;
                """
                broad_n = conn.execute(broad_query).fetchone()[0]
                print(f"Phase 1 broad Indian-ocean count (data-driven mode): {broad_n}")

                suggestion_query = """
                SELECT strftime('%Y-%m', datetime) AS ym, COUNT(*) AS n
                FROM profiles
                WHERE datetime IS NOT NULL
                    AND latitude BETWEEN -30 AND 30
                    AND longitude BETWEEN 30 AND 120
                GROUP BY ym
                ORDER BY n DESC
                LIMIT 1;
                """
                best = conn.execute(suggestion_query).fetchone()
                if best and best[0]:
                        print(
                                "Suggested data-driven golden query: "
                                f"'Show salinity profiles near the equator in {best[0]}'"
                        )
        finally:
                conn.close()


def main():
    parser = argparse.ArgumentParser(description="Run Argo pipeline")
    parser.add_argument("--db-url", default="sqlite:///data/databases/argo_data.db")
    parser.add_argument("--targeted-demo", action="store_true", help="Ingest only demo-relevant March 2023 equatorial Indian Ocean floats")
    parser.add_argument(
        "--match-mode",
        choices=["strict", "relaxed", "auto"],
        default="relaxed",
        help="strict: March-2023 equatorial, relaxed: data-driven Indian Ocean, auto: strict then relaxed fallback",
    )
    parser.add_argument("--target-floats", type=int, default=5, help="Number of qualifying floats to ingest in targeted mode")
    parser.add_argument("--max-scan-per-center", type=int, default=600, help="How many float IDs to scan per center in targeted mode")
    parser.add_argument(
        "--max-no-match-per-center",
        type=int,
        default=60,
        help="Stop scanning a center after this many non-matching floats",
    )
    parser.add_argument(
        "--max-runtime-minutes",
        type=int,
        default=8,
        help="Total runtime budget for targeted ingest",
    )
    parser.add_argument("--reset-db", action="store_true", help="Delete existing SQLite file before ingest")
    parser.add_argument(
        "--allow-relaxed-fallback",
        action="store_true",
        help="If strict pass finds no floats, run a relaxed pass for fast demo bootstrap",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ARGO Data Pipeline - Direct API Access")
    print("=" * 60)

    db_file = Path("data/databases/argo_data.db")
    if args.reset_db:
        clear_sqlite_db(db_file)

    if args.targeted_demo:
        mode = args.match_mode
        if mode == "auto":
            selected = ingest_targeted_demo_data(
                db_url=args.db_url,
                target_floats=args.target_floats,
                max_scan_per_center=args.max_scan_per_center,
                max_no_match_per_center=args.max_no_match_per_center,
                match_mode="strict",
                max_runtime_minutes=args.max_runtime_minutes,
            )
        else:
            selected = ingest_targeted_demo_data(
                db_url=args.db_url,
                target_floats=args.target_floats,
                max_scan_per_center=args.max_scan_per_center,
                max_no_match_per_center=args.max_no_match_per_center,
                match_mode=mode,
                max_runtime_minutes=args.max_runtime_minutes,
            )

        if (args.allow_relaxed_fallback or mode == "auto") and not selected:
            logger.info("No strict matches found. Running relaxed fallback pass...")
            selected = ingest_targeted_demo_data(
                db_url=args.db_url,
                target_floats=max(1, min(args.target_floats, 3)),
                max_scan_per_center=max(80, min(args.max_scan_per_center, 200)),
                max_no_match_per_center=max(20, min(args.max_no_match_per_center, 40)),
                match_mode="relaxed",
                max_runtime_minutes=args.max_runtime_minutes,
            )
    else:
        stream_multiple_floats(
            data_center="aoml",
            num_floats=2,
            db_url=args.db_url,
            save_parquet=True,
        )

    query_data_example(args.db_url)
    validate_demo_window(db_file)
    print("\n✓ Pipeline complete! Data ready for analysis.")


if __name__ == "__main__":
    main()
