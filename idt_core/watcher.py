"""
Watcher — monitors a directory for new images and describes them automatically.

Uses polling (no extra dependencies). Suitable for automation pipelines
like downloading NYT images and getting descriptions without manual intervention.

Usage via CLI:
  idt watch ~/Downloads/NYT/ --interval 30 --provider anthropic

The watcher:
  1. Does an initial describe pass on startup
  2. Polls every --interval seconds for new image files
  3. Describes any images that appeared since the last scan
  4. Prints each description to stdout as it completes (live output)
  5. Runs until interrupted with Ctrl+C
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Optional

from .pipeline import Pipeline, PipelineEvent, RunOptions
from .project import Project
from .providers.base import BaseProvider
from .scanner import scan_images


@dataclass
class WatchOptions:
    interval_seconds: int = 30
    prompt_name: str = "detailed"
    prompt_text: str = ""
    on_event: Optional[Callable[[PipelineEvent], None]] = None
    on_poll: Optional[Callable[[int], None]] = None   # called with seconds until next poll


class Watcher:
    """
    Continuously monitors source_dir for new images and describes them.
    Yields PipelineEvent objects — caller decides how to display them.
    """

    def __init__(self, project: Project, provider: BaseProvider, options: WatchOptions):
        self.project = project
        self.provider = provider
        self.options = options

    def run(self) -> Iterator[PipelineEvent]:
        """
        Yield events indefinitely.
        Raises KeyboardInterrupt when the user presses Ctrl+C — callers should catch it.
        """
        run_opts = RunOptions(
            prompt_name=self.options.prompt_name,
            prompt_text=self.options.prompt_text,
        )
        pipeline = Pipeline(self.project, self.provider)
        known_paths: set[Path] = set()

        # Initial pass
        initial_queue = list(self.project.undescribed())
        if initial_queue:
            for event in pipeline.run(run_opts):
                known_paths.add(event.item.source_path)
                yield event
        else:
            # Seed known_paths from existing items so we don't re-process them
            for item in self.project.items():
                known_paths.add(item.source_path)

        # Poll loop
        while True:
            remaining = self.options.interval_seconds
            while remaining > 0:
                if self.options.on_poll:
                    self.options.on_poll(remaining)
                time.sleep(min(5, remaining))
                remaining -= 5

            current_paths = set(scan_images(self.project.source_dir))
            new_paths = current_paths - known_paths

            if new_paths:
                # Reload the project to pick up any sidecar files written externally
                fresh_project = Project.open(self.project.source_dir)
                fresh_pipeline = Pipeline(fresh_project, self.provider)

                # Describe only the new files
                new_items = [
                    item for item in fresh_project.undescribed()
                    if item.source_path in new_paths
                ]
                for item in new_items:
                    from .pipeline import PipelineEvent as _E
                    events = list(fresh_pipeline.run(
                        RunOptions(
                            prompt_name=run_opts.prompt_name,
                            prompt_text=run_opts.prompt_text,
                            limit=len(new_items),
                        )
                    ))
                    for event in events:
                        known_paths.add(event.item.source_path)
                        yield event
                    break  # pipeline.run already processes all queued items

            known_paths |= new_paths
