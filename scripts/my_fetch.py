#!/usr/bin/env python3
"""Fetch the Laws of Malaysia (federal principal Acts, "Updated" consolidated texts) from the
Attorney General's Chambers portal https://lom.agc.gov.my.

The portal's "Principal Act - Updated" listing offers an official PDF export
(generate-principal-pdf.php?type=updated) whose link annotations point to the consolidated
PDF of every Act in English (BI) and Malay (BM). We parse that export and download the PDFs.
The Federal Constitution PDFs are linked from federal-constitution.php.

Usage: my_fetch.py [RAW_DIR]
"""
import json
import os
import re
import sys
import time
import urllib.parse

import requests
from pypdf import PdfReader

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
BASE = "https://lom.agc.gov.my/"
DELAY = 1.0
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "_raw", "my")
os.makedirs(os.path.join(RAW, "pdf"), exist_ok=True)
S = requests.Session()
S.headers["User-Agent"] = UA


def get(url, **kw):
    for i in range(6):
        try:
            r = S.get(url, timeout=300, **kw)
            if r.status_code == 404:
                return r
            r.raise_for_status()
            time.sleep(DELAY)
            return r
        except Exception as e:  # noqa
            w = 5 * 2 ** i
            print(f"  ! {url}: {e!r}; retry in {w}s", flush=True)
            time.sleep(w)
    raise RuntimeError(url)


def parse_list(pdf_path):
    acts, cur = [], None
    for page in PdfReader(pdf_path).pages:
        for a in page.get("/Annots") or []:
            a = a.get_object()
            uri = (a.get("/A") or {}).get("/URI")
            if not uri:
                continue
            m = re.match(r"act-detail\.php\?act=([^&]+)&lang=(BI|BM)&date=([\d-]+)", uri)
            if m:
                if cur is None or cur["act"] != m.group(1):
                    cur = {"act": m.group(1), "date": m.group(3), "pdf": {}}
                    acts.append(cur)
                continue
            if uri.lower().endswith(".pdf") and cur is not None:
                lang = "BM" if re.search(r"_BM/|\bBM\.pdf$", uri) else "BI"
                if lang in cur["pdf"]:
                    lang = "BM" if lang == "BI" else "BI"
                cur["pdf"].setdefault(lang, urllib.parse.urljoin(BASE, uri))
    return acts


def main():
    lst = os.path.join(RAW, "updated_list.pdf")
    if not os.path.exists(lst):
        r = get(BASE + "generate-principal-pdf.php?type=updated&lang=&search=")
        open(lst, "wb").write(r.content)
    acts = parse_list(lst)
    # Federal Constitution
    fc = get(BASE + "federal-constitution.php").text
    cons = {}
    for p in re.findall(r"(ilims/upload/portal/akta/outputaktap/[^\"'&]+?\.pdf)", fc):
        lang = "BM" if "_BM/" in p else "BI"
        cons.setdefault(lang, urllib.parse.urljoin(BASE, urllib.parse.quote(p)))
    acts.insert(0, {"act": "FC", "date": None, "pdf": cons})
    json.dump(acts, open(os.path.join(RAW, "acts.json"), "w"), indent=1)
    print(len(acts), "entries", flush=True)
    for n, a in enumerate(acts):
        for lang, url in a["pdf"].items():
            d = os.path.join(RAW, "pdf", lang)
            os.makedirs(d, exist_ok=True)
            f = os.path.join(d, re.sub(r"[^A-Za-z0-9]+", "_", a["act"]) + ".pdf")
            if os.path.exists(f):
                continue
            u = url if "%" in url else urllib.parse.quote(url, safe=":/?&=%")
            r = get(u)
            if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                print(f"  FAIL {a['act']} {lang} {r.status_code}", flush=True)
                continue
            open(f + ".part", "wb").write(r.content)
            os.replace(f + ".part", f)
        if n % 50 == 0:
            print(f"  {n}/{len(acts)} act {a['act']}", flush=True)


if __name__ == "__main__":
    main()
