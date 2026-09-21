from .cli import main

try:
    main()
except KeyboardInterrupt:          # Ctrl+C: stop quietly (screens restore themselves on the way out)
    print()
    raise SystemExit(130)
