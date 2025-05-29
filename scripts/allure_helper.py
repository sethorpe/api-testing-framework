#!/usr/bin/env python3
"""Script to clean, generate, and optionally serve an Allure report with parameterized paths"""
import argparse
import os
import shutil
import subprocess
import sys

from api_testing_framework.logger import logger


def clean_allure_report(report_path: str) -> None:
    """Clean the existing Allure report directory"""
    if os.path.isdir(report_path):
        logger.info("Cleaning old Allure report at: %s", report_path)
        shutil.rmtree(report_path)


def generate_allure_report(results_dir: str, report_dir: str) -> None:
    """Generate the Allure report from results"""
    logger.info("Generating Allure report from %s to %s...", results_dir, report_dir)
    try:

        subprocess.run(
            ["allure", "generate", results_dir, "--clean", "-o", report_dir],
            check=True,
            capture_output=True,
        )
        logger.info("Report generated at: %s/index.html", report_dir)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else str(e)
        logger.error("Allure generation failed: %s", stderr)
        raise


def serve_allure_report(results_dir: str) -> None:
    """Serve the Allure report interactively"""
    logger.info("Serving Allure report from results: %s...", results_dir)
    try:
        subprocess.run(
            ["allure", "serve", results_dir], check=True, capture_output=True
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else str(e)
        print("Allure serving failed: %s", stderr)


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Clean, generate, and serve Allure reports."
    )
    parser.add_argument(
        "--results-dir",
        default=os.path.join(project_root, "allure-results"),
        help="Directory containing pytest --alluredir output",
    )
    parser.add_argument(
        "--report-dir",
        default=os.path.join(project_root, "allure-report"),
        help="Directory where the HTML report will be generated",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="After generation, serve the report in a local web server",
    )
    args = parser.parse_args()

    # Validate results dictionary
    if not os.path.isdir(args.results_dir) or not os.listdir(args.results_dir):
        logger.warning(
            "No Allure results found in %s. Run pytest with --alluredir first.",
            args.results_dir,
        )
        sys.exit(0)

    # Clean, generate, and optionally serve
    clean_allure_report(args.report_dir)
    try:
        generate_allure_report(args.results_dir, args.report_dir)
        if args.serve:
            serve_allure_report(args.results_dir)
    except subprocess.CalledProcessError as e:
        logger.error("Error during Allure operation: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
