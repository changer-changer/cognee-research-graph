# Contributing to Cognee Research Graph

Thank you for your interest! This is an early-stage research project.

## How to Contribute

1. **Fork** the repository
2. **Create a branch** (`git checkout -b feature/your-feature`)
3. **Commit** your changes (`git commit -am 'Add some feature'`)
4. **Push** to the branch (`git push origin feature/your-feature`)
5. **Open a Pull Request**

## Development Setup

```bash
git clone https://github.com/changer-changer/cognee-research-graph.git
cd cognee-research-graph
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start GROBID (required for PDF parsing)
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0

# Run tests
python tests/comprehensive_pipeline_test.py
```

## Areas Needing Help

- **Multi-paper batch processing**: Test taxonomy builder with 10+ papers
- **Training objective extraction**: Extend prompts to capture §3.4 training details
- **Evaluation metrics**: Add accuracy/BLEU/ROUGE extraction to resources
- **Support for more LLM providers**: DeepSeek, OpenRouter, etc.
- **Survey paper support**: Adapt prompts for survey/review papers

## Code Style

- Python 3.10+
- Type hints encouraged
- Async/await for I/O bound operations
- No hardcoded limits on entity counts
