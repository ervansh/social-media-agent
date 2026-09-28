import subprocess
from pathlib import Path
from typing import Protocol


class CommandRunner(Protocol):

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
    ) -> None:
        ...


class SubprocessCommandRunner:

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
    ) -> None:

        try:
            subprocess.run(
                args,
                cwd=(
                    str(cwd)
                    if cwd is not None
                    else None
                ),
                check=True,
                capture_output=True,
                text=True,
            )

        except FileNotFoundError as exc:
            raise RuntimeError(
                "FFmpeg executable was not found. "
                "Install FFmpeg or configure "
                "FFMPEG_BINARY."
            ) from exc

        except subprocess.CalledProcessError as exc:

            stderr = (
                exc.stderr
                or exc.stdout
                or str(exc)
            )

            raise RuntimeError(
                "FFmpeg command failed: "
                f"{stderr.strip()}"
            ) from exc
