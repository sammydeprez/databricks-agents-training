# Databricks notebook source
# MAGIC %md
# MAGIC # Lab data
# MAGIC The only notebook you need to import for the data side of this training. You'll come back to
# MAGIC this same notebook twice:
# MAGIC
# MAGIC - **Day 1:** leave the setting below on **Set up my data** and click **Run all**.
# MAGIC - **End of Day 2:** change it to **Clean up my data** and click **Run all** again.
# MAGIC
# MAGIC Leave **Catalog** empty to use your workspace's default catalog. Only fill it in if your trainer
# MAGIC gives you a catalog name — and use the same value again when you clean up.
# MAGIC
# MAGIC Both fetch the latest lab material straight from GitHub and run it here. Nothing to clone,
# MAGIC download or upload by hand.

# COMMAND ----------

dbutils.widgets.dropdown("action", "Set up my data", ["Set up my data", "Clean up my data"], "What do you want to do?")
dbutils.widgets.text("catalog", "", "Catalog (leave empty unless your trainer gives you one)")
ACTION = dbutils.widgets.get("action")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Fetch the latest lab material

# COMMAND ----------

# MAGIC %sh
# MAGIC rm -rf /tmp/databricks-agents-training
# MAGIC git clone --quiet --depth 1 https://github.com/sammydeprez/databricks-agents-training /tmp/databricks-agents-training
# MAGIC echo "fetched"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Run it

# COMMAND ----------

REPO = "/tmp/databricks-agents-training"
SCRIPT = f"{REPO}/notebooks/00_setup_my_data.py" if ACTION == "Set up my data" else f"{REPO}/notebooks/99_cleanup_my_data.py"

print(f"running: {ACTION}")
with open(SCRIPT) as f:
    exec(f.read())
