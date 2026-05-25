"""
Anomaly detection on daily sales revenue using Z-score and Isolation Forest.
Reads from Databricks gold layer; writes flagged rows back to Delta.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


@dataclass
class AnomalyConfig:
    z_score_threshold: float = 2.5
    isolation_contamination: float = 0.05
    rolling_window_days: int = 30
    lookback_days: int = 90
    alert_recipients: list[str] = field(default_factory=list)


class SalesAnomalyDetector:
    def __init__(self, config: AnomalyConfig | None = None):
        self.config = config or AnomalyConfig()
        self._scaler = StandardScaler()
        self._iso_forest = IsolationForest(
            contamination=self.config.isolation_contamination,
            random_state=42,
            n_estimators=200,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return df with anomaly columns appended."""
        df = df.copy().sort_values("sale_date")
        df = self._add_rolling_stats(df)
        df = self._z_score_flag(df)
        df = self._isolation_forest_flag(df)
        df["is_anomaly"] = df["z_anomaly"] | df["iso_anomaly"]
        df["detected_at"] = datetime.utcnow()
        return df

    def summary(self, df: pd.DataFrame) -> dict:
        flagged = df[df["is_anomaly"]]
        return {
            "total_rows":      len(df),
            "anomaly_count":   len(flagged),
            "anomaly_rate_pct": round(len(flagged) / max(len(df), 1) * 100, 2),
            "revenue_at_risk": round(flagged["daily_revenue"].sum(), 2),
            "regions_affected": flagged["region"].nunique(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_rolling_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        w = self.config.rolling_window_days
        df["rolling_mean"] = (
            df.groupby("region")["daily_revenue"]
            .transform(lambda s: s.rolling(w, min_periods=7).mean())
        )
        df["rolling_std"] = (
            df.groupby("region")["daily_revenue"]
            .transform(lambda s: s.rolling(w, min_periods=7).std())
        )
        return df

    def _z_score_flag(self, df: pd.DataFrame) -> pd.DataFrame:
        df["z_score"] = (
            (df["daily_revenue"] - df["rolling_mean"])
            / df["rolling_std"].replace(0, np.nan)
        ).round(3)
        df["z_anomaly"] = df["z_score"].abs() > self.config.z_score_threshold
        return df

    def _isolation_forest_flag(self, df: pd.DataFrame) -> pd.DataFrame:
        features = ["daily_revenue", "rolling_mean", "rolling_std"]
        valid = df.dropna(subset=features)
        if len(valid) < 20:
            df["iso_anomaly"] = False
            return df

        X = self._scaler.fit_transform(valid[features])
        preds = self._iso_forest.fit_predict(X)
        df.loc[valid.index, "iso_anomaly"] = preds == -1
        df["iso_anomaly"] = df["iso_anomaly"].fillna(False)
        return df


# ------------------------------------------------------------------
# Databricks entry-point (called by Databricks Job)
# ------------------------------------------------------------------

def run_on_databricks():
    from pyspark.sql import SparkSession  # noqa: PLC0415

    spark = SparkSession.builder.getOrCreate()

    cutoff = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
    pdf = (
        spark.table("gold.daily_revenue_by_region")
        .filter(f"sale_date >= '{cutoff}'")
        .toPandas()
    )

    detector = SalesAnomalyDetector()
    result = detector.detect(pdf)
    summary = detector.summary(result)

    print("Anomaly Detection Summary:", summary)

    sdf = spark.createDataFrame(result[result["is_anomaly"]])
    (
        sdf.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable("gold.revenue_anomalies_ml")
    )
    return summary


if __name__ == "__main__":
    run_on_databricks()
