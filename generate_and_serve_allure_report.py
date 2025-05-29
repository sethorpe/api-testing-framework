import os
import shutil
import subprocess


def clean_allure_report(allure_report_path: str):
    """Clean the existing Allure report directory"""
    if os.path.exists(allure_report_path):
        print(f"Cleaning up old Allure report at: {allure_report_path}")
        shutil.rmtree(allure_report_path)


def generate_and_serve_allure_report():
    """Generate and serve the Allure report."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    allure_results = os.path.join(project_root, "allure-results")
    allure_report = os.path.join(project_root, "allure-report")

    # Check if allure-results exists
    if not os.path.exists(allure_results) or not os.listdir(allure_results):
        print(
            f"No Allure results found in {allure_results}. Run your tests with --alluredir first."
        )
        return

    # Step 1: Clean the old Allure report
    clean_allure_report(allure_report)

    # Step 2: Generate the Allure report
    print("Generating Allure report...")
    subprocess.run(
        ["allure", "generate", allure_results, "--clean", "-o", allure_report],
        check=True,
    )

    # Step 3: Serve the Allure report
    print("Serving Allure report...")
    subprocess.Popen(["allure", "serve", allure_results])


if __name__ == "__main__":
    try:
        generate_and_serve_allure_report()
    except Exception as e:
        print(f"Error: {e}")
