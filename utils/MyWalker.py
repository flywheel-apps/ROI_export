import logging

from flywheel_gear_toolkit.utils.datatypes import Container
from flywheel_gear_toolkit.utils import walker

log = logging.getLogger("export-ROI")


class MyWalker(walker.Walker):
    def queue_children(self, element: Container) -> None:
        """Returns children of the element.

        Args:
            element (Container): container to find children of.

        """
        container_type = element.container_type

        # No children of files
        if container_type == "file":
            return

        if container_type == "analysis":
            return

        element = element.reload()
        log.info(
            f"Queueing children for {container_type} {element.label or element.code}"
        )

        self.deque.extend(element.files or [])

        # Make sure that the analyses attribute is a list before iterating
        self.deque.extend(element.analyses or [])
        if container_type == "project":
            self.deque.extend(element.subjects())
        elif container_type == "subject":
            self.deque.extend(element.sessions())
        elif container_type == "session":
            self.deque.extend(element.acquisitions())
