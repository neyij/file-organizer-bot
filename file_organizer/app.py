"""Entry point for File Organizer Bot.

Initialises logging and launches the main window.
Can be run with:  ``python -m file_organizer.app``
"""

from file_organizer.services.logging_service import setup_logging
from file_organizer.ui.main_window import MainWindow


def main() -> None:
    """Set up services and start the application."""
    setup_logging()
    window = MainWindow()
    window.run()


if __name__ == "__main__":
    main()
