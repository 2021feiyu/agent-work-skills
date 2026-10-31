# -*- coding: utf-8 -*-
"""H5 static audit for h5-dashboard-dev V3.

Usage:
    python audit_h5.py <dashboard.html> [--node /path/to/node] [--json]

FAIL is used for deterministic structural/syntax defects. WARN marks a risk that
requires human review. This script does not prove contrast, layout, data accuracy,
runtime keyboard behavior, motion quality, or delivery-hash consistency.
"""
import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


@dataclass
class Result:
    level: str
    check: str
    detail: str = ""


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.inline_scripts = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append({"tag": tag, "attrs": attributes, "line": self.getpos()[0]})
        if tag == "script" and not attributes.get("src"):
            script_type = attributes.get("type", "").lower()
            if script_type in ("", "text/javascript", "application/javascript", "module"):
                self._script = {"type": script_type, "line": self.getpos()[0], "code": []}

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "script":
            self._script = None

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.inline_scripts.append({
                "type": self._script["type"],
                "line": self._script["line"],
                "code": "".join(self._script["code"])
            })
            self._script = None

    def handle_data(self, data):
        if self._script is not None:
            self._script["code"].append(data)


def local_path(base, uri):
    if not uri or uri.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlsplit(uri)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if not path:
        return None
    target = Path(path) if Path(path).is_absolute() else base / path
    return target.resolve()


def line_of(element):
    return "line %s" % element.get("line", "?")


