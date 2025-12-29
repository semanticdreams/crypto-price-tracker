# Agents Guide

## Scraper inspection workflow

For live DOM inspection with Playwright in restricted environments, use a single approved script that can be updated as needed:

1. Create or edit the approved script (currently `inspect_coingecko.py`).
2. Run it once with approval:

```bash
python inspect_coingecko.py
```

Because the filename stays the same, you only need to approve that one command. Update the script to refine selectors or extract additional DOM details, then re-run the same command.
