# Malaysia — LawCodex

Malaysian federal legislation as plain Markdown, in English (`en/`) and Malay (`ms/`, the
national language). Part of [LawCodex](https://github.com/LawCodex).

## What is covered

The **Federal Constitution** and every federal **principal Act** listed under
"Principal Act → Updated" on the official *Laws of Malaysia* portal of the Attorney General's
Chambers (AGC), i.e. the consolidated ("as at" date) text of each Act in force:

| Category | English (`en/`) | Malay (`ms/`) |
|---|---|---|
| Federal Constitution (`constitution/`) | 1 | 1 |
| Principal Acts (`acts/<range>/act-<no>-<title>.md`) | 745 | 626 |
| **Total** | **746** | **627** |

### Gaps

The "Updated" listing has 885 Act entries (Act 1 – Act 886). Of these:

- 45 entries offer no PDF at all;
- 75 English and 53 Malay PDFs are placeholders for Acts that are **repealed / superseded /
  ceased to have effect** (the listing still shows them) — skipped;
- 18 English and some Malay PDFs are image scans without a text layer (e.g. Acts 10, 63, 91, 97,
  115, 119, 210, 271, 272, 276, 277, 280, 312, 319, 324, 336, 371, 788 in English) — skipped,
  no OCR; most of the 64 skipped Malay PDFs state "Tiada teks bahasa kebangsaan" (no national
  language text);
- 4 PDFs returned HTTP 500 from the portal (Acts 150 and 175 in English, 780 and 781 in Malay).


### Not covered

- Subsidiary legislation (P.U.(A) / P.U.(B)), amending Acts (Act A…), repealed Acts, Bills.
- State enactments (each State publishes its own laws) and Syariah laws.
- The *List of Amendments* / *List of Articles Amended* particulars printed at the end of each
  reprint, and the editorial **NOTES** pages of the Federal Constitution reprint (amendment
  history), are omitted. Cover pages, the arrangement of sections and running headers are removed.
- Some Acts have no Malay text ("Tiada teks bahasa kebangsaan") or only an English text; for some
  Acts the Malay text is an unofficial AGC translation (stated in the document itself).

## Format and structure

One Markdown file per Act and language. `en/acts/0800-0899/act-886-…md` — Acts are sharded by
hundreds of their Act number. Front matter: `title`, `identifier` (`Act N` / `Federal
Constitution`), `type`, `language`, `last_amended` (the portal's "As At" date of the updated
text), `status`, `source` (PDF URL), `retrieved`.

Parts and Schedules are `##` headings, Chapters `###`, sections/Articles (number + marginal
note) the next level. Text is extracted from the official PDFs with `pdftotext`; paragraphs are
re-flowed. Tables and complex schedules lose their layout — check them against the PDF linked in
`source`. Section detection is heuristic; a few marginal notes may appear in the text instead of
the heading.

## Source

Attorney General's Chambers of Malaysia, Laws of Malaysia portal — https://lom.agc.gov.my/
(listing via the portal's official PDF export `generate-principal-pdf.php?type=updated`, whose
links point to the consolidated PDFs under `/ilims/upload/portal/akta/outputaktap/`; the Federal
Constitution reprint linked from `federal-constitution.php`). Retrieved 2026-10-12/13.
robots.txt returns an HTTP 500 (none usable); downloads used a descriptive User-Agent, ≤3
parallel connections and a 1 s delay per connection. The portal's interactive listings return
encrypted JSON; they were **not** used (no decryption was attempted) — only the public PDF export.

## Copyright

The portal states "Copyright … Attorney General's Chambers, Malaysia, all rights reserved"
and that federal legislation "can be accessed and downloaded at no charge". These Markdown files
are an unofficial, non-authoritative rendering for public information. Per the portal's terms,
online texts are not the reprints under s.14 of the Revision of Laws Act 1968 and are not copies
of the Gazette; the printed Gazette / official reprints remain authoritative.

## Regenerate

```sh
pip install -r scripts/requirements.txt   # plus poppler (pdftotext)
python scripts/my_fetch.py ../_raw/my
python scripts/my_convert.py ../_raw/my .
```
