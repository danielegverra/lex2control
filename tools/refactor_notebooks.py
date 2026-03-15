import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_notebook(path: Path) -> dict:
    return json.loads(path.read_text())


def save_notebook(path: Path, notebook: dict) -> None:
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1))


def markdown_cell(text: str) -> dict:
    content = textwrap.dedent(text).strip()
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in content.splitlines()],
    }


def code_cell(text: str) -> dict:
    content = textwrap.dedent(text).strip()
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in content.splitlines()],
    }


def clear_outputs(notebook: dict) -> None:
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["execution_count"] = None
            cell["outputs"] = []


def build_phase1_cells() -> list:
    return [
        markdown_cell(
            """
            ## NIST preprocessing

            Pipeline note:
            - this notebook produces the canonical NIST artifact for the matching pipeline
            - the only pipeline output is `nist_controls_svo_v2_with_family.csv`
            - diagnostics are written separately under `diagnostics/`
            """
        ),
        markdown_cell("📌 1. Setup runtime and shared paths"),
        code_cell(
            """
            import importlib
            import json
            import re
            import subprocess
            import sys
            from pathlib import Path

            REQUIRED_PACKAGES = [
                ("pandas", "pandas"),
                ("requests", "requests"),
                ("openpyxl", "openpyxl"),
                ("spacy", "spacy"),
            ]

            for module_name, package_name in REQUIRED_PACKAGES:
                try:
                    importlib.import_module(module_name)
                except ModuleNotFoundError:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", "-q", package_name]
                    )

            MODEL_NAME = "en_core_web_md"
            try:
                importlib.import_module(MODEL_NAME)
            except ModuleNotFoundError:
                subprocess.check_call(
                    [sys.executable, "-m", "spacy", "download", MODEL_NAME]
                )

            import pandas as pd
            import requests
            import spacy

            BASE_DIR = Path.cwd()
            RAW_XLSX = BASE_DIR / "sp800-53r5-control-catalog.xlsx"
            CANONICAL_OUTPUT = BASE_DIR / "nist_controls_svo_v2_with_family.csv"
            DIAGNOSTICS_DIR = BASE_DIR / "diagnostics"
            DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)

            nlp = spacy.load(MODEL_NAME)
            nlp.max_length = 2_000_000

            print(f"✅ Base directory: {BASE_DIR}")
            print(f"✅ Canonical output: {CANONICAL_OUTPUT.name}")
            print(f"✅ Diagnostics directory: {DIAGNOSTICS_DIR}")
            """
        ),
        markdown_cell("📌 2. Download the NIST catalog with validation and local fallback"),
        code_cell(
            """
            DOWNLOAD_URLS = [
                "https://csrc.nist.gov/files/pubs/sp/800/53/r5/upd1/final/docs/sp800-53r5-control-catalog.xlsx",
            ]

            def validate_catalog(path: Path) -> bool:
                try:
                    workbook = pd.ExcelFile(path)
                except Exception:
                    return False
                return bool(workbook.sheet_names)

            def download_catalog(target: Path, urls: list[str]) -> Path:
                errors = []
                session = requests.Session()
                session.headers.update({"User-Agent": "lex2control-phase1/1.0"})

                for url in urls:
                    tmp_path = target.with_suffix(".tmp")
                    try:
                        with session.get(url, stream=True, timeout=(15, 180)) as response:
                            response.raise_for_status()
                            with tmp_path.open("wb") as handle:
                                for chunk in response.iter_content(chunk_size=1024 * 256):
                                    if chunk:
                                        handle.write(chunk)

                        if not validate_catalog(tmp_path):
                            raise ValueError("downloaded file is not a valid Excel workbook")

                        tmp_path.replace(target)
                        print(f"✅ Downloaded catalog from: {url}")
                        return target
                    except Exception as exc:
                        errors.append(f"{url} -> {exc}")
                        if tmp_path.exists():
                            tmp_path.unlink()

                if target.exists() and validate_catalog(target):
                    print("⚠️ Download failed; using existing validated local workbook.")
                    for err in errors:
                        print("   ", err)
                    return target

                raise RuntimeError("Unable to obtain a valid NIST catalog workbook.\\n" + "\\n".join(errors))

            catalog_path = download_catalog(RAW_XLSX, DOWNLOAD_URLS)
            print(f"✅ Workbook ready at: {catalog_path}")
            """
        ),
        markdown_cell("📌 3. Load controls and apply controlled text normalization"),
        code_cell(
            """
            REQUIRED_SOURCE_COLUMNS = [
                "Control Identifier",
                "Control (or Control Enhancement) Name",
                "Control Text",
            ]

            def load_controls_frame(path: Path) -> pd.DataFrame:
                workbook = pd.ExcelFile(path)

                for sheet_name in workbook.sheet_names:
                    candidate = pd.read_excel(path, sheet_name=sheet_name)
                    if set(REQUIRED_SOURCE_COLUMNS).issubset(candidate.columns):
                        return candidate

                raise ValueError("No worksheet contains the required NIST control columns.")

            def normalize_control_text(text: str) -> str:
                cleaned = str(text)
                cleaned = cleaned.replace("\\r", " ").replace("\\n", " ")
                cleaned = cleaned.replace("\\u00a0", " ")
                cleaned = cleaned.replace("\\u2013", "-").replace("\\u2014", "-")
                cleaned = re.sub(r"\\s+", " ", cleaned)
                cleaned = re.sub(r"\\s+([,;:.])", r"\\1", cleaned)
                return cleaned.strip()

            df_raw = load_controls_frame(catalog_path)
            df = (
                df_raw[REQUIRED_SOURCE_COLUMNS]
                .rename(
                    columns={
                        "Control Identifier": "Control ID",
                        "Control (or Control Enhancement) Name": "Control Name",
                    }
                )
                .dropna(subset=["Control Text"])
                .copy()
            )

            for column in ["Control ID", "Control Name", "Control Text"]:
                df[column] = df[column].astype(str).str.strip()

            df = df[df["Control ID"] != ""].reset_index(drop=True)
            df["Cleaned Text"] = df["Control Text"].map(normalize_control_text)
            df = df[df["Cleaned Text"].str.len() > 5].reset_index(drop=True)

            print(f"✅ Loaded {len(df)} NIST controls after normalization.")
            df.head()
            """
        ),
        markdown_cell("📌 4. Extract SVO v2 features and assign control families"),
        code_cell(
            """
            FAMILY_LABELS = {
                "AC": "Access Control",
                "AT": "Awareness and Training",
                "AU": "Audit and Accountability",
                "CA": "Assessment, Authorization, and Monitoring",
                "CM": "Configuration Management",
                "CP": "Contingency Planning",
                "IA": "Identification and Authentication",
                "IR": "Incident Response",
                "MA": "Maintenance",
                "MAP": "Program Management",
                "MEDIA": "Media Protection",
                "MP": "Media Protection",
                "PE": "Physical and Environmental Protection",
                "PL": "Planning",
                "PM": "Program Management",
                "PS": "Personnel Security",
                "PT": "Personally Identifiable Information Processing and Transparency",
                "RA": "Risk Assessment",
                "SA": "System and Services Acquisition",
                "SC": "System and Communications Protection",
                "SI": "System and Information Integrity",
                "SR": "Supply Chain Risk Management",
            }

            SUBJECT_DEPS = {"nsubj", "nsubjpass", "csubj", "expl"}
            OBJECT_DEPS = {"dobj", "obj", "pobj", "attr", "dative", "oprd"}
            VERB_POS = {"VERB", "AUX"}

            def ordered_unique(values: list[str]) -> list[str]:
                seen = set()
                ordered = []
                for value in values:
                    candidate = value.strip()
                    if candidate and candidate not in seen:
                        seen.add(candidate)
                        ordered.append(candidate)
                return ordered

            def span_text(token) -> str:
                return " ".join(part.text for part in token.subtree).strip()

            def extract_svo_v2(text: str) -> pd.Series:
                doc = nlp(text)

                subjects = []
                verbs = []
                objects = []
                noun_chunks = ordered_unique([chunk.text.strip() for chunk in doc.noun_chunks])

                explicit_subject_present = any(token.dep_ in SUBJECT_DEPS for token in doc)

                for token in doc:
                    if token.pos_ not in VERB_POS:
                        continue
                    if token.dep_ == "aux" and token.head.pos_ == "VERB":
                        continue

                    token_subjects = []
                    token_objects = []

                    for child in token.children:
                        if child.dep_ in SUBJECT_DEPS:
                            token_subjects.append(span_text(child))
                        elif child.dep_ in OBJECT_DEPS:
                            token_objects.append(span_text(child))
                        elif child.dep_ == "prep":
                            for grandchild in child.children:
                                if grandchild.dep_ == "pobj":
                                    token_objects.append(span_text(grandchild))

                    if (
                        not token_subjects
                        and not explicit_subject_present
                        and token.dep_ == "ROOT"
                        and token.tag_ in {"VB", "VBP"}
                    ):
                        token_subjects.append("organization")

                    if token_subjects or token_objects:
                        lemma = token.lemma_.lower().strip()
                        if lemma:
                            verbs.append(lemma)

                    subjects.extend(token_subjects)
                    objects.extend(token_objects)

                return pd.Series(
                    {
                        "Subjects": ordered_unique(subjects),
                        "Verbs": ordered_unique(verbs),
                        "Objects": ordered_unique(objects),
                        "Noun Chunks": noun_chunks,
                    }
                )

            def tag_control_family(control_id: str) -> str:
                family_code = control_id.split("-", 1)[0].strip().upper()
                return FAMILY_LABELS.get(family_code, "Unknown")

            svo_features = df["Cleaned Text"].apply(extract_svo_v2)
            df_final = pd.concat([df, svo_features], axis=1)
            df_final["Control Family"] = df_final["Control ID"].map(tag_control_family)

            df_final = df_final[
                [
                    "Control ID",
                    "Control Name",
                    "Control Text",
                    "Cleaned Text",
                    "Subjects",
                    "Verbs",
                    "Objects",
                    "Noun Chunks",
                    "Control Family",
                ]
            ].copy()

            df_final.to_csv(CANONICAL_OUTPUT, index=False)
            print(f"✅ Saved canonical Phase 1 output to: {CANONICAL_OUTPUT.name}")
            df_final.head()
            """
        ),
        markdown_cell("📌 5. Generate diagnostics without creating extra pipeline artifacts"),
        code_cell(
            """
            family_counts = (
                df_final["Control Family"]
                .value_counts(dropna=False)
                .rename_axis("Control Family")
                .reset_index(name="Count")
                .sort_values(["Count", "Control Family"], ascending=[False, True])
            )

            diagnostics_summary = {
                "controls": int(len(df_final)),
                "unique_control_ids": int(df_final["Control ID"].nunique()),
                "empty_cleaned_text": int(df_final["Cleaned Text"].eq("").sum()),
                "controls_with_subjects": int(df_final["Subjects"].map(len).gt(0).sum()),
                "controls_with_verbs": int(df_final["Verbs"].map(len).gt(0).sum()),
                "controls_with_objects": int(df_final["Objects"].map(len).gt(0).sum()),
                "controls_with_noun_chunks": int(df_final["Noun Chunks"].map(len).gt(0).sum()),
                "unknown_family_labels": int(df_final["Control Family"].eq("Unknown").sum()),
            }

            family_counts_path = DIAGNOSTICS_DIR / "nist_phase1_family_counts.csv"
            summary_path = DIAGNOSTICS_DIR / "nist_phase1_summary.json"

            family_counts.to_csv(family_counts_path, index=False)
            summary_path.write_text(json.dumps(diagnostics_summary, indent=2))

            print(f"✅ Saved diagnostics summary to: {summary_path}")
            print(f"✅ Saved family counts to: {family_counts_path}")
            print(json.dumps(diagnostics_summary, indent=2))
            family_counts.head(10)
            """
        ),
    ]


