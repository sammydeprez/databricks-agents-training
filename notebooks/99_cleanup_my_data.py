# Databricks notebook source
# MAGIC %md
# MAGIC # Clean up your data
# MAGIC Run this at the end of the training to remove the schema `00_setup_my_data` created for you.
# MAGIC
# MAGIC **All you need to do:** click **Run all**. This only touches your own schema — nobody else's data
# MAGIC is affected.
# MAGIC
# MAGIC This does **not** delete the agents you built (Genie Agent, Knowledge Assistant, Supervisor
# MAGIC Agent) — delete those yourself from the **Agents** page, since each is its own object with a
# MAGIC **Delete** option in its `⋮` menu. Do that first if you want a full cleanup, since a couple of
# MAGIC them point at tables this notebook is about to remove.

# COMMAND ----------

# Same catalog as setup: whatever is in the lab_data notebook's "catalog" box, otherwise the workspace default.
try:
    CATALOG = dbutils.widgets.get("catalog").strip()
except Exception:
    CATALOG = ""
CATALOG = CATALOG or spark.sql("SELECT current_catalog() AS c").collect()[0]["c"]

user_email = spark.sql("SELECT current_user() AS u").collect()[0]["u"]
local_part = user_email.split("@")[0].lower()

import re
SCHEMA_NAME = re.sub(r"[^a-z0-9_]", "_", local_part)
SCHEMA = f"`{CATALOG}`.`{SCHEMA_NAME}`"

print(f"About to drop: {CATALOG}.{SCHEMA_NAME}")

# COMMAND ----------

spark.sql(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")

print(f"Dropped {CATALOG}.{SCHEMA_NAME} and everything in it (tables, the docs volume, the open_work_orders function).")
print("Last step: go to the Agents page and delete your Genie Agent, Knowledge Assistant and Supervisor Agent, if you haven't already.")
