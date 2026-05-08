# -*- coding: utf-8 -*-
"""
dashboard/app.py — Dashboard Streamlit interactif pour le Moteur de Stress Testing IFRS 9.

Lancement :  streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import joblib
from pandas.errors import EmptyDataError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Moteur Stress Testing IFRS 9",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"
MODELS_DIR = OUTPUT_DIR / "models"
RESULTS_DIR = OUTPUT_DIR / "results"

from src.stress_scenarios import SCENARIOS, SCENARIO_LABELS, SCENARIO_COLORS, BASELINE
from src.resilience import CET1_INITIAL, CET1_REGULATORY_MIN, CET1_TOTAL_MIN, load_capital_assumptions
from src.scenario_projection import compute_dynamic_projection
from src.banking_core import (
    apply_reporting_date,
    capital_actions_from_shortfall,
    compute_basel_metrics,
    enrich_banking_view,
    ensure_model_registry,
    load_audit_log,
    log_audit_event,
    segment_summary,
)

PALETTE = {"Stage 1": "#2ecc71", "Stage 2": "#f39c12", "Stage 3": "#e74c3c"}
ACTIVE_STRESS_SCENARIOS = {
    name: scenario
    for name, scenario in SCENARIOS.items()
    if name != "baseline"
}

REQUIRED_DATA_FILES = [
    OUTPUT_DIR / "loan_clean.parquet",
    OUTPUT_DIR / "ecl_baseline.parquet",
]

OPTIONAL_MODEL_FILES = [
    MODELS_DIR / "satellite_pd_models.pkl",
    MODELS_DIR / "satellite_pd_features.pkl",
    MODELS_DIR / "pd_model_comparison.csv",
]


def read_parquet_required(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except ImportError as exc:
        raise RuntimeError(
            "Lecture parquet impossible: installez pyarrow ou fastparquet "
            "dans l'environnement qui lance Streamlit."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Impossible de lire {path.name}: {exc}") from exc


# ---------------------------------------------------------------------------
# Chargement des données (cache Streamlit)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Chargement du portefeuille...")
def load_data():
    df = read_parquet_required(OUTPUT_DIR / "loan_clean.parquet")
    df_ecl = read_parquet_required(OUTPUT_DIR / "ecl_baseline.parquet")
    df["PD_pred"]   = df_ecl["PD_pred"].values
    df["ECL_ifrs9"] = df_ecl["ECL_ifrs9"].values
    return df


@st.cache_resource(show_spinner="Chargement des modèles...")
def load_models():
    models = {}
    for f in MODELS_DIR.glob("pd_model_*.pkl"):
        name = f.stem.replace("pd_model_", "")
        try:
            models[name] = joblib.load(f)
        except Exception:
            continue

    try:
        results_df = pd.read_csv(MODELS_DIR / "pd_model_comparison.csv", index_col=0)
        champion = results_df["AUC-ROC"].idxmax().lower()
    except Exception:
        champion = list(models.keys())[0] if models else None

    try:
        sat_pd = joblib.load(MODELS_DIR / "satellite_pd_models.pkl")
    except Exception:
        sat_pd = {}
    try:
        sat_feats = joblib.load(MODELS_DIR / "satellite_pd_features.pkl")
    except Exception:
        sat_feats = []

    try:
        sat_res = pd.read_csv(MODELS_DIR / "satellite_pd_comparison.csv", index_col=0)
        eligible = sat_res[sat_res["economic_ok"] == True] if "economic_ok" in sat_res.columns else sat_res.iloc[0:0]
        sat_champ = eligible["RMSE"].idxmin() if len(eligible) else sat_res["RMSE"].idxmin()
    except Exception:
        sat_champ = "OLS"

    return models, champion, sat_pd, sat_feats, sat_champ


@st.cache_data(show_spinner="Chargement des résultats de stress...")
def load_results():
    def safe_csv(path: Path, **kwargs):
        if not path.exists():
            return None
        try:
            return pd.read_csv(path, **kwargs)
        except EmptyDataError:
            return None

    summary = safe_csv(RESULTS_DIR / "stress_ecl_summary.csv")
    curve = safe_csv(RESULTS_DIR / "resilience_curve.csv")
    cet1 = safe_csv(RESULTS_DIR / "cet1_resilience_table.csv", index_col=0)
    rst = safe_csv(RESULTS_DIR / "reverse_stress_test.csv")
    scenario_validation = safe_csv(RESULTS_DIR / "scenario_design_validation.csv")
    stress_validation = safe_csv(RESULTS_DIR / "stress_validation_report.csv")
    forward = safe_csv(RESULTS_DIR / "forward_looking_ecl.csv")
    markov = safe_csv(RESULTS_DIR / "stage_migration_markov_summary.csv")
    sat_wf = safe_csv(MODELS_DIR / "satellite_pd_walk_forward.csv")
    sat_cmp = safe_csv(MODELS_DIR / "satellite_pd_comparison.csv")
    stress_models = safe_csv(RESULTS_DIR / "stress_model_comparison.csv")
    stress_champion = safe_csv(RESULTS_DIR / "stress_model_champion.csv")
    fred_dict = safe_csv(RESULTS_DIR / "fred_variable_dictionary.csv")
    project_eval = safe_csv(RESULTS_DIR / "project_evaluation.csv")
    project_deductions = safe_csv(RESULTS_DIR / "project_evaluation_deductions.csv")
    final_audit = safe_csv(RESULTS_DIR / "final_banking_modeling_audit.csv")
    return summary, curve, cet1, rst, scenario_validation, stress_validation, forward, markov, sat_wf, sat_cmp, stress_models, stress_champion, fred_dict, project_eval, project_deductions, final_audit


def check_outputs_exist():
    return all(p.exists() for p in REQUIRED_DATA_FILES)


def missing_files(paths: list[Path]) -> list[str]:
    return [str(p.relative_to(ROOT)) for p in paths if not p.exists()]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def sidebar():
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/IFRS_Foundation_logo.svg/200px-IFRS_Foundation_logo.svg.png",
                     width=120)
    st.sidebar.title("🏦 Stress Testing IFRS 9")
    st.sidebar.caption("Moteur ECL — Analyse de Résilience Bancaire")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚡ Paramètres du Choc")

    scenario_choice = st.sidebar.selectbox(
        "Scénario prédéfini",
        ["Personnalise", "Adverse", "Severe", "Choc Taux", "Choc Marche 2018", "Crise 2008", "Crise COVID-19"],
    )

    sc_presets = {
        "Adverse":     SCENARIOS.get("adverse", BASELINE),
        "Severe":      SCENARIOS.get("severe", BASELINE),
        "Choc Taux":   SCENARIOS.get("rate_shock", BASELINE),
        "Choc Marche 2018": SCENARIOS.get("market_2018", BASELINE),
        "Crise 2008":  SCENARIOS.get("crisis_2008", BASELINE),
        "Crise COVID-19": SCENARIOS.get("covid_2020", BASELINE),
        "Personnalise": BASELINE,
    }

    preset = sc_presets[scenario_choice]

    unrate_stress = st.sidebar.slider(
        "UNRATE (Chômage %)", 0.0, 15.0,
        float(preset["UNRATE"]), step=0.5
    )
    gdp_stress = st.sidebar.slider(
        "PIB réel Growth (% YoY)", -8.0, 5.0,
        float(preset["GDPC1_growth"]), step=0.5
    )
    fedfunds_stress = st.sidebar.slider(
        "Fed Funds Rate (%)", 0.0, 10.0,
        float(preset["FEDFUNDS"]), step=0.25
    )
    spread_stress = st.sidebar.slider(
        "HY Spread (%)", 1.0, 25.0,
        float(preset.get("HY_SPREAD", 3.5)), step=0.5
    )

    custom_scenario = {
        "UNRATE":       unrate_stress,
        "GDPC1_growth": gdp_stress,
        "FEDFUNDS":     fedfunds_stress,
        "HY_SPREAD":    spread_stress,
        "CPI_change":   preset.get("CPI_change", 2.0),
        "DRCCLACBS":    preset.get("DRCCLACBS", 2.5),
    }

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Paramètres CET1")
    assumptions = load_capital_assumptions()
    cet1_init = st.sidebar.slider("CET1 Initial (%)", 8.0, 18.0,
                                    float(assumptions["cet1_initial_pct"]), step=0.5) / 100
    tax_rate = st.sidebar.slider("Taux d'impôt (%)", 20, 40,
                                 int(assumptions["tax_rate_pct"]), step=5) / 100

    return custom_scenario, cet1_init, tax_rate


# ---------------------------------------------------------------------------
# Onglet 1 — Vue Globale
# ---------------------------------------------------------------------------
def sidebar_dynamic():
    """Sidebar avec scenario bancaire modifiable et horizon pluriannuel."""
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/IFRS_Foundation_logo.svg/200px-IFRS_Foundation_logo.svg.png",
                     width=120)
    st.sidebar.title("Stress Testing IFRS 9")
    st.sidebar.caption("Moteur ECL - Analyse de Resilience Bancaire")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Date d'arrete")
    reporting_date = st.sidebar.date_input(
        "Portefeuille observe au",
        value=pd.Timestamp.today().date(),
        help="La banque calcule le risque sur un portefeuille vivant a une date de reporting.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Scenario et variables macro")
    scenario_options = {
        "Personnalise": "custom",
        "Adverse": "adverse",
        "Severe": "severe",
        "Choc Taux": "rate_shock",
        "Choc Marche 2018": "market_2018",
        "Inflation Ukraine 2022": "ukraine_2022",
        "Crise 2008": "crisis_2008",
        "Crise COVID-19": "covid_2020",
    }
    scenario_choice = st.sidebar.selectbox(
        "Scenario predefini",
        list(scenario_options.keys()),
        help="Les crises historiques/reglementaires sont verrouillees. Utilisez Personnalise pour creer un choc libre.",
    )
    scenario_key = scenario_options[scenario_choice]
    preset = SCENARIOS.get(scenario_key, BASELINE)
    macro_locked = scenario_key != "custom"
    if macro_locked:
        st.sidebar.caption("Scenario verrouille: les variables macro proviennent de la calibration de crise.")
    else:
        st.sidebar.caption("Scenario personnalise: vous pouvez definir les chocs macro.")

    unrate_stress = st.sidebar.slider(
        "UNRATE - chomage (%)", 0.0, 15.0,
        float(preset["UNRATE"]), step=0.5, key=f"{scenario_key}_UNRATE",
        disabled=macro_locked,
    )
    gdp_stress = st.sidebar.slider(
        "PIB reel growth (% YoY)", -10.0, 6.0,
        float(preset["GDPC1_growth"]), step=0.5, key=f"{scenario_key}_GDP",
        disabled=macro_locked,
    )
    fedfunds_stress = st.sidebar.slider(
        "Fed Funds Rate (%)", 0.0, 10.0,
        float(preset["FEDFUNDS"]), step=0.25, key=f"{scenario_key}_FED",
        disabled=macro_locked,
    )
    spread_stress = st.sidebar.slider(
        "HY Spread (%)", 1.0, 25.0,
        float(preset.get("HY_SPREAD", 3.5)), step=0.5, key=f"{scenario_key}_HY",
        disabled=macro_locked,
    )
    cpi_stress = st.sidebar.slider(
        "Inflation CPI (% YoY)", -2.0, 12.0,
        float(preset.get("CPI_change", 2.0)), step=0.25, key=f"{scenario_key}_CPI",
        disabled=macro_locked,
    )
    delinquency_stress = st.sidebar.slider(
        "Delinquance bancaire (%)", 0.0, 10.0,
        float(preset.get("DRCCLACBS", 2.5)), step=0.25, key=f"{scenario_key}_DRC",
        disabled=macro_locked,
    )

    custom_scenario = {
        "UNRATE": unrate_stress,
        "GDPC1_growth": gdp_stress,
        "FEDFUNDS": fedfunds_stress,
        "HY_SPREAD": spread_stress,
        "CPI_change": cpi_stress,
        "DRCCLACBS": delinquency_stress,
    }

    st.sidebar.markdown("---")
    st.sidebar.subheader("Horizon temporel")
    horizon_years = st.sidebar.slider("Horizon de projection", 1, 5, 3, 1)
    profile_label = st.sidebar.selectbox(
        "Profil du choc",
        [
            "Choc immediat puis normalisation",
            "Montee lineaire",
            "Pic retarde",
            "Reprise rapide",
        ],
    )
    profile_map = {
        "Choc immediat puis normalisation": "front_loaded",
        "Montee lineaire": "linear",
        "Pic retarde": "delayed_peak",
        "Reprise rapide": "recovery",
    }

    st.sidebar.markdown("---")
    st.sidebar.subheader("Parametres CET1")
    assumptions = load_capital_assumptions()
    cet1_init = st.sidebar.slider(
        "CET1 Initial (%)", 8.0, 18.0,
        float(assumptions["cet1_initial_pct"]), step=0.5,
    ) / 100
    tax_rate = st.sidebar.slider(
        "Taux d'impot (%)", 20, 40,
        int(assumptions["tax_rate_pct"]), step=5,
    ) / 100

    return (
        custom_scenario,
        scenario_key,
        scenario_choice,
        reporting_date,
        horizon_years,
        profile_map[profile_label],
        cet1_init,
        tax_rate,
    )


def management_action_from_cet1(cet1_pct: float) -> tuple[str, str]:
    """Decision de management simple a partir du CET1 post-stress."""
    if cet1_pct >= CET1_TOTAL_MIN * 100:
        return (
            "Resiliente",
            "Surveillance normale, maintien des coussins et suivi trimestriel.",
        )
    if cet1_pct >= CET1_REGULATORY_MIN * 100:
        return (
            "Sous pression",
            "Plan capital: limiter dividendes, reduire croissance RWA, renforcer recouvrement.",
        )
    if cet1_pct > 0:
        return (
            "Non resiliente",
            "Action urgente: recapitalisation, cession d'actifs risques, gel des nouvelles expositions.",
        )
    return (
        "Rupture",
        "Plan de resolution: restructuration, recapitalisation immediate ou reduction massive du bilan.",
    )


def one_year_stress_matrix(
    df: pd.DataFrame,
    selected_scenario: dict,
    selected_scenario_key: str,
    selected_scenario_label: str,
    pd_champion,
    features: list,
    sat_pd_models: dict,
    sat_pd_features: list,
    sat_champion: str,
    cet1_init: float,
    tax_rate: float,
) -> pd.DataFrame:
    """Table bancaire: perte/provision attendue l'annee prochaine par scenario."""
    scenarios_to_run = {selected_scenario_key: selected_scenario}
    scenarios_to_run.update({
        key: scenario
        for key, scenario in ACTIVE_STRESS_SCENARIOS.items()
        if key != selected_scenario_key
    })
    rows = []
    for name, scenario in scenarios_to_run.items():
        projection, _ = compute_dynamic_projection(
            df=df,
            target_scenario=scenario,
            champion_pd_model=pd_champion,
            features=features,
            satellite_pd_model=sat_pd_models,
            satellite_pd_features=sat_pd_features,
            satellite_pd_champion=sat_champion,
            horizon_years=1,
            profile="front_loaded",
            cet1_initial=cet1_init,
            tax_rate=tax_rate,
            scenario_name=name,
        )
        row = projection.iloc[0].to_dict()
        status, action = management_action_from_cet1(row["CET1_%"])
        rows.append({
            "Scenario": selected_scenario_label if name == selected_scenario_key else SCENARIO_LABELS.get(name, name),
            "Perte_attendue_Y1_M$": row["Annual_provision_M$"],
            "ECL_Y1_M$": row["ECL_M$"],
            "Delta_ECL_vs_T0_M$": row["Delta_ECL_vs_T0_M$"],
            "CET1_post_stress_%": row["CET1_%"],
            "PD_moyenne_%": row["PD_mean_%"],
            "LGD_moyenne_%": row["LGD_mean_%"],
            "Severite": row["severity_score"],
            "Decision": status,
            "Action_management": action,
        })
    return pd.DataFrame(rows)


