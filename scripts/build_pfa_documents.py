from __future__ import annotations

import ast
import csv
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "documents"
RESULTS = ROOT / "outputs" / "results"
FIGS = ROOT / "outputs"


ACCENT = RGBColor(31, 78, 121)
MUTED = RGBColor(91, 103, 112)
LIGHT_BLUE = "D9EAF7"
LIGHT_GRAY = "F2F4F7"
LIGHT_GREEN = "E2F0D9"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: str, bold: bool = False, color: RGBColor | None = None, size: float = 8.5) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(str(text))
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def keep_row_together(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_table_fixed(table) -> None:
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)


def set_cell_width(cell, width_cm: float) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.first_child_found_in("w:tcW")
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def style_doc(doc: Document, landscape: bool = False) -> None:
    sec = doc.sections[0]
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    sec.top_margin = Cm(1.8)
    sec.bottom_margin = Cm(1.7)
    sec.left_margin = Cm(1.8)
    sec.right_margin = Cm(1.8)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Aptos")
    normal.font.size = Pt(10.2)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.08

    for name, size in [("Title", 22), ("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11)]:
        style = styles[name]
        style.font.name = "Aptos Display" if name != "Heading 3" else "Aptos"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), style.font.name)
        style.font.size = Pt(size)
        style.font.color.rgb = ACCENT
        style.font.bold = True
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)


