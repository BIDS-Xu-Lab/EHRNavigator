# RAG Database Pipeline

A complete pipeline for building and querying EHR databases using RAG (Retrieval-Augmented Generation) with BGE embeddings.

## 📁 Directory Structure

```
rag_database_pipeline/
├── 1_create_database.py          # Step 1: Create SQLite database from CSV files
├── 2_generate_descriptions.py    # Step 2: Generate table descriptions using LLM
├── 3_rag_qa.ipynb                # Step 3: RAG Q&A system with BGE embeddings
├── utils/                        # Utility modules
│   ├── db_schema_loader.py       # Auto-load database schema and descriptions
│   └── test_auto_load.py         # Test script for auto-load functionality
├── data/                         # Data directory (symbolic links or actual data)
│   ├── my_database_mimic.db      # SQLite database
│   ├── sqlite_table_descriptions.json  # Table descriptions
│   └── tableinfos/               # Individual table info files
├── cache/                        # Cache directory for indexes
│   └── table_index_dir/          # Vector store indexes
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

Install required packages:

```bash
pip install llama-index
pip install llama-index-embeddings-huggingface
pip install sentence-transformers
pip install torch
pip install sqlalchemy
pip install pandas
pip install openai  # For LLM in description generation
```

### Step 1: Create Database

```bash
python 1_create_database.py
```

This script:
- Reads CSV files from source directory
- Creates SQLite database
- Sanitizes column names
- Creates necessary tables

### Step 2: Generate Descriptions

```bash
python 2_generate_descriptions.py
```

This script:
- Connects to the database
- Inspects all tables and columns
- Uses LLM to generate detailed descriptions
- Saves to `data/sqlite_table_descriptions.json`

**Note**: Set `OPENAI_API_KEY` environment variable before running.

### Step 3: Run RAG Q&A

Open `3_rag_qa.ipynb` in Jupyter and run the cells:

```bash
jupyter notebook 3_rag_qa.ipynb
```

The notebook:
- Auto-loads database schema and descriptions
- Uses **BGE embeddings** (open source, high performance)
- Creates vector indexes for tables
- Retrieves relevant notes for patients
- Generates SQL queries from natural language
- Answers clinical questions with evidence

## 🔧 Configuration

### BGE Embedding Models

The pipeline uses **BGE (BAAI General Embedding)** models. You can choose different model sizes in `3_rag_qa.ipynb` Cell 3:

```python
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-large-en-v1.5",  # Best quality (default)
    # model_name="BAAI/bge-base-en-v1.5",  # Good balance
    # model_name="BAAI/bge-small-en-v1.5",  # Fastest
    device="cuda",  # Use "cuda" for GPU, "cpu" for CPU
    cache_folder="./model_cache"
)
```

### Database Path

By default, the pipeline looks for `my_database_mimic.db` in the `data/` directory. You can change this in Cell 5 of `3_rag_qa.ipynb`:

```python
table_names, table_infos, table_columns = auto_load_database(
    search_dir="../",  # Search in parent directory
    # Or specify explicitly:
    # db_path="path/to/your/database.db"
)
```

## 📊 Features

### Auto-Loading
- **Automatic discovery** of database and description files
- **Multi-source merging**: Combines detailed descriptions and table summaries
- **Priority system**: Prefers detailed descriptions over summaries

### BGE Embeddings
- **Open source**: No API costs
- **High performance**: State-of-the-art embedding quality
- **Local execution**: Runs on your GPU/CPU
- **Model caching**: Downloads once, reuses forever

### RAG Pipeline
- **Table retrieval**: Finds relevant tables for questions
- **Note retrieval**: Retrieves patient clinical notes with temporal alignment
- **SQL generation**: Converts natural language to SQL
- **Evidence-based answers**: Synthesizes structured and unstructured data

## 🔍 Example Queries

```python
query = """
How did the INR change in the days following heparin administration 
for patient 123, and what is the time for every drugs and labs?
"""

response = qp.run(query=query)
print(response.message.content)
```

The system will:
1. Retrieve relevant tables (PRESCRIPTIONS, LABEVENTS)
2. Generate SQL to query drugs and lab results
3. Fetch clinical notes for the patient
4. Synthesize a comprehensive answer with evidence

## 🛠️ Utilities

### Auto-Load Database

```python
from utils.db_schema_loader import auto_load_database

# Automatically find and load everything
table_names, table_infos, table_columns = auto_load_database()
```

### Test Auto-Load

```bash
cd utils && python test_auto_load.py
```

This will verify:
- ✓ Database discovery
- ✓ Description loading
- ✓ Column extraction
- ✓ Coverage statistics

## 🐛 Troubleshooting

### GPU Out of Memory

If you encounter GPU memory issues with `bge-large`:

```python
# Switch to smaller model
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5",
    device="cuda"
)
```

Or use CPU:

```python
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-large-en-v1.5",
    device="cpu"  # Slower but no GPU required
)
```

### Model Download Issues

If model download fails, manually download from HuggingFace:

```bash
git clone https://huggingface.co/BAAI/bge-large-en-v1.5
```

Then specify local path:

```python
Settings.embed_model = HuggingFaceEmbedding(
    model_name="./bge-large-en-v1.5",
    device="cuda"
)
```

### No Descriptions Found

Run description generation:

```bash
export OPENAI_API_KEY="your-key-here"
python 2_generate_descriptions.py
```

## 📈 Performance Tips

1. **Use GPU**: BGE models run 10-50x faster on GPU
2. **Cache indexes**: Vector indexes are persisted automatically
3. **Batch queries**: Process multiple questions in one session
4. **Choose right model**: Use `bge-base` for speed, `bge-large` for quality

## 📚 References

- **BGE Models**: https://huggingface.co/BAAI/bge-large-en-v1.5
- **LlamaIndex**: https://docs.llamaindex.ai/
- **MIMIC Database**: https://mimic.mit.edu/

