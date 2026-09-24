import streamlit as st

from social_media_agent.persistence.database import (
    SessionFactory,
    initialize_database,
)
from social_media_agent.persistence.repository import (
    ContentRepository,
)
from social_media_agent.persistence.service import (
    PersistenceService,
)
from social_media_agent.services.llm.factory import (
    get_llm_provider,
)
from social_media_agent.services.pipeline.content_pipeline_service import (
    ContentPipelineService,
)
from social_media_agent.services.search.factory import (
    get_search_provider,
)
from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.image.factory import (
    get_image_provider,
)
from social_media_agent.services.image_generation.creative_image_service import (
    CreativeImageGenerationService,
)
from social_media_agent.services.publishing.publishing_service import (
    PublishingService,
)
from social_media_agent.services.publishing.factory import (
    get_publishers,
)
from social_media_agent.services.publishing.instagram_graph_client import (
    InstagramGraphClient,
)
from social_media_agent.services.publishing.instagram_preflight import (
    InstagramPublishingPreflight,
)
from social_media_agent.services.publishing.instagram_run_preflight import (
    InstagramRunPreflightService,
)
from social_media_agent.services.publishing.media_url_factory import (
    get_media_url_resolver,
)


@st.cache_resource
def get_publishing_service():

    return PublishingService(
        persistence=(
            get_persistence_service()
        ),
        publishers=get_publishers(),
    )

@st.cache_resource
def get_instagram_run_preflight_service():

    return InstagramRunPreflightService(
        persistence=get_persistence_service(),
        preflight=InstagramPublishingPreflight(
            client=InstagramGraphClient(),
            media_url_resolver=(
                get_media_url_resolver()
            ),
        ),
    )


@st.cache_resource
def get_persistence_service() -> PersistenceService:

    initialize_database()

    repository = ContentRepository(
        SessionFactory
    )

    return PersistenceService(
        repository
    )

@st.cache_resource
def get_content_pipeline_service():

    return ContentPipelineService(
        llm=get_llm_provider(),
        search_provider=get_search_provider(),
        persistence=get_persistence_service(),
        image_generation_service=(
            get_image_generation_service()
        ),
    )

@st.cache_resource
def get_image_generation_service():

    if not settings.image_generation_enabled:
        return None

    provider = get_image_provider()

    return CreativeImageGenerationService(
        provider=provider,
    )

# @st.cache_resource
# def get_publishing_service():

#     return PublishingService(
#         persistence=(
#             get_persistence_service()
#         ),
#         publisher=DryRunPublisher(),
#     )