def audit(path, node_path=None):
    path = Path(path).resolve()
    text = io.open(str(path), encoding="utf-8-sig").read()
    parser = DocumentParser()
    parser.feed(text)
    parser.close()
    elements = parser.elements
    results = []

    def add(level, check, detail=""):
        results.append(Result(level, check, detail))

    ids = [e["attrs"]["id"] for e in elements if e["attrs"].get("id")]
    counts = Counter(ids)
    duplicates = sorted(key for key, value in counts.items() if value > 1)
    add("FAIL" if duplicates else "PASS", "unique_ids", ", ".join(duplicates) or "no duplicate id")
    id_set = set(ids)

    broken_anchors = []
    for element in elements:
        href = element["attrs"].get("href", "")
        if href.startswith("#") and not href.startswith("#/") and len(href) > 1:
            target = unquote(href[1:])
            if target not in id_set:
                broken_anchors.append("%s -> #%s" % (line_of(element), target))
    add("FAIL" if broken_anchors else "PASS", "local_anchors", "; ".join(broken_anchors) or "all static local anchors resolve")

    broken_refs = []
    for element in elements:
        for attribute in ("aria-controls", "aria-labelledby", "aria-describedby"):
            value = element["attrs"].get(attribute, "")
            for target in value.split():
                if target not in id_set:
                    broken_refs.append("%s %s=%s" % (line_of(element), attribute, target))
    add("FAIL" if broken_refs else "PASS", "aria_idrefs", "; ".join(broken_refs) or "ARIA ID references resolve")

    tab_errors = []
    tablist_warnings = []
    for element in elements:
        attrs = element["attrs"]
        role = attrs.get("role")
        if role == "tab":
            if not attrs.get("aria-controls"):
                tab_errors.append("%s tab lacks aria-controls" % line_of(element))
            if attrs.get("aria-selected") not in ("true", "false"):
                tab_errors.append("%s tab lacks valid aria-selected" % line_of(element))
        if role == "tabpanel" and not attrs.get("aria-labelledby"):
            tab_errors.append("%s tabpanel lacks aria-labelledby" % line_of(element))
        if role == "tablist" and not (attrs.get("aria-label") or attrs.get("aria-labelledby")):
            tablist_warnings.append("%s tablist has no accessible name" % line_of(element))
    add("FAIL" if tab_errors else "PASS", "tabs_static_contract", "; ".join(tab_errors) or "static tab relationships present")
    add("WARN" if tablist_warnings else "PASS", "tablist_names", "; ".join(tablist_warnings) or "tablists have accessible names")

    missing_assets = []
    linked_css = []
    for element in elements:
        tag, attrs = element["tag"], element["attrs"]
        uri = None
        if tag == "script" and attrs.get("src"):
            uri = attrs["src"]
        elif tag == "link" and "stylesheet" in attrs.get("rel", "").lower() and attrs.get("href"):
            uri = attrs["href"]
            target = local_path(path.parent, uri)
            if target and target.exists():
                try:
                    linked_css.append(io.open(str(target), encoding="utf-8-sig").read())
                except (OSError, UnicodeError) as exc:
                    add("WARN", "linked_css_read", "%s: %s" % (target, exc))
        elif tag == "img" and attrs.get("src"):
            uri = attrs["src"]
        if uri:
            target = local_path(path.parent, uri)
            if target and not target.exists():
                missing_assets.append("%s: %s" % (line_of(element), target))
    add("FAIL" if missing_assets else "PASS", "local_assets", "; ".join(missing_assets) or "referenced local assets exist")

    css_text = "\n".join([text] + linked_css)
    css_without_comments = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    defined = set(re.findall(r"(--[a-zA-Z0-9_-]+)\s*:", css_without_comments))
    missing_vars = []
    fallback_vars = []
    for match in re.finditer(r"var\(\s*(--[a-zA-Z0-9_-]+)\s*([^)]*)\)", css_without_comments):
        name, remainder = match.group(1), match.group(2)
        if name not in defined:
            if remainder.lstrip().startswith(","):
                fallback_vars.append(name)
            else:
                missing_vars.append(name)
    add("FAIL" if missing_vars else "PASS", "css_variables", ", ".join(sorted(set(missing_vars))) or "CSS variables resolve or have fallback")
    if fallback_vars:
        add("WARN", "css_variable_fallbacks", "undefined with fallback: " + ", ".join(sorted(set(fallback_vars))))

    svg_refs = sorted(set(re.findall(r"url\(\s*#([a-zA-Z_][\w:.-]*)\s*\)", css_without_comments)) - id_set)
    add("FAIL" if svg_refs else "PASS", "svg_local_refs", ", ".join(svg_refs) or "static SVG url(#id) references resolve")

    js_refs = set()
    for script in parser.inline_scripts:
        code = script["code"]
        js_refs.update(re.findall(r"getElementById\(\s*['\"]([^'\"]+)['\"]\s*\)", code))
    dynamic_id_warnings = sorted(js_refs - id_set)
    if dynamic_id_warnings:
        add("WARN", "js_id_refs", "verify dynamically-created ids: " + ", ".join(dynamic_id_warnings))
    else:
        add("PASS", "js_id_refs", "static getElementById targets exist")

    node = node_path or shutil.which("node")
    if not parser.inline_scripts:
        add("PASS", "javascript_syntax", "no inline JavaScript to parse")
    elif not node:
        add("WARN", "javascript_syntax", "Node.js not found; pass --node to enable real JS parsing")
    else:
        syntax_errors = []
        with tempfile.TemporaryDirectory(prefix="h5-audit-") as temp_dir:
            for index, script in enumerate(parser.inline_scripts):
                suffix = ".mjs" if script["type"] == "module" else ".js"
                target = Path(temp_dir) / ("inline_%03d%s" % (index, suffix))
                io.open(str(target), "w", encoding="utf-8", newline="\n").write(script["code"])
                completed = subprocess.run(
                    [node, "--check", str(target)], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30
                )
                if completed.returncode:
                    detail = (completed.stderr or completed.stdout).strip().splitlines()
                    syntax_errors.append("inline script line %s: %s" % (script["line"], " | ".join(detail[-4:])))
        add("FAIL" if syntax_errors else "PASS", "javascript_syntax", "; ".join(syntax_errors) or "Node.js parsed all inline scripts")

    combined = text + "\n" + "\n".join(linked_css)
    has_motion = bool(re.search(r"@keyframes|animation\s*:|transition\s*:", combined))
    has_motion_gate = "prefers-reduced-motion" in combined
    add("WARN" if has_motion and not has_motion_gate else "PASS", "reduced_motion_css",
        "motion found without a CSS reduced-motion media query" if has_motion and not has_motion_gate else "CSS motion gate present or no motion found")
    has_smooth = bool(re.search(r"behavior\s*:\s*['\"]smooth['\"]|scroll-behavior\s*:\s*smooth", combined))
    has_js_motion_gate = "prefers-reduced-motion" in combined and ("matchMedia" in combined or "H5Motion" in combined)
    add("WARN" if has_smooth and not has_js_motion_gate else "PASS", "reduced_motion_javascript",
        "smooth scrolling found without a JS motion-preference gate" if has_smooth and not has_js_motion_gate else "JS motion gate present or no smooth scrolling found")
    has_echarts_animation = bool(re.search(r"animationDuration(?:Update)?\s*:", combined))
    add("WARN" if has_echarts_animation and not has_js_motion_gate else "PASS", "echarts_motion_gate",
        "ECharts animation timing found without a JS motion-preference gate" if has_echarts_animation and not has_js_motion_gate else "ECharts motion gate present or no explicit timing found")

    return {
        "file": str(path),
        "results": results,
        "summary": {
            "pass": sum(r.level == "PASS" for r in results),
            "warn": sum(r.level == "WARN" for r in results),
            "fail": sum(r.level == "FAIL" for r in results)
        },
        "scope_note": "Static audit only. Browser interaction, visual, contrast, data and delivery-hash checks remain mandatory; print/PDF checks apply only when explicitly required."
    }


def main():
    cli = argparse.ArgumentParser(description="H5 static structure and JavaScript syntax audit")
    cli.add_argument("html", help="HTML file to audit")
    cli.add_argument("--node", dest="node_path", help="Node.js executable for JS parsing")
    cli.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = cli.parse_args()
    report = audit(args.html, args.node_path)
    if args.json:
        print(json.dumps({
            "file": report["file"],
            "summary": report["summary"],
            "results": [asdict(result) for result in report["results"]],
            "scope_note": report["scope_note"]
        }, ensure_ascii=False, indent=2))
    else:
        print("\nH5 static audit: %s" % report["file"])
        for result in report["results"]:
            print("  [%-4s] %-28s %s" % (result.level, result.check, result.detail))
        print("Summary: %(pass)d PASS / %(warn)d WARN / %(fail)d FAIL" % report["summary"])
        print(report["scope_note"])
    return 1 if report["summary"]["fail"] else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
