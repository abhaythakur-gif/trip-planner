"""
🌍 AI Smart Travel Planning System - Streamlit Chat Frontend

A conversational interface for planning trips using AI agents.
"""

import streamlit as st
import asyncio
from datetime import datetime
from typing import Optional
import uuid

# Page configuration
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    .system-message {
        background-color: #fff3cd;
        text-align: center;
        font-style: italic;
    }
    .stButton>button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Import local modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.schemas.state import TravelState, create_initial_state
from src.orchestration.graph import create_travel_planning_graph
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("trip_planner.app")


# Session state initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "travel_state" not in st.session_state:
    st.session_state.travel_state = None
if "planning_complete" not in st.session_state:
    st.session_state.planning_complete = False
if "waiting_for_user" not in st.session_state:
    st.session_state.waiting_for_user = False


def render_header():
    """Render the page header."""
    st.markdown('<h1 class="main-header">🌍 AI Travel Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Tell me about your dream trip - I\'ll gather the details and create your perfect itinerary</p>',
        unsafe_allow_html=True
    )


def render_sidebar():
    """Render the sidebar with configuration."""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Configuration
        with st.expander("🔑 API Settings", expanded=False):
            api_key = st.text_input(
                "OpenAI API Key",
                value=settings.openai_api_key if settings.openai_api_key else "",
                type="password",
                help="Your OpenAI API key for LLM access"
            )
            if api_key and api_key != settings.openai_api_key:
                settings.openai_api_key = api_key
                st.success("API key updated!")
            
            llm_model = st.selectbox(
                "LLM Model",
                ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
                index=0
            )
            settings.llm_model = llm_model
        
        # Conversation Status
        with st.expander("💬 Conversation Status", expanded=True):
            if st.session_state.travel_state:
                state = st.session_state.travel_state
                info_complete = state.get("information_complete", False)
                accumulated = state.get("accumulated_trip_info")
                
                if info_complete:
                    st.success("✅ All information collected!")
                    st.caption("Ready to plan your trip")
                else:
                    missing = state.get("missing_fields", [])
                    if missing:
                        st.info(f"📝 Still need: {', '.join(missing)}")
                    else:
                        st.caption("🤔 Gathering your trip details...")
                
                if accumulated:
                    if accumulated.origin:
                        st.metric("🛫 Origin", accumulated.origin)
                    if accumulated.destination:
                        st.metric("🎯 Destination", accumulated.destination)
                    if accumulated.budget:
                        st.metric("💰 Budget", f"${accumulated.budget:,.0f}")
            else:
                st.caption("Start chatting to begin!")
        
        # Quick Actions
        st.divider()
        if st.button("🔄 New Conversation"):
            st.session_state.messages = []
            st.session_state.travel_state = None
            st.session_state.planning_complete = False
            st.session_state.waiting_for_user = False
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
        
        # Help
        with st.expander("❓ Help", expanded=False):
            st.markdown("""
            **How to use:**
            1. Start by telling me where you want to go
            2. I'll ask follow-up questions to understand your needs
            3. Once I have all details, I'll create your travel plan
            
            **Required information:**
            - 🛫 Origin (where you're traveling from)
            - 🎯 Destination (where you want to go)
            - 📅 Travel dates or preferred month
            - ⏱️ Trip duration
            - 💰 Budget
            
            **You can say things like:**
            - "I want to visit Paris from New York"
            - "Next month in May"
            - "My budget is $2500"
            - "We're 2 travelers"
            """)


def render_chat_message(role: str, content: str):
    """Render a single chat message."""
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>You:</strong> {content}
        </div>
        """, unsafe_allow_html=True)
    elif role == "assistant":
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 Assistant:</strong> {content}
        </div>
        """, unsafe_allow_html=True)
    elif role == "system":
        st.markdown(f"""
        <div class="chat-message system-message">
            {content}
        </div>
        """, unsafe_allow_html=True)


def render_chat_history():
    """Render all chat messages."""
    for msg in st.session_state.messages:
        render_chat_message(msg["role"], msg["content"])


