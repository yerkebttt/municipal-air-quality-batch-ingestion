"""Generate the four assessed portfolio PDFs with deterministic formatting."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
DOCS = ROOT / "docs"
FONT_ROOT = Path(
    "/opt/codex/runtimes/codex-primary-runtime/dependencies/native/"
    "libreoffice-headless/libreoffice/share/fonts/truetype"
)

NAMES = {
    "p1": "Batyrova-Yerkezhan_92131651_DataEngineering_P1_S.pdf",
    "p2": "Batyrova-Yerkezhan_92131651_DataEngineering_P2_S.pdf",
    "abstract": "Batyrova-Yerkezhan_92131651_DataEngineering_P3_S_Abstract.pdf",
    "product": "Batyrova-Yerkezhan_92131651_DataEngineering_P3_S_Product.pdf",
}

REPO = "https://github.com/yerkebttt/municipal-air-quality-batch-ingestion"
UCI = "https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data"


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("Arial", str(FONT_ROOT / "LiberationSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_ROOT / "LiberationSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Italic", str(FONT_ROOT / "LiberationSans-Italic.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", str(FONT_ROOT / "LiberationMono-Regular.ttf")))


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName="Arial-Bold", fontSize=12,
            leading=18, alignment=TA_LEFT, textColor=colors.HexColor("#15324B"),
            spaceAfter=7,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["Normal"], fontName="Arial", fontSize=9.5,
            leading=12, textColor=colors.HexColor("#465866"), spaceAfter=9,
        ),
        "heading": ParagraphStyle(
            "Heading", parent=base["Heading2"], fontName="Arial-Bold", fontSize=12,
            leading=16.5, textColor=colors.HexColor("#15324B"), spaceBefore=5,
            spaceAfter=3, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Arial", fontSize=11,
            leading=16.5, alignment=TA_JUSTIFY, spaceAfter=6,
            allowWidows=0, allowOrphans=0, splitLongWords=True,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName="Arial", fontSize=8.5,
            leading=11, alignment=TA_LEFT, textColor=colors.HexColor("#465866"),
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName="Arial", fontSize=10.5,
            leading=14, alignment=TA_LEFT, leftIndent=13, firstLineIndent=-9,
            bulletIndent=2, spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "Code", parent=base["Code"], fontName="Mono", fontSize=8.3,
            leading=11, leftIndent=8, rightIndent=8, borderColor=colors.HexColor("#C7D3DC"),
            borderWidth=0.5, borderPadding=6, backColor=colors.HexColor("#F4F7F9"),
            spaceBefore=3, spaceAfter=6,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"], fontName="Arial", fontSize=8,
            leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#607784"),
        ),
    }


def word_count(blocks: list[str]) -> int:
    plain = " ".join(re.sub(r"<[^>]+>", " ", block) for block in blocks)
    return len(re.findall(r"\b[\w$-]+\b", plain, flags=re.UNICODE))


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#C7D3DC"))
    canvas.line(2 * cm, 1.35 * cm, A4[0] - 2 * cm, 1.35 * cm)
    canvas.setFont("Arial", 8)
    canvas.setFillColor(colors.HexColor("#607784"))
    canvas.drawString(2 * cm, 0.95 * cm, "Yerkezhan Batyrova | 92131651 | Data Engineering | Task 1")
    canvas.drawRightString(A4[0] - 2 * cm, 0.95 * cm, f"Page {doc.page}")
    canvas.restoreState()


def make_doc(path: Path) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=1.7 * cm,
        title=path.stem, author="Yerkezhan Batyrova",
        subject="DLBDSEDE02 Project: Data Engineering - Task 1",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="portfolio", frames=[frame], onPage=footer))
    return doc


def header(s: dict[str, ParagraphStyle], title: str, phase: str) -> list:
    return [
        Paragraph(title, s["title"]),
        Paragraph(
            f"Batyrova, Yerkezhan | Matriculation no. 92131651 | "
            f"DLBDSEDE02 Project: Data Engineering | {phase}",
            s["meta"],
        ),
    ]


P1_BLOCKS = [
    "The proposed system is an hourly municipal air-quality data layer. Environmental analysts inspect trends, gaps and anomalous readings; city planners compare stations and policy periods; a dashboard developer requests recent values; a data steward monitors runs; and an authorised warning officer may review threshold candidates. The prototype never sends public alerts.",
    "The UCI Beijing dataset supplies 420,768 historical rows from 12 stations only as a scale and missing-data simulation. It cannot represent another city: calibration, precision, station siting and spatial coverage are unverified, while hourly values may be unsuitable for some health questions.",
    "MongoDB stores one flexible station-hour document, validated shared fields and quality flags. Compound indexes support station/time and comparison queries. PostgreSQL offers stronger fixed relational structure; files lack concurrent indexed queries; a warehouse is excessive for this operational prototype.",
    "The loader will use 1,000-row batches, deterministic identifiers, insert-only upserts, bounded retries, quarantine and run heartbeats. Success requires 420,768 source rows reconciled, no duplicate station-hours, a harmless replay, visible quality counts, and four stakeholder queries within a 2-second local target. Any silent imputation, unreconciled row, failed run, unapproved alert or missed target is failure.",
]

P2_BLOCKS = [
    f"Repository: {REPO}",
    "I implemented a Python-to-MongoDB batch pipeline around user decisions rather than a generic dashboard. The public-dashboard contract returns the latest 24 station records; analysts receive daily pollutant trends with observation counts; planners compare stations over a chosen policy period; and data stewards receive quality summaries, run status, heartbeats and reconciliation counters. Each query is timed against a configurable 2,000 ms prototype target.",
    "The loader now recognises UCI's nested archive, normalises timezone-aware station-hours, writes 1,000-record batches and safely replays them through deterministic IDs and insert-only upserts. Structural failures enter a quarantine collection. Missing values remain absent; configurable completeness and plausibility checks retain questionable readings with warning flags instead of inventing values. Example thresholds generate review candidates only and cannot notify citizens.",
    "Testing includes eleven unit tests plus a complete source parse. All 420,768 rows were readable: 383,964 passed configured checks and 36,804 carried warnings; none was structurally rejected. Docker Compose provides MongoDB, ingestion and an optional benchmark service. Run `docker compose up --build`, inspect `python -m src.monitoring`, then execute the verification profile. Production still requires municipal sensor metadata, approved health policy, authentication, TLS, backups and measured infrastructure-specific latency.",
]


def build_p1(s: dict[str, ParagraphStyle]) -> None:
    assert word_count(P1_BLOCKS) <= 200, word_count(P1_BLOCKS)
    story = header(s, "Stakeholder-driven municipal air-quality batch system", "Portfolio part 1 - Conception")
    headings = ["Purpose and stakeholders", "Evidence and limitations", "Database choice", "Plan and success criteria"]
    for heading_text, body in zip(headings, P1_BLOCKS):
        story.extend([Paragraph(heading_text, s["heading"]), Paragraph(body, s["body"])])
    story.append(Paragraph(
        f"Sources: UCI Machine Learning Repository, Beijing Multi-Site Air Quality, {UCI}; "
        "MongoDB, Data Modeling, https://www.mongodb.com/docs/manual/data-modeling/",
        s["small"],
    ))
    make_doc(OUTPUT / NAMES["p1"]).build(story)


def build_p2(s: dict[str, ParagraphStyle]) -> None:
    assert word_count(P2_BLOCKS) <= 200, word_count(P2_BLOCKS)
    story = header(s, "Development and reflection", "Portfolio part 2")
    headings = ["Implementation and user contracts", "Reliability and data quality", "Verification and boundaries"]
    story.append(Paragraph(P2_BLOCKS[0], s["small"]))
    for heading_text, body in zip(headings, P2_BLOCKS[1:]):
        story.extend([Paragraph(heading_text, s["heading"]), Paragraph(body, s["body"])])
    make_doc(OUTPUT / NAMES["p2"]).build(story)


def build_abstract(s: dict[str, ParagraphStyle]) -> None:
    story = header(s, "Municipal air-quality decision-support pipeline", "Portfolio part 3 - Abstract")
    story += [
        Paragraph("Problem framing and stakeholder requirements", s["heading"]),
        Paragraph(
            "A municipal air-quality pipeline is useful only when its outputs correspond to real decisions. "
            "The redesigned prototype therefore starts with five roles. Environmental analysts need raw values, "
            "missingness and anomaly flags to judge whether a trend is credible. City planners and policy teams "
            "need station comparisons and before/after date windows, including observation counts, to discuss "
            "transport or land-use interventions. Public-dashboard developers need a stable latest-reading and "
            "daily-series contract. Data stewards need run status, heartbeats, rejected rows and reconciliation "
            "counters. Authorised warning officers may review threshold candidates, but public notification is "
            "outside this prototype and must remain blocked until a municipality approves thresholds, ownership "
            "and escalation rules.", s["body"]),
        Paragraph(
            "These needs become measurable acceptance criteria. A load must reconcile all source rows as stored "
            "or quarantined, create no duplicate station-hour keys, survive a replay without changing the stored "
            "count, expose terminal run status and quality totals, and support four representative queries within "
            "a configurable 2,000 ms target in the declared local environment. The latency target is a prototype "
            "service objective, not a universal performance claim; the included benchmark stores elapsed time and "
            "fails its command when any query misses the target.", s["body"]),
        Paragraph("Source, bias and fitness for use", s["heading"]),
        Paragraph(
            "The UCI Beijing Multi-Site Air Quality dataset contains 420,768 hourly records from 12 stations for "
            "2013-2017 (UCI Machine Learning Repository, n.d.). It is used as a historical test fixture because its "
            "volume, multiple stations and missing fields exercise the ingestion design. It is not the intended "
            "production feed and cannot justify conclusions about another city. The supplied CSV data alone do "
            "not establish sensor calibration, precision, maintenance history, station coordinates, siting "
            "quality or independence between nearby stations. A government source is therefore recorded as "
            "provenance, not treated as proof of accuracy. Hourly values may be adequate for operational trends "
            "yet inappropriate for short exposure events or policy indicators requiring other averaging periods "
            "(World Health Organization, 2021).", s["body"]),
        Paragraph(
            "The pipeline makes those limits visible. Missing measurements remain absent instead of becoming "
            "zero. Technical plausibility ranges are configurable and explicitly separated from legal or health "
            "limits. Questionable but structurally usable observations remain queryable with warning flags; "
            "malformed rows enter a quarantine collection with a reason. Aggregations return observation counts, "
            "allowing users to see whether comparisons rely on unequal evidence. Production onboarding would add "
            "a station registry with coordinates, calibration and sensor model, signed delivery manifests, "
            "independent-reference checks and a domain-approved aggregation policy.", s["body"]),
        PageBreak(),
    ]
    story += header(s, "Municipal air-quality decision-support pipeline", "Portfolio part 3 - Abstract")
    story += [
        Paragraph("Implementation and maintainability", s["heading"]),
        Paragraph(
            "The Python loader downloads the official archive, recognises its nested ZIP structure and streams "
            "the twelve station CSV files. Each row becomes a timezone-aware station-hour document. Deterministic "
            "identifiers and insert-only upserts make replays harmless; batches of 1,000 use bounded retry for "
            "transient errors. The flexible measurements object accepts future sensor fields, while JSON Schema "
            "validation protects identity, timestamp, provenance and quality fields (MongoDB, n.d.-a).", s["body"]),
        Paragraph(
            "MongoDB was chosen for indexed station/time access and evolving measurement sets. PostgreSQL suits a "
            "stable relational registry and join-heavy analysis; files lack concurrent indexed queries; a "
            "warehouse adds premature scope. Separate collections hold measurements, quarantine, runs, benchmarks "
            "and source metadata. Docker Compose packages the prototype, while production still requires secrets, "
            "TLS, backups, replication and workload-led sharding.", s["body"]),
        Paragraph("Evaluation and learning", s["heading"]),
        Paragraph(
            "Eleven unit tests cover transformation, missing values, future metrics, batching, nested archives, "
            "quarantine IDs, quality flags and query contracts. A complete parse read all 420,768 rows across 12 "
            "stations: 383,964 passed every configured check and 36,804 remained available with warnings. In "
            "36,788 rows a required pollutant was missing; 16 contained an out-of-range value; categories can "
            "overlap. No row was structurally rejected. The repository includes the reproducible profile, health "
            "and quality commands, and latency benchmark. Docker was unavailable in the document-generation "
            "environment, so infrastructure latency is not claimed; the executable benchmark is the target-machine "
            "acceptance gate.", s["body"]),
        Paragraph(
            "Feedback showed that naming users is insufficient: each needs a decision, data contract, quality "
            "evidence and failure condition. This changed a generic loader into an auditable service boundary. "
            "Next, municipal interviews should validate needs; a registry should capture stations and calibration; "
            "spatial coverage, averaging and alert policies need domain approval; and concurrent workloads require "
            "benchmarking before a dashboard consumes the contracts.", s["body"]),
        Paragraph("References", s["heading"]),
        Paragraph(
            f"UCI Machine Learning Repository. (n.d.). <i>Beijing Multi-Site Air Quality Data</i>. {UCI}<br/>"
            "MongoDB. (n.d.-a). <i>Schema validation</i>. https://www.mongodb.com/docs/manual/core/schema-validation/<br/>"
            "MongoDB. (n.d.-b). <i>Indexes</i>. https://www.mongodb.com/docs/manual/indexes/<br/>"
            "World Health Organization. (2021). <i>WHO global air quality guidelines</i>. "
            "https://www.who.int/publications/i/item/9789240034228",
            s["small"],
        ),
    ]
    make_doc(OUTPUT / NAMES["abstract"]).build(story)


def build_product(s: dict[str, ParagraphStyle]) -> None:
    story = header(s, "Product handover and verification guide", "Portfolio part 3 - Product")
    story += [
        Paragraph("Repository", s["heading"]),
        Paragraph(REPO, s["body"]),
        Paragraph("1. Clean start", s["heading"]),
        Paragraph("docker compose down -v<br/>docker compose up --build", s["code"]),
        Paragraph(
            "The first command removes only this Compose project's database volume. The second starts MongoDB, "
            "waits for its health check, downloads the official nested UCI archive and performs an idempotent "
            "batch load.", s["body"]),
        Paragraph("2. Inspect health and data quality", s["heading"]),
        Paragraph(
            "docker compose run --rm ingest python -m src.monitoring<br/>"
            "docker compose run --rm ingest python -m src.queries quality",
            s["code"],
        ),
        Paragraph(
            "A successful health report shows a terminal `succeeded` run with source, accepted, warning, rejected, "
            "inserted and existing-row counters. Source rows must reconcile. The verified fixture profile contains "
            "420,768 rows: 383,964 accepted and 36,804 warning; no structural rejection.", s["body"]),
        Paragraph("3. Exercise user contracts and latency gate", s["heading"]),
        Paragraph(
            "docker compose run --rm ingest python -m src.queries trend --station Aotizhongxin --pollutant pm25<br/>"
            "docker compose run --rm ingest python -m src.queries compare --pollutant pm25<br/>"
            "docker compose --profile verification up --build --abort-on-container-exit",
            s["code"],
        ),
        Paragraph(
            "The benchmark checks recent readings, a daily trend, a station comparison and the quality summary "
            "against the configurable 2,000 ms target. It records evidence in `query_benchmarks` and exits nonzero "
            "on failure. Re-run ingestion once; the measurement count must not increase.", s["body"]),
        Paragraph("Operational boundary", s["heading"]),
        Paragraph(
            "`config/alert_thresholds.example.json` is non-authoritative and produces review candidates only. The "
            "prototype sends no citizen notification. Before production, replace the historical fixture with a "
            "contracted municipal feed and add verified station metadata, approved policy thresholds, access "
            "control, TLS, backups, replication and workload testing.", s["body"]),
    ]
    make_doc(OUTPUT / NAMES["product"]).build(story)


def main() -> None:
    register_fonts()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    s = styles()
    build_p1(s)
    build_p2(s)
    build_abstract(s)
    build_product(s)
    for filename in NAMES.values():
        (DOCS / filename).write_bytes((OUTPUT / filename).read_bytes())
    print(f"P1 body words: {word_count(P1_BLOCKS)}")
    print(f"P2 body words: {word_count(P2_BLOCKS)}")
    for filename in NAMES.values():
        print(OUTPUT / filename)


if __name__ == "__main__":
    main()
