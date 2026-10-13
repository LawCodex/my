#!/usr/bin/env python3
"""Convert Laws of Malaysia PDFs (see my_fetch.py) to LawCodex Markdown.

Text is extracted with poppler's `pdftotext` (reading order); running headers, page numbers,
cover/arrangement pages and the trailing "List of Amendments" particulars are removed;
Parts, Chapters, sections (with their marginal notes) and Schedules become headings.

Usage: my_convert.py [RAW_DIR] [OUT_DIR]
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "_raw", "my")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..")
RETRIEVED = date.today().isoformat()

LANGS = {"BI": "en", "BM": "ms"}
LOM = re.compile(r"^(LAWS OF MALAYSIA|UNDANG-UNDANG MALAYSIA)$")
ARR = re.compile(r"^(ARRANGEMENT OF (SECTIONS|ARTICLES)|SUSUNAN (SEKSYEN|PERKARA))$")
AMEND = re.compile(r"^(LIST OF AMENDMENTS|SENARAI PINDAAN|LIST OF ARTICLES AMENDED|SENARAI PERKARA YANG DIPINDA)")
START = re.compile(r"^(An Act |An Ordinance |Suatu Akta |Suatu Ordinan |ENACTED |DIPERBUAT |WHEREAS|BAHAWASANYA|"
                   r"BE IT ENACTED|MAKA INILAH)")
PART = re.compile(r"^(PART|Part|BAHAGIAN|Bahagian)\s+([IVXLC]+[A-Z]?|\d+[A-Z]?)$")
CHAP = re.compile(r"^(CHAPTER|Chapter|BAB|Bab)\s+(\d+[A-Z]?|[IVXLC]+)(\s*[—–-]\s*.+)?$")
ORD = "FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH|THIRTEENTH"
SCHED = re.compile(rf"^(((?:{ORD})\s+)?SCHEDULE|JADUAL(\s+[A-Z]+)?)(\s*\[.*)?$", re.I)
SEC = re.compile(r"^\**(\d{1,4}[A-Za-z]{0,3})\.\s+(.*)$")
NEWPARA = re.compile(r"^(\((\d+[A-Z]*|[a-z]{1,3}|[A-Z]{1,2})\)|“|\"|Illustration|Explanation|Huraian|Penjelasan|Proviso)")
TERM = (".", ";", ":", "—", "–", "-", ",", ")", "]")


def upper_line(s):
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def pdftext(path):
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def merge_lom(ls):
    out = []
    for x in ls:
        if out and x == "MALAYSIA" and out[-1] in ("UNDANG-UNDANG", "LAWS OF"):
            out[-1] = out[-1] + " MALAYSIA"
        else:
            out.append(x)
    return out


def cover_title(page1):
    ls = merge_lom([x.strip() for x in page1.split("\n") if x.strip()])
    i = next((k for k, x in enumerate(ls) if re.fullmatch(r"(Act|Akta|ACT|AKTA)\s+\S+", x)), None)
    if i is None:
        return ""
    t = []
    for x in ls[i + 1:]:
        if re.match(r"^\((Revised|Disemak|REVISED|DISEMAK)", x) or not (upper_line(x) or x.startswith("(")):
            break
        if re.match(r"^(REVISED BY|DISEMAK OLEH)", x):
            break
        t.append(x)
    return " ".join(t)


def strip_headers(pages, actno):
    pages = ["\n".join(merge_lom([x.strip() for x in p.split("\n") if x.strip()])) for p in pages]
    zone = []
    for p in pages:
        ls = [x.strip() for x in p.split("\n") if x.strip()]
        zone.append(set(ls[:5] + ls[-4:]))
    cnt = Counter(x for z in zone for x in z)
    n = len(pages)
    running = {x for x, c in cnt.items() if c >= max(3, n * 0.2) and len(x) < 120 and not SEC.match(x)
               and not PART.match(x)}
    out = []
    for p in pages:
        ls = [x.strip() for x in p.split("\n") if x.strip()]
        if any(x in ("NOTES", "CATATAN") for x in ls[:5]):
            continue  # editorial amendment-notes pages (Federal Constitution reprint)
        keep = []
        for i, x in enumerate(ls):
            inzone = i < 6 or i >= len(ls) - 4
            if re.fullmatch(r"\[(Article|Perkara|Art\.|Per\.)\s+\w+\]", x):
                continue  # running "[Article 19]" continuation markers
            if inzone and (re.fullmatch(r"\d{1,4}", x) or x in running
                           or re.fullmatch(r"(Laws of Malaysia|Undang-Undang Malaysia)", x)
                           or re.fullmatch(rf"(Act|Akta|ACT|AKTA)\s+{re.escape(actno)}", x)):
                continue
            keep.append(x)
        out.extend(keep)
    return out


def esc(t):
    if re.match(r"^(\d+[.)]\s|[#>*+|]|-\s|=+\s*$)", t):
        return "\\" + t
    return t


def join_lines(lines, sched=False):
    """Join physical lines into paragraphs."""
    paras, cur = [], ""
    for ln in lines:
        if not cur:
            cur = ln
            continue
        if (sched and re.match(r"^\d+[A-Za-z]?\.\s", ln)) or (upper_line(ln) and len(ln) < 80 and len(ln) > 3) \
                or (upper_line(cur) and len(cur) < 80 and not cur.endswith(("OF", "AND", "DAN"))):
            paras.append(cur)
            cur = ln
        elif (NEWPARA.match(ln) and (cur.endswith(TERM[:5]) or re.search(r"\b(and|or|but|dan|atau|tetapi)$", cur))) \
                or START.match(ln) or ln.startswith("["):
            paras.append(cur)
            cur = ln
        elif cur.endswith("-") and len(cur) > 1 and cur[-2].isalpha() and ln[:1].islower():
            cur += ln
        else:
            cur += " " + ln
    if cur:
        paras.append(cur)
    return [esc(p) for p in paras]


def note_tail(buf):
    """Pop trailing marginal-note lines from buf (lines after the last terminal line)."""
    k = 0
    while k < min(3, len(buf)):
        ln = buf[-1 - k]
        if ln.endswith(TERM[:7]) or NEWPARA.match(ln) or SEC.match(ln):
            break
        k += 1
    if k == 0:
        return None
    # the line before the note must close the previous provision (or be absent / a heading)
    if len(buf) > k and not buf[-1 - k].endswith(TERM[:7] + (")", "]")) and not upper_line(buf[-1 - k]):
        return None
    note = " ".join(buf[len(buf) - k:])
    del buf[len(buf) - k:]
    return note


def convert_text(lines):
    """Return (title, blocks) where blocks = list of (kind, level-key, text/lines)."""
    # body start
    arr = next((i for i, x in enumerate(lines) if ARR.match(x)), None)
    st = 0
    if arr is not None:
        first = next((i for i in range(arr + 1, len(lines))
                      if re.match(r"^\*?1\.\s+\S", lines[i])), None)
        if first is not None:
            st = next((i for i in range(first - 1, max(arr, first - 60), -1)
                       if LOM.match(lines[i]) or lines[i] in ("FEDERAL CONSTITUTION", "PERLEMBAGAAN PERSEKUTUAN")),
                      None)
            if st is None:
                st = next((i for i in range(first - 1, max(arr, first - 60), -1) if START.match(lines[i])), first)
        else:
            st = next((i for i in range(arr + 1, len(lines)) if LOM.match(lines[i])), arr + 1)
    # end: last LAWS OF MALAYSIA followed by LIST OF AMENDMENTS
    end = len(lines)
    for i in range(len(lines) - 1, st, -1):
        if AMEND.match(lines[i]):
            j = next((k for k in range(i, max(st, i - 12), -1) if LOM.match(lines[k])), i)
            end = j
            break
    body = lines[st:end]
    # title: upper-case lines after LAWS OF MALAYSIA / Act NNN
    title, i = [], 0
    while i < len(body) and (LOM.match(body[i]) or re.fullmatch(r"(Act|Akta|ACT|AKTA)\s+\S+", body[i])
                             or body[i] in ("FEDERAL CONSTITUTION", "PERLEMBAGAAN PERSEKUTUAN")):
        i += 1
    while i < len(body) and (upper_line(body[i]) or re.fullmatch(r"\(.*\)", body[i])) and not PART.match(body[i]) \
            and not START.match(body[i]) and not SCHED.match(body[i]):
        title.append(body[i])
        i += 1
    body = body[i:]
    blocks, buf = [], []
    last = 0
    in_sched = False

    def flush():
        if buf:
            blocks.append(("text", None, join_lines(buf, in_sched)))
            buf.clear()
    j = 0
    while j < len(body):
        ln = body[j]
        m = PART.match(ln)
        if m and in_sched:
            nxt = [SEC.match(x) for x in body[j + 1:j + 8]]
            if any(x and int(re.match(r"\d+", x.group(1)).group()) > last for x in nxt):
                flush()
                in_sched = False
        if m and not in_sched:
            flush()
            heads = []
            j += 1
            while j < len(body) and upper_line(body[j]) and not SEC.match(body[j]) and not CHAP.match(body[j]) \
                    and not PART.match(body[j]) and len(heads) < 4:
                heads.append(body[j])
                j += 1
            blocks.append(("part", 0, ln + (" — " + " ".join(heads) if heads else "")))
            continue
        m = CHAP.match(ln)
        if m and not in_sched:
            flush()
            heads = []
            j += 1
            while j < len(body) and upper_line(body[j]) and not SEC.match(body[j]) and len(heads) < 3:
                heads.append(body[j])
                j += 1
            blocks.append(("chapter", 1, ln + (" — " + " ".join(heads) if heads else "")))
            continue
        if SCHED.match(ln) and (j + 1 >= len(body) or not body[j + 1][:1].islower()) and len(ln) < 80:
            # "Schedule" headings: only when the line stands alone
            flush()
            in_sched = True
            blocks.append(("schedule", 0, ln))
            j += 1
            continue
        m = SEC.match(ln)
        if m and not in_sched:
            num = m.group(1)
            n = int(re.match(r"\d+", num).group())
            if last <= n <= last + 40 and (n > last or num != str(last)):
                note = note_tail(buf)
                flush()
                last = n
                blocks.append(("section", 2, f"{num}." + (f" {note}" if note else "")))
                rest = m.group(2).strip()
                if rest:
                    buf.append(rest)
                j += 1
                continue
        buf.append(ln)
        j += 1
    flush()
    return " ".join(title), blocks


def render(blocks):
    has_part = any(b[0] in ("part", "schedule") for b in blocks)
    has_chap = any(b[0] == "chapter" for b in blocks)
    lv = {"part": 2, "schedule": 2, "chapter": 3 if has_part else 2}
    sec_lv = 2 + int(has_part) + int(has_chap)
    out = []
    for kind, _, x in blocks:
        if kind == "text":
            out.extend(x)
        elif kind == "section":
            out.append("#" * min(6, sec_lv) + " " + x)
        else:
            out.append("#" * lv[kind] + " " + x)
    return "\n\n".join(out)


def slug(s, n=70):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n].rstrip("-")


def yq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    acts = json.load(open(os.path.join(RAW, "acts.json")))
    stats = Counter()
    for a in acts:
        for lang, url in a["pdf"].items():
            f = os.path.join(RAW, "pdf", lang, re.sub(r"[^A-Za-z0-9]+", "_", a["act"]) + ".pdf")
            if not os.path.exists(f):
                continue
            txt = pdftext(f)
            pages = txt.split("\f")
            actno = a["act"]
            lines = strip_headers(pages, actno)
            title, blocks = convert_text(lines)
            title = cover_title(pages[0]) or title
            if title.startswith("WARTA KERAJAAN"):
                title = f"Act {actno}" if lang == "BI" else f"Akta {actno}"
            if not title:
                title = ("Federal Constitution" if lang == "BI" else "Perlembagaan Persekutuan") \
                    if actno == "FC" else f"Act {actno}"
            body = render(blocks)
            head = " ".join(pages[:2])
            if (len(pages) <= 4 and re.search(r"\((Repealed|Dimansuhkan)\b", head)) or \
                    re.search(r"\b(Repealed|Superseded|Ceased to have effect|Dimansuhkan|Digantikan|Terhenti)\b", title, re.I):
                stats["repealed-placeholder-" + lang] += 1
                continue
            if len(body) < 200:
                stats["empty-" + lang] += 1
                print("  short/empty:", actno, lang, flush=True)
                continue
            L = LANGS[lang]
            if actno == "FC":
                rel = f"{L}/constitution/federal-constitution.md"
                typ, ident = "constitution", "Federal Constitution"
            else:
                n = int(re.match(r"\d+", actno).group()) if re.match(r"\d+", actno) else 0
                shard = f"{(n // 100) * 100:04d}-{(n // 100) * 100 + 99:04d}"
                num = f"{n:04d}" + actno[len(str(n)):].lower() if n else actno.lower()
                rel = f"{L}/acts/{shard}/act-{num}-{slug(title)}.md"
                typ, ident = "act", f"Act {actno}"
            asat = a.get("date")
            fm = ["---", f"title: {yq(title)}", f"identifier: {yq(ident)}", f"type: {typ}",
                  "jurisdiction: my", f"language: {L}"]
            if asat:
                d, mth, y = asat.split("-")
                fm.append(f"last_amended: {y}-{mth}-{d}")
            fm += ["status: in_force", f"source: {yq(url)}", f"retrieved: {RETRIEVED}", "---", "",
                   f"# {title}", "", body, ""]
            p = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(fm))
            stats[L] += 1
    print(dict(stats))


if __name__ == "__main__":
    main()
