const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");
const sharp = require("sharp");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "outputs");
const RES = path.join(OUT, "results");
const MODELS = path.join(OUT, "models");
const DECK_DIR = path.join(OUT, "presentations");
fs.mkdirSync(DECK_DIR, { recursive: true });

const W = 13.333;
const H = 7.5;
const S = { rect: "rect", line: "line", ellipse: "ellipse" };
const C = {
  ink: "17202A",
  muted: "5D6D7E",
  line: "D6DBDF",
  bg: "F7F9FA",
  white: "FFFFFF",
  teal: "0E7C7B",
  blue: "2E86C1",
  green: "1E8449",
  red: "C0392B",
  orange: "D68910",
  navy: "154360",
};

function csvRows(file) {
  const p = path.join(file);
  if (!fs.existsSync(p)) return [];
  const lines = fs.readFileSync(p, "utf8").trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = splitCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const vals = splitCsvLine(line);
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? ""]));
  });
}

function splitCsvLine(line) {
  const out = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') quoted = !quoted;
    else if (ch === "," && !quoted) {
      out.push(cur);
      cur = "";
    } else cur += ch;
  }
  out.push(cur);
  return out.map((x) => x.replace(/^"|"$/g, ""));
}

function newDeck(subject) {
  const pptx = new PptxGenJS();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "Projet Far7ti";
  pptx.company = "PFA IFRS 9 Stress Testing";
  pptx.subject = subject;
  pptx.theme = {
    headFontFace: "Aptos Display",
    bodyFontFace: "Aptos",
    lang: "fr-FR",
  };
  return pptx;
}

function addFooter(slide, section) {
  slide.addShape(S.line, { x: 0.55, y: 7.05, w: 12.25, h: 0, line: { color: C.line, width: 0.7 } });
  slide.addText(section, { x: 0.62, y: 7.13, w: 6.6, h: 0.18, fontFace: "Aptos", fontSize: 7.5, color: C.muted, margin: 0 });
  slide.addText("Projet IFRS 9 Stress Testing", { x: 9.45, y: 7.13, w: 3.1, h: 0.18, fontFace: "Aptos", fontSize: 7.5, color: C.muted, align: "right", margin: 0 });
}

function title(slide, t, st = "") {
  slide.addText(t, { x: 0.62, y: 0.38, w: 9.8, h: 0.48, fontFace: "Aptos Display", fontSize: 24, bold: true, color: C.ink, margin: 0 });
  if (st) slide.addText(st, { x: 0.64, y: 0.9, w: 10.8, h: 0.28, fontSize: 10.5, color: C.muted, margin: 0 });
}

function cover(pptx, deckTitle, subtitle, chips) {
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  s.addShape(S.rect, { x: 0, y: 5.5, w: W, h: 2.0, fill: { color: C.teal, transparency: 8 }, line: { color: C.teal, transparency: 100 } });
  s.addText(deckTitle, { x: 0.78, y: 1.05, w: 9.8, h: 1.25, fontFace: "Aptos Display", fontSize: 34, bold: true, color: C.white, breakLine: false, margin: 0.03, fit: "shrink" });
  s.addText(subtitle, { x: 0.82, y: 2.52, w: 8.5, h: 0.55, fontSize: 15, color: "D6EAF8", margin: 0 });
  s.addText(chips.join("  |  "), { x: 0.84, y: 6.08, w: 10.8, h: 0.32, fontSize: 10, color: C.white, bold: true, margin: 0 });
  s.addText("PFA 2025-2026", { x: 0.84, y: 6.52, w: 2.6, h: 0.22, fontSize: 8.5, color: "D5DBDB", margin: 0 });
}

function bulletSlide(pptx, section, t, bullets, accent = C.teal) {
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  title(s, t);
  s.addShape(S.line, { x: 0.64, y: 1.35, w: 11.9, h: 0, line: { color: accent, width: 2 } });
  bullets.forEach((b, i) => {
    const y = 1.72 + i * 0.76;
    s.addShape(S.ellipse, { x: 0.74, y: y + 0.08, w: 0.14, h: 0.14, fill: { color: accent }, line: { color: accent, transparency: 100 } });
    s.addText(b[0], { x: 1.05, y, w: 3.1, h: 0.28, fontSize: 13.2, bold: true, color: C.ink, margin: 0 });
    s.addText(b[1], { x: 4.0, y, w: 7.9, h: 0.42, fontSize: 10.5, color: C.muted, margin: 0.01, fit: "shrink" });
  });
  addFooter(s, section);
}

