# Contributing to PantryFlow

Thanks for helping make everyday cooking simpler.

## Before opening a pull request

1. Keep changes focused on the core loop: pantry → recommendation → cooking → inventory update.
2. Do not commit `.env` files, API keys, local databases, build output, or dependencies.
3. Add or update a backend test when changing inventory or recommendation rules.
4. Run the checks below.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider

cd ..\frontend
bun run build
```

For feature proposals, open an issue first and explain the user problem before the implementation.
