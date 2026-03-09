# 🚀 Running the Streamlit Frontend

## Quick Start

```bash
# Make sure you're in the trip_planner directory
cd /home/trantorchd.com/abhay.thakur/trip_planner

# Activate virtual environment (if not already activated)
source venv/bin/activate

# Install Streamlit (if not already installed)
pip install streamlit plotly

# Run the app!
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Features

### 🎨 Beautiful UI
- Modern gradient design
- Responsive layout
- Real-time progress tracking
- Interactive visualizations

### 🔄 Real-Time Streaming
- Watch agents work in real-time
- See AI thinking process
- Progress bars and status updates
- Expandable detail views

### 🧠 Current Capabilities
- **Intent Extraction**: Natural language → Structured data
- **Constraint Modeling**: Requirements → Planning constraints
- **Budget Allocation**: Smart budget distribution with city awareness

### 📊 Visual Components
- Budget breakdown charts
- Progress tracking
- Metric cards
- Expandable agent logs

### 🎯 Quick Examples
- Pre-filled example queries
- One-click trip templates
- Advanced options panel

## Usage

### 1. Configure API Key
- Click on sidebar "API Settings"
- Enter your OpenAI API key
- Select LLM model (default: gpt-4o)

### 2. Describe Your Trip
Enter natural language like:
```
Plan a 5-day trip to Paris in May for $2500 from New York.
I love museums and good food, prefer mid-range hotels.
```

Or use quick examples:
- 🗼 Paris Adventure
- 🏖️ Bali Relaxation
- 🏛️ Rome Culture

### 3. Watch AI Agents Work
See real-time progress as:
- 🧠 Intent Extractor analyzes your request
- 📊 Constraint Modeler builds constraints
- 💰 Budget Allocator distributes budget

### 4. Review Your Plan
- Trip summary with key metrics
- Visual budget breakdown
- Constraint details
- Export options (JSON, text)

## Screenshots of What You'll See

### Agent Progress Tracking
```
🔄 Intent Extractor
   Analyzing your request and extracting travel parameters...
   ✓ Destination: Paris
   ✓ Duration: 5 days
   ✓ Budget: $2,500.00
   ✓ Travelers: 1
   Duration: 2.34s

✅ Constraint Modeler
   Converting your requirements into planning constraints...
   ✓ Max budget: $2,500.00
   ✓ Trip dates: 2026-05-15 to 2026-05-20
   ✓ Comfort level: 3/5
   ✓ Pace: moderate
   Duration: 0.89s

✅ Budget Allocator
   Distributing your budget across travel categories...
   ✓ Transport: $800.00 (32.0%)
   ✓ Accommodation: $875.00 (35.0%)
   ✓ Food: $450.00 (18.0%)
   ✓ Activities: $250.00 (10.0%)
   ✓ Buffer: $125.00 (5.0%)
   Duration: 0.45s
```

### Results Dashboard
- 📋 **Trip Summary**: Key metrics in cards
- 💰 **Budget Allocation**: Bar chart + table
- 📊 **Planning Constraints**: Hard vs Soft
- 🎨 **Your Preferences**: Interests & accommodation
- 🚀 **Next Steps**: What's coming in future phases
- 💾 **Export**: JSON download, copy summary, plan another trip

## Advanced Options

### 🎛️ Available Settings
- ✅ **Flexible with dates/budget**: Enable constraint relaxation
- 📊 **Show token usage**: Track LLM token consumption
- 🐛 **Debug mode**: Show detailed logs
- 💾 **Save results**: Auto-save plans locally

## Customization

### Change Colors
Edit the CSS in `app.py`:
```python
background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
```

### Add More Examples
In the `render_input_form()` function, add buttons:
```python
with col4:
    if st.button("🌴 Tropical Escape"):
        st.session_state.query_input = "Your custom example..."
```

### Modify Layout
Change column ratios:
```python
col1, col2, col3 = st.columns([2, 1, 1])  # Adjust ratios
```

## Troubleshooting

### Port Already in Use
```bash
streamlit run app.py --server.port 8502
```

### API Key Not Working
- Check sidebar API Settings
- Ensure key starts with `sk-`
- Verify account has credits

### Import Errors
```bash
pip install -r requirements.txt
```

### Module Not Found
Make sure you're in the correct directory:
```bash
pwd  # Should show: /home/trantorchd.com/abhay.thakur/trip_planner
```

## Next Steps

### When More Agents Are Ready
Simply add them to the workflow in `app.py`:
```python
# Agent 4: Transport Agent
tracker.start_agent("✈️ Transport Agent", "Searching for flights...")
transport_agent = TransportAgent()
state = await transport_agent.run(state)
tracker.complete_agent(True)
```

The streaming UI will automatically display the new agent's progress!

### Add More Visualizations
Use Plotly for interactive charts:
```python
import plotly.express as px
fig = px.pie(values=[...], names=[...])
st.plotly_chart(fig)
```

## Tips

- 💡 **Use specific queries**: Include origin, destination, dates, budget
- 🎯 **Try quick examples**: Learn what works well
- 📊 **Watch the progress**: See how agents think
- 💾 **Export your plans**: Save as JSON for later
- 🔄 **Iterate quickly**: "Plan Another Trip" button resets everything

## Features Coming Soon

When full implementation is complete, you'll see:
- 🛫 Live flight search results
- 🏨 Hotel recommendations with photos
- 🌤️ Weather forecasts
- 🎭 Activity suggestions
- 📅 Complete day-by-day itineraries
- 🗺️ Interactive maps
- ⚠️ Risk assessments
- 🎯 Confidence scores
- 📱 Mobile-responsive design
- 🔔 Real-time notifications

Enjoy planning your trips! 🌍✈️🎉
