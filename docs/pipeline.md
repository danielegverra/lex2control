# Lex2Control Pipeline

## Obiettivo

Supportare il mapping tra requisiti NIS2 e controlli NIST SP 800-53 per generare un questionario GRC e stimare un livello di compliance.

## Metodo principale

Il metodo principale del progetto e' il `semantic matching`.

Motivazione:

- il parsing sintattico dei testi normativi e' fragile;
- il matching SVO soffre testi lunghi, clausole annidate ed enumerazioni;
- gli embedding semantici sono piu' robusti per trovare controlli NIST pertinenti.

## Baseline / Esperimenti

Il matching SVO e' mantenuto come baseline esplorativa.
Non deve essere presentato come metodo finale se non dopo una validazione comparativa.

## Fase 1: NIST preprocessing

Notebook: `Phase 1_ NIST Rule Extraction.ipynb`

Input:

- download diretto del catalogo NIST in Excel

Output:

- `sp800-53r5-control-catalog.xlsx`
- `nist_controls_svo_v2_with_family.csv`
- `diagnostics/nist_phase1_summary.json`
- `diagnostics/nist_phase1_family_counts.csv`

Scopo:

- estrarre i controlli rilevanti;
- pulire il testo in modo controllato;
- aggiungere solo feature linguistiche SVO v2;
- assegnare la famiglia NIST.

## Fase 2: NIS2 preprocessing

Notebook: `Phase 2_ NIS2 Rule Extraction.ipynb`

Input:

- download HTML della direttiva NIS2
- `nist_controls_svo_v2_with_family.csv`

Output:

- `nis2_directive.html`
- `nis2_requirements_html.csv`
- `nis2_requirements_cleaned.csv`
- `nis2_classified_mpnet.csv`
- `nis2_only_technical_mpnet.csv`
- `nis2_requirements_svo_embedding.csv`
- `nis2_requirements_svo_with_family.csv`
- `nis2_nist_weighted_svo_matching.csv`

Scopo:

- segmentare gli articoli in unita' di requisito;
- pulire il testo;
- classificare i requisiti tecnici;
- produrre una baseline SVO e feature aggiuntive.

## Fase 3: matching semantico finale

Notebook: `Phase 3_ NIS2-NIST Semantic Matching.ipynb`

Input ufficiali:

- `nis2_only_technical_mpnet.csv`
- `nist_controls_svo_v2_with_family.csv`

Output:

- `nis2_embeddings_e5.npy`
- `nist_embeddings_e5.npy`
- `nis2_nist_semantic_matches.csv`
- `e5_nis2_to_nist_control_ids.csv`

Nota:

Il file `nis2_technical_filtered.csv` non e' coerente con gli output prodotti dai notebook precedenti. Va sostituito con `nis2_only_technical_mpnet.csv`.

## Fase 4: generazione questionario

Notebook: `Phase 4_ GRC Question Generator.ipynb`

Input:

- `nis2_nist_semantic_matches.csv` oppure, se dichiarato esplicitamente, `nis2_nist_weighted_svo_matching.csv`
- `sp800-53r5-control-catalog.xlsx`

Output:

- `matched_control_ids.csv`
- `nist_controls_questions_refined_v2.csv`

Decisione consigliata:

Per la pipeline principale usare il matching semantico come sorgente dei controlli rilevanti.

## Fase 5: valutazione compliance

Notebook: `Phase 5_ Evaluation.ipynb`

Input:

- `nist_controls_questions_answers.csv`

Output:

- `nis2_compliance_results.csv`

Nota metodologica:

Il punteggio di compliance attuale e' una semplificazione da presentare come scoring prototipale.

## Fase 6: test e diagnostica

Notebook: `Phase 6_ Testing.ipynb`

Scopo:

- analisi diagnostica delle classificazioni;
- sweep di soglie;
- distribuzioni di similarita';
- grafici di robustezza.

Questa fase non rappresenta test automatici software in senso stretto.

## Criticita' note da correggere

1. Output intermedi con naming incoerente.
2. Celle duplicate e varianti alternative nello stesso notebook.
3. Scelte di modello e soglia non ancora giustificate con benchmark forte.
4. Uso di `eval` da eliminare.
5. Dipendenza da Colab esplicita in piu' punti (`files.download`, `!pip install`).
6. Manca una validazione manuale dei match su un campione annotato.