async def process_user_message(user_input: str):
    """Process user message through the conversational workflow."""
    try:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Create or update state
        if st.session_state.travel_state is None:
            # First message - create initial state
            state = create_initial_state(user_input)
        else:
            # Continue existing conversation
            state = st.session_state.travel_state
            state["messages"].append({"role": "user", "content": user_input})
        
        # Get the compiled graph
        graph = create_travel_planning_graph()
        
        # Execute workflow
        logger.info("Executing conversational workflow")
        final_state = await graph.ainvoke(state)
        
        # Save state
        st.session_state.travel_state = final_state
        
        # Check if we have a final plan (planning is complete)
        final_plan = final_state.get("final_plan")
        if final_plan:
            # Planning is complete - display the plan
            st.session_state.planning_complete = True
            st.session_state.messages.append({
                "role": "system",
                "content": "✅ Your trip plan is ready!"
            })
            return True
        
        # Check if information is complete and planning should start
        info_complete = final_state.get("information_complete", False)
        conversation_mode = final_state.get("conversation_mode", True)
        
        if info_complete and not conversation_mode:
            # Planning phase is running
            st.session_state.messages.append({
                "role": "system",
                "content": "✨ Perfect! I have all the information. Starting trip planning..."
            })
        else:
            # Still in conversation - get next question
            next_question = final_state.get("next_question")
            if next_question:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": next_question
                })
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"I encountered an error: {str(e)}. Please try again."
        })
        return False