async function addImage(slide, img, x, y, w, h, border = true) {
  const p = path.join(OUT, img);
  if (!fs.existsSync(p)) return;
  const meta = await sharp(p).metadata();
  const ratio = meta.width / meta.height;
  let iw = w;
  let ih = w / ratio;
  if (ih > h) {
    ih = h;
    iw = h * ratio;
  }
  slide.addImage({ path: p, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih });
  if (border) slide.addShape(S.rect, { x, y, w, h, fill: { color: C.white, transparency: 100 }, line: { color: C.line, width: 0.8 } });
}

async function imageSlide(pptx, section, t, st, images, note = "", accent = C.teal) {
  const s = pptx.addSlide();
  s.background = { color: C.white };
  title(s, t, st);
  const n = images.length;
  const slots = n === 1
    ? [{ x: 0.72, y: 1.35, w: 11.85, h: 5.35 }]
    : n === 2
      ? [{ x: 0.65, y: 1.42, w: 6.05, h: 4.92 }, { x: 6.88, y: 1.42, w: 5.75, h: 4.92 }]
      : [{ x: 0.65, y: 1.55, w: 3.9, h: 4.35 }, { x: 4.72, y: 1.55, w: 3.9, h: 4.35 }, { x: 8.8, y: 1.55, w: 3.75, h: 4.35 }];
  for (let i = 0; i < images.length; i++) await addImage(s, images[i], slots[i].x, slots[i].y, slots[i].w, slots[i].h);
  if (note) {
    s.addShape(S.line, { x: 0.7, y: 6.55, w: 11.7, h: 0, line: { color: accent, width: 1.2 } });
    s.addText(note, { x: 0.75, y: 6.68, w: 11.3, h: 0.28, fontSize: 9.5, color: C.ink, margin: 0, fit: "shrink" });
  }
  addFooter(s, section);
}

function tableSlide(pptx, section, t, st, headers, rows, accent = C.teal) {
  const s = pptx.addSlide();
  s.background = { color: C.white };
  title(s, t, st);
  const table = [headers.map((h) => ({ text: h, options: { bold: true, color: C.white } }))];
  rows.forEach((r) => table.push(r.map((v) => ({ text: String(v), options: { color: C.ink } }))));
  s.addTable(table, {
    x: 0.72, y: 1.52, w: 11.82, h: 4.9,
    border: { type: "solid", color: C.line, pt: 0.6 },
    fill: { color: C.white },
    color: C.ink,
    fontFace: "Aptos",
    fontSize: 8.5,
    margin: 0.06,
    autoFit: false,
    valign: "mid",
    rowH: 0.38,
    bold: false,
  });
  s.addShape(S.rect, { x: 0.72, y: 1.52, w: 11.82, h: 0.43, fill: { color: accent }, line: { color: accent, transparency: 100 } });
  addFooter(s, section);
}

function codeSlide(pptx, section, t, st, code, callouts, accent = C.navy) {
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  title(s, t, st);
  s.addShape(S.rect, { x: 0.72, y: 1.42, w: 7.45, h: 4.82, fill: { color: "101820" }, line: { color: "101820" } });
  s.addText(code.trim(), {
    x: 0.95, y: 1.68, w: 6.95, h: 4.35,
    fontFace: "Cascadia Mono",
    fontSize: 8.2,
    color: "ECF0F1",
    margin: 0.02,
    fit: "shrink",
    breakLine: false,
  });
  s.addShape(S.line, { x: 8.55, y: 1.48, w: 0, h: 4.65, line: { color: accent, width: 2 } });
  callouts.forEach((c, i) => {
    const y = 1.58 + i * 0.88;
    s.addText(c[0], { x: 8.86, y, w: 3.45, h: 0.25, fontSize: 11.5, bold: true, color: C.ink, margin: 0 });
    s.addText(c[1], { x: 8.86, y: y + 0.29, w: 3.55, h: 0.38, fontSize: 8.6, color: C.muted, margin: 0.01, fit: "shrink" });
  });
  addFooter(s, section);
}

