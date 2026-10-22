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


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName="Arial-Bold", fontSize=10,
            leading=15, alignment=TA_LEFT, textColor=colors.black, spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["Normal"], fontName="Arial", fontSize=10,
            leading=15, textColor=colors.black, spaceAfter=7,
        ),
        "heading": ParagraphStyle(
            "Heading", parent=base["Heading2"], fontName="Arial-Bold", fontSize=10,
            leading=15, textColor=colors.black, spaceBefore=4,
            spaceAfter=3, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Arial", fontSize=10,
            leading=15, alignment=TA_JUSTIFY, spaceAfter=5,
            allowWidows=0, allowOrphans=0, splitLongWords=True,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName="Arial", fontSize=10,
            leading=13, alignment=TA_LEFT, textColor=colors.black,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName="Arial", fontSize=10,
            leading=15, alignment=TA_LEFT, leftIndent=13, firstLineIndent=-9,
            bulletIndent=2, spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "Code", parent=base["Code"], fontName="Arial", fontSize=10,
            leading=13, leftIndent=8, rightIndent=8, borderColor=colors.black,
            borderWidth=0.5, borderPadding=5, backColor=None, textColor=colors.black,
            spaceBefore=3, spaceAfter=6,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"], fontName="Arial", fontSize=10,
            leading=10, alignment=TA_CENTER, textColor=colors.black,
        ),
    }


def word_count(blocks: list[str]) -> int:
    plain = " ".join(re.sub(r"<[^>]+>", " ", block) for block in blocks)
    return len(re.findall(r"\b[\w$-]+\b", plain, flags=re.UNICODE))


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.black)
    canvas.line(2 * cm, 1.35 * cm, A4[0] - 2 * cm, 1.35 * cm)
    canvas.setFont("Arial", 10)
    canvas.setFillColor(colors.black)
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
    "The product is a batch data service for municipal air-quality work. Analysts study trends and doubtful readings; planners compare locations and policy periods; dashboard developers request recent values. A data steward checks runs, while an authorised officer reviews possible alert cases. The system does not send warnings to citizens.",
    "The UCI Beijing dataset provides 420,768 hourly observations from 12 stations. It supports testing of volume and missing values, but it cannot describe another municipality. The files do not confirm calibration, sensor precision or spatial coverage, and hourly data may not answer every health question.",
    "MongoDB stores each station-hour as a flexible document with protected common fields and quality labels. Indexes support time and station queries. PostgreSQL is stronger for a stable relational model, CSV files provide weak concurrent access, and a warehouse would add too much scope.",
    "Implementation will use batches of 1,000, deterministic IDs, insert-only upserts, limited retries, quarantine records and run heartbeats. Success means all source rows are reconciled, no duplicate station-hours appear, replay is harmless, quality results are visible, and four user queries stay below two seconds. Silent replacement of missing data, failed runs or an unapproved alert are treated as failures.",
]

