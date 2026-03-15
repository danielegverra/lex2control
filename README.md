# Progetto Laurea

Pipeline sperimentale per:

1. estrarre e pulire requisiti NIS2 e controlli NIST SP 800-53;
2. filtrare i contenuti tecnici rilevanti;
3. eseguire il mapping NIS2 -> NIST;
4. generare domande GRC;
5. stimare un punteggio di compliance a partire dalle risposte.

## Stato del progetto

Il repository mantiene i notebook Jupyter come interfaccia principale di lavoro, con esecuzione prevista su Google Colab quando servono GPU e download di modelli.

La pipeline canonica da seguire e documentare in tesi e' questa:

1. `Phase 1_ NIST Rule Extraction.ipynb`
2. `Phase 2_ NIS2 Rule Extraction.ipynb`
3. `Phase 3_ NIS2-NIST Semantic Matching.ipynb`
4. `Phase 4_ GRC Question Generator.ipynb`
5. `Phase 5_ Evaluation.ipynb`
6. `Phase 6_ Testing.ipynb`

Il metodo principale da considerare finale e' il `semantic matching`.
Il `syntactic / SVO matching` resta utile come baseline esplorativa o esperimento preliminare.

## Struttura

- `README.md`: panoramica del progetto e ordine ufficiale di esecuzione.
- `docs/pipeline.md`: definizione della pipeline canonica, input/output e criticita' note.
- `requirements.txt`: dipendenze Python base per l'esecuzione locale o in Colab.
- `.gitignore`: file da non versionare.
- Notebook `.ipynb`: fasi operative della pipeline.

## File intermedi ufficiali

I nomi ufficiali da usare nella documentazione e nelle prossime rifattorizzazioni sono:

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

Nota: alcuni notebook attuali usano ancora nomi non coerenti come `nis2_technical_filtered.csv`. Nelle prossime modifiche questi riferimenti vanno riallineati ai nomi ufficiali sopra.

## Esecuzione su Colab

Linee guida minime:

1. caricare il notebook della fase desiderata;
2. eseguire prima la cella delle dipendenze;
3. verificare sempre input richiesti e output prodotti della fase;
4. non mescolare output di varianti sperimentali con output della pipeline canonica.

## Limiti attuali

- pipeline ancora notebook-driven e non completamente riproducibile;
- presenza di approcci alternativi nello stesso notebook;
- soglie e modelli non ancora consolidati da una validazione forte;
- assenza di una ground truth annotata per valutare il mapping.