async function buildEdaDeck() {
  const pptx = newDeck("EDA Lending Club IFRS 9");
  cover(pptx, "Exploration des Données", "Ce que l'EDA a montré, les figures produites et les décisions retenues", ["Lending Club", "FRED macro", "Défaut / LGD / segmentation"]);
  bulletSlide(pptx, "EDA", "Objectif de l'EDA", [
    ["Question", "Comprendre le portefeuille avant toute modélisation: défaut, segments, temporalité et variables macro."],
    ["Base utilisée", "loan.csv Lending Club, variables utiles chargées en chunks pour réduire la mémoire."],
    ["Sorties", "Figures fig_01 à fig_11 dans outputs, plus tableaux qualité après amélioration du preprocessing."],
    ["Décision", "Identifier les risques de censure, les variables instables et les segments explicatifs du défaut."],
  ], C.blue);
  await imageSlide(pptx, "EDA", "Distribution de la cible", "Statut des prêts et transformation en default_flag", ["fig_01_loan_status.png", "fig_04_default_by_grade.png"], "Output: fig_01_loan_status.png et fig_04_default_by_grade.png. Le grade est bien ordonné par risque et sert de variable clé PD.", C.blue);
  await imageSlide(pptx, "EDA", "Qualité des données", "Valeurs manquantes et premières décisions de nettoyage", ["fig_03_missing_values.png"], "Output: fig_03_missing_values.png. Les colonnes manquantes doivent être traitées par règles documentées, pas seulement par fillna global.", C.orange);
  bulletSlide(pptx, "EDA", "Méthodes utilisées dans l'EDA", [
    ["Analyse cible", "Distribution de loan_status puis création de default_flag pour mesurer le taux de défaut."],
    ["Segmentation", "GroupBy par grade, sub_grade, term, home_ownership et purpose pour comparer les taux de défaut."],
    ["Analyse temporelle", "Conversion issue_d en année/trimestre pour observer les cohortes et la crise 2008."],
    ["Analyse macro", "Fusion visuelle du taux de défaut trimestriel avec UNRATE, PIB, Fed Funds et HY spread."],
    ["LGD préliminaire", "Recovery rate = remboursements + recoveries rapportés au funded amount."],
  ], C.blue);
  codeSlide(pptx, "EDA", "Extrait code EDA", "Création de la cible et taux de défaut par grade", `
DEFAULT_STATUS = {
    "Default", "Charged Off",
    "Does not meet the credit policy. Status:Charged Off"
}

df_raw["default_flag"] = (
    df_raw["loan_status"].isin(DEFAULT_STATUS).astype(int)
)

dr_grade = df_raw.groupby("grade")["default_flag"].agg(
    default_rate="mean",
    loans="count"
).sort_index()
`, [
    ["Cible binaire", "Transforme le statut final en indicateur de défaut."],
    ["Segmentation", "Mesure le risque moyen par grade A à G."],
    ["Sortie", "Alimente fig_04_default_by_grade.png."],
  ], C.blue);
  codeSlide(pptx, "EDA", "Code src utilisé par le notebook EDA", "Fonctions importées depuis src/data_prep.py", `
from src.data_prep import load_loan_data, load_macro_data, LOAN_COLS

df_raw = load_loan_data(DATA_DIR / "loan.csv")
macro = load_macro_data()

# load_loan_data:
# - lecture en chunks
# - selection LOAN_COLS
# - on_bad_lines="skip"
`, [
    ["Pourquoi src ?", "Centralise le chargement pour éviter du code différent entre notebook et pipeline."],
    ["Pourquoi chunks ?", "loan.csv fait environ 1.2 Go; la lecture par morceaux limite la RAM."],
    ["Output", "DataFrames df_raw et macro utilisés par les figures fig_01 à fig_11."],
  ], C.navy);
  bulletSlide(pptx, "EDA", "Pourquoi ces méthodes et ces outputs", [
    ["Graphes de distribution", "Vérifier l'équilibre de la cible et les variables continues avant modélisation."],
    ["GroupBy segment", "Montrer que le risque varie par grade, subgrade, terme et profil emprunteur."],
    ["Courbes temporelles", "Détecter crise, effet vintage et risque de censure des prêts récents."],
    ["Matrice corrélation", "Identifier les variables candidates et les redondances avant modèle PD."],
    ["LGD empirique", "Préparer la composante pertes du futur calcul ECL."],
  ], C.green);
  const fredRowsEda = csvRows(path.join(RES, "fred_variable_dictionary.csv")).slice(0, 7)
    .map(r => [r.variable, r.fred_series, r.role, r.business_use]);
  tableSlide(pptx, "EDA", "Utilisation des données FRED", "Variables macro exploitées dans l'EDA et les satellites", ["Variable", "FRED", "Rôle", "Utilisation métier"], fredRowsEda, C.navy);
  await imageSlide(pptx, "EDA", "Segmentation du risque", "Grade, sub-grade, terme, logement et objet du prêt", ["fig_05_heatmap_subgrade.png", "fig_06_default_segments.png"], "Output: fig_05 et fig_06. Ces analyses justifient l'encodage ordinal grade/subgrade et les variables one-hot home ownership.", C.blue);
  await imageSlide(pptx, "EDA", "Dimension temporelle et crise 2008", "Default rate par année et cycle macro", ["fig_07_default_over_time.png", "fig_10_macro_credit_cycle.png"], "Point expert: la lecture temporelle révèle un risque de censure des cohortes récentes, à traiter dans le preprocessing.", C.red);
  await imageSlide(pptx, "EDA", "Variables continues et corrélations", "Distribution, outliers et relation avec le défaut", ["fig_08_distributions.png", "fig_09_correlation_matrix.png"], "Output: fig_08 et fig_09. Les outliers DTI/revenu/revol_util motivent winsorisation et contrôles avant modèle.", C.teal);
  await imageSlide(pptx, "EDA", "Analyse LGD préliminaire", "Recouvrement observé sur prêts en défaut", ["fig_11_lgd_analysis.png"], "La LGD empirique par grade devient la base de l'EAD/LGD du moteur ECL.", C.green);
  bulletSlide(pptx, "EDA", "Conclusion EDA: ce qui est réutilisé", [
    ["Features PD", "grade_num, subgrade_num, DTI, taux, revenu log, ancienneté crédit, défauts passés, variables macro."],
    ["Contrôles requis", "Missing values, outliers, cohérence temporelle, censure et séparation variables à l'octroi / post-origination."],
    ["Outputs", "fig_01 à fig_11, puis rapports CSV schema/missing/outliers/vintage."],
    ["Suite", "Le preprocessing transforme ces constats en pipeline reproductible."],
  ], C.green);
  const out = path.join(DECK_DIR, "01_Presentation_EDA.pptx");
  await pptx.writeFile({ fileName: out });
  return out;
}

