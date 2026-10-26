"""Support ``python -m gwrc`` with the console-script behavior."""

from gwrc.cli.main import main

raise SystemExit(main())