def refactor_phase1() -> None:
    path = ROOT / "Phase 1_ NIST Rule Extraction.ipynb"
    notebook = load_notebook(path)
    notebook["cells"] = build_phase1_cells()
    clear_outputs(notebook)
    save_notebook(path, notebook)


def refactor_phase2() -> None:
    path = ROOT / "Phase 2_ NIS2 Rule Extraction.ipynb"
    notebook = load_notebook(path)
    cells = notebook["cells"]

    cells[0]["source"] = [
        "## NIS2 preprocessing\n",
        "\n",
        "Pipeline note:\n",
        "- canonical classifier for technical requirements: `all-mpnet-base-v2`\n",
        "- semantic matching is implemented in Phase 3\n",
        "- MiniLM and SVO-based matching below are retained as baselines / exploratory experiments\n",
    ]
    cells[4]["source"] = ["📌 3. Clean and normalize NIS2 requirement text\n"]
    cells[6]["source"] = ["📌 4a. Baseline classifier: remove non-technical requirements with MiniLM-L6\n"]
    cells[9]["source"] = ["📌 4b. Canonical classifier: remove non-technical requirements with MPNet\n"]
    cells[13]["source"] = ["📌 5. Baseline feature extraction: Legal-BERT + spaCy SVO features\n"]
    cells[16]["source"] = ["📌 6. Tag NIS2 requirements with Control Family\n"]
    cells[18]["source"] = ["📌 7. Baseline experiment: SVO-based matching\n"]
    cells[20]["source"] = ["📌 8. Baseline refinement: weighted SVO matching\n"]
    cells[22]["source"] = ["📌 9. Baseline diagnostics\n"]
    cells[25]["source"] = ["📌 10. Baseline plots\n"]

    cells[8]["source"] = [
        "# Filter technical articles from the MiniLM baseline\n",
        "df_technical = df_pred[df_pred[\"Category\"] == \"technical\"]\n",
        "\n",
        "# Save with an explicit baseline name to avoid confusion with the canonical MPNet output\n",
        "df_technical.to_csv(\"nis2_only_technical_minilm.csv\", index=False)\n",
        "print(\"✅ Saved MiniLM baseline output as 'nis2_only_technical_minilm.csv'.\")\n",
    ]

    cells[12]["source"] = [
        "# Filter technical articles from the canonical MPNet classifier\n",
        "df_technical = df_pred[df_pred[\"Category\"] == \"technical\"]\n",
        "\n",
        "# Save the official input for Phase 3 semantic matching\n",
        "df_technical.to_csv(\"nis2_only_technical_mpnet.csv\", index=False)\n",
        "print(\"✅ Saved canonical technical requirements as 'nis2_only_technical_mpnet.csv'.\")\n",
    ]

    # Remove unsupported claims and obsolete notes.
    cells[27]["source"] = [
        "Baseline diagnostic note:\n",
        "- the plots below describe the weighted SVO experiment only\n",
        "- they must not be presented as validation of the final semantic pipeline without manual benchmarking\n",
    ]
    cells[29]["source"] = [
        "Note:\n",
        "- semantic similarity is the final matching strategy and is implemented in Phase 3\n",
        "- keep SVO results as comparison material, not as the primary thesis outcome\n",
    ]

    clear_outputs(notebook)
    save_notebook(path, notebook)