async function buildPreprocessingDeck() {
  const pptx = newDeck("Preprocessing IFRS 9");
  cover(pptx, "Preprocessing & Dataset Final", "Nettoyage, feature engineering, staging IFRS 9 et artefacts produits", ["Pipeline reproductible", "loan_clean.parquet", "Rapports qualité"]);
  bulletSlide(pptx, "Preprocessing", "Pipeline appliqué", [
    ["Lecture", "Chargement chunked de loan.csv avec sélection des colonnes utiles."],
    ["Normalisation", "Parsing dates/taux, encodage grade, subgrade, emploi, vérification et logement."],
    ["Feature engineering", "credit_age_months, log_annual_inc, term_months, vintage_year, observation_months."],
    ["Cibles", "default_flag, stage IFRS 9 proxy, LGD empirique et EAD."],
  ], C.teal);
  bulletSlide(pptx, "Preprocessing", "Méthodes utilisées", [
    ["Parsing", "Dates Lending Club au format mois-année, taux en pourcentage convertis en float."],
    ["Encodage", "Grade/subgrade en ordinal, emploi et verification_status en scores, logement en one-hot."],
    ["Outliers", "Winsorisation annual_inc et dti au percentile 99, revol_util borné entre 0 et 100."],
    ["Imputation", "Médiane par grade pour variables crédit, puis médiane globale en fallback."],
    ["Censure", "Ajout observation_months et flags mature_12m/mature_24m pour contrôler les cohortes récentes."],
  ], C.teal);
  codeSlide(pptx, "Preprocessing", "Extrait code preprocessing", "Correction macro, censure et EAD", `
macro["GDPC1_growth"] = macro["GDPC1"].pct_change(12) * 100

last_obs = df["last_pymnt_d"].fillna(df["last_pymnt_d"].max())
df["observation_months"] = (
    (last_obs - df["issue_d"]).dt.days / 30.4375
).clip(lower=0)

df["mature_12m_flag"] = (df["observation_months"] >= 12).astype(int)
df["EAD"] = df["funded_amnt"].fillna(df["loan_amnt"])
`, [
    ["Macro", "PIB réel en croissance annuelle correcte après resampling mensuel."],
    ["Censure", "Évite de considérer trop vite les prêts récents comme bons."],
    ["EAD", "Exposition initiale plus défendable pour un stress historique."],
  ], C.teal);
  codeSlide(pptx, "Preprocessing", "Code src utilisé par le notebook 02", "Pipeline principal appelé dans 02_Preprocessing.ipynb", `
from src.data_prep import build_clean_dataset, get_pd_features

df, macro = build_clean_dataset(
    loan_path=DATA_DIR / "loan.csv",
    save_parquet=True,
    save_reports=True,
    ead_method="initial"
)

features = get_pd_features(df)
`, [
    ["Reproductibilité", "Une seule fonction relance tout le pipeline de préparation."],
    ["Traçabilité", "save_reports génère les CSV d'audit utilisés dans les slides."],
    ["Output", "outputs/loan_clean.parquet + rapports CSV dans outputs/results."],
  ], C.navy);
  codeSlide(pptx, "Preprocessing", "Code src: imputation et outliers", "Règles documentées avant sauvegarde du dataset final", `
df["annual_inc"] = df["annual_inc"].clip(
    upper=df["annual_inc"].quantile(0.99)
)
df["revol_util"] = df["revol_util"].clip(0, 100)

for col in ["dti", "revol_util", "revol_bal"]:
    df[col] = df.groupby("grade_num")[col].transform(
        lambda x: x.fillna(x.median())
    )
    df[col] = df[col].fillna(df[col].median())
`, [
    ["Pourquoi cap 99%", "Réduit l'influence des valeurs extrêmes sans supprimer le portefeuille."],
    ["Pourquoi par grade ?", "L'imputation respecte le niveau de risque du prêt."],
    ["Output", "Features PD sans NaN critique et outlier_summary.csv."],
  ], C.orange);
  bulletSlide(pptx, "Preprocessing", "Pourquoi ces méthodes et ces outputs", [
    ["Parquet final", "Format compact et rapide pour les notebooks 03 à 07."],
    ["Schema report", "Prouve que les colonnes critiques existent avant transformation."],
    ["Missing/outlier reports", "Documentent les choix de nettoyage pour la soutenance."],
    ["Vintage profile", "Montre que la censure temporelle a été contrôlée."],
    ["Feature list", "Garantit que les modèles utilisent des variables cohérentes."],
  ], C.green);
  const fredRowsPrep = csvRows(path.join(RES, "fred_variable_dictionary.csv")).slice(0, 7)
    .map(r => [r.variable, r.frequency, r.role, r.business_use]);
  tableSlide(pptx, "Preprocessing", "Traçabilité FRED dans le pipeline", "Le preprocessing documente chaque variable macro et son usage", ["Variable", "Freq.", "Rôle", "Usage"], fredRowsPrep, C.navy);
  const schema = csvRows(path.join(RES, "schema_quality_report.csv")).slice(0, 8).map(r => [r.column, r.expected_type, r.exists, r.missing_rate]);
  tableSlide(pptx, "Preprocessing", "Contrôle du schéma", "Colonnes critiques attendues avant transformation", ["Colonne", "Type attendu", "Existe", "Missing"], schema, C.teal);
  await imageSlide(pptx, "Preprocessing", "Staging IFRS 9", "Transformation des statuts de prêt en Stage 1 / 2 / 3", ["fig_12_stages_ifrs9.png"], "Output: fig_12_stages_ifrs9.png. Le stage est une approximation pédagogique basée sur loan_status.", C.green);
  await imageSlide(pptx, "Preprocessing", "Validation LGD / EAD", "Cohérence du risque par grade et exposition utilisée", ["fig_13_lgd_ead_validation.png"], "Output: fig_13_lgd_ead_validation.png. L'EAD par défaut est désormais initiale pour mieux convenir au stress historique.", C.green);
  const audit = csvRows(path.join(RES, "preprocessing_audit.csv"))[0] || {};
  tableSlide(pptx, "Preprocessing", "Audit du dataset final", "Indicateurs synthétiques sauvegardés dans preprocessing_audit.csv", ["Indicateur", "Valeur"], [
    ["Lignes", audit.n_rows || "à générer"],
    ["Colonnes", audit.n_columns || "à générer"],
    ["Taux défaut", audit.default_rate || "à générer"],
    ["EAD total", audit.ead_total || "à générer"],
    ["LGD médiane", audit.lgd_median || "à générer"],
    ["Maturité 12m", audit.mature_12m_rate || "à générer"],
  ], C.blue);
  const vintage = csvRows(path.join(RES, "vintage_default_profile.csv")).slice(0, 10).map(r => [r.vintage_year, r.loans, r.default_rate, r.mature_12m_rate || "", r.obs_months_median || ""]);
  tableSlide(pptx, "Preprocessing", "Censure et vintage", "Contrôle ajouté pour éviter de classer trop vite les prêts récents comme bons", ["Année", "Prêts", "DR", "Mat. 12m", "Obs. méd."], vintage, C.orange);
  bulletSlide(pptx, "Preprocessing", "Outputs produits", [
    ["Parquet final", "outputs/loan_clean.parquet avec variables PD, macro, cibles IFRS 9, LGD et EAD."],
    ["Rapports CSV", "schema_quality_report, feature_missing_report, outlier_summary, vintage_default_profile."],
    ["Décision expert", "Documenter les imputations et la censure pour rendre la modélisation défendable."],
    ["Suite", "Le dataset final alimente le modèle PD baseline puis le premier moteur de stress."],
  ], C.navy);
  const out = path.join(DECK_DIR, "02_Presentation_Preprocessing.pptx");
  await pptx.writeFile({ fileName: out });
  return out;
}

