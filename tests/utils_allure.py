import glob
import json
import os
import time
from typing import Any, Dict, Iterable, Optional


def _iter_attachments(node: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for att in node.get("attachments", []) or []:
        yield att
    for step in node.get("steps", []) or []:
        yield from _iter_attachments(step)


def _result_has_label(res: Dict[str, Any], name: str, value: str) -> bool:
    for lab in res.get("labels", []) or []:
        if lab.get("name") == name and lab.get("value") == value:
            return True
    return False


def wait_for_result_with_label(
    allure_dir: str, label_name: str, label_value: str, timeout: float = 12.0
) -> Optional[Dict[str, Any]]:
    """Poll allure-results for a test result that has given label."""
    deadline = time.time() + timeout
    time.sleep(0.2)
    pattern = os.path.join(allure_dir, "*-result.json")

    while time.time() < deadline:
        for path in glob.glob(pattern):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    res = json.load(f)
            except Exception:
                continue
            if _result_has_label(res, label_name, label_value):
                return res
        time.sleep(0.1)
    return None


def find_attachment_path(
    res: Dict[str, Any], allure_dir: str, name: str
) -> Optional[str]:
    """Return full path to the first attachment named `name` in this result (top or steps)."""
    for att in _iter_attachments(res):
        if att.get("name") == name and att.get("source"):
            path = os.path.join(allure_dir, att["source"])
            if os.path.exists(path):
                return path
    return None


# def _result_has_marker(res: Dict[str, Any], marker_name: str) -> bool:
#     for att in _iter_attachments(res):
#         if att.get("name") == marker_name:
#             return True
#     return False


def find_attachment_by_name_in_result(
    res: Dict[str, Any], allure_dir: str, attachment_name: str
) -> Optional[str]:
    """Return full path to the first attachment named `attachment_name` in this result."""
    for att in _iter_attachments(res):
        if att.get("name") == attachment_name:
            src = att.get("source")
            if src:
                path = os.path.join(allure_dir, src)
                if os.path.exists(path):
                    return path
    return None


# def wait_for_result_with_marker(
#     allure_dir: str, marker_name: str, timeout: float = 10.0
# ) -> Optional[Dict[str, Any]]:
#     """Poll allure-results for a test result that contains our marker attachment."""

#     deadline = time.time() + timeout
#     # small delay helps when tests are very fast
#     time.sleep(0.2)
#     while time.time() < deadline:
#         for path in glob.glob(os.path.join(allure_dir, "*-result.json")):
#             try:
#                 with open(path, "r", encoding="utf-8") as f:
#                     res = json.load(f)
#             except Exception:
#                 continue
#             if _result_has_marker(res, marker_name):
#                 return res
#         time.sleep(0.1)
#     return None


def find_response_body_attachment(
    allure_dir: str, name_hint: str, timeout: float = 5.0
):
    """Wait up to `timeout` seconds for Allure result whose name/fullName
    contains `name_hint`; then return the full path to the 'Response Body' attachment.
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        result_files = glob.glob(os.path.join(allure_dir, "*-result.json"))
        for path in result_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    res = json.load(f)
            except Exception:
                continue
            name = res.get("name") or res.get("fullName") or ""
            if name_hint in name:
                for att in res.get("attachments", []):
                    if att.get("name") == "Response Body":
                        src = os.path.join(allure_dir, att.get("source", ""))
                        if os.path.exists(src):
                            return src
        time.sleep(0.1)
    return None
