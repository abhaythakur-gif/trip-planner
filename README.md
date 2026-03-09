# 🌍 AI Smart Travel Multi-Agent Planning System

A sophisticated multi-agent travel planning system that converts natural language requests into optimized, constraint-aware travel plans using LangGraph and specialized AI agents.

## ✨ Features

### 🎨 Interactive Web Interface
- **Beautiful Streamlit UI**: Modern, responsive design with gradient themes
- **Real-Time Streaming**: Watch AI agents think and work in real-time
- **Progress Tracking**: Visual progress bars and status updates for each agent
- **Interactive Visualizations**: Budget charts, metric cards, and expandable logs

### 🤖 AI-Powered Planning
- **Natural Language Input**: Describe your trip in plain English
- **Multi-Agent Architecture**: Specialized agents for transport, accommodation, weather, and attractions
- **Constraint Optimization**: Respects budget, time, and preference constraints
- **Intelligent Replanning**: Automatically adjusts when constraints are violated
- **Risk Assessment**: Simulates scenarios and provides fallback options
- **Confidence Scoring**: Quantifies plan reliability

### 📊 Smart Features
- **Budget Allocation**: Automatic distribution with 40+ city cost-of-living adjustments
- **Constraint Modeling**: Hard vs soft constraints with relaxation logic
- **Export Options**: Download plans as JSON or copy as text
- **Quick Examples**: Pre-filled trip templates to get started fast

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (for AI agents)
- Redis (optional, for caching in production)

### Installation

```bash
# Clone the repository
cd trip_planner

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run the Web Interface (Recommended)

```bash
# Easy way - use the launch script
./run_app.sh

# Or manually
streamlit run app.py
```

The app will open at `http://localhost:8501` 🎉

**Features:**
- 🎨 Beautiful, modern UI
- 🔄 Real-time agent progress streaming
- 📊 Interactive visualizations
- 💾 Export results as JSON
- ⚙️ Configure API keys in the sidebar

See [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md) for detailed usage.

### Run CLI Version

```bash
# Run the command-line demo
python src/main.py
```

### Example Usage (Programmatic)

```python
from src.main import plan_trip

result = plan_trip(
    "Plan a 5-day trip to Paris in May for $2500 from New York. "
    "I love museums and good food, and prefer mid-range hotels."
)

print(result.final_plan)
```

## 📁 Project Structure

```
trip_planner/
├── src/
│   ├── agents/          # Specialized AI agents
│   ├── schemas/         # Pydantic models
│   ├── tools/           # External API wrappers
│   ├── orchestration/   # LangGraph workflow
│   ├── scoring/         # Scoring algorithms
│   ├── api/             # FastAPI application
│   └── utils/           # Utilities
├── tests/               # Test suite
├── data/                # Configuration and prompts
└── docs/                # Documentation
```

## 🏗️ Architecture

The system operates through 6 execution layers:

1. **Intent Structuring**: Extract structured travel parameters
2. **Constraint Modeling**: Define hard/soft constraints
3. **Parallel Agent Layer**: Gather data from multiple sources
4. **Optimization Layer**: Validate and rebalance
5. **Risk & Confidence Layer**: Assess reliability
6. **Output Layer**: Generate final plan

See [docs/architecture.md](docs/architecture.md) for details.

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Run specific test suite
pytest tests/test_agents/
```

## 📚 Documentation

- [Architecture Guide](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Agent Specifications](docs/agent_specifications.md)
- [Deployment Guide](docs/deployment.md)

## 🔧 Configuration

Key configuration options in `.env`:

- `LLM_MODEL`: Choose between GPT-4, GPT-3.5, Claude
- `MAX_REPLAN_ATTEMPTS`: Maximum replanning iterations (default: 3)
- `MIN_CONFIDENCE_SCORE`: Minimum acceptable confidence (default: 70)
- Budget allocation defaults in `data/scoring_weights.yaml`

## 📈 Performance

- Average execution time: 60-120 seconds
- Token usage: 20k-40k per plan
- Cached API calls: 80%+ reduction in costs

## 🤝 Contributing

This is an implementation of the specification in `documents/document_1.md`.

## 📄 License

MIT License

## 🙏 Acknowledgments

Built with LangGraph, LangChain, and powered by OpenAI/Anthropic models.