def render_chat_interface():
    """Render the chat interface."""
    # Chat history
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            # Welcome message
            st.markdown("""
            <div class="chat-message assistant-message">
                <strong>🤖 Assistant:</strong> 
                Hi! I'm your AI travel planning assistant. Tell me where you're traveling from and where you'd like to go, 
                and I'll help you plan an amazing trip! 🌍✈️
                <br><br>
                <em>Example: "I want to travel from New York to Paris in May with a budget of $3000"</em>
            </div>
            """, unsafe_allow_html=True)
        else:
            render_chat_history()
    
    # Input area
    st.markdown("---")
    
    # Check if planning is complete
    if st.session_state.planning_complete:
        # Display the final plan
        if st.session_state.travel_state and st.session_state.travel_state.get("final_plan"):
            final_plan = st.session_state.travel_state["final_plan"]
            
            st.success("✅ Trip planning complete!")
            
            # Debug info
            with st.expander("🔍 Debug Info", expanded=False):
                st.write("**Final Plan Structure:**")
                st.write(f"- Has summary: {final_plan.summary is not None}")
                st.write(f"- Has budget: {final_plan.budget_breakdown is not None}")
                st.write(f"- Has transport: {final_plan.transport_outbound is not None}")
                st.write(f"- Has accommodation: {final_plan.accommodation is not None}")
                st.write(f"- Has itinerary: {final_plan.daily_itinerary is not None}")
                if final_plan.daily_itinerary:
                    st.write(f"- Itinerary has days: {hasattr(final_plan.daily_itinerary, 'days')}")
                    if hasattr(final_plan.daily_itinerary, 'days'):
                        st.write(f"- Number of days: {len(final_plan.daily_itinerary.days)}")
                        st.write(f"- Days content: {final_plan.daily_itinerary.days}")
                st.write(f"- Confidence: {final_plan.confidence_score:.1f}%")
                st.write(f"- Confidence explanation: {final_plan.confidence_explanation}")
            
            # Display plan summary
            with st.expander("📋 Trip Summary", expanded=True):
                summary = final_plan.summary
                if summary:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Destination", summary.destination)
                        st.metric("Duration", f"{summary.duration_days} days")
                    with col2:
                        st.metric("Travelers", summary.num_travelers)
                        st.metric("Total Budget", f"${summary.total_budget:,.2f}")
                    with col3:
                        st.metric("Total Cost", f"${summary.total_cost:,.2f}")
                        st.metric("Remaining", f"${summary.remaining_budget:,.2f}")
            
            # Display flight details
            with st.expander("✈️ Flight Details", expanded=True):
                outbound = final_plan.transport_outbound
                ret = final_plan.transport_return
                if outbound or ret:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Outbound Flight")
                        if outbound:
                            st.write(f"**Carrier:** {outbound.carrier}")
                            if outbound.flight_number:
                                st.write(f"**Flight No:** {outbound.flight_number}")
                            st.write(f"**From:** {outbound.origin}")
                            st.write(f"**To:** {outbound.destination}")
                            st.write(f"**Departs:** {outbound.departure.strftime('%d %b %Y  %H:%M')}")
                            st.write(f"**Arrives:** {outbound.arrival.strftime('%d %b %Y  %H:%M')}")
                            st.write(f"**Duration:** {outbound.duration_hours:.1f} hrs")
                            st.write(f"**Price:** ${outbound.price:,.2f}")
                        else:
                            st.info("Outbound flight details not available")
                    with col2:
                        st.subheader("Return Flight")
                        if ret:
                            st.write(f"**Carrier:** {ret.carrier}")
                            if ret.flight_number:
                                st.write(f"**Flight No:** {ret.flight_number}")
                            st.write(f"**From:** {ret.origin}")
                            st.write(f"**To:** {ret.destination}")
                            st.write(f"**Departs:** {ret.departure.strftime('%d %b %Y  %H:%M')}")
                            st.write(f"**Arrives:** {ret.arrival.strftime('%d %b %Y  %H:%M')}")
                            st.write(f"**Duration:** {ret.duration_hours:.1f} hrs")
                            st.write(f"**Price:** ${ret.price:,.2f}")
                        else:
                            st.info("Return flight details not available")
                    if outbound and ret:
                        st.metric("Total Flight Cost", f"${outbound.price + ret.price:,.2f}")
                else:
                    st.info("Flight information not available")

            # Display itinerary
            with st.expander("🗓️ Daily Itinerary", expanded=True):
                itinerary = final_plan.daily_itinerary
                if itinerary and itinerary.days and len(itinerary.days) > 0:
                    for day in itinerary.days:
                        st.subheader(f"Day {day.day_number}: {day.date.strftime('%B %d, %Y')}")
                        if day.weather:
                            st.caption(f"Weather: {day.weather.condition} ({day.weather.temp_min:.0f}°C - {day.weather.temp_max:.0f}°C)")
                        
                        if day.activities and len(day.activities) > 0:
                            for activity in day.activities:
                                time_range = f"{activity.time_start.strftime('%H:%M')} - {activity.time_end.strftime('%H:%M')}"
                                st.write(f"**{time_range}**: {activity.attraction.name}")
                                st.caption(f"{activity.attraction.category} • {activity.attraction.description}")
                        else:
                            st.info("No activities planned for this day yet")
                        
                        # Show meals
                        if day.meals:
                            with st.expander(f"🍽️ Meals for Day {day.day_number}"):
                                for meal in day.meals:
                                    st.write(f"**{meal.type.capitalize()}** at {meal.time.strftime('%H:%M')}: {meal.location} (${meal.estimated_cost:.2f})")
                        
                        st.write(f"💰 **Daily Cost**: ${day.total_cost:.2f}")
                        st.divider()
                elif itinerary and itinerary.days and len(itinerary.days) == 0:
                    st.warning("⚠️ Itinerary was created but has no days scheduled. This may be due to missing data.")
                else:
                    st.info("ℹ️ Itinerary details not yet available")
            
            # Display budget breakdown
            with st.expander("💰 Budget Breakdown"):
                budget = final_plan.budget_breakdown
                if budget:
                    st.write(f"**Transport**: ${budget.transport:,.2f}")
                    st.write(f"**Accommodation**: ${budget.stay:,.2f}")
                    st.write(f"**Food**: ${budget.food:,.2f}")
                    st.write(f"**Activities**: ${budget.activities:,.2f}")
                    st.write(f"**Buffer**: ${budget.buffer:,.2f}")
        
        if st.button("Start New Trip"):
            st.session_state.messages = []
            st.session_state.travel_state = None
            st.session_state.planning_complete = False
            st.rerun()
        return
    
    # Chat input
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder="Type your message here...",
                label_visibility="collapsed"
            )
        with col2:
            send_button = st.form_submit_button("Send 📤", use_container_width=True)
    
    # Process input
    if send_button and user_input:
        if not settings.openai_api_key:
            st.error("⚠️ Please add your OpenAI API key in the sidebar!")
        else:
            with st.spinner("Thinking..."):
                success = asyncio.run(process_user_message(user_input))
                if success:
                    st.rerun()


def main():
    """Main application."""
    render_header()
    render_sidebar()
    
    # Check API key
    if not settings.openai_api_key:
        st.warning("⚠️ Please configure your OpenAI API key in the sidebar to start chatting.")
        st.info("👈 Click on the sidebar to add your API key")
    
    # Render chat interface
    render_chat_interface()


if __name__ == "__main__":
    main()
