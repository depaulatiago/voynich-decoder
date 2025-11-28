# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.10 or higher
- Git
- 2 GB free disk space

### Installation

```bash
# Clone the repository
git clone https://github.com/depaulatiago/voynich-decoder.git
cd voynich-decoder

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Quick Test

Run the smoke test to verify everything works:

```bash
./scripts/smoke_run.sh
```

This will:
1. Preprocess sample transcription
2. Generate tokens
3. Compute statistics
4. Create embeddings
5. Generate hypotheses
6. Compare with languages
7. Produce reports

**Expected runtime:** 30-60 seconds

### Explore Results

After the smoke test:

```bash
# View generated reports
cat reports/final_report.md
cat reports/analysis_report.md

# View language comparison
cat reports/comparison/summary.md

# View hypotheses
cat reports/hypotheses/hypotheses_summary.md
```

## 📊 Interactive Analysis

Launch Jupyter to explore notebooks:

```bash
jupyter notebook
```

Open:
- `notebooks/results_analysis.ipynb` - Start here for overview
- `notebooks/timeline_analysis.ipynb` - Temporal patterns
- `notebooks/visual_overlay.ipynb` - Visual manuscript analysis

## 🎯 Common Tasks

### Run Full Pipeline

```bash
python src/pipeline/run_full_pipeline.py
```

### Generate Timeline Analysis

```bash
python src/analysis/temporal_evolution.py
```

### Create Visual Overlays

```bash
python src/visualization/overlay.py
```

### Compare with Languages

```bash
python src/compare/compare_corpora.py \
  --voynich data/processed/voynich_run.jsonl \
  --corpora data/corpora \
  --out reports/comparison
```

## 🔧 Using the CLI

The project includes a unified CLI:

```bash
# View available commands
python src/cli.py --help

# Run ingestion
python src/cli.py ingest data/raw/sample.txt

# Generate statistics
python src/cli.py stats data/processed/voynich_run.jsonl

# Train embeddings
python src/cli.py train-embeddings data/processed/voynich_run.jsonl

# Generate overlays
python src/cli.py overlay

# Compare corpora
python src/cli.py compare-corpora
```

## 📚 Next Steps

1. **Read the documentation**
   - [Main README](../README.md)
   - [Final Report](../reports/final_report.md)
   - [Project Structure](STRUCTURE.md)

2. **Explore the notebooks**
   - Start with `results_analysis.ipynb`
   - Try `timeline_analysis.ipynb`
   - Experiment with `visual_overlay.ipynb`

3. **Run experiments**
   - Try different parameters
   - Add your own corpora
   - Generate new hypotheses

4. **Extend the project**
   - Add new analysis modules
   - Implement new visualizations
   - Test alternative algorithms

## ⚙️ Configuration

### Environment Variables

```bash
# For LLM API access (optional)
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

### Data Paths

Default paths (can be overridden):
- Input: `data/raw/`
- Processed: `data/processed/`
- Models: `models/`
- Reports: `reports/`

## 🐛 Troubleshooting

### Import Errors

If you get import errors:

```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Missing Data

If data files are missing:

```bash
# The example files should be in git
ls data/processed/examples/

# Raw data might need to be added manually
# See README.md for data sources
```

### Jupyter Kernel Issues

```bash
# Install ipykernel in the virtual environment
pip install ipykernel

# Register the kernel
python -m ipykernel install --user --name=voynich-decoder
```

### Performance Issues

For faster processing:

```bash
# Install PyTorch with GPU support (if available)
pip install torch --index-url https://download.pytorch.org/whl/cu118

# Use smaller models for testing
python src/llm/local_llm_runner.py --model google/flan-t5-small
```

## 💡 Tips

1. **Start Small**: Use the example data first before processing the full manuscript
2. **Check Logs**: Pipeline outputs detailed logs to help debug issues
3. **Save Progress**: Intermediate results are saved in `data/processed/`
4. **Incremental**: Run pipeline steps individually rather than all at once
5. **Visualize**: Use notebooks for interactive exploration and visualization

## 🆘 Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Open an issue on GitHub
- **Code**: Read inline comments and docstrings
- **Tests**: Look at `tests/` for usage examples

## ✅ Verification

To verify your installation is working:

```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
pip list | grep -E "pandas|numpy|matplotlib|transformers"

# Run quick test
python -c "import pandas, numpy, matplotlib; print('✓ Core dependencies OK')"

# Run smoke test
./scripts/smoke_run.sh
```

If all commands succeed, you're ready to go! 🎉

---

**Next:** Read the [Main README](../README.md) for detailed documentation.