def build_phase3_cells() -> list:
    return [
        markdown_cell(
            """
            ## NIS2-NIST semantic matching

            Pipeline note:
            - this notebook is the canonical matching phase
            - input technical requirements come from `nis2_only_technical_mpnet.csv`
            - the final mapping method is embedding-based semantic similarity with E5
            """
        ),
        code_cell(
            """
            !pip install -q sentence-transformers umap-learn
            """
        ),
        markdown_cell("📌 1. Load NIS2 and NIST datasets"),
        code_cell(
            """
            import pandas as pd

            df_nis2 = pd.read_csv("nis2_only_technical_mpnet.csv")
            df_nist = pd.read_csv("nist_controls_svo_v2_with_family.csv")

            print(f"✅ Loaded {len(df_nis2)} technical NIS2 requirements")
            print(f"✅ Loaded {len(df_nist)} NIST controls")
            """
        ),
        markdown_cell("📌 2. Generate E5 embeddings"),
        code_cell(
            """
            from sentence_transformers import SentenceTransformer

            model_name = "intfloat/e5-large"
            model = SentenceTransformer(model_name)
            print(f"✅ Loaded model: {model_name}")

            nis2_texts = ["passage: " + text.strip() for text in df_nis2["Cleaned Requirement"]]
            nist_texts = ["passage: " + text.strip() for text in df_nist["Cleaned Text"]]

            nis2_embeddings = model.encode(
                nis2_texts,
                batch_size=16,
                show_progress_bar=True,
                convert_to_tensor=True,
            )
            nist_embeddings = model.encode(
                nist_texts,
                batch_size=16,
                show_progress_bar=True,
                convert_to_tensor=True,
            )

            print("✅ Embeddings generated for NIS2 and NIST datasets.")
            """
        ),
        markdown_cell("📌 3. Save embeddings for reuse"),
        code_cell(
            """
            import numpy as np

            np.save("nis2_embeddings_e5.npy", nis2_embeddings.cpu().numpy())
            np.save("nist_embeddings_e5.npy", nist_embeddings.cpu().numpy())

            print("✅ Embeddings saved to 'nis2_embeddings_e5.npy' and 'nist_embeddings_e5.npy'.")
            """
        ),
        markdown_cell("📌 4. Perform semantic similarity matching"),
        code_cell(
            """
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            SIM_THRESHOLD = 0.83  # to be validated on a labelled sample

            nis2_emb = np.load("nis2_embeddings_e5.npy")
            nist_emb = np.load("nist_embeddings_e5.npy")

            results = []

            for i, req_row in df_nis2.iterrows():
                sims = cosine_similarity([nis2_emb[i]], nist_emb)[0]
                matched_idxs = np.where(sims >= SIM_THRESHOLD)[0]

                matched_controls = []
                matched_families = set()

                for idx in matched_idxs:
                    control_id = df_nist.iloc[idx]["Control ID"]
                    family = df_nist.iloc[idx]["Control Family"]
                    score = float(sims[idx])
                    matched_controls.append((control_id, round(score, 4)))
                    matched_families.add(family)

                matched_controls.sort(key=lambda item: item[1], reverse=True)

                results.append({
                    "Req ID": req_row["Req ID"],
                    "Cleaned Requirement": req_row["Cleaned Requirement"],
                    "Matched Controls": matched_controls,
                    "Matched Families": sorted(matched_families),
                })

            df_result = pd.DataFrame(results)
            output_file = "nis2_nist_semantic_matches.csv"
            df_result.to_csv(output_file, index=False)

            print(f"✅ Saved semantic matching results to '{output_file}'.")
            print(df_result.head())
            """
        ),
        markdown_cell("📌 5. Inspect similarity score distribution"),
        code_cell(
            """
            import matplotlib.pyplot as plt

            all_scores = []
            for i in range(len(nis2_emb)):
                sims = cosine_similarity([nis2_emb[i]], nist_emb)[0]
                all_scores.extend(sims.tolist())

            plt.figure(figsize=(8, 4.5))
            plt.hist(all_scores, bins=50, color="steelblue", edgecolor="white")
            plt.axvline(SIM_THRESHOLD, color="red", linestyle="--", label=f"Threshold = {SIM_THRESHOLD}")
            plt.title("Distribution of cosine similarities (NIS2 vs NIST)")
            plt.xlabel("Cosine similarity")
            plt.ylabel("Number of pairs")
            plt.legend()
            plt.tight_layout()
            plt.show()
            """
        ),
        markdown_cell("📌 6. Export simplified mapping (Article -> Control IDs)"),
        code_cell(
            """
            import ast

            df_simple = df_result[["Req ID", "Matched Controls"]].copy()

            def extract_control_ids(value):
                matches = value if isinstance(value, list) else ast.literal_eval(value)
                return ", ".join(control_id for control_id, _ in matches)

            df_simple["Control IDs"] = df_simple["Matched Controls"].apply(extract_control_ids)
            df_simple[["Req ID", "Control IDs"]].to_csv("e5_nis2_to_nist_control_ids.csv", index=False)

            print("✅ Saved simplified mapping to 'e5_nis2_to_nist_control_ids.csv'.")
            """
        ),
        markdown_cell("📌 7. Visualize embedding space"),
        code_cell(
            """
            import numpy as np
            import matplotlib.pyplot as plt
            from pathlib import Path

            images_dir = Path("images")
            images_dir.mkdir(parents=True, exist_ok=True)

            x_nis2 = np.load("nis2_embeddings_e5.npy")
            x_nist = np.load("nist_embeddings_e5.npy")

            x = np.vstack([x_nis2, x_nist])
            y = np.array(["NIS2"] * len(x_nis2) + ["NIST"] * len(x_nist))

            try:
                import umap

                reducer = umap.UMAP(
                    n_neighbors=15,
                    min_dist=0.1,
                    metric="cosine",
                    random_state=42,
                )
                emb2d = reducer.fit_transform(x)
                method = "UMAP"
            except Exception:
                from sklearn.manifold import TSNE

                reducer = TSNE(
                    n_components=2,
                    perplexity=30,
                    metric="cosine",
                    random_state=42,
                )
                emb2d = reducer.fit_transform(x)
                method = "t-SNE"

            fig, ax = plt.subplots(figsize=(7.2, 6))
            for label in ["NIS2", "NIST"]:
                mask = y == label
                ax.scatter(emb2d[mask, 0], emb2d[mask, 1], s=12, alpha=0.7, label=label)

            ax.set_title(f"2D projection of embeddings ({method})")
            ax.set_xlabel("dim 1")
            ax.set_ylabel("dim 2")
            ax.grid(True, linestyle=":", linewidth=0.5)
            ax.legend()

            out = images_dir / "embeddings_2d_projection.png"
            fig.savefig(out, dpi=220, bbox_inches="tight")
            print("✅ Saved:", out)
            plt.show()
            """
        ),
    ]