def add_cover(doc: Document, title: str, subtitle: str, kind: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(90)
    r = p.add_run(title)
    r.font.name = "Aptos Display"
    r.font.size = Pt(24)
    r.font.bold = True
    r.font.color.rgb = ACCENT

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(subtitle)
    r.font.size = Pt(13)
    r.font.color.rgb = MUTED

    table = doc.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    table.autofit = True
    rows = [
        ("Projet", "Moteur IFRS 9 de stress testing bancaire"),
        ("Type de document", kind),
        ("Source", "Code, notebooks, sorties et rapports du projet Far7ti"),
        ("Date", date.today().isoformat()),
    ]
    for row, (k, v) in zip(table.rows, rows):
        set_cell_text(row.cells[0], k, bold=True, color=ACCENT)
        set_cell_shading(row.cells[0], LIGHT_BLUE)
        set_cell_text(row.cells[1], v)
    doc.add_page_break()


def add_toc_placeholder(doc: Document) -> None:
    doc.add_heading("Sommaire", level=1)
    p = doc.add_paragraph()
    p.add_run("Astuce : dans Microsoft Word, clic droit sur le sommaire puis ")
    p.add_run("Mettre a jour le champ").bold = True
    p.add_run(" pour generer automatiquement les numeros de pages.")
    doc.add_paragraph("1. Introduction generale")
    doc.add_paragraph("2. Cadre theorique")
    doc.add_paragraph("3. Donnees et architecture")
    doc.add_paragraph("4. Analyse exploratoire et preprocessing")
    doc.add_paragraph("5. Modelisation IFRS 9")
    doc.add_paragraph("6. Stress testing et resilience")
    doc.add_paragraph("7. Dashboard et validation")
    doc.add_paragraph("8. Conclusion et annexes")
    doc.add_page_break()


def add_note(doc: Document, title: str, text: str, fill: str = LIGHT_GRAY) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    p = cell.paragraphs[0]
    r = p.add_run(title + " : ")
    r.bold = True
    r.font.color.rgb = ACCENT
    r.font.size = Pt(10)
    rr = p.add_run(text)
    rr.font.size = Pt(9.5)


def add_csv_table(doc: Document, title: str, csv_path: Path, max_rows: int = 8) -> None:
    if not csv_path.exists():
        return
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    doc.add_heading(title, level=3)
    header, data = rows[0], rows[1 : max_rows + 1]
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    for cell, value in zip(table.rows[0].cells, header):
        set_cell_text(cell, value, bold=True, color=ACCENT)
        set_cell_shading(cell, LIGHT_BLUE)
    for row_data in data:
        cells = table.add_row().cells
        for cell, value in zip(cells, row_data):
            set_cell_text(cell, value[:180])
    doc.add_paragraph()


def add_figure(doc: Document, filename: str, caption: str, width_cm: float = 13.5) -> None:
    path = FIGS / filename
    if not path.exists():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    cap = doc.add_paragraph(caption)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.runs[0].italic = True
    cap.runs[0].font.size = Pt(8.5)
    cap.runs[0].font.color.rgb = MUTED


def read_md_excerpt(path: Path, max_chars: int = 2200) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\|.*\|\n", "", text)
    text = re.sub(r"#+\s*", "", text)
    return text[:max_chars].strip()


def build_report() -> Path:
    doc = Document()
    style_doc(doc)
    add_cover(
        doc,
        "Rapport PFA",
        "Conception et developpement d'un moteur IFRS 9 de stress testing bancaire",
        "Rapport academique",
    )
    add_toc_placeholder(doc)

    doc.add_heading("Introduction Generale", level=1)
    doc.add_paragraph(
        "Le secteur bancaire est expose a un risque de credit qui evolue avec la qualite des emprunteurs, "
        "les conditions macroeconomiques et les exigences prudentielles. La norme IFRS 9 impose une logique "
        "prospective de provisionnement basee sur les pertes de credit attendues, ou Expected Credit Loss."
    )
    doc.add_paragraph(
        "Ce projet vise a construire un moteur analytique complet permettant de preparer un portefeuille de credit, "
        "d'estimer les composantes PD, LGD et EAD, de calculer une ECL baseline, de projeter des scenarios macroeconomiques "
        "de stress et d'evaluer l'impact sur les pertes attendues et le ratio CET1."
    )
    add_note(
        doc,
        "Problematique",
        "Comment transformer des donnees de credit et des variables macroeconomiques en un dispositif IFRS 9 capable "
        "de mesurer l'ECL, de tester des scenarios de crise et d'interpreter la resilience du capital bancaire ?",
        LIGHT_BLUE,
    )

    doc.add_heading("Cadre Theorique et Reglementaire", level=1)
    for title, text in [
        ("Risque de credit", "Le risque de credit correspond a la possibilite qu'un emprunteur ne rembourse pas ses obligations contractuelles. Il se materialise par une probabilite de defaut, une perte en cas de defaut et une exposition au moment du defaut."),
        ("IFRS 9", "IFRS 9 remplace une logique de pertes encourues par une logique de pertes attendues. L'ECL combine PD, LGD et EAD, avec une dimension forward-looking fondee sur plusieurs scenarios economiques."),
        ("Stress testing", "Le stress testing consiste a appliquer des chocs economiques defavorables afin de mesurer la sensibilite d'un portefeuille et la robustesse du capital."),
        ("CET1", "Le ratio CET1 mesure le capital de meilleure qualite rapporte aux actifs ponderes par les risques. Dans ce projet, il sert a interpreter l'absorption des pertes additionnelles de stress."),
    ]:
        doc.add_heading(title, level=2)
        doc.add_paragraph(text)

    doc.add_heading("Presentation du Projet et des Donnees", level=1)
    doc.add_paragraph(
        "Le projet est organise autour de notebooks sequentiels, de modules Python reutilisables, de scripts de validation, "
        "de sorties auditables et d'un dashboard Streamlit. Les donnees de credit proviennent du portefeuille Lending Club, "
        "tandis que les variables macroeconomiques sont issues de FRED."
    )
    add_csv_table(doc, "Dictionnaire des variables macroeconomiques", RESULTS / "fred_variable_dictionary.csv", 10)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, val in zip(table.rows[0].cells, ["Composant", "Role", "Livrables"]):
        set_cell_text(cell, val, bold=True, color=ACCENT)
        set_cell_shading(cell, LIGHT_BLUE)
    rows = [
        ("notebooks", "Experimentation et narration analytique", "01_EDA a 07_Validation_Avancee"),
        ("src", "Code industrialise", "preprocessing, ECL, satellites, stress, resilience"),
        ("scripts", "Generation et validation", "rapports CSV/Markdown, tests metier"),
        ("dashboard", "Restitution interactive", "application Streamlit"),
        ("outputs", "Traçabilite", "figures, tableaux, rapports et presentations"),
    ]
    for vals in rows:
        cells = table.add_row().cells
        for cell, val in zip(cells, vals):
            set_cell_text(cell, val)

    doc.add_heading("Analyse Exploratoire des Donnees", level=1)
    doc.add_paragraph(
        "L'EDA analyse la cible de defaut, les montants de prets, la segmentation par grade, les valeurs manquantes, "
        "les correlations et la dynamique temporelle du defaut. Cette etape permet de detecter les risques de biais, "
        "de comprendre la distribution du portefeuille et de preparer les choix de preprocessing."
    )
    add_figure(doc, "fig_01_loan_status.png", "Figure 1 - Distribution des statuts de pret.")
    add_figure(doc, "fig_04_default_by_grade.png", "Figure 2 - Taux de defaut par grade.")
    add_figure(doc, "fig_09_correlation_matrix.png", "Figure 3 - Matrice de correlation.")

    doc.add_heading("Preprocessing et Construction du Dataset", level=1)
    doc.add_paragraph(
        "Le preprocessing transforme les donnees brutes en un dataset exploitable pour la modelisation. Il inclut la selection "
        "des variables, le nettoyage, la gestion des valeurs manquantes, l'encodage, la creation de variables metier et la fusion macroeconomique."
    )
    add_csv_table(doc, "Audit preprocessing", RESULTS / "preprocessing_audit.csv")
    add_csv_table(doc, "Synthese des outliers", RESULTS / "outlier_summary.csv")

    doc.add_heading("Modelisation Baseline IFRS 9", level=1)
    doc.add_paragraph(
        "La baseline IFRS 9 estime la probabilite de defaut individuelle et calcule l'ECL initiale. Plusieurs modeles sont compares "
        "sur des metriques de discrimination, calibration et stabilite."
    )
    add_csv_table(doc, "Comparaison des modeles PD", RESULTS / "pd_model_comparison.csv", 10)
    add_figure(doc, "fig_13_model_comparison.png", "Figure 4 - Comparaison des modeles PD.")
    add_figure(doc, "fig_19_ecl_baseline.png", "Figure 5 - ECL baseline.")

    doc.add_heading("Modeles Satellites Macro", level=1)
    doc.add_paragraph(
        "Les modeles satellites relient le taux de defaut aux variables macroeconomiques afin de transformer un scenario economique "
        "en trajectoire de risque. Le projet compare des approches lineaires et non lineaires, puis valide leur coherence economique."
    )
    add_csv_table(doc, "Comparaison des modeles satellites", RESULTS / "stress_model_comparison.csv", 8)
    add_figure(doc, "fig_22_satellite_pd_comparison.png", "Figure 6 - Comparaison satellite PD.")
    add_figure(doc, "fig_15_walk_forward.png", "Figure 7 - Backtesting walk-forward.")

    doc.add_heading("Stress Testing IFRS 9", level=1)
    doc.add_paragraph(
        "Le stress testing applique differents scenarios : adverse, severe, choc de taux, choc marche 2018, crise 2008 et COVID-19. "
        "Chaque scenario modifie les facteurs de risque, puis les effets sont traduits sur la PD, la LGD, l'EAD et l'ECL."
    )
    add_csv_table(doc, "Resultats ECL stresses", RESULTS / "stress_ecl_summary.csv", 10)
    add_csv_table(doc, "Validation des scenarios", RESULTS / "scenario_design_validation.csv", 10)
    add_figure(doc, "fig_26_stress_ecl_comparison.png", "Figure 8 - Comparaison des ECL stressees.")
    add_figure(doc, "fig_29_stage_migration.png", "Figure 9 - Migration des stages IFRS 9.")

    doc.add_heading("Validation Avancee", level=1)
    doc.add_paragraph(
        "La validation avancee verifie que les scenarios sont economiquement adverses, que les sorties respectent les contraintes metier "
        "et que le choix du moteur champion repose sur un score multi-criteres."
    )
    add_csv_table(doc, "Champion stress testing", RESULTS / "stress_model_champion.csv")
    add_csv_table(doc, "Migration Markov", RESULTS / "stage_migration_markov_summary.csv", 10)
    add_note(
        doc,
        "Interpretation",
        "Le projet ne retient pas uniquement le modele le plus severe. Le moteur champion est selectionne selon un compromis entre coherence economique, precision, stabilite temporelle et interpretabilite.",
        LIGHT_GREEN,
    )

    doc.add_heading("Resilience CET1 et Reverse Stress Test", level=1)
    doc.add_paragraph(
        "L'analyse de resilience convertit les pertes additionnelles en impact capital. Elle permet d'identifier les scenarios ou le ratio CET1 "
        "reste au-dessus des seuils prudentiels et ceux qui conduisent a une zone critique."
    )
    add_csv_table(doc, "Table de resilience CET1", RESULTS / "cet1_resilience_table.csv", 10)
    add_csv_table(doc, "Reverse stress test", RESULTS / "reverse_stress_test.csv", 5)
    add_figure(doc, "fig_31_cet1_scenarios.png", "Figure 10 - CET1 apres stress.")
    add_figure(doc, "fig_32_resilience_curve.png", "Figure 11 - Courbe de resilience.")

    doc.add_heading("Dashboard Streamlit", level=1)
    doc.add_paragraph(
        "Le dashboard centralise les resultats du projet sous forme interactive. Il facilite la demonstration et la lecture metier : "
        "portefeuille, ECL baseline, scenarios de stress, resilience CET1 et controles de validation."
    )
    add_note(doc, "Point de demonstration", "Avant la soutenance, installer streamlit, plotly, pyarrow et joblib puis lancer streamlit run dashboard/app.py.", LIGHT_BLUE)

    doc.add_heading("Evaluation et Limites", level=1)
    doc.add_paragraph(read_md_excerpt(RESULTS / "project_evaluation.md", 1800))
    doc.add_paragraph(
        "Les principales limites concernent les hypotheses pedagogiques de capital/RWA, la validation externe encore limitee et la necessite "
        "de figer les resultats apres une reexecution complete des notebooks."
    )

    doc.add_heading("Conclusion Generale", level=1)
    doc.add_paragraph(
        "Le projet livre une chaine coherente allant de la preparation des donnees au stress testing et a l'interpretation prudentielle. "
        "Il demontre la capacite a combiner data science, risque de credit, IFRS 9, variables macroeconomiques et restitution decisionnelle."
    )
    doc.add_heading("Annexes", level=1)
    doc.add_paragraph("Annexe A - Structure du projet et ordre d'execution des notebooks.")
    doc.add_paragraph("Annexe B - Rapports CSV generes dans outputs/results.")
    doc.add_paragraph("Annexe C - Figures sauvegardees dans outputs.")

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "Rapport_PFA_IFRS9_Stress_Testing.docx"
    doc.save(path)
    return path


def explain_line(line: str, context: str = "") -> tuple[str, str, str]:
    s = line.strip()
    if not s:
        return ("Ligne vide.", "Lisibilite.", "Aucun effet.")
    if s.startswith("#"):
        return ("Commentaire.", "Documente l'intention.", "Ignore a l'execution.")
    if s.startswith(("import ", "from ")):
        return ("Importe une dependance.", "Rend l'API disponible.", "Utilisable ensuite.")
    if s.startswith("def "):
        name = s.split("(")[0].replace("def", "").strip()
        return (f"Declare `{name}`.", "Logique reutilisable.", "Executee lors d'un appel.")
    if s.startswith("class "):
        name = s.split("(")[0].replace("class", "").replace(":", "").strip()
        return (f"Declare `{name}`.", "Structure un objet metier.", "Classe instanciable.")
    if s.startswith("return"):
        return ("Retourne une valeur.", "Transmet le calcul.", "Fin de fonction.")
    if s.startswith(("if ", "elif ")):
        return ("Teste une condition.", "Adapte le flux.", "Bloc execute si vrai.")
    if s.startswith("else"):
        return ("Cas alternatif.", "Couvre le reste.", "Bloc execute sinon.")
    if s.startswith(("for ", "while ")):
        return ("Boucle.", "Repete le traitement.", "Iteration sur elements.")
    if s.startswith(("try:", "except", "finally:")):
        return ("Gestion d'erreur.", "Robustesse.", "Exception traitee.")
    if s.startswith(("with ", "async with ")):
        return ("Contexte gere.", "Libere la ressource.", "Ouverture puis fermeture.")
    if s.startswith(("assert ",)):
        return ("Assertion.", "Controle une hypothese.", "Erreur si faux.")
    if "=" in s and not s.startswith(("==", "!=")):
        left = s.split("=", 1)[0].strip()
        return (f"Met a jour `{left}`.", "Stocke une valeur.", "Reutilisable ensuite.")
    if s.startswith(("st.", "fig.", "px.", "go.")):
        return ("Element visuel.", "Restitution dashboard.", "Affichage utilisateur.")
    if s.startswith(("print(", "console.log")):
        return ("Affichage console.", "Diagnostic.", "Message terminal.")
    if s.startswith(("raise ",)):
        return ("Leve une erreur.", "Signale un cas invalide.", "Execution interrompue.")
    return ("Instruction.", "Logique metier/calcul.", "Etat ou sortie modifie.")


def file_summary(path: Path) -> str:
    name = path.name
    rel = path.relative_to(ROOT).as_posix()
    if "data_prep" in name:
        return "Prepare les donnees Lending Club, controle la qualite, cree les variables metier et fusionne les donnees macro."
    if "ecl_engine" in name:
        return "Calcule les composantes IFRS 9 PD, LGD, EAD et l'ECL baseline."
    if "fred_client" in name:
        return "Recupere et documente les variables macroeconomiques FRED."
    if "satellite" in name:
        return "Construit les modeles satellites reliant cycle macroeconomique et risque de defaut."
    if "stress" in name:
        return "Definit, applique, compare ou valide les scenarios de stress testing."
    if "resilience" in name:
        return "Mesure l'impact des pertes stressees sur le capital CET1 et le reverse stress test."
    if "validation" in name:
        return "Assemble les controles et rapports de validation."
    if rel.startswith("dashboard"):
        return "Application Streamlit de restitution interactive."
    if rel.startswith("tests"):
        return "Tests automatises garantissant la coherence metier."
    return "Script d'orchestration ou de generation de livrables."


def add_code_table(doc: Document, path: Path) -> None:
    rel = path.relative_to(ROOT).as_posix()
    doc.add_heading(rel, level=2)
    doc.add_paragraph(file_summary(path))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines, start=1):
        exp, interest, result = explain_line(line)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1.5)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(f"L{i} ")
        r.bold = True
        r.font.color.rgb = ACCENT
        r.font.size = Pt(7.6)
        code = p.add_run(f"{line[:320] if line else '[ligne vide]'}")
        code.font.name = "Consolas"
        code._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        code.font.size = Pt(7.4)
        meta = p.add_run(f" | Explication: {exp} | Interet: {interest} | Resultat: {result}")
        meta.font.size = Pt(7.4)
        meta.font.color.rgb = MUTED
    doc.add_paragraph()