P2_BLOCKS = [
    f"Repository: {REPO}",
    "I developed a Python and MongoDB pipeline based on stakeholder actions. A dashboard receives the latest 24 records, analysts request daily pollutant trends, planners compare stations for a selected period, and data stewards inspect quality and run status. Every query is measured against a 2,000 ms target.",
    "The loader opens the nested UCI archive, converts each row into a timezone-aware station-hour document and writes batches of 1,000. Deterministic IDs and insert-only upserts make repeated runs safe. Invalid structures go to quarantine. Missing measurements stay absent, while doubtful values are kept with warning labels. Example thresholds only create cases for human review; they do not send an alert.",
    "Eleven unit tests passed. The complete Docker run stored all 420,768 rows: 383,964 were accepted and 36,804 had quality warnings, with zero structural rejection. All four benchmark queries passed the 2,000 ms target; the slowest quality summary took 221.352 ms. Docker Compose provides a reproducible environment and monitoring commands. For production, the municipality still needs verified station metadata, approved health rules, authentication, TLS, backups and interviews with actual users.",
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
        Paragraph("Purpose and stakeholder needs", s["heading"]),
        Paragraph(
            "The purpose of this project is to provide a reliable data layer for municipal air-quality decisions. "
            "The design begins with people who will actually use its outputs. Environmental analysts need raw "
            "measurements, missing-value information and warning labels, so they can decide whether a trend is "
            "trustworthy. City planners and policy teams need comparisons between stations and time periods when "
            "they discuss traffic or land-use measures. A dashboard developer needs recent readings and daily "
            "series in a stable format. The data steward needs run status, rejected rows and clear reconciliation "
            "figures. An authorised warning officer may review threshold cases, but the prototype cannot send "
            "messages to citizens. Such action requires approved policy and named responsibility.", s["body"]),
        Paragraph(
            "These expectations were converted into testable conditions. Every source row must be either stored or "
            "quarantined, a repeated run must not create duplicates, and every ingestion run must finish with a "
            "visible status. The system also needs to return four representative queries within 2,000 ms on the "
            "declared local computer. This target is not a promise for every infrastructure. It is a practical "
            "prototype limit, and the benchmark records the measured time for later comparison.", s["body"]),
        Paragraph("Dataset limitations and possible bias", s["heading"]),
        Paragraph(
            "The UCI Beijing Multi-Site Air Quality dataset contains 420,768 hourly records from 12 stations for "
            "2013-2017 (UCI Machine Learning Repository, n.d.). In this project it represents a future municipal "
            "batch feed and allows realistic volume testing. However, it is historical Beijing data and should not "
            "be used for conclusions about another city. The CSV files do not prove calibration accuracy, sensor "
            "maintenance, station placement or spatial coverage. They also do not show whether nearby stations "
            "observe the same local conditions. Even if the source was published by a government organisation, "
            "this does not automatically remove bias. Hourly measurements are suitable for many trends, but they "
            "may be too broad for short pollution events or health indicators based on another averaging period "
            "(World Health Organization, 2021).", s["body"]),
        Paragraph(
            "The pipeline does not hide these issues. Missing measurements remain absent rather than being changed "
            "to zero. Configurable plausibility ranges are used only for technical screening and are not presented "
            "as medical limits. A doubtful but readable record is kept with a warning, while a structurally invalid "
            "row goes to quarantine with a reason. Query results include observation counts, which helps users see "
            "when two comparisons are based on unequal evidence. Before production use, municipality should add a "
            "station register with coordinates, sensor models, calibration dates and maintenance history.", s["body"]),
        PageBreak(),
    ]
    story += header(s, "Municipal air-quality decision-support pipeline", "Portfolio part 3 - Abstract")
    story += [
        Paragraph("Technical implementation", s["heading"]),
        Paragraph(
            "The Python loader downloads the official source, opens its nested ZIP archive and reads the 12 station "
            "files in sequence. Every CSV row becomes one timezone-aware station-hour document. The ID is produced "
            "from station and timestamp, therefore the same row receives the same key during each run. Insert-only "
            "upserts make replay safe, while batches of 1,000 and limited exponential retries deal with temporary "
            "database problems. MongoDB validation protects the identity, time, provenance and quality fields, "
            "although the measurements object stays flexible for a future sensor metric (MongoDB, n.d.-a).", s["body"]),
        Paragraph(
            "MongoDB was chosen because it supports indexed station and time queries while accepting a changing set "
            "of measurements. PostgreSQL would be a good option for a fixed relational registry, but plain files "
            "cannot provide the same concurrent indexed access. A warehouse would create unnecessary complexity "
            "for this stage. Separate collections store readings, rejected rows, ingestion runs, query benchmarks "
            "and source limitations. Docker Compose makes the prototype reproducible. A real deployment would "
            "still require secure secrets, TLS, backups, replication and workload testing before sharding.", s["body"]),
        Paragraph("Testing and observed results", s["heading"]),
        Paragraph(
            "Eleven unit tests passed and covered normalisation, missing values, new metrics, batching, nested "
            "archives, quality flags and user query contracts. The full Docker run processed all 420,768 rows. "
            "It stored 383,964 accepted observations and 36,804 warning observations, with zero structural "
            "rejections. Among the warnings, 36,788 records missed at least one required pollutant and 16 contained "
            "a value outside the screening range; these categories can overlap. Replay protection and run counters "
            "are available for further checks.", s["body"]),
        Paragraph(
            "All four benchmark queries met the 2,000 ms target on the test laptop. The latest-reading query took "
            "15.931 ms, the daily PM2.5 trend took 16.505 ms, the station comparison took 21.217 ms, and the quality "
            "summary took 221.352 ms. These results show that the prototype can deliver the required amount of data "
            "in reasonable time for one local run, but they do not replace concurrent production testing.", s["body"]),
        Paragraph("Reflection and next steps", s["heading"]),
        Paragraph(
            "The most important change after feedback was moving from a developer-centred idea to a stakeholder "
            "view. Listing users was not sufficient; each role needed a decision, a query, a quality condition and "
            "a clear failure case. This made the solution more useful and also easier to test. The next step is to "
            "interview real municipal staff, confirm their display and comparison needs, register stations, test "
            "spatial coverage, and approve averaging and alert rules before system can be used by the public.", s["body"]),
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
    story = header(s, "Product use and verification guide", "Portfolio part 3 - Product")
    story += [
        Paragraph("Repository", s["heading"]),
        Paragraph(REPO, s["body"]),
        Paragraph("1. Clean start", s["heading"]),
        Paragraph("docker compose down -v<br/>docker compose up --build", s["code"]),
        Paragraph(
            "The first command removes the database volume for this project. The second command starts MongoDB, "
            "waits for a successful health check, downloads the official nested UCI archive and loads the data in "
            "repeatable batches.", s["body"]),
        Paragraph("2. Inspect health and data quality", s["heading"]),
        Paragraph(
            "docker compose run --rm ingest python -m src.monitoring<br/>"
            "docker compose run --rm ingest python -m src.queries quality",
            s["code"],
        ),
        Paragraph(
            "The health report should show a completed run and counters for source, accepted, warning, rejected, "
            "inserted and existing records. The verified run processed and stored all 420,768 rows. It reported "
            "383,964 accepted observations, 36,804 warnings and zero structural rejection.", s["body"]),
        Paragraph("3. Exercise user contracts and latency gate", s["heading"]),
        Paragraph(
            "docker compose run --rm ingest python -m src.queries trend --station Aotizhongxin --pollutant pm25<br/>"
            "docker compose run --rm ingest python -m src.queries compare --pollutant pm25<br/>"
            "docker compose --profile verification up --build --exit-code-from verify",
            s["code"],
        ),
        Paragraph(
            "The benchmark checks recent readings, a daily PM2.5 trend, a comparison of 12 stations and a quality "
            "summary. All queries passed the 2,000 ms target. Their measured times were 15.931 ms, 16.505 ms, "
            "21.217 ms and 221.352 ms. The command records results in query_benchmarks and exits with an error code "
            "if a future query misses the target. After a repeated load, the measurement count must not increase.", s["body"]),
        Paragraph("Operational boundary", s["heading"]),
        Paragraph(
            "The threshold configuration is an example and creates cases for review only. The prototype cannot "
            "notify citizens. Before production use, the historical fixture must be replaced by an agreed municipal "
            "feed. The municipality also needs verified station metadata, approved policy thresholds, access "
            "control, TLS, backups, replication and testing with concurrent users.", s["body"]),
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
