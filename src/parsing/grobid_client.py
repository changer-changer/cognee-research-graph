import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Dict
import time


@dataclass
class PaperStruct:
    title: str
    authors: List[str]
    abstract: str
    year: Optional[int]
    venue: Optional[str]
    sections: List[Dict]
    references: List[Dict]
    doi: Optional[str] = None


class GrobidClient:
    def __init__(self, service_url: str = "http://localhost:8070"):
        self.url = service_url
        self._wait_for_ready(timeout=60)

    def _wait_for_ready(self, timeout: int):
        for _ in range(timeout):
            try:
                r = requests.get(f"{self.url}/api/isalive", timeout=2)
                if r.status_code == 200:
                    body = r.text.strip()
                    if body == "true" or body == '{"grobid":"true"}':
                        return
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError("GROBID service not ready")

    def parse_pdf(self, pdf_path: str) -> PaperStruct:
        with open(pdf_path, "rb") as f:
            files = {"input": (pdf_path, f, "application/pdf")}
            r = requests.post(
                f"{self.url}/api/processFulltextDocument",
                files=files,
                data={"consolidateHeader": "1", "includeRawCitations": "1"},
                timeout=120,
            )
        r.raise_for_status()
        return self._parse_tei_xml(r.text)

    def _parse_tei_xml(self, xml_text: str) -> PaperStruct:
        root = ET.fromstring(xml_text.encode("utf-8"))
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}

        title = ""
        title_elem = root.find(".//tei:titleStmt/tei:title", ns)
        if title_elem is not None and title_elem.text:
            title = title_elem.text.strip()

        authors = []
        for author in root.findall(".//tei:sourceDesc//tei:author", ns):
            pers = author.find(".//tei:persName", ns)
            if pers is not None:
                parts = []
                for s in pers.findall(".//tei:surname", ns):
                    if s.text:
                        parts.append(s.text)
                for f in pers.findall(".//tei:forename", ns):
                    if f.text:
                        parts.append(f.text)
                if parts:
                    authors.append(" ".join(parts))

        abstract = ""
        abs_elem = root.find(".//tei:profileDesc/tei:abstract", ns)
        if abs_elem is not None:
            p = abs_elem.find(".//tei:p", ns)
            if p is not None and p.text:
                abstract = " ".join(t.strip() for t in p.itertext() if t.strip())

        year = None
        venue = None
        bibl = root.find(".//tei:sourceDesc/tei:biblStruct", ns)
        if bibl is not None:
            date = bibl.find(".//tei:date[@type='published']", ns)
            if date is not None and date.get("when"):
                try:
                    year = int(date.get("when")[:4])
                except Exception:
                    pass
            title_j = bibl.find(".//tei:title[@level='j']", ns)
            if title_j is not None and title_j.text:
                venue = title_j.text.strip()

        doi = None
        idno = root.find(".//tei:biblScope[@unit='doi']", ns)
        if idno is not None and idno.text:
            doi = idno.text.strip()

        sections = []
        body = root.find(".//tei:text/tei:body", ns)
        if body is not None:
            for div in body.findall(".//tei:div", ns):
                head = div.find("tei:head", ns)
                heading = (
                    head.text.strip()
                    if head is not None and head.text
                    else "Untitled"
                )
                texts = []
                for p in div.findall(".//tei:p", ns):
                    para = " ".join(
                        t.strip() for t in p.itertext() if t.strip()
                    )
                    if para:
                        texts.append(para)
                if texts:
                    sections.append(
                        {
                            "heading": heading,
                            "text": "\n\n".join(texts),
                            "level": 1,
                        }
                    )

        references = []
        for bibl in root.findall(".//tei:listBibl/tei:biblStruct", ns):
            ref_title = None
            ref_authors = []
            ref_year = None

            t = bibl.find(".//tei:title[@level='a']", ns)
            if t is None:
                t = bibl.find(".//tei:title", ns)
            if t is not None and t.text:
                ref_title = t.text.strip()

            for a in bibl.findall(".//tei:author", ns):
                pers = a.find(".//tei:persName", ns)
                if pers is not None:
                    names = []
                    for s in pers.findall(".//tei:surname", ns):
                        if s.text:
                            names.append(s.text)
                    if names:
                        ref_authors.append(" ".join(names))

            d = bibl.find(".//tei:date", ns)
            if d is not None and d.get("when"):
                try:
                    ref_year = int(d.get("when")[:4])
                except Exception:
                    pass

            if ref_title:
                references.append(
                    {
                        "title": ref_title,
                        "authors": ref_authors,
                        "year": ref_year,
                        "raw_text": ET.tostring(
                            bibl, encoding="unicode", method="text"
                        )[:200],
                    }
                )

        return PaperStruct(
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            venue=venue,
            doi=doi,
            sections=sections,
            references=references,
        )