def add_notebook_summary(doc: Document) -> None:
    doc.add_heading("Guide de lecture des notebooks", level=1)
    notebooks = [
        ("01_EDA.ipynb", "Analyse exploratoire : cible, distributions, defaut par segment, valeurs manquantes, vintage et correlations."),
        ("02_Preprocessing.ipynb", "Nettoyage, encodage, feature engineering, LGD/EAD et fusion macroeconomique."),
        ("03_Baseline_ECL.ipynb", "Comparaison des modeles PD et calcul de l'ECL baseline."),
        ("04_Modeles_Satellites_Macro.ipynb", "Modeles macro-satellites, sensibilites economiques et backtesting walk-forward."),
        ("05_Stress_Testing.ipynb", "Application des scenarios et calcul des ECL stressees."),
        ("06_Resilience_Reverse_Stress.ipynb", "Impact CET1, courbe de resilience et point de rupture."),
        ("07_Stress_Testing_Validation_Avancee.ipynb", "Validation metier, migration Markov, ECL forward-looking et comparaison des moteurs."),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, title in zip(table.rows[0].cells, ["Notebook", "Interet", "Resultat attendu"]):
        set_cell_text(cell, title, bold=True, color=ACCENT)
        set_cell_shading(cell, LIGHT_BLUE)
    for nb, desc in notebooks:
        cells = table.add_row().cells
        set_cell_text(cells[0], nb)
        set_cell_text(cells[1], desc)
        set_cell_text(cells[2], "Produit des figures, tableaux et fichiers reutilises dans le rapport et le dashboard.")


def build_guide() -> Path:
    doc = Document()
    style_doc(doc, landscape=True)
    add_cover(
        doc,
        "Guide Technique Detaille",
        "Explication ligne par ligne du code, interet, resultats et interpretation",
        "Manuel technique",
    )
    doc.add_heading("Mode d'emploi du guide", level=1)
    doc.add_paragraph(
        "Ce document explique les fichiers de code du projet ligne par ligne. Pour chaque ligne, le tableau indique le role technique, "
        "l'interet dans le projet et le resultat attendu. Les lignes tres similaires, comme les affectations ou appels de bibliotheques, "
        "sont interpretees selon leur fonction dans le fichier."
    )
    add_note(
        doc,
        "Important",
        "Le projet contient environ 4 500 lignes de code. Le guide couvre les fichiers Python et JavaScript sources : modules, scripts, dashboard et tests.",
        LIGHT_BLUE,
    )
    add_notebook_summary(doc)

    doc.add_heading("Architecture Fonctionnelle", level=1)
    arch = [
        ("data_prep.py", "Donnees", "Construit un dataset propre et auditable."),
        ("ecl_engine.py", "IFRS 9", "Calcule PD, LGD, EAD et ECL."),
        ("satellite_models.py", "Macro", "Relie les variables economiques au defaut."),
        ("stress_scenarios.py", "Stress", "Applique les scenarios adverses."),
        ("resilience.py", "Capital", "Traduit les pertes en impact CET1."),
        ("dashboard/app.py", "Restitution", "Expose les resultats via Streamlit."),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, title in zip(table.rows[0].cells, ["Fichier", "Bloc metier", "Role"]):
        set_cell_text(cell, title, bold=True, color=ACCENT)
        set_cell_shading(cell, LIGHT_BLUE)
    for vals in arch:
        cells = table.add_row().cells
        for cell, val in zip(cells, vals):
            set_cell_text(cell, val)

    doc.add_heading("Explication Ligne par Ligne", level=1)
    code_files = []
    for folder in ["src", "scripts", "dashboard", "tests"]:
        code_files.extend(sorted((ROOT / folder).rglob("*.py")))
        code_files.extend(sorted((ROOT / folder).rglob("*.js")))
    code_files = [p for p in code_files if "__pycache__" not in p.parts]
    for path in code_files:
        add_code_table(doc, path)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "Guide_Technique_Ligne_Par_Ligne_Projet_IFRS9.docx"
    doc.save(path)
    return path


def main() -> None:
    report = build_report()
    guide = build_guide()
    print(report)
    print(guide)


if __name__ == "__main__":
    main()