def tab_overview(df: pd.DataFrame):
    st.header("📊 Vue Globale du Portefeuille")

    ecl_total = df["ECL_ifrs9"].sum() / 1e6
    ead_total = df["EAD"].sum() / 1e9
    pd_mean   = df["PD_pred"].mean()
    lgd_med   = df["LGD"].median()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Nombre de prêts",  f"{len(df):,}")
    c2.metric("ECL Baseline",     f"${ecl_total:,.1f}M")
    c3.metric("EAD Total",        f"${ead_total:,.2f} Mrd")
    c4.metric("PD Moyenne",       f"{pd_mean:.2%}")
    c5.metric("LGD Médiane",      f"{lgd_med:.2%}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # Distribution stages
    stage_dist = df["stage"].value_counts().sort_index()
    stage_names = {1: "Stage 1 (Sain)", 2: "Stage 2 (Dégradé)", 3: "Stage 3 (Défaut)"}
    fig_stage = go.Figure(data=[go.Pie(
        labels=[stage_names.get(s, s) for s in stage_dist.index],
        values=stage_dist.values,
        hole=0.4,
        marker_colors=["#2ecc71", "#f39c12", "#e74c3c"],
    )])
    fig_stage.update_layout(title="Distribution des Stages IFRS 9", height=350)
    col1.plotly_chart(fig_stage, use_container_width=True)

    # ECL par grade
    if "grade" in df.columns:
        ecl_grade = df.groupby("grade")["ECL_ifrs9"].sum().reindex(["A","B","C","D","E","F","G"]) / 1e6
        fig_grade = px.bar(
            x=ecl_grade.index, y=ecl_grade.values,
            color=ecl_grade.values,
            color_continuous_scale="RdYlGn_r",
            labels={"x": "Grade", "y": "ECL (M$)"},
            title="ECL Baseline par Grade (M$)"
        )
        fig_grade.update_layout(height=350, showlegend=False)
        col2.plotly_chart(fig_grade, use_container_width=True)

    # Coverage ratio
    st.markdown("---")
    st.subheader("📈 Taux de Couverture ECL/EAD")
    cov_data = df.groupby("stage").apply(
        lambda x: x["ECL_ifrs9"].sum() / x["EAD"].sum() * 100 if x["EAD"].sum() > 0 else 0
    ).reset_index()
    cov_data.columns = ["Stage", "Coverage_%"]
    cov_data["Stage"] = cov_data["Stage"].map(stage_names)
    fig_cov = px.bar(cov_data, x="Stage", y="Coverage_%",
                      color="Coverage_%", color_continuous_scale="RdYlGn_r",
                      title="Coverage Ratio ECL/EAD par Stage (%)")
    st.plotly_chart(fig_cov, use_container_width=True)


# ---------------------------------------------------------------------------
# Onglet 2 — Scénarios de Stress
# ---------------------------------------------------------------------------
def tab_stress(df: pd.DataFrame, custom_scenario: dict,
               scenario_key: str, scenario_label: str,
               pd_champion, features: list,
               sat_pd_models: dict, sat_pd_features: list, sat_champion: str,
               cet1_init: float, tax_rate: float):
    st.header("⚡ Scénarios de Stress — ECL Stressée")
    if pd_champion is None:
        st.warning(
            "Modele PD pickle indisponible: l'application utilise PD_pred deja calculee "
            "dans ecl_baseline.parquet pour simuler le stress."
        )
    if not sat_pd_models or not sat_pd_features:
        st.warning(
            "Modele satellite macro-PD indisponible: le stress applique le plancher "
            "economique de severite au lieu du lift satellite."
        )

    ecl_baseline = df["ECL_ifrs9"].sum() / 1e6
    ead_total    = df["EAD"].sum() / 1e6

    # Calcul ECL stressée pour le scénario custom
    st.subheader("Stress testing bancaire a 1 an")
    st.caption(
        "Objectif: estimer la provision/perte attendue l'annee prochaine sous plusieurs chocs, "
        "mesurer le CET1 post-stress et deduire l'action de management."
    )
    with st.spinner("Calcul des scenarios a 1 an..."):
        matrix_y1 = one_year_stress_matrix(
            df, custom_scenario, scenario_key, scenario_label,
            pd_champion, features,
            sat_pd_models, sat_pd_features, sat_champion,
            cet1_init, tax_rate,
        )

    worst = matrix_y1.sort_values("CET1_post_stress_%").iloc[0]
    run_id = log_audit_event(
        event_type="one_year_stress_matrix",
        user="streamlit_user",
        parameters={
            "scenario": scenario_label,
            "horizon_years": 1,
            "cet1_init": cet1_init,
            "tax_rate": tax_rate,
        },
        outputs={
            "worst_scenario": worst["Scenario"],
            "worst_loss_y1_m": worst["Perte_attendue_Y1_M$"],
            "worst_cet1_pct": worst["CET1_post_stress_%"],
            "decision": worst["Decision"],
        },
    )
    c0, c1, c2, c3 = st.columns(4)
    c0.metric("Pire scenario", worst["Scenario"])
    c1.metric("Perte attendue Y1", f"${worst['Perte_attendue_Y1_M$']:,.1f}M")
    c2.metric("CET1 post-stress", f"{worst['CET1_post_stress_%']:.2f}%")
    c3.metric("Decision", worst["Decision"])
    st.caption(f"Run audite: {run_id}")

    st.dataframe(
        matrix_y1.sort_values("CET1_post_stress_%"),
        use_container_width=True,
        hide_index=True,
    )

    fig_y1 = px.bar(
        matrix_y1.sort_values("Perte_attendue_Y1_M$", ascending=False),
        x="Scenario",
        y="Perte_attendue_Y1_M$",
        color="Decision",
        title="Provision/perte attendue l'annee prochaine par scenario",
        labels={"Perte_attendue_Y1_M$": "Perte attendue Y1 (M$)"},
    )
    fig_y1.update_layout(height=380)
    st.plotly_chart(fig_y1, use_container_width=True)

    from src.stress_scenarios import apply_stress

    with st.spinner("Calcul ECL stressée..."):
        df_stressed = apply_stress(
            df, custom_scenario, "custom",
            pd_champion, features,
            sat_pd_models, sat_pd_features, sat_champion,
        )
    ecl_stressed = df_stressed["ECL_stressed"].sum() / 1e6
    lift = ecl_stressed / max(ecl_baseline, 1e-6)

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ECL Baseline",  f"${ecl_baseline:,.1f}M")
    c2.metric("ECL Stressée",  f"${ecl_stressed:,.1f}M",
               delta=f"+${ecl_stressed - ecl_baseline:,.1f}M")
    c3.metric("Amplification", f"×{lift:.2f}")
    c4.metric("PD Stressée",   f"{df_stressed['PD_stressed'].mean():.2%}",
               delta=f"+{(df_stressed['PD_stressed'].mean() - df['PD_pred'].mean())*100:.2f}pp")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # Comparaison tous scénarios
    summary_loaded, *_ = load_results()
    if summary_loaded is not None:
        fig_comp = px.bar(
            summary_loaded, x="Scenario", y="ECL_stressed_M$",
            color="ECL_stressed_M$", color_continuous_scale="RdYlGn_r",
            title="ECL par Scénario (M$) — Résultats Pré-calculés",
            text="ECL_stressed_M$",
        )
        fig_comp.update_traces(texttemplate="%{text:.0f}M", textposition="outside")
        fig_comp.update_layout(height=380)
        col1.plotly_chart(fig_comp, use_container_width=True)

    # Decomposition PD/LGD/EAD pour le scénario custom
    pd_b  = df["PD_pred"].mean() * 100
    pd_s  = df_stressed["PD_stressed"].mean() * 100
    lgd_b = df["LGD"].mean() * 100
    lgd_s = df_stressed["LGD_stressed"].mean() * 100
    ead_b = df["EAD"].sum() / 1e9
    ead_s = df_stressed["EAD_stressed"].sum() / 1e9

    components = ["PD (%)", "LGD (%)", "EAD (Mrd$)"]
    base_vals = [pd_b, lgd_b, ead_b]
    stress_vals = [pd_s, lgd_s, ead_s]

    fig_decomp = go.Figure()
    fig_decomp.add_trace(go.Bar(name="Baseline", x=components, y=base_vals,
                                 marker_color="#2ecc71", opacity=0.85))
    fig_decomp.add_trace(go.Bar(name="Scénario Custom", x=components, y=stress_vals,
                                 marker_color="#e74c3c", opacity=0.85))
    fig_decomp.update_layout(barmode="group", title="Décomposition ΔPD/ΔLGD/ΔEAD — Scénario Personnalisé",
                               height=380)
    col2.plotly_chart(fig_decomp, use_container_width=True)

    # ECL par grade sous stress
    st.markdown("---")
    if "grade" in df.columns:
        ecl_g_base = df.groupby("grade")["ECL_ifrs9"].sum().reindex(["A","B","C","D","E","F","G"]) / 1e6
        ecl_g_stress = df_stressed.groupby("grade")["ECL_stressed"].sum().reindex(["A","B","C","D","E","F","G"]) / 1e6

        fig_grade_stress = go.Figure()
        fig_grade_stress.add_trace(go.Bar(
            name="Baseline", x=ecl_g_base.index, y=ecl_g_base.values,
            marker_color="#2ecc71", opacity=0.8
        ))
        fig_grade_stress.add_trace(go.Bar(
            name="Stressé", x=ecl_g_stress.index, y=ecl_g_stress.values,
            marker_color="#e74c3c", opacity=0.8
        ))
        fig_grade_stress.update_layout(
            barmode="group",
            title="ECL Baseline vs Stressée par Grade (M$)",
            xaxis_title="Grade", yaxis_title="ECL (M$)", height=400
        )
        st.plotly_chart(fig_grade_stress, use_container_width=True)


# ---------------------------------------------------------------------------
# Onglet 3 — Migration de Stage
# ---------------------------------------------------------------------------
def tab_projection(df: pd.DataFrame, custom_scenario: dict, scenario_key: str,
                   scenario_label: str, horizon_years: int, shock_profile: str,
                   cet1_init: float, tax_rate: float,
                   pd_champion, features: list,
                   sat_pd_models: dict, sat_pd_features: list, sat_champion: str):
    st.header("Projection Dynamique T1-T5")
    st.caption(
        "Le scenario choisi sert de crise de depart. Les sliders macro le modifient, "
        "puis le moteur projette PD, LGD, EAD, stages, ECL et CET1 annee par annee."
    )

    with st.spinner("Projection dynamique du portefeuille..."):
        projection, stage_projection = compute_dynamic_projection(
            df=df,
            target_scenario=custom_scenario,
            champion_pd_model=pd_champion,
            features=features,
            satellite_pd_model=sat_pd_models,
            satellite_pd_features=sat_pd_features,
            satellite_pd_champion=sat_champion,
            horizon_years=horizon_years,
            profile=shock_profile,
            cet1_initial=cet1_init,
            tax_rate=tax_rate,
            scenario_name=scenario_key,
        )

    first = projection.iloc[0]
    last = projection.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scenario", scenario_label)
    c2.metric("ECL fin horizon", f"${last['ECL_M$']:,.1f}M",
              delta=f"{last['Delta_ECL_vs_T0_M$']:,.1f}M vs T0")
    c3.metric("CET1 fin horizon", f"{last['CET1_%']:.2f}%",
              delta=f"{last['CET1_%'] - first['CET1_%']:.2f}pp")
    c4.metric("PD moyenne fin horizon", f"{last['PD_mean_%']:.2f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)

    fig_ecl = go.Figure()
    fig_ecl.add_trace(go.Scatter(
        x=projection["year"], y=projection["ECL_M$"],
        mode="lines+markers", name="ECL", line=dict(color="#c0392b", width=3),
    ))
    fig_ecl.add_trace(go.Bar(
        x=projection["year"], y=projection["Annual_provision_M$"],
        name="Provision annuelle", marker_color="#f39c12", opacity=0.55,
    ))
    fig_ecl.update_layout(
        title="Trajectoire ECL et provisions par annee",
        xaxis_title="Annee projetee", yaxis_title="Montant (M$)",
        height=390, hovermode="x unified",
    )
    col1.plotly_chart(fig_ecl, use_container_width=True)

    fig_cet1 = go.Figure()
    fig_cet1.add_trace(go.Scatter(
        x=projection["year"], y=projection["CET1_%"],
        mode="lines+markers", name="CET1", line=dict(color="#1f618d", width=3),
    ))
    fig_cet1.add_hline(y=CET1_REGULATORY_MIN * 100, line_dash="dash",
                       line_color="red", annotation_text="Min 4.5%")
    fig_cet1.add_hline(y=CET1_TOTAL_MIN * 100, line_dash="dash",
                       line_color="orange", annotation_text="Coussin 7%")
    fig_cet1.update_layout(
        title="CET1 projete sous trajectoire macro",
        xaxis_title="Annee projetee", yaxis_title="CET1 (%)",
        height=390, hovermode="x unified",
    )
    col2.plotly_chart(fig_cet1, use_container_width=True)

    st.markdown("---")
    col3, col4 = st.columns(2)

    stage_cols = ["Stage 1_%", "Stage 2_%", "Stage 3_%"]
    fig_stage_path = go.Figure()
    colors = ["#2ecc71", "#f39c12", "#e74c3c"]
    for col, color in zip(stage_cols, colors):
        fig_stage_path.add_trace(go.Scatter(
            x=stage_projection["year"],
            y=stage_projection[col],
            mode="lines+markers",
            stackgroup="one",
            name=col.replace("_%", ""),
            line=dict(color=color),
        ))
    fig_stage_path.update_layout(
        title="Migration IFRS 9 dynamique par stage",
        xaxis_title="Annee projetee", yaxis_title="Part du portefeuille (%)",
        height=390, hovermode="x unified",
    )
    col3.plotly_chart(fig_stage_path, use_container_width=True)

    macro_long = projection.melt(
        id_vars="year",
        value_vars=["UNRATE", "GDPC1_growth", "FEDFUNDS", "HY_SPREAD", "CPI_change", "DRCCLACBS"],
        var_name="Variable",
        value_name="Valeur",
    )
    fig_macro = px.line(
        macro_long, x="year", y="Valeur", color="Variable",
        markers=True, title="Trajectoire des variables macro retenues",
    )
    fig_macro.update_layout(height=390, xaxis_title="Annee projetee")
    col4.plotly_chart(fig_macro, use_container_width=True)

    st.markdown("---")
    st.subheader("Table de projection")
    display_cols = [
        "year", "severity_score", "UNRATE", "GDPC1_growth", "FEDFUNDS",
        "HY_SPREAD", "CPI_change", "DRCCLACBS", "EAD_M$", "ECL_M$",
        "Annual_provision_M$", "PD_mean_%", "LGD_mean_%", "CET1_%",
    ]
    st.dataframe(projection[display_cols], use_container_width=True)


def tab_basel_governance(df: pd.DataFrame, reporting_date, cet1_init: float):
    st.header("Bale & Gouvernance")
    st.caption(
        "Vue reglementaire: portefeuille a date d'arrete, segmentation, RWA, capital stack, "
        "registre modele et audit trail."
    )

    metrics = compute_basel_metrics(df, cet1_ratio=cet1_init)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Date d'arrete", pd.to_datetime(reporting_date).strftime("%Y-%m-%d"))
    c2.metric("RWA", f"${metrics['RWA_M$']:,.1f}M")
    c3.metric("Densite RWA", f"{metrics['RWA_density_%']:.1f}%")
    c4.metric("CET1", f"{metrics['CET1_ratio_%']:.2f}%")
    c5.metric("Leverage", f"{metrics['Leverage_ratio_%']:.2f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Capital stack et shortfalls")
        cap_rows = pd.DataFrame([metrics]).T.reset_index()
        cap_rows.columns = ["Indicateur", "Valeur"]
        st.dataframe(cap_rows, use_container_width=True, hide_index=True)
        action = capital_actions_from_shortfall(
            metrics["CET1_ratio_%"], metrics["Shortfall_CET1_7_M$"]
        )
        st.info(action)

    with col2:
        st.subheader("Segmentation reglementaire")
        seg = segment_summary(df)
        st.dataframe(seg, use_container_width=True, hide_index=True)
        fig_seg = px.bar(
            seg.sort_values("RWA_M", ascending=False),
            x="regulatory_segment",
            y=["EAD_M", "RWA_M"],
            barmode="group",
            title="EAD vs RWA par segment",
        )
        st.plotly_chart(fig_seg, use_container_width=True)

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Model registry")
        registry = ensure_model_registry()
        st.dataframe(registry, use_container_width=True, hide_index=True)
    with col4:
        st.subheader("Audit trail")
        audit = load_audit_log(limit=50)
        if audit.empty:
            st.info("Aucun run audite pour le moment.")
        else:
            st.dataframe(audit, use_container_width=True, hide_index=True)


def tab_migration(df: pd.DataFrame):
    st.header("🔄 Migration de Stage IFRS 9")
    st.info("Les données de migration proviennent des calculs du notebook 07 de validation avancée. "
            "Relancez les notebooks 05 à 07 pour obtenir les résultats de stress à jour.")

    summary, *_ = load_results()
    if summary is not None and "Scenario" in summary.columns:
        st.subheader("Résumé par Scénario")
        st.dataframe(summary, use_container_width=True)

    # Distribution stages actuelle
    stage_dist = df["stage"].value_counts().sort_index()
    stage_names = {1: "Stage 1", 2: "Stage 2", 3: "Stage 3"}
    fig_dist = go.Figure(data=[go.Bar(
        x=[stage_names[s] for s in stage_dist.index],
        y=stage_dist.values,
        marker_color=["#2ecc71", "#f39c12", "#e74c3c"][:len(stage_dist)],
    )])
    fig_dist.update_layout(title="Distribution Stage Actuelle (Baseline)",
                            height=350)
    st.plotly_chart(fig_dist, use_container_width=True)

    # Simulation simplifiée migration sous stress sévère
    st.subheader("Simulation Migration — Stress Sévère (Crise 2008)")
    pd_threshold_s2 = st.slider("Seuil PD pour Stage 1 → Stage 2 (lift)", 1.5, 5.0, 2.0, 0.5)
    pd_threshold_s3 = st.slider("Seuil PD absolu pour Stage 2 → Stage 3", 0.10, 0.60, 0.30, 0.05)

    pd_s2 = df["PD_pred"] * pd_threshold_s2
    stage_stressed = df["stage"].copy()
    stage_stressed.loc[(df["stage"] == 1) & (pd_s2 >= 0.05)] = 2
    stage_stressed.loc[(df["stage"] == 2) & (pd_s2 > pd_threshold_s3)] = 3
    stage_stressed.loc[(df["stage"] == 1) & (pd_s2 > pd_threshold_s3)] = 3

    dist_stressed = stage_stressed.value_counts().sort_index()
    col1, col2 = st.columns(2)
    fig_before = go.Figure(data=[go.Pie(
        labels=[stage_names.get(s, s) for s in stage_dist.index],
        values=stage_dist.values, hole=0.4,
        marker_colors=["#2ecc71", "#f39c12", "#e74c3c"],
        title="Baseline"
    )])
    col1.plotly_chart(fig_before, use_container_width=True)

    fig_after = go.Figure(data=[go.Pie(
        labels=[stage_names.get(s, s) for s in dist_stressed.index],
        values=dist_stressed.values, hole=0.4,
        marker_colors=["#2ecc71", "#f39c12", "#e74c3c"][:len(dist_stressed)],
        title="Post-Stress"
    )])
    col2.plotly_chart(fig_after, use_container_width=True)


# ---------------------------------------------------------------------------
# Onglet 4 — Résilience CET1
# ---------------------------------------------------------------------------
def tab_resilience(df: pd.DataFrame, cet1_init: float, tax_rate: float):
    st.header("🏛️ Résilience CET1 — Impact Réglementaire")

    _, curve_df, cet1_table, rst, *_ = load_results()
    ecl_baseline = df["ECL_ifrs9"].sum() / 1e6
    ead_total    = df["EAD"].sum() / 1e6

    # Métriques CET1 par scénario
    if cet1_table is not None:
        st.subheader("Impact par Scénario")
        from src.resilience import compute_cet1_impact
        rows = []
        for idx, row in cet1_table.iterrows():
            ecl_s = row.get("ECL_stressed_M$", ecl_baseline)
            impact = compute_cet1_impact(ecl_baseline, ecl_s, ead_total, cet1_init, tax_rate)
            impact["Scenario"] = idx
            rows.append(impact)

        df_display = pd.DataFrame(rows)
        display_cols = [
            "Scenario", "CET1_initial_%", "ΔCET1_%", "CET1_post_stress_%",
            "ΔECL_M$", "Shortfall_4_5_M$", "Shortfall_7_0_M$",
            "zone", "management_action",
        ]
        df_display = df_display[[c for c in display_cols if c in df_display.columns]]
        st.dataframe(df_display.set_index("Scenario"), use_container_width=True)

    # Courbe de résilience
    if curve_df is not None:
        st.subheader("Courbe de Résilience Dynamique")
        fig_curve = go.Figure()

        # Zones
        fig_curve.add_hrect(y0=CET1_TOTAL_MIN * 100, y1=15, fillcolor="green",
                             opacity=0.06, line_width=0, annotation_text="Résilient ≥ 7%")
        fig_curve.add_hrect(y0=CET1_REGULATORY_MIN * 100, y1=CET1_TOTAL_MIN * 100,
                             fillcolor="orange", opacity=0.10, line_width=0,
                             annotation_text="Attention 4.5–7%")
        fig_curve.add_hrect(y0=0, y1=CET1_REGULATORY_MIN * 100, fillcolor="red",
                             opacity=0.12, line_width=0, annotation_text="Critique < 4.5%")

        fig_curve.add_trace(go.Scatter(
            x=curve_df["intensity"], y=curve_df["CET1_%"],
            mode="lines+markers", name="CET1",
            line=dict(color="navy", width=3),
            marker=dict(size=6)
        ))
        fig_curve.add_hline(y=CET1_REGULATORY_MIN * 100, line_dash="dash",
                             line_color="red", annotation_text="Seuil Bâle III 4.5%")
        fig_curve.add_hline(y=CET1_TOTAL_MIN * 100, line_dash="dash",
                             line_color="orange", annotation_text="Coussin 7.0%")

        if rst is not None and not rst.empty and rst["intensity_critical"].iloc[0] is not None:
            try:
                ic = float(rst["intensity_critical"].iloc[0])
                fig_curve.add_vline(x=ic, line_dash="dashdot", line_color="red",
                                     annotation_text=f"Point rupture ×{ic:.2f}")
            except Exception:
                pass

        fig_curve.update_layout(
            title="Courbe de Résilience : CET1 vs Intensité du Choc",
            xaxis_title="Intensité du choc (×Crise 2008)",
            yaxis_title="CET1 (%)",
            yaxis=dict(range=[0, 15]),
            height=500, hovermode="x unified"
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    # Reverse Stress Test
    if rst is not None and not rst.empty:
        st.subheader("🔬 Résultat du Reverse Stress Test")
        row = rst.iloc[0]
        if pd.notna(row.get("intensity_critical")):
            col1, col2, col3 = st.columns(3)
            col1.metric("Intensité critique", f"×{row['intensity_critical']:.3f}")
            col2.metric("CET1 atteint",       f"{row['cet1_achieved_%']:.2f}%")
            col3.metric("ECL critique",        f"${row['ECL_critical_M$']:,.0f}M")

            if "macro_critical" in rst.columns:
                try:
                    import ast
                    macro_crit = ast.literal_eval(row["macro_critical"])
                    st.subheader("Variables Macro au Point de Rupture")
                    macro_df = pd.DataFrame([
                        {"Variable": k, "Baseline": BASELINE.get(k, "-"), "Critique": v,
                         "Δ": f"+{v - BASELINE.get(k, 0):.1f}"}
                        for k, v in macro_crit.items()
                    ])
                    st.dataframe(macro_df, use_container_width=True)
                except Exception:
                    pass
        else:
            st.success(row.get("message", "Portefeuille très résilient"))


# ---------------------------------------------------------------------------
# Onglet 5 — Modèle PD & SHAP
# ---------------------------------------------------------------------------
def tab_model(df: pd.DataFrame):
    st.header("🤖 Modèle PD — Performance & Interprétabilité")

    # Tableau métriques
    metrics_path = MODELS_DIR / "pd_model_comparison.csv"
    if metrics_path.exists():
        st.subheader("Comparaison des 4 Modèles PD")
        metrics_df = pd.read_csv(metrics_path, index_col=0)

        def color_metrics(val, col):
            thresholds = {
                "AUC-ROC": (0.70, 0.80),
                "Gini":    (0.40, 0.60),
                "KS":      (0.30, 0.45),
                "Brier":   (0.10, 0.07),
                "PSI":     (0.10, 0.05),
            }
            if col in thresholds:
                lo, hi = thresholds[col]
                if col in ["Brier", "PSI"]:
                    if val < hi:
                        return "background-color: #90EE90"
                    elif val < lo:
                        return "background-color: #FFFFE0"
                    else:
                        return "background-color: #FFB6C1"
                else:
                    if val > hi:
                        return "background-color: #90EE90"
                    elif val > lo:
                        return "background-color: #FFFFE0"
                    else:
                        return "background-color: #FFB6C1"
            return ""

        st.dataframe(metrics_df.style.format("{:.4f}"), use_container_width=True)

        # Radar chart métriques
        champion = metrics_df["AUC-ROC"].idxmax()
        row = metrics_df.loc[champion]
        categories = ["AUC-ROC", "Gini", "KS"]
        vals = [row["AUC-ROC"], row["Gini"], row["KS"]]
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            fill="toself", name=champion,
            line_color="#3498db"
        ))
        fig_radar.update_layout(
            title=f"Métriques Champion : {champion}",
            polar=dict(radialaxis=dict(range=[0, 1])),
            height=400
        )
        col1, col2 = st.columns(2)
        col1.plotly_chart(fig_radar, use_container_width=True)

        # Distribution PD
        fig_pd = px.histogram(df, x="PD_pred", nbins=50, color_discrete_sequence=["steelblue"],
                               title="Distribution des PD Prédites",
                               labels={"PD_pred": "PD"})
        fig_pd.add_vline(x=df["PD_pred"].mean(), line_dash="dash", line_color="red",
                          annotation_text=f"Moyenne: {df['PD_pred'].mean():.2%}")
        fig_pd.update_layout(height=400)
        col2.plotly_chart(fig_pd, use_container_width=True)

    # Images SHAP si disponibles
    shap_path = OUTPUT_DIR / "fig_16_shap_beeswarm.png"
    if shap_path.exists():
        st.subheader("SHAP Values — Importance des Features")
        col1, col2 = st.columns(2)
        if (OUTPUT_DIR / "fig_16_shap_beeswarm.png").exists():
            col1.image(str(OUTPUT_DIR / "fig_16_shap_beeswarm.png"), caption="SHAP Beeswarm")
        if (OUTPUT_DIR / "fig_17_shap_bar.png").exists():
            col2.image(str(OUTPUT_DIR / "fig_17_shap_bar.png"), caption="SHAP Importance")
    else:
        st.info("Lancez le notebook 03 de modélisation baseline pour générer les graphiques SHAP.")


def tab_validation():
    st.header("Validation Stress Testing")
    (
        _summary,
        _curve,
        _cet1,
        _rst,
        scenario_validation,
        stress_validation,
        forward,
        markov,
        sat_wf,
        sat_cmp,
        stress_models,
        stress_champion,
        fred_dict,
        project_eval,
        project_deductions,
        final_audit,
    ) = load_results()

    st.subheader("Pipeline final post-notebooks")
    if st.button("Regenerer audit final + rapport de validation", type="primary"):
        try:
            from scripts.run_final_pipeline import run_final_pipeline

            with st.spinner("Execution du pipeline final..."):
                result = run_final_pipeline(run_tests=True)
            load_results.clear()
            st.success(
                f"Pipeline final execute. Tests metier: {result['business_tests_passed']} OK."
            )
            st.caption(f"Rapport: {result['validation_report_md']}")
        except Exception as exc:
            st.error(f"Pipeline final non execute: {exc}")

    if final_audit is not None:
        status_counts = final_audit["status"].value_counts().to_dict() if "status" in final_audit.columns else {}
        cols = st.columns(max(len(status_counts), 1))
        for col, (status, count) in zip(cols, status_counts.items()):
            col.metric(status, count)
        st.dataframe(final_audit, use_container_width=True)
        audit_path = RESULTS_DIR / "final_banking_modeling_audit.md"
        if audit_path.exists():
            st.download_button(
                "Telecharger le check-up final Markdown",
                data=audit_path.read_text(encoding="utf-8"),
                file_name="final_banking_modeling_audit.md",
                mime="text/markdown",
            )
    else:
        st.info("final_banking_modeling_audit.csv non disponible. Cliquez sur le bouton de pipeline final.")

    st.subheader("Evaluation globale du projet")
    if project_eval is not None:
        total_score = project_eval["score"].sum()
        max_score = project_eval["weight"].sum()
        deductions = project_deductions["points"].sum() if project_deductions is not None else 0
        st.metric("Score expert ajuste", f"{total_score - deductions:.1f}/{max_score:.0f}")
        st.dataframe(project_eval, use_container_width=True)
        if project_deductions is not None:
            st.caption("Penalites de maturite restantes")
            st.dataframe(project_deductions, use_container_width=True)
    else:
        st.info("project_evaluation.csv non disponible. Lancez scripts/evaluate_project.py.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Validation metier des scenarios")
        if scenario_validation is not None:
            st.dataframe(scenario_validation, use_container_width=True)
        else:
            st.warning("scenario_design_validation.csv non disponible.")

    with col2:
        st.subheader("Controles des sorties de stress")
        if stress_validation is not None:
            ok = (stress_validation.get("validation_status") == "OK").all()
            st.metric("Statut global", "OK" if ok else "A revoir")
            st.dataframe(stress_validation, use_container_width=True)
        else:
            st.warning("stress_validation_report.csv non disponible.")

    st.markdown("---")
    st.subheader("Comparaison des moteurs de stress testing")
    if stress_models is not None:
        if stress_champion is not None and not stress_champion.empty:
            st.metric("Champion retenu", stress_champion.iloc[0].get("champion_model", "N/A"))
        st.dataframe(stress_models, use_container_width=True)
        if {"model_name", "final_score"}.issubset(stress_models.columns):
            fig_models = px.bar(
                stress_models.sort_values("final_score", ascending=False),
                x="model_name", y="final_score", color="final_score",
                color_continuous_scale="Viridis",
                title="Score final par moteur de stress",
            )
            fig_models.update_layout(xaxis_title="Moteur", yaxis_title="Score")
            st.plotly_chart(fig_models, use_container_width=True)
    else:
        st.info("stress_model_comparison.csv non disponible. Lancez scripts/compare_stress_models.py.")

    st.markdown("---")
    st.subheader("Utilisation des donnees FRED")
    if fred_dict is not None:
        st.dataframe(fred_dict, use_container_width=True)
    else:
        st.info("fred_variable_dictionary.csv non disponible. Relancez le preprocessing avec save_reports=True.")

    st.markdown("---")
    st.subheader("ECL forward-looking IFRS 9 (controle complementaire)")
    if forward is not None:
        st.dataframe(forward, use_container_width=True)
        plot_df = forward[forward["scenario_key"] != "forward_looking"]
        fig = px.bar(
            plot_df,
            x="Scenario",
            y="weighted_ECL_M$",
            color="ECL_M$",
            color_continuous_scale="RdYlGn_r",
            title="Contribution ponderee a l'ECL forward-looking",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("forward_looking_ecl.csv non disponible.")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Modeles satellites macro-PD")
        if sat_cmp is not None:
            st.dataframe(sat_cmp, use_container_width=True)
        else:
            st.info("satellite_pd_comparison.csv non disponible.")

    with c2:
        st.subheader("Backtesting walk-forward")
        if sat_wf is not None and {"Model", "abs_error"}.issubset(sat_wf.columns):
            wf_summary = sat_wf.groupby("Model").agg(
                MAE=("abs_error", "mean"),
                RMSE=("abs_error", lambda x: float(np.sqrt(np.mean(np.square(x))))),
                n_folds=("abs_error", "count"),
            ).reset_index().sort_values("RMSE")
            st.dataframe(wf_summary, use_container_width=True)
        else:
            st.info("satellite_pd_walk_forward.csv non disponible.")

    st.markdown("---")
    st.subheader("Migration Markov IFRS 9")
    if markov is not None:
        st.dataframe(markov, use_container_width=True)
    else:
        st.info("stage_migration_markov_summary.csv non disponible.")

    report_path = RESULTS_DIR / "validation_report.md"
    if report_path.exists():
        st.download_button(
            "Telecharger le rapport de validation Markdown",
            data=report_path.read_text(encoding="utf-8"),
            file_name="validation_report.md",
            mime="text/markdown",
        )
    dfast_path = RESULTS_DIR / "dfast_like_report.md"
    if dfast_path.exists():
        st.download_button(
            "Telecharger le rapport DFAST-like",
            data=dfast_path.read_text(encoding="utf-8"),
            file_name="dfast_like_report.md",
            mime="text/markdown",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    (
        custom_scenario,
        scenario_key,
        scenario_label,
        reporting_date,
        horizon_years,
        shock_profile,
        cet1_init,
        tax_rate,
    ) = sidebar_dynamic()

    if not check_outputs_exist():
        st.error("⚠️ Les fichiers de données nettoyées n'existent pas encore.")
        st.write("Fichiers manquants:", missing_files(REQUIRED_DATA_FILES))
        st.info(
            "Lancez les notebooks dans l'ordre: 01_EDA, 02_Preprocessing, "
            "03_Baseline_ECL, 04_Modeles_Satellites_Macro, 05_Stress_Testing, "
            "06_Resilience_Reverse_Stress, 07_Stress_Testing_Validation_Avancee."
        )
        st.stop()

    try:
        df = load_data()
    except RuntimeError as exc:
        st.error(str(exc))
        st.code("pip install pyarrow streamlit", language="bash")
        st.stop()
    df, reporting_date = enrich_banking_view(df, reporting_date)
    if df.empty:
        st.error("Aucun pret disponible a cette date d'arrete.")
        st.stop()

    models, champion, sat_pd, sat_feats, sat_champ = load_models()
    missing_optional = missing_files(OPTIONAL_MODEL_FILES)
    if missing_optional:
        st.warning(
            "Certains artefacts modeles sont absents. L'app reste consultable avec "
            "des fallbacks, mais les resultats complets exigent: "
            + ", ".join(missing_optional)
        )

    from src.data_prep import get_origination_pd_features
    features = get_origination_pd_features(df)

    pd_champion = models.get(champion) if champion in models else None
    if pd_champion is None and models:
        pd_champion = next(iter(models.values()))

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Vue Globale",
        "⚡ Scénarios de Stress",
        "🔄 Migration de Stage",
        "🏛️ Résilience CET1",
        "🤖 Modèle PD",
        "Projection T1-T5",
        "Bale & Gouvernance",
        "Validation",
    ])

    with tab1:
        tab_overview(df)

    with tab2:
        tab_stress(df, custom_scenario, scenario_key, scenario_label,
                   pd_champion, features,
                   sat_pd, sat_feats, sat_champ, cet1_init, tax_rate)

    with tab3:
        tab_migration(df)

    with tab4:
        tab_resilience(df, cet1_init, tax_rate)

    with tab5:
        tab_model(df)

    with tab6:
        tab_projection(
            df, custom_scenario, scenario_key, scenario_label,
            horizon_years, shock_profile, cet1_init, tax_rate,
            pd_champion, features, sat_pd, sat_feats, sat_champ,
        )

    with tab7:
        tab_basel_governance(df, reporting_date, cet1_init)

    with tab8:
        tab_validation()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 12px;'>"
        "Moteur de Stress Testing IFRS 9 · Projet Fin d'Études Cycle Ingénieur 2025-2026 · "
        "ECL = PD × LGD × EAD</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
