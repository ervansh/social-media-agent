import io
import json

import pytest
from PIL import Image

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.image.comfyui_provider import (
    ComfyUIImageAPIError,
    ComfyUIImageProvider,
)
from social_media_agent.services.image.factory import (
    get_image_provider,
)


def make_png(
    width: int,
    height: int,
) -> bytes:

    image = Image.new(
        "RGB",
        (
            width,
            height,
        ),
        "white",
    )

    output = io.BytesIO()

    image.save(
        output,
        format="PNG",
    )

    return output.getvalue()


class FakeResponse:

    def __init__(
        self,
        *,
        payload=None,
        content=b"",
        ok=True,
        status_code=200,
        text="",
    ):
        self._payload = payload
        self.content = content
        self.ok = ok
        self.status_code = status_code
        self.text = text

    def json(
        self,
    ):
        if self._payload is None:
            raise ValueError(
                "no JSON"
            )

        return self._payload


class FakeComfySession:

    def __init__(
        self,
        *,
        image_bytes,
        history_payloads=None,
    ):
        self.image_bytes = image_bytes
        self.history_payloads = list(
            history_payloads
            or []
        )
        self.posts = []
        self.gets = []

    def post(
        self,
        url,
        *,
        json,
        timeout,
    ):
        self.posts.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )

        return FakeResponse(
            payload={
                "prompt_id":
                    "prompt-123"
            }
        )

    def get(
        self,
        url,
        *,
        params=None,
        timeout,
    ):
        self.gets.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )

        if url.endswith(
            "/system_stats"
        ):
            return FakeResponse(
                payload={
                    "system": {
                        "comfyui_version":
                            "test"
                    }
                }
            )

        if "/history/" in url:
            if self.history_payloads:
                payload = (
                    self.history_payloads
                    .pop(0)
                )
            else:
                payload = {
                    "prompt-123": {
                        "outputs": {
                            "9": {
                                "images": [
                                    {
                                        "filename":
                                            "output.png",
                                        "subfolder":
                                            "",
                                        "type":
                                            "output",
                                    }
                                ]
                            }
                        },
                        "status": {
                            "completed":
                                True
                        },
                    }
                }

            return FakeResponse(
                payload=payload
            )

        if url.endswith(
            "/view"
        ):
            return FakeResponse(
                payload={},
                content=(
                    self.image_bytes
                ),
            )

        raise AssertionError(
            f"Unexpected GET: {url}"
        )


def write_workflow(
    tmp_path,
    *,
    include_negative=True,
):

    workflow = {
        "1": {
            "class_type":
                "PositivePrompt",
            "inputs": {
                "text":
                    "__PROMPT__"
            },
        },
        "2": {
            "class_type":
                "Latent",
            "inputs": {
                "width":
                    "__WIDTH__",
                "height":
                    "__HEIGHT__",
            },
        },
        "3": {
            "class_type":
                "Sampler",
            "inputs": {
                "seed":
                    "__SEED__"
            },
        },
        "9": {
            "class_type":
                "SaveImage",
            "inputs": {
                "filename_prefix":
                    "__OUTPUT_PREFIX__"
            },
        },
    }

    if include_negative:
        workflow["4"] = {
            "class_type":
                "NegativePrompt",
            "inputs": {
                "text":
                    "__NEGATIVE_PROMPT__"
            },
        }

    path = (
        tmp_path
        / "workflow.json"
    )

    path.write_text(
        json.dumps(
            workflow
        ),
        encoding="utf-8",
    )

    return path


def configure_settings(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "image_size_multiple",
        16,
    )

    monkeypatch.setattr(
        settings,
        "comfyui_request_timeout_seconds",
        30,
    )

    monkeypatch.setattr(
        settings,
        "comfyui_generation_timeout_seconds",
        60,
    )

    monkeypatch.setattr(
        settings,
        "comfyui_poll_interval_seconds",
        0.01,
    )

    monkeypatch.setattr(
        settings,
        "comfyui_jpeg_quality",
        90,
    )

    monkeypatch.setattr(
        settings,
        "comfyui_output_prefix",
        "social_media_agent",
    )


def test_comfyui_provider_generates_exact_size_jpeg(
    tmp_path,
    monkeypatch,
):

    configure_settings(
        monkeypatch
    )

    workflow_path = write_workflow(
        tmp_path
    )

    session = FakeComfySession(
        image_bytes=make_png(
            1088,
            1360,
        )
    )

    provider = ComfyUIImageProvider(
        session=session,
        base_url=(
            "http://127.0.0.1:8188"
        ),
        workflow_path=workflow_path,
        model_label=(
            "test-local-model"
        ),
        sleep_fn=lambda _: None,
    )

    result = provider.generate(
        prompt=(
            "Professional QA workflow"
        ),
        width=1080,
        height=1350,
        negative_prompt=(
            "clutter, artifacts"
        ),
    )

    assert result.provider == "comfyui"
    assert (
        result.model
        == "test-local-model"
    )
    assert result.file_extension == "jpeg"
    assert result.width == 1080
    assert result.height == 1350

    with Image.open(
        io.BytesIO(
            result.image_bytes
        )
    ) as image:
        assert image.format == "JPEG"
        assert image.size == (
            1080,
            1350,
        )

    prompt_request = (
        session.posts[0]["json"]
    )

    workflow = prompt_request[
        "prompt"
    ]

    assert (
        workflow["1"]["inputs"]["text"]
        == "Professional QA workflow"
    )

    assert (
        workflow["4"]["inputs"]["text"]
        == "clutter, artifacts"
    )

    assert (
        workflow["2"]["inputs"]["width"]
        == 1088
    )

    assert (
        workflow["2"]["inputs"]["height"]
        == 1360
    )

    assert isinstance(
        workflow["3"]["inputs"]["seed"],
        int,
    )

    assert (
        str(
            workflow["3"]["inputs"]["seed"]
        )
        in workflow["9"]["inputs"][
            "filename_prefix"
        ]
    )

    view_calls = [
        call
        for call
        in session.gets
        if call["url"].endswith(
            "/view"
        )
    ]

    assert view_calls[0]["params"] == {
        "filename": "output.png",
        "subfolder": "",
        "type": "output",
    }


