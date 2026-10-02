"""Generate synthetic training datasets. Nothing here is real.
Usage: python data/generate_synthetic_data.py  -> writes CSVs to data/out/
"""
import csv, random, os
from datetime import date, timedelta

random.seed(42)
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
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

def write(name, rows, fields):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

# assets
assets = []
for i in range(1, 121):
    assets.append({"asset_id": f"A-{i:04d}", "asset_type": random.choice(ASSET_TYPES),
                   "unit": random.choice(UNITS), "system": random.choice(SYSTEMS),
                   "install_year": random.randint(2015, 2024), "criticality": random.choice(["High", "Medium", "Low"])})
write("assets.csv", assets, list(assets[0]))

# technicians
techs = []
for i in range(1, 41):
    techs.append({"technician_id": f"T-{i:03d}", "name": f"{random.choice(FIRST)} {random.choice(LAST)}",
                  "team": random.choice(["Mechanical", "Electrical", "I&C"]), "shift": random.choice(["Day", "Night"]),
                  "phone_masked": masked_phone()})
write("technicians.csv", techs, list(techs[0]))

# work orders
wos = []
for i in range(1, 2001):
    a = random.choice(assets); t = random.choice(techs)
    created = TODAY - timedelta(days=random.randint(0, 365))
    wo_type = random.choices(["PM", "CM"], [0.6, 0.4])[0]
    due = created + timedelta(days=random.randint(3, 45))
    status = random.choices(["Open", "Closed", "Cancelled"], [0.3, 0.65, 0.05])[0]
    closed = created + timedelta(days=random.randint(1, 40)) if status == "Closed" else ""
    desc = {"PM": f"Scheduled inspection and lubrication of {a['asset_type'].lower()} {a['asset_id']}",
            "CM": random.choice([f"Abnormal vibration reported on {a['asset_id']}", f"Leak observed at {a['asset_id']} flange",
                                 f"{a['asset_type']} {a['asset_id']} tripped on high temperature", f"Calibration drift on {a['asset_id']}"])}[wo_type]
    wos.append({"wo_id": f"WO-{i:05d}", "wo_type": wo_type, "status": status, "priority": random.choice(["High", "Medium", "Low"]),
                "unit": a["unit"], "asset_id": a["asset_id"], "technician_id": t["technician_id"],
                "created_date": created, "due_date": due, "closed_date": closed, "description": desc})
write("work_orders.csv", wos, list(wos[0]))

# IT tickets, ~20% Arabic
EN = ["Cannot log in to the maintenance system, whole shift blocked", "Printer on floor {f} out of toner",
      "Laptop {tag} fan is very loud and hot", "Need access to the document control share for new joiner",
      "Badge reader at gate {g} intermittent since Sunday", "Wi-Fi drops in meeting room {r} every few minutes",
      "Outlook shows disconnected on laptop {tag}", "Monitor {tag} flickers when docked", "VPN token expired, cannot work from site office",
      "Reporting dashboard shows yesterday's data only"]
AR = ["لا أستطيع تسجيل الدخول إلى نظام الصيانة، الوردية كاملة متوقفة", "الطابعة في الطابق {f} نفد منها الحبر",
      "مروحة الحاسوب المحمول {tag} صوتها مرتفع جداً", "أحتاج صلاحية الوصول إلى مجلد ضبط الوثائق للموظف الجديد",
      "قارئ البطاقات عند البوابة {g} يعمل بشكل متقطع منذ يوم الأحد", "شبكة الواي فاي تنقطع في غرفة الاجتماعات {r}"]
tickets = []
for i in range(1, 501):
    ar = random.random() < 0.2
    tpl = random.choice(AR if ar else EN)
    desc = tpl.format(f=random.randint(1, 6), g=random.randint(1, 5), r=random.randint(101, 320), tag=f"LT-{random.randint(1000, 9999)}")
    tickets.append({"ticket_id": f"INC-{i:05d}", "created_at": TODAY - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23)),
                    "requester_team": random.choice(["Operations", "Maintenance", "Engineering", "HR", "Finance", "Security"]),
                    "language": "ar" if ar else "en", "description": desc})
write("it_tickets.csv", tickets, list(tickets[0]))

# incident reports (synthetic narratives)
reports = []
for i in range(1, 61):
    a = random.choice(assets); d = TODAY - timedelta(days=random.randint(0, 300))
    reports.append({"report_id": f"IR-{i:04d}", "report_date": d,
                    "narrative": f"On {d} at {random.randint(6, 22):02d}:{random.choice(['05','20','40'])} a technician noticed "
                                 f"{random.choice(['a minor oil leak', 'an unexpected alarm', 'a tripped breaker', 'a loose guard'])} on {a['asset_type'].lower()} "
                                 f"{a['asset_id']} in {a['unit']} ({a['system']} system). The area was isolated, the supervisor was informed and "
                                 f"work order WO-{random.randint(1, 2000):05d} was raised. No injuries. Root cause under review."})
write("incident_reports.csv", reports, list(reports[0]))

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
transcripts = []
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
    transcripts.append({"transcript_id": f"MT-{i:02d}", "meeting_date": d, "team": team, "transcript": transcript})
write("meeting_transcripts.csv", transcripts, list(transcripts[0]))

# monthly KPIs, for the KPI / annual operating report capstone case
kpis = []
for m in range(12):
    month = date(2025, 11, 1) + timedelta(days=31 * m)
    month = month.replace(day=1)
    for u in UNITS:
        kpis.append({"month": month, "unit": u,
                     "availability_pct": round(random.uniform(92, 99), 1),
                     "planned_maintenance_completion_pct": round(random.uniform(80, 100), 1),
                     "corrective_work_orders": random.randint(5, 40),
                     "safety_incidents": random.choices([0, 1, 2, 3], [0.6, 0.25, 0.1, 0.05])[0],
                     "budget_variance_pct": round(random.uniform(-10, 10), 1)})
write("monthly_kpis.csv", kpis, list(kpis[0]))

print("written to", OUT)
