# Project Structure

```
voynich-decoder/
│
├── README.md                          # Main project documentation
├── LICENSE                            # MIT License
├── requirements.txt                   # Python dependencies
├── .gitignore                        # Git ignore rules
│
├── data/                             # Data directory (mostly gitignored)
│   ├── corpora/                      # Historical language corpora
│   │   ├── arabic_quran.txt
│   │   ├── english.txt
│   │   ├── hebrew.txt
│   │   ├── latin.txt
│   │   └── middle_english.txt
│   ├── external/                     # External data (manuscript images)
│   │   └── images/
│   │       ├── 1r.jpg, 24v.jpg, 25r.jpg
│   │       ├── 103v.jpg, 104r.jpg
│   │       └── ...
│   ├── processed/                    # Processed data outputs
│   │   ├── examples/                 # Example files for testing
│   │   ├── voynich_run.jsonl        # Main transcription
│   │   ├── voynich_run_tokens.jsonl # Tokenized version
│   │   └── token_coords.jsonl       # Token coordinates
│   └── raw/                          # Raw input transcriptions
│       └── voynich_takahashi_extracted.txt
│
├── docs/                             # Documentation
│   ├── README.md                     # Documentation index
│   ├── project/                      # Project documentation
│   │   └── TIMELINE_COMPLETE.md
│   └── technical/                    # Technical specs
│       └── token_coords.md
│
├── notebooks/                        # Jupyter notebooks
│   ├── results_analysis.ipynb       # Results interpretation (31 KB)
│   ├── takahashi_analysis.ipynb     # Takahashi transcription analysis
│   ├── timeline_analysis.ipynb      # Temporal evolution analysis
│   └── visual_overlay.ipynb         # Visual overlay generation (12 MB)
│
├── reports/                          # Analysis reports and outputs
│   ├── final_report.md              # Main scientific report (3,494 words)
│   ├── process_log.md               # Development log (3,133 words)
│   ├── analysis_report.md           # Results analysis (4,511 bytes)
│   ├── comparison/                  # Language comparison results
│   │   ├── summary.md
│   │   ├── summary.csv
│   │   ├── *_details.json
│   │   └── comparison_metadata.json
│   ├── figures/                     # Visualizations
│   │   ├── timeline_analysis.md
│   │   ├── overlays/                # Overlay images and metadata
│   │   │   ├── overlay_*.png
│   │   │   ├── overlay_*_metadata.json
│   │   │   └── overlay_summary.json
│   │   └── timeline/                # Timeline visualizations
│   │       ├── token_frequency_heatmap.png
│   │       ├── vocabulary_diversity_evolution.png
│   │       └── vocabulary_shifts.png
│   ├── hypotheses/                  # AI-generated hypotheses
│   │   ├── run_hypotheses.jsonl
│   │   ├── hypotheses_aggregated.jsonl
│   │   ├── hypotheses_summary.md
│   │   └── hypotheses_summary.csv
│   └── metrics/                     # Experiment metrics
│       ├── experiment_metrics.json
│       └── experiment_metrics.md
│
├── scripts/                          # Utility scripts
│   └── smoke_run.sh                 # Smoke test pipeline
│
├── src/                              # Source code (25 modules)
│   ├── __init__.py
│   ├── cli.py                       # Command-line interface
│   │
│   ├── analysis/                    # Analysis modules
│   │   ├── report_metrics.py        # Metrics reporting
│   │   └── temporal_evolution.py    # Timeline analysis
│   │
│   ├── analytics/                   # Statistical analysis
│   │   ├── __init__.py
│   │   └── stats.py                 # Basic statistics
│   │
│   ├── compare/                     # Language comparison
│   │   ├── compare_corpora.py       # Corpus comparison
│   │   └── compare_languages.py     # Language similarity
│   │
│   ├── embeddings/                  # Embedding models
│   │   ├── __init__.py
│   │   ├── sentence_embeddings.py   # Sentence transformers
│   │   └── train.py                 # Word2Vec/FastText training
│   │
│   ├── ingest/                      # Data ingestion
│   │   ├── extract_coords.py        # Extract token coordinates
│   │   ├── generate_token_coords.py # Generate coordinate mappings
│   │   ├── ingest.py                # Main ingestion pipeline
│   │   ├── preprocess_takahashi.py  # Takahashi preprocessing
│   │   └── tokenize.py              # Tokenization
│   │
│   ├── llm/                         # LLM integration
│   │   ├── aggregate_hypotheses.py  # Hypothesis aggregation
│   │   ├── hypothesize.py           # Hypothesis generation
│   │   ├── local_llm_runner.py      # Local LLM runner
│   │   ├── rule_hypothesize.py      # Rule-based hypotheses
│   │   └── run_hypotheses.py        # Hypothesis execution
│   │
│   ├── pipeline/                    # Pipeline orchestration
│   │   └── run_full_pipeline.py     # Full pipeline runner
│   │
│   ├── utils/                       # Utilities
│   │   ├── __init__.py
│   │   └── experiment_logger.py     # Experiment logging
│   │
│   └── visualization/               # Visualization
│       └── overlay.py               # Overlay generation
│
├── tests/                           # Test suite
│   └── test_smoke_pipeline.py       # Smoke tests
│
└── .github/                         # GitHub configuration
    └── workflows/
        └── ci.yml                   # CI/CD pipeline
```

## Module Organization

### Core Pipeline
1. **Ingest** (`src/ingest/`) - Data loading and preprocessing
2. **Analytics** (`src/analytics/`) - Statistical analysis
3. **Embeddings** (`src/embeddings/`) - Semantic representations
4. **Compare** (`src/compare/`) - Language comparison
5. **LLM** (`src/llm/`) - Hypothesis generation
6. **Analysis** (`src/analysis/`) - Advanced analysis (timeline, metrics)
7. **Visualization** (`src/visualization/`) - Visual outputs

### Support
- **Utils** (`src/utils/`) - Shared utilities
- **Pipeline** (`src/pipeline/`) - End-to-end orchestration
- **CLI** (`src/cli.py`) - Command-line interface

## Key Files

### Configuration
- `requirements.txt` - All Python dependencies
- `.gitignore` - Git ignore patterns

### Documentation
- `README.md` - Main project README
- `docs/README.md` - Documentation index
- `reports/final_report.md` - Scientific report
- `reports/process_log.md` - Development log

### Entry Points
- `src/cli.py` - CLI entry point
- `src/pipeline/run_full_pipeline.py` - Full pipeline
- `scripts/smoke_run.sh` - Quick test script

## Data Flow

```
Raw Transcription
    ↓
[Ingest] → preprocessed JSONL
    ↓
[Tokenize] → tokens JSONL
    ↓
[Analytics] → n-grams, stats
    ↓
[Embeddings] → semantic vectors
    ↓
[Compare] → language similarity scores
    ↓
[LLM] → hypotheses
    ↓
[Analysis] → metrics, timeline
    ↓
[Visualization] → overlays, plots
    ↓
Reports & Notebooks
```

## Size Summary

- **Source Code**: 25 Python modules (~8,000 lines)
- **Notebooks**: 4 notebooks (~12 MB total)
- **Documentation**: ~11,000 words
- **Reports**: 9 report files + visualizations
- **Data**: Variable (corpora ~5 MB, images ~10 MB)
