"""
banking_core.py - Noyau bancaire: date d'arrete, segmentation, RWA et gouvernance.

Ces fonctions restent simples et explicables pour un PFA, mais elles imposent
les reflexes d'une plateforme bancaire: portefeuille a une date donnee,
segmentation reglementaire, capital stack et audit trail.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"
RESULTS_DIR = OUTPUT_DIR / "results"
GOVERNANCE_DIR = OUTPUT_DIR / "governance"
AUDIT_LOG_PATH = GOVERNANCE_DIR / "audit_log.jsonl"
MODEL_REGISTRY_PATH = GOVERNANCE_DIR / "model_registry.csv"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)


BASEL_MINIMA = {
    "cet1_min": 0.045,
    "capital_conservation_buffer": 0.025,
    "tier1_min": 0.06,
    "total_capital_min": 0.08,
    "leverage_min": 0.03,
}

CAPITAL_STACK_DEFAULTS = {
    "cet1_ratio": 0.12,
    "at1_ratio": 0.015,
    "tier2_ratio": 0.02,
}

RISK_WEIGHT_BY_SEGMENT = {
    "retail_consumer": 0.75,
    "mortgage": 0.35,
    "sme": 0.85,
    "corporate": 1.00,
    "high_risk": 1.50,
    "defaulted": 1.50,
}


def apply_reporting_date(df: pd.DataFrame, reporting_date=None) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Filtre le portefeuille comme une vue a date d'arrete."""
    if reporting_date is None:
        if "issue_d" in df.columns and df["issue_d"].notna().any():
            reporting_date = pd.to_datetime(df["issue_d"]).max()
        else:
            reporting_date = pd.Timestamp.today().normalize()
    reporting_date = pd.to_datetime(reporting_date)
    result = df.copy()
    if "issue_d" in result.columns:
        issue_d = pd.to_datetime(result["issue_d"], errors="coerce")
        result = result[issue_d <= reporting_date].copy()
    result["reporting_date"] = reporting_date
    return result, reporting_date


def assign_regulatory_segment(df: pd.DataFrame) -> pd.Series:
    """Segmentation reglementaire explicable a partir des champs disponibles."""
    segment = pd.Series("retail_consumer", index=df.index, dtype="object")

    if "purpose" in df.columns:
        purpose = df["purpose"].astype(str).str.lower()
        segment.loc[purpose.str.contains("home|house|mortgage", regex=True, na=False)] = "mortgage"
        segment.loc[purpose.str.contains("small_business|business", regex=True, na=False)] = "sme"

    if "loan_amnt" in df.columns:
        loan_amnt = pd.to_numeric(df["loan_amnt"], errors="coerce").fillna(0)
        segment.loc[loan_amnt >= 100_000] = "corporate"

    if "grade" in df.columns:
        grade = df["grade"].astype(str).str.upper()
        segment.loc[grade.isin(["F", "G"])] = "high_risk"

    if "stage" in df.columns:
        segment.loc[pd.to_numeric(df["stage"], errors="coerce").fillna(1).astype(int) == 3] = "defaulted"

    return segment


def enrich_banking_view(df: pd.DataFrame, reporting_date=None) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Ajoute date d'arrete, segment reglementaire et risk weight."""
    result, reporting_date = apply_reporting_date(df, reporting_date)
    result["regulatory_segment"] = assign_regulatory_segment(result)
    result["risk_weight"] = result["regulatory_segment"].map(RISK_WEIGHT_BY_SEGMENT).fillna(1.0)
    result["RWA"] = pd.to_numeric(result["EAD"], errors="coerce").fillna(0) * result["risk_weight"]
    return result, reporting_date


