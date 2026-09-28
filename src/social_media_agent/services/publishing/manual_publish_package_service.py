import hashlib
import json
import mimetypes
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
)
from social_media_agent.models.manual_publish_package import (
    ManualPublishFile,
    ManualPublishPackage,
)
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)
from social_media_agent.models.publication_plan import (
    PublicationPlan,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.services.media_store.local_store import (
    LocalMediaStore,
)
from social_media_agent.services.publishing.publication_plan_service import (
    PublicationPlanService,
)


class ManualPublishPackageService:

    def __init__(
        self,
        *,
        persistence,
        media_store,
        package_root: str | Path | None = None,
        generated_assets_root: str | Path | None = None,
    ):
        self.persistence = persistence
        self.media_store = media_store

        self.package_root = Path(
            package_root
            if package_root is not None
            else settings.publish_packages_dir
        ).resolve()

        self.generated_assets_store = (
            LocalMediaStore(
                local_root=(
                    generated_assets_root
                    if generated_assets_root
                    is not None
                    else settings.generated_assets_dir
                )
            )
        )

        self.plan_service = (
            PublicationPlanService(
                persistence=persistence
            )
        )

    def build(
        self,
        run_id: str,
    ) -> ManualPublishPackage:

        run = self.persistence.get_run(
            run_id
        )

        if run is None:
            raise ValueError(
                f"Content run not found: {run_id}"
            )

        if (
            run.status
            != RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ):
            raise ValueError(
                "Manual publish package requires "
                "approved_for_publishing status. "
                f"Current status: {run.status}"
            )

        plan = (
            self.plan_service
            .load_latest(
                run_id
            )
        )

        if plan is None:
            raise ValueError(
                "Manual publish package requires "
                "a publication plan."
            )

        self.plan_service.assert_current(
            run_id=run_id,
            plan=plan,
        )

        self.media_store.verify_access()

        package_key = (
            f"{run_id}/{plan.plan_id}"
        )

        final_directory = (
            self.package_root
            / run_id
            / plan.plan_id
        )

        staging_directory = (
            self.package_root
            / run_id
            / (
                f".{plan.plan_id}.tmp-"
                f"{uuid4().hex[:8]}"
            )
        )

        if staging_directory.exists():
            shutil.rmtree(
                staging_directory
            )

        staging_directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        created_at = datetime.now(
            timezone.utc
        )

        local_entries: list[
            dict
        ] = []

        try:
            self._write_json(
                staging_directory
                / "publication_plan.json",
                plan.model_dump(
                    mode="json"
                ),
            )

            local_entries.append(
                self._entry(
                    staging_directory
                    / "publication_plan.json",
                    staging_directory,
                    platform=None,
                    role="publication_plan",
                )
            )

            for platform in plan.platforms:
                local_entries.extend(
                    self._write_platform_files(
                        plan=plan,
                        platform=platform,
                        root=staging_directory,
                    )
                )

            creative = self._load_creative(
                plan
            )

            if creative is not None:
                local_entries.extend(
                    self._write_storyboards(
                        creative=creative,
                        root=staging_directory,
                        platforms=set(
                            plan.platforms
                        ),
                    )
                )

            generated = self._load_generated(
                plan
            )

            if generated is not None:
                local_entries.extend(
                    self._copy_generated_media(
                        generated=generated,
                        root=staging_directory,
                        platforms=set(
                            plan.platforms
                        ),
                    )
                )

            if final_directory.exists():
                shutil.rmtree(
                    final_directory
                )

            final_directory.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            staging_directory.replace(
                final_directory
            )

            stored_files = []

            for local_entry in local_entries:

                relative_path = str(
                    Path(
                        package_key
                    )
                    / local_entry[
                        "relative_path"
                    ]
                ).replace(
                    "\\",
                    "/",
                )

                stored_media = (
                    self.media_store
                    .store(
                        relative_path
                    )
                )

                stored_files.append(
                    ManualPublishFile(
                        relative_path=(
                            local_entry[
                                "relative_path"
                            ]
                        ),
                        platform=(
                            local_entry[
                                "platform"
                            ]
                        ),
                        role=(
                            local_entry[
                                "role"
                            ]
                        ),
                        content_type=(
                            local_entry[
                                "content_type"
                            ]
                        ),
                        size_bytes=(
                            local_entry[
                                "size_bytes"
                            ]
                        ),
                        sha256=(
                            local_entry[
                                "sha256"
                            ]
                        ),
                        source_provider=(
                            local_entry.get(
                                "source_provider"
                            )
                        ),
                        source_model=(
                            local_entry.get(
                                "source_model"
                            )
                        ),
                        stored_media=(
                            stored_media
                        ),
                    )
                )

            manifest_payload = {
                "schema_version": 1,
                "run_id": run_id,
                "publication_plan_id":
                    plan.plan_id,
                "created_at":
                    created_at.isoformat(),
                "platforms":
                    plan.platforms,
                "artifact_refs": [
                    ref.model_dump(
                        mode="json"
                    )
                    for ref
                    in plan.artifact_refs
                ],
                "files": [
                    file.model_dump(
                        mode="json"
                    )
                    for file
                    in stored_files
                ],
            }

            manifest_path = (
                final_directory
                / "manifest.json"
            )

            self._write_json(
                manifest_path,
                manifest_payload,
            )

            manifest_local = self._entry(
                manifest_path,
                final_directory,
                platform=None,
                role="manifest",
            )

            manifest_storage_key = str(
                Path(
                    package_key
                )
                / "manifest.json"
            ).replace(
                "\\",
                "/",
            )

            manifest_stored = (
                self.media_store
                .store(
                    manifest_storage_key
                )
            )

            manifest_file = (
                ManualPublishFile(
                    relative_path=(
                        "manifest.json"
                    ),
                    platform=None,
                    role="manifest",
                    content_type=(
                        manifest_local[
                            "content_type"
                        ]
                    ),
                    size_bytes=(
                        manifest_local[
                            "size_bytes"
                        ]
                    ),
                    sha256=(
                        manifest_local[
                            "sha256"
                        ]
                    ),
                    stored_media=(
                        manifest_stored
                    ),
                )
            )

            package = ManualPublishPackage(
                run_id=run_id,
                publication_plan_id=(
                    plan.plan_id
                ),
                store_provider=(
                    self.media_store
                    .PROVIDER_NAME
                ),
                package_key=package_key,
                platforms=plan.platforms,
                artifact_refs=(
                    plan.artifact_refs
                ),
                files=[
                    *stored_files,
                    manifest_file,
                ],
                created_at=created_at,
            )

            self.persistence.save_model(
                run_id,
                ArtifactType
                .MANUAL_PUBLISH_PACKAGE,
                package,
            )

            return package

        except Exception:

            if staging_directory.exists():
                shutil.rmtree(
                    staging_directory,
                    ignore_errors=True,
                )

            raise

    def _write_platform_files(
        self,
        *,
        plan: PublicationPlan,
        platform: str,
        root: Path,
    ) -> list[dict]:

        ref = plan.get_ref(
            artifact_type=(
                ArtifactType
                .PLATFORM_CONTENT
                .value
            ),
            platform=platform,
        )

        if ref is None:
            raise ValueError(
                "Publication plan is missing "
                "platform content reference "
                f"for {platform}."
            )

        payload = (
            self.persistence
            .get_payload_at_version(
                run_id=plan.run_id,
                artifact_type=(
                    ArtifactType
                    .PLATFORM_CONTENT
                ),
                platform=platform,
                version=ref.version,
            )
        )

        if payload is None:
            raise ValueError(
                "Frozen platform content "
                "could not be loaded. "
                f"platform={platform}, "
                f"version={ref.version}"
            )

        platform_root = (
            root
            / platform
        )

        platform_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        entries = []

        full_content = (
            platform_root
            / "platform_content.json"
        )

        self._write_json(
            full_content,
            payload,
        )

        entries.append(
            self._entry(
                full_content,
                root,
                platform=platform,
                role="platform_content",
            )
        )

        if platform == "instagram":
            package = (
                InstagramPackage
                .model_validate(
                    payload
                )
            )

            entries.extend(
                self._write_text_files(
                    root=root,
                    platform_root=platform_root,
                    platform=platform,
                    files={
                        "caption.txt":
                            package.caption,
                        "hashtags.txt":
                            " ".join(
                                package.hashtags
                            ),
                        "call_to_action.txt":
                            package.call_to_action,
                        "reel_hook.txt":
                            package.reel_hook,
                        "reel_script.txt":
                            package.reel_script,
                    },
                )
            )

            carousel = (
                platform_root
                / "carousel_content.json"
            )

            self._write_json(
                carousel,
                [
                    slide.model_dump(
                        mode="json"
                    )
                    for slide
                    in package.carousel_slides
                ],
            )

            entries.append(
                self._entry(
                    carousel,
                    root,
                    platform=platform,
                    role="carousel_content",
                )
            )

        elif platform == "x":
            package = (
                XPackage
                .model_validate(
                    payload
                )
            )

            entries.extend(
                self._write_text_files(
                    root=root,
                    platform_root=platform_root,
                    platform=platform,
                    files={
                        "post.txt":
                            package.single_post,
                        "thread.txt":
                            "\n\n".join(
                                package.thread
                            ),
                        "call_to_action.txt":
                            package.call_to_action,
                    },
                )
            )

        elif platform == "youtube":
            package = (
                YouTubePackage
                .model_validate(
                    payload
                )
            )

            entries.extend(
                self._write_text_files(
                    root=root,
                    platform_root=platform_root,
                    platform=platform,
                    files={
                        "title.txt":
                            package.title,
                        "description.txt":
                            package.description,
                        "script.txt":
                            package.script,
                        "call_to_action.txt":
                            package.call_to_action,
                    },
                )
            )

            for filename, value, role in (
                (
                    "chapters.json",
                    package.chapters,
                    "chapters",
                ),
                (
                    "shorts_hooks.json",
                    package.shorts_hooks,
                    "shorts_hooks",
                ),
            ):
                path = (
                    platform_root
                    / filename
                )

                self._write_json(
                    path,
                    value,
                )

                entries.append(
                    self._entry(
                        path,
                        root,
                        platform=platform,
                        role=role,
                    )
                )

        else:
            raise ValueError(
                "Unsupported platform in "
                "publication plan: "
                f"{platform}"
            )

        return entries

    def _write_storyboards(
        self,
        *,
        creative: CreativeAssetBundle,
        root: Path,
        platforms: set[str],
    ) -> list[dict]:

        entries = []

        for storyboard in creative.storyboards:

            if (
                storyboard.platform
                not in platforms
            ):
                continue

            platform_root = (
                root
                / storyboard.platform
            )

            platform_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            filename = (
                f"{self._safe_name(storyboard.asset_type)}"
                ".json"
            )

            path = (
                platform_root
                / filename
            )

            self._write_json(
                path,
                storyboard.model_dump(
                    mode="json"
                ),
            )

            entries.append(
                self._entry(
                    path,
                    root,
                    platform=(
                        storyboard.platform
                    ),
                    role=(
                        storyboard.asset_type
                    ),
                )
            )

        return entries

    def _copy_generated_media(
        self,
        *,
        generated: GeneratedAssetBundle,
        root: Path,
        platforms: set[str],
    ) -> list[dict]:

        entries = []

        assets = sorted(
            [
                asset
                for asset
                in [
                    *generated.images,
                    *generated.videos,
                ]
                if asset.platform
                in platforms
            ],
            key=lambda asset: (
                asset.platform,
                asset.asset_type,
                asset.storage_key,
            ),
        )

        for asset in assets:

            source_ref = (
                self.generated_assets_store
                .store(
                    asset.storage_key
                )
            )

            source_path = (
                self.generated_assets_store
                .resolve_path(
                    source_ref
                )
            )

            extension = (
                source_path.suffix.lower()
            )

            if not extension:
                raise ValueError(
                    "Generated media file has "
                    "no extension: "
                    f"{asset.storage_key}"
                )

            media_root = (
                root
                / asset.platform
                / "media"
            )

            media_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            filename = (
                f"{self._safe_name(asset.asset_type)}"
                f"{extension}"
            )

            target = (
                media_root
                / filename
            )

            if target.exists():
                raise ValueError(
                    "Duplicate generated media "
                    "asset type in package: "
                    f"{asset.platform}/"
                    f"{asset.asset_type}"
                )

            shutil.copy2(
                source_path,
                target,
            )

            entries.append(
                self._entry(
                    target,
                    root,
                    platform=asset.platform,
                    role=asset.asset_type,
                    source_provider=(
                        asset.provider
                    ),
                    source_model=(
                        asset.model
                    ),
                )
            )

        return entries

    def _load_generated(
        self,
        plan: PublicationPlan,
    ) -> GeneratedAssetBundle | None:

        ref = plan.get_ref(
            artifact_type=(
                ArtifactType
                .GENERATED_ASSETS
                .value
            )
        )

        if ref is None:
            return None

        payload = (
            self.persistence
            .get_payload_at_version(
                run_id=plan.run_id,
                artifact_type=(
                    ArtifactType
                    .GENERATED_ASSETS
                ),
                version=ref.version,
            )
        )

        if payload is None:
            raise ValueError(
                "Frozen generated-assets "
                "artifact could not be loaded."
            )

        return (
            GeneratedAssetBundle
            .model_validate(
                payload
            )
        )

    def _load_creative(
        self,
        plan: PublicationPlan,
    ) -> CreativeAssetBundle | None:

        ref = plan.get_ref(
            artifact_type=(
                ArtifactType
                .CREATIVE_ASSETS
                .value
            )
        )

        if ref is None:
            return None

        payload = (
            self.persistence
            .get_payload_at_version(
                run_id=plan.run_id,
                artifact_type=(
                    ArtifactType
                    .CREATIVE_ASSETS
                ),
                version=ref.version,
            )
        )

        if payload is None:
            raise ValueError(
                "Frozen creative-assets "
                "artifact could not be loaded."
            )

        return (
            CreativeAssetBundle
            .model_validate(
                payload
            )
        )

    def _write_text_files(
        self,
        *,
        root: Path,
        platform_root: Path,
        platform: str,
        files: dict[str, str],
    ) -> list[dict]:

        entries = []

        for filename, value in files.items():

            path = (
                platform_root
                / filename
            )

            path.write_text(
                value.rstrip()
                + "\n",
                encoding="utf-8",
            )

            entries.append(
                self._entry(
                    path,
                    root,
                    platform=platform,
                    role=(
                        Path(filename)
                        .stem
                    ),
                )
            )

        return entries

    @staticmethod
    def _write_json(
        path: Path,
        payload,
    ) -> None:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _entry(
        path: Path,
        root: Path,
        *,
        platform: str | None,
        role: str,
        source_provider: str | None = None,
        source_model: str | None = None,
    ) -> dict:

        data = path.read_bytes()

        return {
            "relative_path":
                str(
                    path.relative_to(
                        root
                    )
                ).replace(
                    "\\",
                    "/",
                ),
            "platform":
                platform,
            "role":
                role,
            "content_type":
                (
                    mimetypes.guess_type(
                        path.name
                    )[0]
                    or "application/octet-stream"
                ),
            "size_bytes":
                len(data),
            "sha256":
                hashlib.sha256(
                    data
                ).hexdigest(),
            "source_provider":
                source_provider,
            "source_model":
                source_model,
        }

    @staticmethod
    def _safe_name(
        value: str,
    ) -> str:

        normalized = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            value.strip().lower(),
        )

        normalized = (
            normalized.strip(
                "_"
            )
        )

        if not normalized:
            raise ValueError(
                "Package file name cannot "
                "be empty."
            )

        return normalized
