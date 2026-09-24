import streamlit as st

from social_media_agent.ui.pages.create_content import (
    render as render_create_content,
)
from social_media_agent.ui.pages.dashboard import (
    render as render_dashboard,
)
from social_media_agent.ui.pages.review import (
    render as render_review,
)
from social_media_agent.ui.pages.publishing import (
    render as render_publishing,
)

st.set_page_config(
    page_title="Social Media Agent",
    page_icon="🤖",
    layout="wide",
)


def dashboard_page():
    render_dashboard()


def create_content_page():
    render_create_content()


def content_review_page():
    render_review()

def publishing_page():
    render_publishing()

dashboard = st.Page(
    dashboard_page,
    title="Dashboard",
    icon="📊",
    default=True,
)

create_content = st.Page(
    create_content_page,
    title="Create Content",
    icon="✨",
    url_path="create",
)

review = st.Page(
    content_review_page,
    title="Content Review",
    icon="✅",
    url_path="review",
)

publishing = st.Page(
    publishing_page,
    title="Publishing",
    icon="🚀",
    url_path="publishing",
)

navigation = st.navigation(
    [
        dashboard,
        create_content,
        review,
        publishing,
    ]
)

navigation.run()