def compute_basel_metrics(
    df: pd.DataFrame,
    cet1_ratio: float = CAPITAL_STACK_DEFAULTS["cet1_ratio"],
    at1_ratio: float = CAPITAL_STACK_DEFAULTS["at1_ratio"],
    tier2_ratio: float = CAPITAL_STACK_DEFAULTS["tier2_ratio"],
    exposure_multiplier: float = 1.0,
) -> dict:
    """Calcule RWA, ratios capital et shortfalls reglementaires."""
    view = df.copy()
    if "regulatory_segment" not in view.columns or "RWA" not in view.columns:
        view, _ = enrich_banking_view(view)

    ead_total = float(pd.to_numeric(view["EAD"], errors="coerce").fillna(0).sum())
    rwa_total = float(pd.to_numeric(view["RWA"], errors="coerce").fillna(0).sum())
    leverage_exposure = max(ead_total * exposure_multiplier, 1e-9)

    cet1_capital = cet1_ratio * rwa_total
    at1_capital = at1_ratio * rwa_total
    tier2_capital = tier2_ratio * rwa_total
    tier1_capital = cet1_capital + at1_capital
    total_capital = tier1_capital + tier2_capital

    cet1_req = (BASEL_MINIMA["cet1_min"] + BASEL_MINIMA["capital_conservation_buffer"]) * rwa_total
    tier1_req = BASEL_MINIMA["tier1_min"] * rwa_total
    total_req = BASEL_MINIMA["total_capital_min"] * rwa_total
    leverage_req = BASEL_MINIMA["leverage_min"] * leverage_exposure

    return {
        "EAD_M$": round(ead_total / 1e6, 2),
        "RWA_M$": round(rwa_total / 1e6, 2),
        "RWA_density_%": round((rwa_total / max(ead_total, 1e-9)) * 100, 2),
        "CET1_capital_M$": round(cet1_capital / 1e6, 2),
        "AT1_capital_M$": round(at1_capital / 1e6, 2),
        "Tier2_capital_M$": round(tier2_capital / 1e6, 2),
        "CET1_ratio_%": round((cet1_capital / max(rwa_total, 1e-9)) * 100, 2),
        "Tier1_ratio_%": round((tier1_capital / max(rwa_total, 1e-9)) * 100, 2),
        "Total_capital_ratio_%": round((total_capital / max(rwa_total, 1e-9)) * 100, 2),
        "Leverage_ratio_%": round((cet1_capital / leverage_exposure) * 100, 2),
        "Shortfall_CET1_7_M$": round(max(cet1_req - cet1_capital, 0) / 1e6, 2),
        "Shortfall_Tier1_M$": round(max(tier1_req - tier1_capital, 0) / 1e6, 2),
        "Shortfall_TotalCapital_M$": round(max(total_req - total_capital, 0) / 1e6, 2),
        "Shortfall_Leverage_M$": round(max(leverage_req - cet1_capital, 0) / 1e6, 2),
    }


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Synthese par segment reglementaire."""
    view = df.copy()
    if "regulatory_segment" not in view.columns or "RWA" not in view.columns:
        view, _ = enrich_banking_view(view)
    summary = view.groupby("regulatory_segment").agg(
        loans=("EAD", "count"),
        EAD_M=("EAD", lambda x: float(x.sum()) / 1e6),
        RWA_M=("RWA", lambda x: float(x.sum()) / 1e6),
        PD_mean=("PD_pred", "mean") if "PD_pred" in view.columns else ("EAD", lambda x: np.nan),
        LGD_mean=("LGD", "mean") if "LGD" in view.columns else ("EAD", lambda x: np.nan),
        ECL_M=("ECL_ifrs9", lambda x: float(x.sum()) / 1e6) if "ECL_ifrs9" in view.columns else ("EAD", lambda x: np.nan),
    ).reset_index()
    summary["RWA_density_%"] = summary["RWA_M"] / summary["EAD_M"].replace(0, np.nan) * 100
    return summary.round(4)


def capital_actions_from_shortfall(cet1_pct: float, shortfall_m: float) -> str:
    """Action de management centree capital."""
    if cet1_pct >= 7.0 and shortfall_m <= 0:
        return "Maintenir coussins, suivi normal et revue trimestrielle des limites."
    if cet1_pct >= 4.5:
        return "Limiter dividendes, reduire croissance RWA, renforcer recouvrement et pricing risque."
    return "Recapitaliser, vendre actifs risques, suspendre origination risquee et activer plan de remediation."


def log_audit_event(event_type: str, user: str, parameters: dict, outputs: dict | None = None) -> str:
    """Ecrit un audit trail JSONL reproductible."""
    run_id = str(uuid.uuid4())
    event = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user": user or "streamlit_user",
        "parameters": parameters,
        "outputs": outputs or {},
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True, default=str) + "\n")
    return run_id


def load_audit_log(limit: int = 100) -> pd.DataFrame:
    if not AUDIT_LOG_PATH.exists():
        return pd.DataFrame()
    rows = []
    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows[-limit:])


def ensure_model_registry() -> pd.DataFrame:
    """Cree un registre modele minimal si absent."""
    if MODEL_REGISTRY_PATH.exists():
        return pd.read_csv(MODEL_REGISTRY_PATH)
    registry = pd.DataFrame([
        {
            "model_id": "PD_CHAMPION",
            "version": "v1.0",
            "owner": "Risk Modeling",
            "validation_status": "Validated for PFA prototype",
            "approval_status": "Model Committee simulated",
            "last_review_date": datetime.now().date().isoformat(),
        },
        {
            "model_id": "SATELLITE_MACRO_PD",
            "version": "v1.0",
            "owner": "Stress Testing",
            "validation_status": "Backtesting required before production",
            "approval_status": "Conditional approval",
            "last_review_date": datetime.now().date().isoformat(),
        },
        {
            "model_id": "BASEL_RWA_STANDARDIZED",
            "version": "v1.0",
            "owner": "Regulatory Capital",
            "validation_status": "Rule-based benchmark",
            "approval_status": "Approved for simulation",
            "last_review_date": datetime.now().date().isoformat(),
        },
    ])
    registry.to_csv(MODEL_REGISTRY_PATH, index=False)
    return registry
