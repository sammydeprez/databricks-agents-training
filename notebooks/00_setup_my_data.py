# Databricks notebook source
# MAGIC %md
# MAGIC # Set up your data
# MAGIC Run this once at the start of the training, in your own Databricks workspace.
# MAGIC
# MAGIC **All you need to do:** click **Run all** at the top of this notebook. Nothing to type, nothing
# MAGIC to download or upload. It creates a private schema just for you and fills it with the data used
# MAGIC in every lab.
# MAGIC
# MAGIC Safe to re-run any time, for example if something looks broken — it replaces your data
# MAGIC rather than erroring because it already exists.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Find out who you are and name your schema
# MAGIC Your schema is named after your login, so it is automatically yours and won't clash with
# MAGIC anyone else's.

# COMMAND ----------

import re

# Catalog: whatever was typed in the lab_data notebook's "catalog" box, otherwise the workspace default.
try:
    CATALOG = dbutils.widgets.get("catalog").strip()
except Exception:
    CATALOG = ""
CATALOG = CATALOG or spark.sql("SELECT current_catalog() AS c").collect()[0]["c"]
if CATALOG == "hive_metastore":
    raise Exception("Your workspace's default catalog is hive_metastore, which can't hold the lab data. "
                    "Ask your trainer for a catalog name and type it into the 'catalog' box at the top.")

user_email = spark.sql("SELECT current_user() AS u").collect()[0]["u"]
local_part = user_email.split("@")[0].lower()
SCHEMA_NAME = re.sub(r"[^a-z0-9_]", "_", local_part)
NAME_SAFE = SCHEMA_NAME.replace("_", "-")  # for agent names later, which only allow letters, numbers and dashes

SCHEMA = f"`{CATALOG}`.`{SCHEMA_NAME}`"  # quoted for SQL, in case the catalog name has a dash in it

print(f"Your catalog is: {CATALOG}")
print(f"Your schema is: {SCHEMA_NAME}")
print(f"Use '{CATALOG}' wherever the guide says 'your_catalog', and '{SCHEMA_NAME}' wherever it says 'your_schema'.")
print(f"When a step asks you to name an agent, use '{NAME_SAFE}' instead of 'your-name', e.g. '{NAME_SAFE}-regulations-assistant'.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Create your schema
# MAGIC This needs permission to create a schema in your catalog — your trainer sets this up once for
# MAGIC everyone before the training starts.

# COMMAND ----------

try:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {SCHEMA}.docs")
    print(f"Ready: {CATALOG}.{SCHEMA_NAME}")
except Exception as e:
    print(f"Could not create your schema in the catalog '{CATALOG}'. Ask your trainer which catalog to use, "
          "type it into the 'catalog' box at the top of the lab_data notebook, and run it again.")
    raise e

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Generate your data
# MAGIC Nothing below is real — names, work orders and tickets are all made up.

# COMMAND ----------

import random
from datetime import date, timedelta

random.seed(42)
TODAY = date(2026, 10, 1)

UNITS = ["Unit 1", "Unit 2", "Unit 3", "Unit 4"]
SYSTEMS = ["Feedwater", "Cooling water", "Electrical", "HVAC", "Instrumentation", "Fire protection"]
ASSET_TYPES = ["Pump", "Valve", "Transformer", "Sensor", "Fan", "Breaker"]
FIRST = ["Ahmed", "Fatima", "Mohammed", "Maryam", "Khalid", "Noura", "Saeed", "Hessa", "Omar", "Shamma", "Rashid", "Alia"]
LAST = ["Al Mazrouei", "Al Nuaimi", "Al Ketbi", "Al Shamsi", "Al Hammadi", "Al Suwaidi", "Al Dhaheri", "Al Mansoori"]

def masked_phone():
    prefix = random.choice(["50", "52", "54", "55", "56", "58"])
    last4 = f"{random.randint(0, 9999):04d}"
    return f"+971-{prefix[0]}*-***-{last4}"

# assets
assets = []
for i in range(1, 121):
    assets.append({"asset_id": f"A-{i:04d}", "asset_type": random.choice(ASSET_TYPES),
                   "unit": random.choice(UNITS), "system": random.choice(SYSTEMS),
                   "install_year": random.randint(2015, 2024), "criticality": random.choice(["High", "Medium", "Low"])})

# technicians
technicians = []
for i in range(1, 41):
    technicians.append({"technician_id": f"T-{i:03d}", "name": f"{random.choice(FIRST)} {random.choice(LAST)}",
                        "team": random.choice(["Mechanical", "Electrical", "I&C"]), "shift": random.choice(["Day", "Night"]),
                        "phone_masked": masked_phone()})

# work orders
work_orders = []
for i in range(1, 2001):
    a = random.choice(assets); t = random.choice(technicians)
    created = TODAY - timedelta(days=random.randint(0, 365))
    wo_type = random.choices(["PM", "CM"], [0.6, 0.4])[0]
    due = created + timedelta(days=random.randint(3, 45))
    status = random.choices(["Open", "Closed", "Cancelled"], [0.3, 0.65, 0.05])[0]
    closed = created + timedelta(days=random.randint(1, 40)) if status == "Closed" else None
    desc = {"PM": f"Scheduled inspection and lubrication of {a['asset_type'].lower()} {a['asset_id']}",
            "CM": random.choice([f"Abnormal vibration reported on {a['asset_id']}", f"Leak observed at {a['asset_id']} flange",
                                 f"{a['asset_type']} {a['asset_id']} tripped on high temperature", f"Calibration drift on {a['asset_id']}"])}[wo_type]
    work_orders.append({"wo_id": f"WO-{i:05d}", "wo_type": wo_type, "status": status, "priority": random.choice(["High", "Medium", "Low"]),
                        "unit": a["unit"], "asset_id": a["asset_id"], "technician_id": t["technician_id"],
                        "created_date": created, "due_date": due, "closed_date": closed, "description": desc})

# IT tickets, ~20% Arabic
EN = ["Cannot log in to the maintenance system, whole shift blocked", "Printer on floor {f} out of toner",
      "Laptop {tag} fan is very loud and hot", "Need access to the document control share for new joiner",
      "Badge reader at gate {g} intermittent since Sunday", "Wi-Fi drops in meeting room {r} every few minutes",
      "Outlook shows disconnected on laptop {tag}", "Monitor {tag} flickers when docked", "VPN token expired, cannot work from site office",
      "Reporting dashboard shows yesterday's data only"]
AR = ["لا أستطيع تسجيل الدخول إلى نظام الصيانة، الوردية كاملة متوقفة", "الطابعة في الطابق {f} نفد منها الحبر",
      "مروحة الحاسوب المحمول {tag} صوتها مرتفع جداً", "أحتاج صلاحية الوصول إلى مجلد ضبط الوثائق للموظف الجديد",
      "قارئ البطاقات عند البوابة {g} يعمل بشكل متقطع منذ يوم الأحد", "شبكة الواي فاي تنقطع في غرفة الاجتماعات {r}"]
it_tickets = []
for i in range(1, 501):
    ar = random.random() < 0.2
    tpl = random.choice(AR if ar else EN)
    desc = tpl.format(f=random.randint(1, 6), g=random.randint(1, 5), r=random.randint(101, 320), tag=f"LT-{random.randint(1000, 9999)}")
    it_tickets.append({"ticket_id": f"INC-{i:05d}", "created_at": TODAY - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23)),
                       "requester_team": random.choice(["Operations", "Maintenance", "Engineering", "HR", "Finance", "Security"]),
                       "language": "ar" if ar else "en", "description": desc})

