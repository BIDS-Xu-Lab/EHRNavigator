# EHRNavigator

Patient-level clinical question answering over EHRs. The pipeline queries **structured tables (SQL)** and **unstructured clinical notes**, then synthesizes an evidence-backed answer. Works on MIMIC (MIMIC-III/IV) and OMOP schemas without schema-specific training.

## Pipeline

| Step | File | What it does |
|------|------|--------------|
| 1 | `1_create_database.py` | Build a SQLite DB from CSV files |
| 2 | `2_generate_descriptions.py` | LLM generates a description per table → `sqlite_table_descriptions.json` |
| 3 | `3_rag_qa.ipynb` | RAG Q&A: table retrieval → text-to-SQL (+retry) → structure-aware note retrieval → answer synthesis |
| eval | `4_llm_judge.py` | LLM-as-Judge: grade a model answer against the gold answer by value/meaning |

## Models

- **Backbone LLM**: Azure OpenAI **GPT-4o** (`temperature=0`). Set via env `AZURE_OPENAI_MODEL` / `AZURE_DEPLOYMENT_ID`.
- **Embeddings**: `BAAI/bge-large-en-v1.5` (local, GPU/CPU).
- Table retrieval top-k = 10; notes chunked at 256 tokens / 32 overlap; notes retrieval top-k = 5.
- SQL execution guarded with a 120s timeout; SQL is regenerated (≤3×) on execution error.

## Dataset switch

In `3_rag_qa.ipynb`, one variable picks both the text-to-SQL and answer-synthesis prompts:

```python
DATASET = "ynhhqa"  # "ynhhqa" | "drugehrqa" | "ehrsql" | "ehrnoteqa"
```

- `ehrsql` reuses DrugEHRQA's synthesis prompt.
- `ehrnoteqa` reuses a generic SQL prompt (SQL result may be none) and a notes-based summary prompt.

## Quick start

```bash
pip install -r requirements.txt

python 1_create_database.py          # build DB (edit paths inside)
export OPENAI_API_KEY=...             # for step 2
python 2_generate_descriptions.py    # generate table descriptions

jupyter notebook 3_rag_qa.ipynb      # run Q&A (set Azure vars in the notebook)
```

## Notes

- Note retrieval auto-detects OMOP (`NOTE`/`PERSON_ID`) and MIMIC (`NOTEEVENTS`/`SUBJECT_ID`).
- Vector indexes are cached under `table_index_dir/` and `patient_indexes/`.
