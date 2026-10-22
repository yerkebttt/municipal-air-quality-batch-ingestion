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


def abstract_styles() -> dict[str, ParagraphStyle]:
    """Formal abstract styles required by section 4.3 of the assignment."""
    s = styles()
    s["title"] = ParagraphStyle(
        "AbstractTitle", parent=s["title"], fontSize=12, leading=18,
        spaceAfter=6, textColor=colors.black,
    )
    s["heading"] = ParagraphStyle(
        "AbstractHeading", parent=s["heading"], fontSize=12, leading=18,
        spaceBefore=4, spaceAfter=3, textColor=colors.black,
    )
    s["body"] = ParagraphStyle(
        "AbstractBody", parent=s["body"], fontSize=11, leading=16.5,
        alignment=TA_JUSTIFY, spaceAfter=6, hyphenationLang="en_GB",
    )
    s["small"] = ParagraphStyle(
        "AbstractSmall", parent=s["small"], fontSize=10, leading=15,
        alignment=TA_JUSTIFY, spaceAfter=6, hyphenationLang="en_GB",
    )
    s["reference"] = ParagraphStyle(
        "AbstractReference", parent=s["small"], fontSize=10, leading=12,
        alignment=TA_LEFT, spaceAfter=2,
    )
    return s


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
        topMargin=2 * cm, bottomMargin=2 * cm,
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
    "The product is a batch data service for municipal air-quality work. Analysts study trends and doubtful readings; planners compare locations and policy periods; dashboard developers request recent values. A data steward checks runs, while an authorised officer reviews possible alert cases. The prototype does not warn citizens automatically.",
    "The UCI Beijing dataset provides 420,768 hourly observations from 12 stations. It supports testing of volume and missing values, but it cannot describe another municipality. The files do not confirm calibration, sensor precision or spatial coverage, and hourly data may not answer every health question.",
    "MongoDB stores each station-hour as a flexible document with validated common fields and quality labels. Indexes support user queries; replica sets and sharding allow later cloud growth. PostgreSQL suits a stable relational model, CSV files give weak concurrent access, and a warehouse adds unnecessary scope.",
    "Implementation will use Docker Compose, batches of 1,000, deterministic IDs, insert-only upserts, limited retries, quarantine and run heartbeats. Success means all source rows reconcile, replay creates no duplicates, quality results stay visible, and four user queries remain below two seconds. Silent replacement of missing data, a failed run or unapproved alert is failure.",
]

