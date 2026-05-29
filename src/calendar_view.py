"""Calendar view helpers for the Streamlit UI."""

import streamlit as st


def render_calendar_placeholder() -> None:
    """Render a lightweight placeholder until the calendar stage is implemented."""
    st.write("Calendar visualization will appear here in a later stage.")
    st.write("- Fixed events: blue time blocks")
    st.write("- Deadline tasks: orange timeline bars")
    st.write("- Essential tasks: green daily bars")
    st.write("- Completed tasks: gray")
