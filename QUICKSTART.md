# 🚀 Quick Start Guide

## Step 1: Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add at minimum:
# OPENAI_API_KEY=your_key_here
# or
# ANTHROPIC_API_KEY=your_key_here
```

## Step 3: Run the Demo

```bash
# Run the main demo
python src/main.py
```

This will execute Phase 1 of the system (Intent Extraction, Constraint Modeling, Budget Allocation).

## Step 4: Run Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_agents/

# Run with coverage
pytest --cov=src
```

## What's Implemented (Phase 0-1)

✅ **Project Structure**: Complete folder layout  
✅ **Configuration**: Environment-based settings  
✅ **Core Schemas**: Pydantic models for all data structures  
✅ **State Management**: Centralized state for workflow  
✅ **Base Agent**: Abstract base class with logging  
✅ **Intent Extractor**: Extracts structured request from natural language  
✅ **Constraint Modeler**: Converts request to hard/soft constraints  
✅ **Budget Allocator**: Distributes budget with destination-aware logic  
✅ **Logging**: Structured JSON logging  
✅ **Testing**: Pytest setup with sample tests  

## Next Steps for Full Implementation

### Phase 2: Data Retrieval Agents (Week 2-4)
- [ ] Implement Transport Agent (flight search & scoring)
- [ ] Implement Stay Agent (hotel search & scoring)
- [ ] Implement Weather Agent (forecast & risk assessment)
- [ ] Implement Attraction Agent (places & activities)
- [ ] Add caching layer (Redis)

### Phase 3: Itinerary Synthesis (Week 4-5)
- [ ] Implement Itinerary Builder
- [ ] Add schedule conflict detection
- [ ] Geographic clustering for efficiency

### Phase 4-5: Optimization & Risk (Week 5-7)
- [ ] Global Optimizer
- [ ] Calendar Validator
- [ ] Risk Simulator
- [ ] Confidence Scorer

### Phase 6: Orchestration (Week 7-8)
- [ ] Build LangGraph StateGraph
- [ ] Implement conditional routing
- [ ] Add loop control & replanning logic

### Phase 7-8: API & Output (Week 8-9)
- [ ] FastAPI endpoints
- [ ] Output formatters (Markdown, JSON)
- [ ] Authentication & rate limiting

### Phase 9-10: Testing & Deployment (Week 10-12)
- [ ] Integration tests
- [ ] E2E tests with real APIs
- [ ] Docker deployment
- [ ] Documentation

## Current Demo Output

When you run `python src/main.py`, you'll see:

```
🌍 AI Smart Travel Multi-Agent Planning System
============================================================

📝 Your request: I want to plan a 5-day trip to Paris...

============================================================

✅ Planning your trip!
📍 Destination: Paris
📅 Duration: 5 days
💰 Budget: $2500.00
   - Transport: $800.00
   - Stay: $875.00
   - Food: $450.00
   - Activities: $250.00
   - Buffer: $125.00

🔄 Full implementation coming soon with LangGraph orchestration!
```

## Architecture Overview

```
User Query
    ↓
Intent Extractor (LLM) → TravelRequest
    ↓
Constraint Modeler → ConstraintSet
    ↓
Budget Allocator → BudgetAllocation
    ↓
[Phase 2] Parallel Agents (Transport, Stay, Weather, Attractions)
    ↓
[Phase 3] Itinerary Builder
    ↓
[Phase 4] Global Optimizer + Calendar Validator
    ↓
[Phase 5] Risk Simulator + Confidence Scorer
    ↓
[Phase 6] Output Formatter → FinalTravelPlan
```

## Development Tips

### Adding a New Agent

1. Create file in `src/agents/your_agent.py`
2. Inherit from `BaseAgent`
3. Implement `async def execute(self, state: TravelState) -> TravelState`
4. Read from state, write to designated fields
5. Log decisions and audit entries
6. Add tests in `tests/test_agents/test_your_agent.py`

### Testing

```python
import pytest
from src.agents.your_agent import YourAgent
from src.schemas.state import create_initial_state

@pytest.mark.asyncio
async def test_your_agent():
    agent = YourAgent()
    state = create_initial_state("test query")
    # Setup state...
    result = await agent.execute(state)
    # Assert results...
```

### Adding External API Integration

1. Create wrapper in `src/tools/api_name.py`
2. Implement caching logic
3. Add error handling and retries
4. Mock in tests using `pytest-mock`

## Project Status

**Version**: 0.1.0 (Foundation Complete)  
**Phase**: 1 of 10 (Intent & Constraints)  
**Estimated Completion**: 8-10 weeks for full system  

## Questions?

Refer to:
- [README.md](README.md) - Main documentation
- [documents/document_1.md](documents/document_1.md) - Full specification
- Tests in `tests/` - Usage examples

Happy coding! 🚀