P2_BLOCKS = [
    f"Repository: {REPO}",
    "I developed a Python and MongoDB pipeline around stakeholder actions. It sits between a future municipal sensor export and an API or BI layer: dashboards receive the latest 24 records, analysts request daily pollutant trends, planners compare stations for a selected period, and data stewards inspect quality and run status. Every query is measured against a 2,000 ms target.",
    "The loader opens the nested UCI archive, converts each row into a timezone-aware station-hour document and writes batches of 1,000. Deterministic IDs and insert-only upserts make repeated runs safe. Invalid structures go to quarantine. Missing measurements stay absent, while doubtful values are kept with warning labels. Example thresholds only create cases for human review; they do not send an alert.",
    "Fourteen unit tests passed. The Docker run stored all 420,768 rows: 383,964 were accepted and 36,804 had warnings, with zero structural rejection. Reconciliation now blocks incomplete runs. All four benchmark queries passed; the slowest quality summary took 221.352 ms. Docker Compose makes the system reproducible. Production still requires verified station metadata, approved health rules, authentication, TLS, backups and interviews with actual users.",
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
            "This project provides a reliable data layer for municipal air-quality decisions. Environmental "
            "analysts need raw measurements, missing-value information and warning labels to judge trends. City "
            "planners compare stations and policy periods when discussing traffic or land-use measures. A dashboard "
            "developer needs recent readings and daily series in a stable format, while the data steward needs run "
            "status, rejected rows and reconciliation figures. An authorised officer may review threshold cases, "
            "but the prototype cannot notify citizens without approved policy and named responsibility.", s["body"]),
        Paragraph(
            "These needs become testable conditions. Every source row must be stored or quarantined, replay must "
            "not create duplicates, and each run must finish with a visible status. Four representative queries "
            "must complete within 2,000 ms on the test laptop. This is a prototype target rather than a universal "
            "performance claim, and every benchmark result is recorded.", s["body"]),
        Paragraph("Dataset limitations and possible bias", s["heading"]),
        Paragraph(
            "The UCI Beijing Multi-Site Air Quality dataset contains 420,768 hourly records from 12 stations for "
            "2013-2017 (UCI Machine Learning Repository, n.d.). It simulates a future municipal batch feed and gives "
            "realistic volume and missingness, but it cannot support conclusions about another city. The files do "
            "not prove calibration, precision, maintenance history, station placement or spatial coverage. Nearby "
            "stations may also observe similar local conditions. Government publication does not remove possible "
            "bias. Hourly values can support trends but may hide short events or fail health indicators that require "
            "another averaging period "
            "(World Health Organization, 2021).", s["body"]),
        Paragraph(
            "Missing measurements therefore remain absent instead of becoming zero. Plausibility ranges are only "
            "technical screens, not medical limits. Doubtful readable records remain available with warnings; "
            "invalid structures go to quarantine with a reason. Aggregates include observation counts so unequal "
            "evidence is visible. Production needs a municipal station register with coordinates, sensor models, "
            "calibration dates and maintenance history.", s["body"]),
        Paragraph("Technical implementation", s["heading"]),
        Paragraph(
            "The Python loader downloads the source, opens its nested ZIP archive and reads 12 station files. Each "
            "row becomes a timezone-aware station-hour document. An ID from station and timestamp, together with "
            "insert-only upserts, makes replay safe. Batches of 1,000 and bounded exponential retries handle temporary "
            "database errors. MongoDB validation protects identity, time, provenance and quality fields while the "
            "measurements object remains flexible for future metrics (MongoDB, n.d.-a).", s["body"]),
        PageBreak(),
    ]
    story += header(s, "Municipal air-quality decision-support pipeline", "Portfolio part 3 - Abstract")
    story += [
        Paragraph("Database choice and portability", s["heading"]),
        Paragraph(
            "MongoDB supports indexed station/time queries and changing measurement sets. PostgreSQL is attractive "
            "for a fixed relational registry, plain files lack concurrent indexed access, and a warehouse is excessive "
            "for this prototype. Separate collections hold readings, quarantine, runs, benchmarks and source limits. "
            "Docker Compose provides portability. Production still needs secrets, TLS, backups, replication and "
            "workload testing before sharding.", s["body"]),
        Paragraph("Testing and observed results", s["heading"]),
        Paragraph(
            "Fourteen unit tests cover normalisation, future metrics, batching, nested archives, quality flags, query "
            "contracts and reconciliation. The full Docker run processed all 420,768 rows: 383,964 were accepted, "
            "36,804 retained with warnings, and none structurally rejected. Of the warnings, 36,788 missed a required "
            "pollutant and 16 contained an out-of-range value; categories can overlap.", s["body"]),
        Paragraph(
            "All four local benchmark queries met 2,000 ms: latest readings took 15.931 ms, daily PM2.5 trend "
            "16.505 ms, station comparison 21.217 ms, and quality summary 221.352 ms. This supports the prototype "
            "scenario but does not replace concurrent production testing.", s["body"]),
        Paragraph("Reflection and next steps", s["heading"]),
        Paragraph(
            "Feedback showed me that listing users is not enough: every role needs a decision, query, quality condition "
            "and failure case. A technical problem appeared when the outer archive exposed a non-measurement CSV; "
            "the loader read it and reported a missing station. I inspected the archive structure, added nested-ZIP "
            "handling and created a regression test. For future projects, I will first interview users, write measurable "
            "data contracts and failure criteria, then test assumptions with representative data before adding features. "
            "Municipal staff must still validate displays, spatial coverage, averaging and alert rules.", s["body"]),
        Paragraph("References", s["heading"]),
        Paragraph(
            f"UCI Machine Learning Repository. (n.d.). <i>Beijing Multi-Site Air Quality Data</i>. {UCI}",
            s["reference"],
        ),
        Paragraph(
            "MongoDB. (n.d.-a). <i>Schema validation</i>. "
            "https://www.mongodb.com/docs/manual/core/schema-validation/",
            s["reference"],
        ),
        Paragraph(
            "MongoDB. (n.d.-b). <i>Indexes</i>. https://www.mongodb.com/docs/manual/indexes/",
            s["reference"],
        ),
        Paragraph(
            "World Health Organization. (2021). <i>WHO global air quality guidelines</i>. "
            "https://www.who.int/publications/i/item/9789240034228",
            s["reference"],
        ),
    ]
    make_doc(OUTPUT / NAMES["abstract"]).build(story)


def build_product(s: dict[str, ParagraphStyle]) -> None:
    story = header(s, "Product use and verification guide", "Portfolio part 3 - Product")
    story += [
        Paragraph("Repository", s["heading"]),
        Paragraph(REPO, s["body"]),
        Paragraph("1. Clone and start", s["heading"]),
        Paragraph(
            "git clone https://github.com/yerkebttt/municipal-air-quality-batch-ingestion.git<br/>"
            "cd municipal-air-quality-batch-ingestion<br/>"
            "docker compose down -v<br/>docker compose up --build",
            s["code"],
        ),
        Paragraph(
            "The down command removes the database volume for this project. The up command starts MongoDB, "
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
    s = styles()
    build_p1(s)
    build_p2(s)
    build_abstract(abstract_styles())
    build_product(s)
    print(f"P1 body words: {word_count(P1_BLOCKS)}")
    print(f"P2 body words: {word_count(P2_BLOCKS)}")
    for filename in NAMES.values():
        print(OUTPUT / filename)


if __name__ == "__main__":
    main()