def refactor_phase3() -> None:
    path = ROOT / "Phase 3_ NIS2-NIST Semantic Matching.ipynb"
    notebook = load_notebook(path)
    notebook["cells"] = build_phase3_cells()
    clear_outputs(notebook)
    save_notebook(path, notebook)


def refactor_phase4() -> None:
    path = ROOT / "Phase 4_ GRC Question Generator.ipynb"
    notebook = load_notebook(path)
    cells = notebook["cells"]

    cells[0]["source"] = [
        "## GRC question generation\n",
        "\n",
        "Pipeline note:\n",
        "- this notebook consumes the canonical semantic matching output `nis2_nist_semantic_matches.csv`\n",
        "- Flan-T5 is used to draft audit questions from the matched NIST controls\n",
    ]

    cells[1]["source"] = [
        "# 📥 Install openpyxl (if not already installed)\n",
        "!pip install -q openpyxl\n",
        "\n",
        "import ast\n",
        "import pandas as pd\n",
        "\n",
        "# 1. Load the canonical NIS2-NIST semantic matching results\n",
        "df_match = pd.read_csv(\"nis2_nist_semantic_matches.csv\")\n",
        "df_match[\"Matched Controls\"] = df_match[\"Matched Controls\"].apply(ast.literal_eval)\n",
        "\n",
        "# 2. Extract unique Control IDs that matched\n",
        "relevant_ids = sorted({\n",
        "    control_id\n",
        "    for matches in df_match[\"Matched Controls\"]\n",
        "    for control_id, _ in matches\n",
        "})\n",
        "\n",
        "# 3. Save to disk for inspection\n",
        "pd.Series(relevant_ids, name=\"Control ID\").to_csv(\"matched_control_ids.csv\", index=False)\n",
        "\n",
        "print(f\"✅ Extracted {len(relevant_ids)} relevant Control IDs to 'matched_control_ids.csv'.\")\n",
    ]

    # Replace fragile string parsing with ast.literal_eval in generation steps.
    for idx in (6, 7):
        source = "".join(cells[idx]["source"])
        source = source.replace('pd.read_csv("nis2_nist_semantic_matches_083.csv")', 'pd.read_csv("nis2_nist_semantic_matches.csv")')
        source = source.replace(
            'relevant_ids = set(df_match["Control ID"].dropna().astype(str))',
            'import ast\nrelevant_ids = {\n    control_id\n    for matches in df_match["Matched Controls"].apply(ast.literal_eval)\n    for control_id, _ in matches\n}'
        )
        cells[idx]["source"] = [line + "\n" for line in source.strip().splitlines()]

    clear_outputs(notebook)
    save_notebook(path, notebook)


def main() -> None:
    refactor_phase1()
    refactor_phase2()
    refactor_phase3()
    refactor_phase4()


if __name__ == "__main__":
    main()
