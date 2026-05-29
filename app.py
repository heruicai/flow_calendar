"""Streamlit entry point for FlowCal."""

import streamlit as st

from src.calendar_view import render_calendar_placeholder
from src.response_generator import build_welcome_message


def main() -> None:
    st.set_page_config(page_title="FlowCal", page_icon="F", layout="wide")

    st.title("FlowCal")
    st.caption("Voice-driven visual calendar assistant")

    left, middle, right = st.columns([1, 2, 1])

    with left:
        st.subheader("Input")
        input_mode = st.radio("Input mode", ["Text", "Voice simulation"], horizontal=True)
        command = st.text_area(
            "Command",
            placeholder="Example: 明天下午三点到四点参加算法面试",
            height=140,
        )
        submitted = st.button("Run command", type="primary")

    with middle:
        st.subheader("Calendar")
        render_calendar_placeholder()

    with right:
        st.subheader("System Response")
        if submitted and command.strip():
            st.info(f"{input_mode} command received: {command.strip()}")
        else:
            st.info(build_welcome_message())


if __name__ == "__main__":
    main()
