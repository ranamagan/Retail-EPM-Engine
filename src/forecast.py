import pandas as pd
from pathlib import Path

GROWTH = 0.05  # budget = last year's sales + 5%

raw = Path("data/raw")
proc = Path("data/processed")
out = Path("outputs")
proc.mkdir(parents=True, exist_ok=True)
out.mkdir(parents=True, exist_ok=True)

# 1. Load data
sales = pd.read_csv(raw / "sales_weekly.csv", parse_dates=["week_start"])
stores = pd.read_csv(raw / "stores.csv")
products = pd.read_csv(raw / "products.csv")

df = (sales
      .merge(stores[["store_id", "city"]], on="store_id")
      .merge(products[["sku_id", "category"]], on="sku_id"))

# 2. Label each week: first 52 weeks = FY2025, next 52 = FY2026
df["week_idx"] = df["week_start"].rank(method="dense").astype(int) - 1
df["fiscal_year"] = (df["week_idx"] // 52).map({0: "FY2025", 1: "FY2026"})
df["week_of_year"] = df["week_idx"] % 52 + 1

# 3. Roll up from product level to store + category + week
keys = ["store_id", "city", "category", "week_of_year"]
agg = (df.groupby(keys + ["fiscal_year"], as_index=False)
         [["units_sold", "revenue", "cogs"]].sum())

history = agg[agg["fiscal_year"] == "FY2025"].drop(columns="fiscal_year")
actual = agg[agg["fiscal_year"] == "FY2026"].drop(columns="fiscal_year")

# 4. Build the budget: same week last year x (1 + growth)
budget = history.copy()
for col in ["units_sold", "revenue", "cogs"]:
    budget[col] = (budget[col] * (1 + GROWTH)).round(2)
budget = budget.rename(columns={"units_sold": "budget_units",
                                "revenue": "budget_revenue",
                                "cogs": "budget_cogs"})
actual = actual.rename(columns={"units_sold": "actual_units",
                                "revenue": "actual_revenue",
                                "cogs": "actual_cogs"})

weekly = budget.merge(actual, on=keys)
weekly["revenue_var"] = (weekly["actual_revenue"] - weekly["budget_revenue"]).round(2)
weekly["revenue_var_pct"] = (weekly["revenue_var"] / weekly["budget_revenue"] * 100).round(2)

# 5. Summary for the full year by store and category
summary = (weekly.groupby(["store_id", "city", "category"], as_index=False)
           [["budget_revenue", "actual_revenue", "budget_cogs", "actual_cogs"]].sum())
summary["revenue_var"] = summary["actual_revenue"] - summary["budget_revenue"]
summary["revenue_var_pct"] = (summary["revenue_var"] / summary["budget_revenue"] * 100).round(2)
summary["budget_margin_pct"] = ((1 - summary["budget_cogs"] / summary["budget_revenue"]) * 100).round(2)
summary["actual_margin_pct"] = ((1 - summary["actual_cogs"] / summary["actual_revenue"]) * 100).round(2)
summary = summary.round(2).sort_values("revenue_var_pct")

# 6. Save results
weekly.to_csv(proc / "budget_vs_actual_weekly.csv", index=False)
summary.to_csv(proc / "variance_by_store_category.csv", index=False)
with pd.ExcelWriter(out / "budget_vs_actual.xlsx") as writer:
    summary.to_excel(writer, sheet_name="Summary", index=False)
    weekly.to_excel(writer, sheet_name="Weekly", index=False)

# 7. Print a quick check
tot_b = summary["budget_revenue"].sum()
tot_a = summary["actual_revenue"].sum()
print("Weekly rows:", len(weekly))
print("Summary rows:", len(summary))
print(f"Total budget revenue: {tot_b:,.0f}")
print(f"Total actual revenue: {tot_a:,.0f}")
print(f"Total variance: {(tot_a - tot_b) / tot_b * 100:.2f}%")
print()
print("Worst 5 store-category combinations vs budget:")
print(summary[["store_id", "city", "category", "revenue_var_pct"]].head().to_string(index=False))