# incident reports (synthetic narratives)
incident_reports = []
for i in range(1, 61):
    a = random.choice(assets); d = TODAY - timedelta(days=random.randint(0, 300))
    incident_reports.append({"report_id": f"IR-{i:04d}", "report_date": d,
                             "narrative": f"On {d} at {random.randint(6, 22):02d}:{random.choice(['05','20','40'])} a technician noticed "
                                          f"{random.choice(['a minor oil leak', 'an unexpected alarm', 'a tripped breaker', 'a loose guard'])} on {a['asset_type'].lower()} "
                                          f"{a['asset_id']} in {a['unit']} ({a['system']} system). The area was isolated, the supervisor was informed and "
                                          f"work order WO-{random.randint(1, 2000):05d} was raised. No injuries. Root cause under review."})

# meeting transcripts, for Lab 3's ai_extract example and the "meeting assistant" capstone case
TEAMS = ["Mechanical", "Electrical", "I&C", "Operations"]
TASKS = ["feedwater pump inspection", "updated safety procedure review", "IT ticket backlog", "monthly KPI report",
         "spare parts audit", "contractor onboarding paperwork", "fire system test", "electrical panel inspection",
         "shift handover log review", "calibration record update"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
ACTION_LINES = [
    "{name}: the {task} is still pending, I will finish it by {day}.",
    "{name}: I need someone to review the {task} before {day} - {name2} agreed to do it.",
    "{name}: no blockers, closing out the {task} by end of week.",
    "{name}: {task} is blocked on parts, expect resolution by {day}.",
    "{name}: {task} done, no further action needed.",
]
meeting_transcripts = []
for i in range(1, 11):
    team = random.choice(TEAMS)
    d = TODAY - timedelta(days=random.randint(0, 60))
    n_lines = random.randint(2, 4)
    people = random.sample([f"{f} {l}" for f in FIRST for l in LAST], n_lines + 1)
    lines = []
    for j in range(n_lines):
        tpl = random.choice(ACTION_LINES)
        lines.append(tpl.format(name=people[j].split()[0], name2=people[j + 1].split()[0],
                                 task=random.choice(TASKS), day=random.choice(WEEKDAYS)))
    transcript = f"{team} standup, {d.strftime('%A')}. " + " ".join(lines)
    meeting_transcripts.append({"transcript_id": f"MT-{i:02d}", "meeting_date": d, "team": team, "transcript": transcript})

# monthly KPIs, for the KPI / annual operating report capstone case
monthly_kpis = []
for m in range(12):
    month = date(2025, 11, 1) + timedelta(days=31 * m)
    month = month.replace(day=1)
    for u in UNITS:
        monthly_kpis.append({"month": month, "unit": u,
                             "availability_pct": round(random.uniform(92, 99), 1),
                             "planned_maintenance_completion_pct": round(random.uniform(80, 100), 1),
                             "corrective_work_orders": random.randint(5, 40),
                             "safety_incidents": random.choices([0, 1, 2, 3], [0.6, 0.25, 0.1, 0.05])[0],
                             "budget_variance_pct": round(random.uniform(-10, 10), 1)})

print(f"generated {len(assets)} assets, {len(technicians)} technicians, {len(work_orders)} work orders, "
      f"{len(it_tickets)} IT tickets, {len(incident_reports)} incident reports, "
      f"{len(meeting_transcripts)} meeting transcripts, {len(monthly_kpis)} monthly KPI rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Load your tables and shared function

# COMMAND ----------

spark.createDataFrame(assets).write.mode("overwrite").saveAsTable(f"{SCHEMA}.assets")
spark.createDataFrame(technicians).write.mode("overwrite").saveAsTable(f"{SCHEMA}.technicians")
spark.createDataFrame(work_orders).write.mode("overwrite").saveAsTable(f"{SCHEMA}.work_orders")
spark.createDataFrame(it_tickets).write.mode("overwrite").saveAsTable(f"{SCHEMA}.it_tickets")
spark.createDataFrame(incident_reports).write.mode("overwrite").saveAsTable(f"{SCHEMA}.incident_reports")
spark.createDataFrame(meeting_transcripts).write.mode("overwrite").saveAsTable(f"{SCHEMA}.meeting_transcripts")
spark.createDataFrame(monthly_kpis).write.mode("overwrite").saveAsTable(f"{SCHEMA}.monthly_kpis")

spark.sql(f"""
CREATE OR REPLACE FUNCTION {SCHEMA}.open_work_orders(unit_name STRING)
RETURNS INT
COMMENT 'Returns the number of open work orders for a unit, e.g. Unit 2'
RETURN (SELECT COUNT(*) FROM {SCHEMA}.work_orders WHERE status = 'Open' AND unit = unit_name)
""")

print(f"loaded tables and open_work_orders into {CATALOG}.{SCHEMA_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Copy in the Lab 4 regulation documents, and the capstone memo templates
# MAGIC These ship inside this repository (`data/lab4-documents/` and `data/capstone-memo-templates/`),
# MAGIC so this only needs the GitHub clone from step 1 — no separate connection to FANR or IAEA, which
# MAGIC some workspaces block on serverless compute. See [Materials and data](../materials.md) in the
# MAGIC guide for what each document is and where it came from.

# COMMAND ----------

import shutil
from pathlib import Path

REPO = globals().get("REPO", "/tmp/databricks-agents-training")
DOCS_DIR = Path(f"/Volumes/{CATALOG}/{SCHEMA_NAME}/docs")

SRC_DIR = Path(REPO) / "data" / "lab4-documents"
copied = 0
for src in sorted(SRC_DIR.glob("*.pdf")):
    shutil.copy(src, DOCS_DIR / src.name)
    copied += 1
    print(f"copied {src.name} ({src.stat().st_size // 1024} KB)")
print(f"{copied} regulation document(s) copied into {DOCS_DIR}")

MEMO_SRC_DIR = Path(REPO) / "data" / "capstone-memo-templates"
MEMO_DIR = DOCS_DIR / "memo_templates"
MEMO_DIR.mkdir(parents=True, exist_ok=True)
memo_copied = 0
for src in sorted(MEMO_SRC_DIR.glob("*.md")):
    shutil.copy(src, MEMO_DIR / src.name)
    memo_copied += 1
    print(f"copied {src.name}")
print(f"{memo_copied} memo template(s) copied into {MEMO_DIR}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done

# COMMAND ----------

print(f"Your catalog: {CATALOG}")
print(f"Your schema: {SCHEMA_NAME}")
print(f"Wherever the guide says 'your_catalog.your_schema', use '{CATALOG}.{SCHEMA_NAME}'.")
print(f"Wherever it says 'your-name' (for agent names), use '{NAME_SAFE}'.")
