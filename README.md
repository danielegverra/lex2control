# Lex2Control

From NIS2 regulatory text to NIST-aligned compliance controls and GRC questions.

Lex2Control is a notebook-based pipeline for:

1. extracting and cleaning NIS2 requirements and NIST SP 800-53 controls;
2. filtering technical requirements;
3. mapping NIS2 requirements to relevant NIST controls;
4. generating GRC-style assessment questions;
5. estimating a compliance score from questionnaire answers.

## Project scope

The repository keeps Jupyter notebooks as the main execution interface, with Google Colab as the expected environment when GPU-backed model inference is needed.

The canonical thesis pipeline is:

1. `Phase 1_ NIST Rule Extraction.ipynb`
2. `Phase 2_ NIS2 Rule Extraction.ipynb`
3. `Phase 3_ NIS2-NIST Semantic Matching.ipynb`
4. `Phase 4_ GRC Question Generator.ipynb`
5. `Phase 5_ Evaluation.ipynb`
6. `Phase 6_ Testing.ipynb`

The final matching strategy is `semantic matching`.
The `syntactic / SVO matching` flow is retained as a baseline and exploratory comparison.

## Repository contents

- `README.md`: project overview and execution order.
- `docs/pipeline.md`: canonical pipeline, official inputs/outputs, and known issues.
- `requirements.txt`: base Python dependencies for local runs or Colab sessions.
- `.gitignore`: generated files and local artifacts to keep out of version control.
- `tools/refactor_notebooks.py`: helper script used to normalize notebook structure.
- `.ipynb` notebooks: the operational phases of the pipeline.

## Canonical intermediate files

The main outputs currently treated as official are:

- `sp800-53r5-control-catalog.xlsx`
- `nist_controls_cleaned.csv`
- `nist_controls_svo_v2.csv`
- `nist_controls_svo_v2_with_family.csv`
- `nis2_directive.html`
- `nis2_requirements_html.csv`
- `nis2_requirements_cleaned.csv`
- `nis2_only_technical_mpnet.csv`
- `nis2_nist_semantic_matches.csv`
- `matched_control_ids.csv`
- `nist_controls_questions_refined_v2.csv`
- `nist_controls_questions_answers.csv`
- `nis2_compliance_results.csv`

## Running on Colab

Minimal operating rules:

1. open the notebook for the phase you want to run;
2. execute the dependency cell first;
3. verify the required inputs and produced outputs for that phase;
4. keep canonical outputs separate from exploratory notebook variants.

## Current limitations

- the project is still notebook-driven rather than package-driven;
- several methodological choices still need stronger validation;
- there is no labelled gold standard yet for mapping evaluation;
- some phases remain prototypical and should be presented as decision-support, not full automation.
