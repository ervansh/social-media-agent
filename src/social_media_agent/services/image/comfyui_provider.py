import hashlib
import io
import json
import math
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import requests
from PIL import (
    Image,
    ImageOps,
    UnidentifiedImageError,
)

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.image.base import (
    ImageGenerationResult,
)


class ComfyUIImageAPIError(
    RuntimeError
):
    pass


class ComfyUIImageProvider:

    PROVIDER_NAME = "comfyui"

    PROMPT_TOKEN = "__PROMPT__"
    NEGATIVE_PROMPT_TOKEN = (
        "__NEGATIVE_PROMPT__"
    )
    WIDTH_TOKEN = "__WIDTH__"
    HEIGHT_TOKEN = "__HEIGHT__"
    SEED_TOKEN = "__SEED__"
    OUTPUT_PREFIX_TOKEN = (
        "__OUTPUT_PREFIX__"
    )

    REQUIRED_TOKENS = {
        PROMPT_TOKEN,
        WIDTH_TOKEN,
        HEIGHT_TOKEN,
    }

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        base_url: str | None = None,
        workflow_path: str | Path | None = None,
        model_label: str | None = None,
        output_node_id: str | None = None,
        sleep_fn=None,
        monotonic_fn=None,
    ):

        self.base_url = (
            base_url
            if base_url is not None
            else settings.comfyui_base_url
        ).rstrip("/")

        self.workflow_path = Path(
            workflow_path
            if workflow_path is not None
            else settings.comfyui_workflow_path
        ).expanduser().resolve()

        self.model = (
            model_label
            if model_label is not None
            else settings.comfyui_model_label
        ).strip()

        configured_output_node = (
            output_node_id
            if output_node_id is not None
            else settings.comfyui_output_node_id
        )

        self.output_node_id = (
            str(configured_output_node)
            if configured_output_node
            else None
        )

        self.session = (
            session
            or requests.Session()
        )

        self.sleep_fn = (
            sleep_fn
            or time.sleep
        )

        self.monotonic_fn = (
            monotonic_fn
            or time.monotonic
        )

        self.request_timeout = (
            settings
            .comfyui_request_timeout_seconds
        )

        self.generation_timeout = (
            settings
            .comfyui_generation_timeout_seconds
        )

        self.poll_interval = (
            settings
            .comfyui_poll_interval_seconds
        )

        self.jpeg_quality = (
            settings
            .comfyui_jpeg_quality
        )

        self.output_prefix = (
            settings
            .comfyui_output_prefix
            .strip()
        )

        self._verified = False

        self._validate_configuration()

        self.workflow_template = (
            self._load_workflow()
        )

        self._validate_workflow_template()

        self.workflow_fingerprint = (
            hashlib.sha256(
                json.dumps(
                    self.workflow_template,
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                    ensure_ascii=False,
                ).encode(
                    "utf-8"
                )
            ).hexdigest()
        )

    def verify_available(
        self,
    ) -> None:

        response = self._get(
            "/system_stats"
        )

        try:
            payload = response.json()

        except ValueError as exc:
            raise ComfyUIImageAPIError(
                "ComfyUI /system_stats returned "
                "a non-JSON response."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ComfyUIImageAPIError(
                "ComfyUI /system_stats returned "
                "an unexpected response shape."
            )

        self._verified = True

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        negative_prompt: str | None = None,
    ) -> ImageGenerationResult:

        if (
            not prompt
            or not prompt.strip()
        ):
            raise ValueError(
                "Image generation prompt "
                "cannot be empty."
            )

        if (
            width <= 0
            or height <= 0
        ):
            raise ValueError(
                "Image dimensions must be "
                "greater than zero."
            )

        if not self._verified:
            self.verify_available()

        (
            workflow_width,
            workflow_height,
        ) = self._normalize_size(
            width,
            height,
        )

        positive_prompt = (
            prompt.strip()
        )

        normalized_negative = (
            negative_prompt.strip()
            if negative_prompt
            else ""
        )

        has_negative_token = (
            self._contains_token(
                self.workflow_template,
                self.NEGATIVE_PROMPT_TOKEN,
            )
        )

        if (
            normalized_negative
            and not has_negative_token
        ):
            positive_prompt = (
                f"{positive_prompt}\n\n"
                "Avoid the following: "
                f"{normalized_negative}"
            )

        seed = self._deterministic_seed(
            positive_prompt=positive_prompt,
            negative_prompt=(
                normalized_negative
            ),
            width=workflow_width,
            height=workflow_height,
        )

        output_prefix = (
            f"{self.output_prefix}_"
            f"{seed}"
        )

        replacements = {
            self.PROMPT_TOKEN:
                positive_prompt,
            self.NEGATIVE_PROMPT_TOKEN:
                normalized_negative,
            self.WIDTH_TOKEN:
                workflow_width,
            self.HEIGHT_TOKEN:
                workflow_height,
            self.SEED_TOKEN:
                seed,
            self.OUTPUT_PREFIX_TOKEN:
                output_prefix,
        }

        workflow = (
            self._substitute(
                self.workflow_template,
                replacements,
            )
        )

        prompt_id = self._queue_prompt(
            workflow
        )

        history_item = (
            self._wait_for_history(
                prompt_id
            )
        )

        image_ref = (
            self._select_image_reference(
                history_item
            )
        )

        raw_image = (
            self._download_image(
                image_ref
            )
        )

        image_bytes = (
            self._normalize_output_image(
                raw_image,
                width=width,
                height=height,
            )
        )

        return ImageGenerationResult(
            image_bytes=image_bytes,
            width=width,
            height=height,
            provider=self.PROVIDER_NAME,
            model=self.model,
            file_extension="jpeg",
        )

    def _queue_prompt(
        self,
        workflow: dict[str, Any],
    ) -> str:

        client_id = str(
            uuid4()
        )

        response = self._post(
            "/prompt",
            json_payload={
                "prompt": workflow,
                "client_id": client_id,
            },
        )

        try:
            payload = response.json()

        except ValueError as exc:
            raise ComfyUIImageAPIError(
                "ComfyUI /prompt returned "
                "a non-JSON response."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ComfyUIImageAPIError(
                "ComfyUI /prompt returned "
                "an unexpected response shape."
            )

        if payload.get(
            "error"
        ):
            raise ComfyUIImageAPIError(
                "ComfyUI rejected the workflow. "
                f"error={payload.get('error')}, "
                "node_errors="
                f"{payload.get('node_errors')}"
            )

        prompt_id = payload.get(
            "prompt_id"
        )

        if not prompt_id:
            raise ComfyUIImageAPIError(
                "ComfyUI /prompt response did "
                "not contain prompt_id."
            )

        return str(
            prompt_id
        )

    def _wait_for_history(
        self,
        prompt_id: str,
    ) -> dict[str, Any]:

        deadline = (
            self.monotonic_fn()
            + self.generation_timeout
        )

        while (
            self.monotonic_fn()
            < deadline
        ):

            response = self._get(
                f"/history/{prompt_id}"
            )

            try:
                payload = response.json()

            except ValueError as exc:
                raise ComfyUIImageAPIError(
                    "ComfyUI history endpoint "
                    "returned non-JSON data."
                ) from exc

            if not isinstance(
                payload,
                dict,
            ):
                raise ComfyUIImageAPIError(
                    "ComfyUI history endpoint "
                    "returned an unexpected shape."
                )

            history_item = (
                payload.get(
                    prompt_id
                )
            )

            if (
                history_item is None
                and "outputs"
                in payload
            ):
                history_item = payload

            if isinstance(
                history_item,
                dict,
            ):
                outputs = (
                    history_item.get(
                        "outputs"
                    )
                )

                if isinstance(
                    outputs,
                    dict,
                ) and outputs:
                    return history_item

                status = (
                    history_item.get(
                        "status",
                        {},
                    )
                )

                if isinstance(
                    status,
                    dict,
                ):
                    status_str = str(
                        status.get(
                            "status_str",
                            "",
                        )
                    ).lower()

                    if status_str in {
                        "error",
                        "failed",
                    }:
                        raise ComfyUIImageAPIError(
                            "ComfyUI workflow "
                            "execution failed. "
                            f"status={status}"
                        )

                    if status.get(
                        "completed"
                    ):
                        raise ComfyUIImageAPIError(
                            "ComfyUI workflow "
                            "completed without an "
                            "image output."
                        )

            self.sleep_fn(
                self.poll_interval
            )

        raise ComfyUIImageAPIError(
            "Timed out waiting for ComfyUI "
            "workflow completion after "
            f"{self.generation_timeout} seconds."
        )

    def _select_image_reference(
        self,
        history_item: dict[str, Any],
    ) -> dict[str, Any]:

        outputs = history_item.get(
            "outputs"
        )

        if not isinstance(
            outputs,
            dict,
        ):
            raise ComfyUIImageAPIError(
                "ComfyUI history did not "
                "contain outputs."
            )

        candidates = []

        if self.output_node_id:

            node_output = outputs.get(
                self.output_node_id
            )

            if not isinstance(
                node_output,
                dict,
            ):
                raise ComfyUIImageAPIError(
                    "Configured ComfyUI output "
                    "node was not found in "
                    "history outputs: "
                    f"{self.output_node_id}"
                )

            images = node_output.get(
                "images"
            )

            if isinstance(
                images,
                list,
            ):
                candidates = [
                    image
                    for image in images
                    if isinstance(
                        image,
                        dict,
                    )
                ]

        else:

            image_nodes = []

            for node_id in sorted(
                outputs,
                key=str,
            ):
                node_output = outputs.get(
                    node_id
                )

                if not isinstance(
                    node_output,
                    dict,
                ):
                    continue

                images = node_output.get(
                    "images"
                )

                valid_images = (
                    [
                        image
                        for image in images
                        if isinstance(
                            image,
                            dict,
                        )
                    ]
                    if isinstance(
                        images,
                        list,
                    )
                    else []
                )

                if valid_images:
                    image_nodes.append(
                        (
                            str(node_id),
                            valid_images,
                        )
                    )

            if len(
                image_nodes
            ) > 1:
                raise ComfyUIImageAPIError(
                    "ComfyUI workflow produced "
                    "images from multiple output "
                    "nodes. Set "
                    "COMFYUI_OUTPUT_NODE_ID "
                    "explicitly."
                )

            if image_nodes:
                candidates = (
                    image_nodes[0][1]
                )

        if not candidates:
            raise ComfyUIImageAPIError(
                "ComfyUI workflow produced "
                "no downloadable image."
            )

        image_ref = candidates[0]

        for key in (
            "filename",
            "subfolder",
            "type",
        ):
            if key not in image_ref:
                raise ComfyUIImageAPIError(
                    "ComfyUI image reference "
                    f"is missing '{key}'."
                )

        return image_ref

    def _download_image(
        self,
        image_ref: dict[str, Any],
    ) -> bytes:

        response = self._get(
            "/view",
            params={
                "filename":
                    image_ref["filename"],
                "subfolder":
                    image_ref["subfolder"],
                "type":
                    image_ref["type"],
            },
        )

        image_bytes = response.content

        if not image_bytes:
            raise ComfyUIImageAPIError(
                "ComfyUI /view returned "
                "empty image bytes."
            )

        return image_bytes

    def _normalize_output_image(
        self,
        image_bytes: bytes,
        *,
        width: int,
        height: int,
    ) -> bytes:

        try:
            with Image.open(
                io.BytesIO(
                    image_bytes
                )
            ) as image:

                image = (
                    ImageOps
                    .exif_transpose(
                        image
                    )
                    .convert(
                        "RGB"
                    )
                )

                if image.size != (
                    width,
                    height,
                ):
                    image = ImageOps.fit(
                        image,
                        (
                            width,
                            height,
                        ),
                        method=(
                            Image.Resampling
                            .LANCZOS
                        ),
                    )

                output = io.BytesIO()

                image.save(
                    output,
                    format="JPEG",
                    quality=(
                        self.jpeg_quality
                    ),
                    optimize=True,
                )

                normalized = (
                    output.getvalue()
                )

        except (
            UnidentifiedImageError,
            OSError,
        ) as exc:
            raise ComfyUIImageAPIError(
                "ComfyUI returned invalid "
                "image bytes."
            ) from exc

        if not normalized:
            raise ComfyUIImageAPIError(
                "Normalized ComfyUI image "
                "is empty."
            )

        return normalized

    def _load_workflow(
        self,
    ) -> dict[str, Any]:

        if not self.workflow_path.is_file():
            raise FileNotFoundError(
                "ComfyUI API workflow file "
                "was not found: "
                f"{self.workflow_path}"
            )

        try:
            payload = json.loads(
                self.workflow_path
                .read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError as exc:
            raise ValueError(
                "ComfyUI workflow file "
                "contains invalid JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "ComfyUI workflow must be "
                "an API-format JSON object."
            )

        return payload

    def _validate_workflow_template(
        self,
    ) -> None:

        missing = [
            token
            for token in sorted(
                self.REQUIRED_TOKENS
            )
            if not self._contains_token(
                self.workflow_template,
                token,
            )
        ]

        if missing:
            raise ValueError(
                "ComfyUI workflow is missing "
                "required placeholders: "
                f"{', '.join(missing)}"
            )

    def _validate_configuration(
        self,
    ) -> None:

        parsed = urlparse(
            self.base_url
        )

        if (
            parsed.scheme
            not in {
                "http",
                "https",
            }
            or not parsed.netloc
        ):
            raise ValueError(
                "COMFYUI_BASE_URL must be a "
                "valid http(s) URL."
            )

        if not self.model:
            raise ValueError(
                "COMFYUI_MODEL_LABEL cannot "
                "be empty."
            )

        if (
            self.request_timeout
            <= 0
        ):
            raise ValueError(
                "COMFYUI_REQUEST_TIMEOUT_SECONDS "
                "must be greater than zero."
            )

        if (
            self.generation_timeout
            <= 0
        ):
            raise ValueError(
                "COMFYUI_GENERATION_TIMEOUT_SECONDS "
                "must be greater than zero."
            )

        if self.poll_interval <= 0:
            raise ValueError(
                "COMFYUI_POLL_INTERVAL_SECONDS "
                "must be greater than zero."
            )

        if not (
            1
            <= self.jpeg_quality
            <= 100
        ):
            raise ValueError(
                "COMFYUI_JPEG_QUALITY must "
                "be between 1 and 100."
            )

        if not self.output_prefix:
            raise ValueError(
                "COMFYUI_OUTPUT_PREFIX cannot "
                "be empty."
            )

    def _normalize_size(
        self,
        width: int,
        height: int,
    ) -> tuple[int, int]:

        multiple = (
            settings.image_size_multiple
        )

        if multiple <= 0:
            raise ValueError(
                "IMAGE_SIZE_MULTIPLE must "
                "be greater than zero."
            )

        return (
            int(
                math.ceil(
                    width
                    / multiple
                )
                * multiple
            ),
            int(
                math.ceil(
                    height
                    / multiple
                )
                * multiple
            ),
        )

    def _deterministic_seed(
        self,
        *,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
    ) -> int:

        payload = (
            f"{positive_prompt}\n"
            f"{negative_prompt}\n"
            f"{width}x{height}\n"
            f"{self.model}\n"
            f"{self.workflow_fingerprint}"
        ).encode(
            "utf-8"
        )

        value = int.from_bytes(
            hashlib.sha256(
                payload
            ).digest()[:8],
            byteorder="big",
            signed=False,
        )

        return value & (
            (1 << 63)
            - 1
        )

    @classmethod
    def _contains_token(
        cls,
        value,
        token: str,
    ) -> bool:

        if isinstance(
            value,
            dict,
        ):
            return any(
                cls._contains_token(
                    item,
                    token,
                )
                for item
                in value.values()
            )

        if isinstance(
            value,
            list,
        ):
            return any(
                cls._contains_token(
                    item,
                    token,
                )
                for item
                in value
            )

        if isinstance(
            value,
            str,
        ):
            return token in value

        return False

    @classmethod
    def _substitute(
        cls,
        value,
        replacements: dict[str, Any],
    ):

        if isinstance(
            value,
            dict,
        ):
            return {
                key:
                    cls._substitute(
                        item,
                        replacements,
                    )
                for key, item
                in value.items()
            }

        if isinstance(
            value,
            list,
        ):
            return [
                cls._substitute(
                    item,
                    replacements,
                )
                for item
                in value
            ]

        if isinstance(
            value,
            str,
        ):
            if value in replacements:
                return replacements[
                    value
                ]

            result = value

            for (
                token,
                replacement,
            ) in replacements.items():
                result = result.replace(
                    token,
                    str(
                        replacement
                    ),
                )

            return result

        return value

    def _get(
        self,
        path: str,
        *,
        params: dict | None = None,
    ):

        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                params=params,
                timeout=(
                    self.request_timeout
                ),
            )

        except requests.RequestException as exc:
            raise ComfyUIImageAPIError(
                "ComfyUI request failed: "
                f"GET {path}"
            ) from exc

        self._raise_for_response(
            response,
            path=path,
        )

        return response

    def _post(
        self,
        path: str,
        *,
        json_payload: dict,
    ):

        try:
            response = self.session.post(
                f"{self.base_url}{path}",
                json=json_payload,
                timeout=(
                    self.request_timeout
                ),
            )

        except requests.RequestException as exc:
            raise ComfyUIImageAPIError(
                "ComfyUI request failed: "
                f"POST {path}"
            ) from exc

        self._raise_for_response(
            response,
            path=path,
        )

        return response

    @staticmethod
    def _raise_for_response(
        response,
        *,
        path: str,
    ) -> None:

        if response.ok:
            return

        detail = ""

        try:
            payload = response.json()

            if isinstance(
                payload,
                dict,
            ):
                detail = (
                    payload.get(
                        "error"
                    )
                    or payload.get(
                        "message"
                    )
                    or str(
                        payload
                    )
                )

        except ValueError:
            detail = (
                getattr(
                    response,
                    "text",
                    "",
                )
                or ""
            )

        raise ComfyUIImageAPIError(
            "ComfyUI request failed. "
            f"path={path}, "
            f"status={response.status_code}, "
            f"detail={detail}"
        )