def test_comfyui_provider_negative_prompt_falls_back_to_positive(
    tmp_path,
    monkeypatch,
):

    configure_settings(
        monkeypatch
    )

    workflow_path = write_workflow(
        tmp_path,
        include_negative=False,
    )

    session = FakeComfySession(
        image_bytes=make_png(
            512,
            512,
        )
    )

    provider = ComfyUIImageProvider(
        session=session,
        workflow_path=workflow_path,
        model_label="test-model",
        sleep_fn=lambda _: None,
    )

    provider.generate(
        prompt="QA dashboard",
        width=512,
        height=512,
        negative_prompt="blurry",
    )

    positive = (
        session.posts[0]["json"]
        ["prompt"]["1"]["inputs"]["text"]
    )

    assert positive == (
        "QA dashboard\n\n"
        "Avoid the following: blurry"
    )


def test_comfyui_provider_polls_until_output_exists(
    tmp_path,
    monkeypatch,
):

    configure_settings(
        monkeypatch
    )

    workflow_path = write_workflow(
        tmp_path
    )

    session = FakeComfySession(
        image_bytes=make_png(
            512,
            512,
        ),
        history_payloads=[
            {},
            {
                "prompt-123": {
                    "outputs": {},
                    "status": {
                        "completed":
                            False
                    },
                }
            },
        ],
    )

    provider = ComfyUIImageProvider(
        session=session,
        workflow_path=workflow_path,
        model_label="test-model",
        sleep_fn=lambda _: None,
    )

    result = provider.generate(
        prompt="QA dashboard",
        width=512,
        height=512,
    )

    assert result.width == 512

    history_calls = [
        call
        for call
        in session.gets
        if "/history/" in call["url"]
    ]

    assert len(
        history_calls
    ) == 3


def test_comfyui_provider_rejects_missing_required_placeholder(
    tmp_path,
    monkeypatch,
):

    configure_settings(
        monkeypatch
    )

    path = (
        tmp_path
        / "workflow.json"
    )

    path.write_text(
        json.dumps(
            {
                "1": {
                    "inputs": {
                        "text":
                            "__PROMPT__"
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="required placeholders",
    ):
        ComfyUIImageProvider(
            session=FakeComfySession(
                image_bytes=b""
            ),
            workflow_path=path,
            model_label="test-model",
        )


def test_comfyui_provider_requires_output_node_when_multiple_image_nodes(
    tmp_path,
    monkeypatch,
):

    configure_settings(
        monkeypatch
    )

    workflow_path = write_workflow(
        tmp_path
    )

    history = {
        "prompt-123": {
            "outputs": {
                "8": {
                    "images": [
                        {
                            "filename":
                                "a.png",
                            "subfolder":
                                "",
                            "type":
                                "output",
                        }
                    ]
                },
                "9": {
                    "images": [
                        {
                            "filename":
                                "b.png",
                            "subfolder":
                                "",
                            "type":
                                "output",
                        }
                    ]
                },
            },
            "status": {
                "completed": True
            },
        }
    }

    provider = ComfyUIImageProvider(
        session=FakeComfySession(
            image_bytes=make_png(
                512,
                512,
            ),
            history_payloads=[
                history
            ],
        ),
        workflow_path=workflow_path,
        model_label="test-model",
        sleep_fn=lambda _: None,
    )

    with pytest.raises(
        ComfyUIImageAPIError,
        match="multiple output nodes",
    ):
        provider.generate(
            prompt="QA",
            width=512,
            height=512,
        )


def test_image_factory_selects_comfyui_provider(
    tmp_path,
    monkeypatch,
):

    configure_settings(
        monkeypatch
    )

    workflow_path = write_workflow(
        tmp_path
    )

    monkeypatch.setattr(
        settings,
        "image_provider",
        "comfyui",
    )

    monkeypatch.setattr(
        settings,
        "comfyui_workflow_path",
        str(
            workflow_path
        ),
    )

    monkeypatch.setattr(
        settings,
        "comfyui_model_label",
        "factory-test-model",
    )

    provider = get_image_provider()

    assert isinstance(
        provider,
        ComfyUIImageProvider,
    )

    assert provider.model == (
        "factory-test-model"
    )


def test_comfyui_provider_surfaces_execution_failure(
    tmp_path,
    monkeypatch,
):

    configure_settings(
        monkeypatch
    )

    workflow_path = write_workflow(
        tmp_path
    )

    session = FakeComfySession(
        image_bytes=b"",
        history_payloads=[
            {
                "prompt-123": {
                    "outputs": {},
                    "status": {
                        "completed":
                            False,
                        "status_str":
                            "error",
                        "messages": [
                            [
                                "execution_error",
                                {
                                    "exception_message":
                                        "model load failed"
                                },
                            ]
                        ],
                    },
                }
            }
        ],
    )

    provider = ComfyUIImageProvider(
        session=session,
        workflow_path=workflow_path,
        model_label="test-model",
        sleep_fn=lambda _: None,
    )

    with pytest.raises(
        ComfyUIImageAPIError,
        match="execution failed",
    ):
        provider.generate(
            prompt="QA",
            width=512,
            height=512,
        )

