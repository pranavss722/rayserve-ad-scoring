"""Generate Pranav Saravanan's resume PDF using reportlab."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

OUTPUT = os.path.join("C:/mnt/user-data/outputs", "Pranav_Saravanan_Resume_2026.pdf")

# Page setup
LEFT_MARGIN = 0.45 * inch
RIGHT_MARGIN = 0.45 * inch
TOP_MARGIN = 0.3 * inch
BOTTOM_MARGIN = 0.3 * inch

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=letter,
    leftMargin=LEFT_MARGIN,
    rightMargin=RIGHT_MARGIN,
    topMargin=TOP_MARGIN,
    bottomMargin=BOTTOM_MARGIN,
)

usable_width = letter[0] - LEFT_MARGIN - RIGHT_MARGIN

# -- En-dash for date ranges --
EN = "\u2013"

# Styles
style_name = ParagraphStyle("Name", fontName="Helvetica-Bold", fontSize=14.5, alignment=TA_CENTER, leading=17)
style_contact = ParagraphStyle("Contact", fontName="Helvetica", fontSize=8.2, alignment=TA_CENTER, leading=10)
style_section = ParagraphStyle("Section", fontName="Helvetica-Bold", fontSize=10, leading=12, spaceBefore=5, spaceAfter=0)
style_jobtitle_left = ParagraphStyle("JobTitleL", fontName="Helvetica-Bold", fontSize=8.7, leading=11)
style_jobtitle_right = ParagraphStyle("JobTitleR", fontName="Helvetica", fontSize=8.7, leading=11, alignment=TA_RIGHT)
style_subtitle = ParagraphStyle("Subtitle", fontName="Helvetica-Oblique", fontSize=8.2, leading=10)
style_body = ParagraphStyle("Body", fontName="Helvetica", fontSize=8.2, leading=10)
style_bullet = ParagraphStyle("Bullet", fontName="Helvetica", fontSize=8.2, leading=10, leftIndent=10, bulletIndent=0)
style_proj_title = ParagraphStyle("ProjTitle", fontName="Helvetica", fontSize=8.2, leading=10)
style_url = ParagraphStyle("URL", fontName="Helvetica", fontSize=7.5, leading=9, leftIndent=10)
style_skills_label = ParagraphStyle("SkillsLabel", fontName="Helvetica", fontSize=8.2, leading=10)


def section_header(text):
    return [
        Spacer(1, 3),
        Paragraph(text, style_section),
        HRFlowable(width="100%", thickness=0.75, color="black", spaceBefore=1, spaceAfter=3),
    ]


def job_header(title, date, subtitle):
    tbl = Table(
        [[Paragraph(title, style_jobtitle_left), Paragraph(date, style_jobtitle_right)]],
        colWidths=[usable_width * 0.75, usable_width * 0.25],
    )
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    items = [tbl]
    if subtitle:
        items.append(Paragraph(subtitle, style_subtitle))
    return items


def bullet(text):
    return Paragraph(f"\u2022  {text}", style_bullet)


story = []

# === NAME ===
story.append(Paragraph("PRANAV SARAVANAN", style_name))
story.append(Spacer(1, 2))

# === CONTACT (languages moved out) ===
contact_line = "pranavss722@gmail.com  |  (669) 264-7569  |  github.com/pranavss722"
story.append(Paragraph(contact_line, style_contact))

# === EDUCATION ===
story.extend(section_header("EDUCATION"))
edu_tbl = Table(
    [[
        Paragraph("<b>Bachelor of Science, Data Science</b>", style_body),
        Paragraph("May 2023", style_jobtitle_right),
    ]],
    colWidths=[usable_width * 0.75, usable_width * 0.25],
)
edu_tbl.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
]))
story.append(edu_tbl)
story.append(Paragraph("Fowler School of Engineering, Chapman University, Orange, CA", style_subtitle))

# === TECHNICAL SKILLS (subcategorized) ===
story.extend(section_header("TECHNICAL SKILLS"))
skills = [
    ("Languages", "Python, SQL, Scala, Java, JavaScript, C++, GraphQL"),
    ("ML &amp; Data", "TensorFlow, PyTorch, XGBoost, Scikit-learn, Spark ML, PySpark, Spark, Hive"),
    ("Cloud &amp; Infra", "AWS (SageMaker, Athena, Glue, S3, DynamoDB), Databricks (Unity Catalog, MLOps Stacks), "
     "Terraform, Kubernetes, Spinnaker, Docker"),
    ("ML Platforms", "MLflow, Feast, Airflow (MWAA), Liquibase"),
    ("Web &amp; APIs", "FastAPI, React, Node.js, Apache Kafka, Redis, LangChain, FAISS"),
    ("Observability", "Langfuse, RAGAS, Prometheus, Grafana, Git"),
]
for label, items in skills:
    story.append(Paragraph(f"<b>{label}:</b> {items}", style_skills_label))

# === EXPERIENCE (full-time roles) ===
story.extend(section_header("EXPERIENCE"))

# Disney
story.extend(job_header(
    "Machine Learning Engineer, Ad Platforms", f"Dec 2024 {EN} Present",
    "Disney Entertainment &amp; ESPN Technology, San Francisco, CA",
))
for b in [
    "Architecting an end-to-end self-service ML platform (Feast, Unity Catalog, DynamoDB, MLflow, Databricks) "
    "covering feature store design, schema migrations, online inference, and automated champion deployment "
    "across Hulu and Disney+ ad products.",
    f"Built standardized inference container with canary rollout (1%\u2192100% traffic splits), SLO-based "
    "auto-rollback, and Airflow-orchestrated daily scoring and retraining pipelines.",
    "Recovered ~1.8M missing Hulu-on-Disney+ users by diagnosing upstream identity pipeline gaps and "
    "coordinating cross-team production fix.",
    "Reduced 30-day XGBoost training runtime by ~40% via GPU acceleration (Databricks CUDA) with no "
    "performance degradation.",
    "Consolidated three legacy feature store repos into one unified framework, cutting maintenance overhead by 66%.",
]:
    story.append(bullet(b))

story.append(Spacer(1, 3))

# AJ Tutoring
story.extend(job_header(
    "Academic Tutor", f"Jan 2024 {EN} Dec 2024",
    "AJ Tutoring, Los Gatos, CA",
))
for b in [
    "Tutored 30+ students in single and multi-variable calculus, adapting lesson plans to diverse learning "
    "styles, proficiency levels, and individual academic goals.",
    "Built personalized pacing frameworks and progress-tracking systems that measurably improved exam scores "
    "and strengthened independent problem-solving skills.",
]:
    story.append(bullet(b))

story.append(Spacer(1, 3))

# Chapman MLAT
story.extend(job_header(
    "ML &amp; Assistive Technology Lab Research Assistant", f"May 2023 {EN} Dec 2023",
    "Chapman University, Orange, CA",
))
for b in [
    "Engineered and deployed Python-based VR research environments supporting 200+ active users across "
    "neurodiversity studies.",
    "Optimized sensor-to-database pipelines to reduce data logging latency and improve signal quality for "
    "downstream ML training.",
    "Led cross-platform mobile app development with real-time feedback loops, improving accessibility across "
    "research cohorts.",
]:
    story.append(bullet(b))

# === INTERNSHIPS (separated from full-time) ===
story.extend(section_header("INTERNSHIPS"))

# Pillar
story.extend(job_header(
    "ML Engineer Intern \u2014 Pillar", f"May 2022 {EN} Dec 2022",
    "Mountain View, CA",
))
for b in [
    "Built and deployed a regression model (Scikit-Learn, Node.js) for renovation cost estimation, improving "
    "accuracy by 18% with sub-200ms GraphQL API latency.",
    "Prototyped a computer vision pipeline (PyTorch) to auto-categorize job-site photos, reducing manual "
    "tagging time by 40%.",
    "Analyzed user behavior (SQL, Python) to identify UX friction points, driving a 15% increase in "
    "engagement metrics.",
]:
    story.append(bullet(b))

story.append(Spacer(1, 3))

# Seedstages
story.extend(job_header(
    "ML Engineer Intern \u2014 Seedstages", f"Mar 2021 {EN} Dec 2021",
    "Claremont, CA",
))
for b in [
    "Designed and deployed the company's first automated ML pipeline with repeatable workflows for training, "
    "validation, and deployment.",
    "Built a real-time feature store for contractor-client matching, improving API response times by 15%.",
    "Developed an NLP text-classification service achieving 15% improvement in automated tagging accuracy "
    "(Scikit-learn, NLTK).",
    "Shipped predictive models for customer acquisition and retention forecasting with interactive dashboards.",
]:
    story.append(bullet(b))

# === PROJECTS (links on dedicated lines) ===
story.extend(section_header("PROJECTS"))

projects = [
    (
        "<b>RAG Ops \u2014 Football Intelligence Platform</b>  "
        "<i>(Python, LangChain, FAISS, FastAPI, Langfuse, RAGAS, Docker)</i>",
        "github.com/pranavss722/rag-ops  |  rag-ops-production.up.railway.app",
        "Built a production-grade RAG pipeline with Langfuse observability, RAGAS evaluation "
        f"(faithfulness 0.874), cost-per-query tracking ($0.0012/query), and a live FIFA-aesthetic "
        f"chat UI \u2014 34 TDD tests, deployed on Railway.",
    ),
    (
        "<b>Stream Vault \u2014 Streaming Feature Store</b>  "
        "<i>(Python, Feast, Apache Kafka, Redis, Delta Lake, Docker)</i>",
        None,
        "Production-grade streaming feature store with dual-write consistency (Delta Lake offline, "
        "Redis online), automated parity validation, CI-integrated drift detection, and sub-100ms "
        "online retrieval.",
    ),
    (
        "<b>Sentinel \u2014 ML Serving Pipeline</b>  "
        "<i>(Python, MLflow, FastAPI, Docker, Kubernetes, Prometheus, Grafana, Evidently AI)</i>",
        None,
        f"Containerized ML serving pipeline with MLflow model registry, canary rollout "
        f"(1%\u2192100%), SLO-based auto-rollback, and real-time drift monitoring via Evidently AI "
        "and Prometheus/Grafana.",
    ),
]

for title_line, url_line, desc in projects:
    story.append(Paragraph(title_line, style_proj_title))
    if url_line:
        story.append(Paragraph(url_line, style_url))
    story.append(bullet(desc))
    story.append(Spacer(1, 2))

# === LANGUAGES (moved to bottom) ===
story.extend(section_header("LANGUAGES"))
story.append(Paragraph("English, Tamil, Spanish", style_body))

# Build
doc.build(story)
print(f"Resume written to {OUTPUT}")