async function buildModelDeck() {
  const pptx = newDeck("Modélisation jusqu'au premier stress testing");
  cover(pptx, "Modélisation ECL & Premier Stress Testing", "De la PD baseline aux modèles satellites, puis au premier choc stressé", ["PD Models", "Baseline ECL", "Satellite Macro", "Stress Testing"]);
  bulletSlide(pptx, "Modélisation", "Méthodes utilisées", [
    ["PD baseline", "Comparaison LogReg, RandomForest, XGBoost et LightGBM avec AUC, Gini, KS, Brier, PSI."],
    ["Validation", "Split temporel et walk-forward pour vérifier la stabilité hors période d'entraînement."],
    ["Explicabilité", "SHAP pour identifier les variables qui pilotent la PD prédite."],
    ["ECL baseline", "ECL = PD_pred x LGD x EAD x facteur horizon IFRS 9."],
    ["Satellite macro", "Modèle macro -> default rate pour transformer un scénario économique en lift de PD."],
  ], C.blue);
  codeSlide(pptx, "Modélisation", "Extrait code ECL baseline", "Calcul de l'ECL IFRS 9 avant stress", `
pd_pred = champion_model.predict_proba(X_chunk)[:, 1]
result["PD_pred"] = pd_pred

horizon_factor = np.where(
    result["stage"] == 1,
    12.0 / term_months.clip(1),
    1.0
)

result["ECL_ifrs9"] = (
    result["PD_pred"] * result["LGD"] * result["EAD"] * horizon_factor
)
`, [
    ["PD", "Prédiction individuelle par le modèle champion."],
    ["IFRS 9", "Stage 1 en horizon 12 mois, Stage 2/3 en lifetime."],
    ["Baseline", "Point zéro utilisé pour mesurer le lift sous stress."],
  ], C.green);
  codeSlide(pptx, "Modélisation", "Code src utilisé par le notebook 03", "Entraînement, évaluation et sauvegarde des modèles PD", `
from src.ecl_engine import train_pd_models, compute_ecl_baseline
from src.data_prep import get_temporal_split, get_pd_features

train, val, test = get_temporal_split(df)
features = get_pd_features(df)

models, results_df = train_pd_models(
    X_train, y_train, X_val, y_val, X_test, y_test
)
df_ecl = compute_ecl_baseline(df, champion_model, features)
`, [
    ["Pourquoi plusieurs PD ?", "Comparer performance, stabilité et calibration avant de retenir un champion."],
    ["Pourquoi split temporel ?", "Évite une validation optimiste sur des prêts futurs."],
    ["Outputs", "pd_model_comparison.csv, modèles .pkl, ecl_baseline.parquet."],
  ], C.blue);
  codeSlide(pptx, "Satellites macro", "Code src utilisé par le notebook 04", "Lien macroéconomique vers taux de défaut", `
from src.satellite_models import (
    compute_quarterly_default_rate,
    merge_macro_quarterly,
    train_satellite_pd
)

dr_q = compute_quarterly_default_rate(df)
sat_data = merge_macro_quarterly(dr_q, macro)
sat_models, sat_results = train_satellite_pd(sat_data)
`, [
    ["Pourquoi trimestriel ?", "Le défaut et les variables macro se comparent mieux à fréquence économique."],
    ["Pourquoi satellite ?", "Transformer un choc macro en lift de PD stressée."],
    ["Outputs", "satellite_pd_comparison.csv, fig_20 à fig_24."],
  ], C.orange);
  await imageSlide(pptx, "Modélisation", "Comparaison des modèles PD", "LogReg, RandomForest, XGBoost et LightGBM", ["fig_13_model_comparison.png", "fig_14_roc_ks.png"], "Outputs: fig_13_model_comparison.png et fig_14_roc_ks.png. Le champion est sélectionné sur AUC/Gini/KS/Brier/PSI.", C.blue);
  await imageSlide(pptx, "Modélisation", "Validation temporelle et explicabilité", "Walk-forward + SHAP pour réduire le risque de boîte noire", ["fig_15_walk_forward.png", "fig_17_shap_bar.png"], "Outputs: fig_15 et fig_17. Le modèle doit être stable et explicable, pas seulement performant.", C.teal);
  await imageSlide(pptx, "ECL Baseline", "ECL de référence IFRS 9", "Point zéro avant application des chocs", ["fig_19_ecl_baseline.png"], "ECL baseline = PD_pred x LGD x EAD x facteur horizon. Cette base sert à mesurer le lift sous stress.", C.green);
  await imageSlide(pptx, "Satellites macro", "Construction du lien macro -> risque", "Taux de défaut trimestriel et corrélations macro", ["fig_20_dr_quarterly.png", "fig_21_macro_corr.png"], "Le satellite transforme un scénario macro en lift de défaut. Il prépare le premier modèle de stress testing.", C.orange);
  await imageSlide(pptx, "Satellites macro", "Comparaison des modèles satellites", "OLS, Ridge, LASSO, ElasticNet, RandomForestReg, XGBoostReg", ["fig_22_satellite_pd_comparison.png", "fig_23_ols_coefficients.png"], "Output: comparaison statistique + coefficients. Le modèle retenu doit rester économiquement cohérent.", C.orange);
  await imageSlide(pptx, "Satellites macro", "Calibration crise 2008", "Backtesting historique du choc sévère", ["fig_24_calibration_2008.png"], "La crise 2008 sert de référence pour vérifier que le modèle reproduit un choc réel.", C.red);
  const scen = csvRows(path.join(RES, "stress_ecl_summary.csv")).slice(0, 7).map(r => [r.Scenario, r["ECL_stressed_M$"], r.ECL_lift, r["PD_stressed_%"], r["LGD_stressed_%"]]);
  tableSlide(pptx, "Premier stress", "Premier moteur de stress testing", "Application des chocs à PD, LGD et EAD", ["Scénario", "ECL M$", "Lift", "PD stress", "LGD stress"], scen, C.red);
  bulletSlide(pptx, "Premier stress", "Scénarios métier ajoutés", [
    ["Adverse / Severe", "Scénarios internes de référence pour stress macro et choc combiné."],
    ["Choc Taux", "Hausse Fed Funds + spread pour tester la sensibilité taux/LGD/EAD."],
    ["Choc Marché 2018", "Resserrement monétaire et spread HY plus élevé, sans récession forte."],
    ["Crise 2008", "Backtesting historique de crise financière sévère."],
    ["Crise COVID-19", "Chômage extrême, contraction PIB, Fed au plancher et spread sous tension."],
  ], C.red);
  codeSlide(pptx, "Premier stress", "Extrait code premier stress", "Application du choc macro au portefeuille", `
model_lift = dr_stress / max(dr_base, 1e-6)
floor_lift = deterministic_pd_lift(scenario)
lift = np.clip(max(model_lift, floor_lift), 1.0, 5.0)

result["PD_stressed"] = (pd_base * lift).clip(0, 1)
result["LGD_stressed"] = compute_lgd_stressed(df, scenario)
result["EAD_stressed"] = compute_ead_stressed(df, scenario)
result["ECL_stressed"] = (
    result["PD_stressed"] * result["LGD_stressed"] * result["EAD_stressed"]
)
`, [
    ["Lift PD", "Le satellite donne le ratio DR stressé / DR baseline."],
    ["Plancher expert", "Empêche un choc adverse de réduire artificiellement la PD."],
    ["Stress ECL", "Mesure l'impact direct du choc, distinct du forward-looking."],
  ], C.red);
  codeSlide(pptx, "Premier stress", "Code src utilisé par le notebook 05", "Moteur de stress ECL multi-scénarios", `
from src.stress_scenarios import compute_stress_ecl

stress_results, summary_df = compute_stress_ecl(
    df_ecl,
    champion_pd_model,
    features,
    satellite_pd_model,
    satellite_pd_features,
    satellite_pd_champion
)

summary_df.to_csv("outputs/results/stress_ecl_summary.csv")
`, [
    ["Pourquoi ce moteur ?", "Il applique le choc à PD, LGD et EAD, puis mesure le lift ECL."],
    ["Pourquoi plusieurs scénarios ?", "Tester adverse, severe, taux, marche 2018, crise 2008 et COVID-19."],
    ["Outputs", "stress_ecl_summary.csv, stress_validation_report.csv, fig_26 à fig_30."],
  ], C.red);
  bulletSlide(pptx, "Premier stress", "Pourquoi ces méthodes et ces outputs", [
    ["PD models", "Le scoring PD donne le risque individuel avant stress."],
    ["SHAP", "Rend le modèle défendable devant un jury ou un régulateur."],
    ["Satellite macro", "Relie explicitement chômage, PIB, taux et spread aux défauts."],
    ["Stress summary", "Table de décision: ECL stressée, lift, PD/LGD/EAD stressés."],
    ["Figures stress", "Montrent visuellement quel choc augmente le plus les pertes."],
  ], C.navy);
  await imageSlide(pptx, "Premier stress", "Résultat du premier stress", "Impact ECL et décomposition PD/LGD/EAD", ["fig_26_stress_ecl_comparison.png", "fig_27_components_stress.png"], "Cette partie n'est pas du forward-looking: elle mesure l'impact direct des chocs stressés.", C.red);
  bulletSlide(pptx, "Premier stress", "Transition vers la suite expert", [
    ["Limite", "Un seul moteur de stress ne suffit pas pour un dispositif expert."],
    ["Amélioration ajoutée", "Comparaison de plusieurs moteurs: déterministe, satellite, Markov, ML challenger et hybride."],
    ["Champion", "Le meilleur modèle est retenu par scoring: backtesting, cohérence économique, stabilité, précision ECL, interprétabilité."],
    ["Suite logique", "Présenter stress_model_comparison.csv comme preuve de sélection du modèle champion."],
  ], C.navy);
  const stressCmp = csvRows(path.join(RES, "stress_model_comparison.csv")).slice(0, 6)
    .map(r => [r.model_name, r.final_score, r.ECL_lift, r.economic_coherent]);
  if (stressCmp.length) {
    tableSlide(pptx, "Premier stress", "Comparaison des moteurs dans l'application", "Le dashboard affiche le scoring et le champion retenu", ["Moteur", "Score", "ECL lift", "Cohérent"], stressCmp, C.navy);
  }
  const out = path.join(DECK_DIR, "03_Presentation_Modelisation_StressTesting.pptx");
  await pptx.writeFile({ fileName: out });
  return out;
}

(async () => {
  const decks = [];
  decks.push(await buildEdaDeck());
  decks.push(await buildPreprocessingDeck());
  decks.push(await buildModelDeck());
  console.log(decks.join("\n"));
})();
