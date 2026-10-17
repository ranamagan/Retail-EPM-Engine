import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
out = Path("data/raw")
out.mkdir(parents=True, exist_ok=True)

cities = ["Mohali", "Chandigarh", "Ludhiana", "Amritsar", "Jalandhar",
          "Patiala", "Delhi", "Gurgaon", "Jaipur", "Lucknow"]
stores = pd.DataFrame({
    "store_id": [f"S{i:02d}" for i in range(1, 11)],
    "city": cities,
    "size_factor": rng.uniform(0.7, 1.5, 10).round(2),
})

products = pd.DataFrame({
    "sku_id": [f"P{i:03d}" for i in range(1, 31)],
    "category": ["Pharma"] * 12 + ["Grocery"] * 18,
    "price": rng.uniform(20, 500, 30).round(2),
    "base_demand": rng.uniform(20, 120, 30).round(0),
})
products["cost"] = (products["price"] * rng.uniform(0.6, 0.85, 30)).round(2)

weeks = pd.DataFrame({"week_start": pd.date_range("2025-01-06", periods=104, freq="W-MON")})

df = stores.merge(products, how="cross").merge(weeks, how="cross")
week_no = df["week_start"].dt.isocalendar().week.astype(int)
season = 1 + 0.2 * np.sin(2 * np.pi * week_no / 52)
df["units_sold"] = rng.poisson(df["base_demand"] * df["size_factor"] * season)
df["revenue"] = (df["units_sold"] * df["price"]).round(2)
df["cogs"] = (df["units_sold"] * df["cost"]).round(2)

stores.to_csv(out / "stores.csv", index=False)
products.to_csv(out / "products.csv", index=False)
df[["week_start", "store_id", "sku_id", "units_sold", "revenue", "cogs"]].to_csv(
    out / "sales_weekly.csv", index=False)

print("Done:", len(df), "sales rows created in data/raw")
