# Gold-and-Silver-tool
Just a small project for tracking gold and silver prices, including its ratio.

## Quick start

```bash
python Setup.py
python tracker_launcher.py
```

## GUI highlights
- Interactive chart (zoom, pan, fit)
- Zoom/pan sensitivity has speed-aware wheel zoom acceleration
- Provider + fallback (`stooq`, `yahoo`, `google`, `twelve`, `metalsapi`, `polygon`)
- Timeline selection (`1M`..`MAX`)
- Live controls: Snapshot, Start Live, Pause Live, Terminate
- Update interval options: 10s / 30s / 1m / 5m
- Axis lock buttons:
  - `🔒X` (lock timeline)
  - `🔒Y` (lock ratio scale)
  - Locks are enforced during both live redraws and direct mouse zoom/pan actions
- Maintainer tuning note:
  - Interaction constants live in `SensitiveViewBox` inside `gs_tracker_qt.py` (`WHEEL_BASE`, gain clamps, speed curve, and `PAN_GAIN`)
- Status island:
  - mode (IDLE/LIVE/PAUSED/ERROR)
  - provider in use
  - activity state
  - last update timestamp (US Eastern EST/EDT when timezone data is available)
- Theme/Customization page:
  - Palettes with swatches and names under each preview
  - font family, font size, font weight
  - history/live line widths

## Easy installation
All setup and launch flows are simple (`Setup.py`, `tracker_launcher.py`).

## Install dependencies manually (optional)
```bash
python -m pip install -r requirements.txt
```

## Provider setup (API feeds)
Symbols are normalized internally to `XAUUSD` and `XAGUSD` (USD per troy ounce), regardless of whether you pass `GC=F`, `SI=F`, `XAU/USD`, or `XAG/USD`.

### Free-ish option: Twelve Data
- Provider key: `twelve`
- Env vars:
  - `TWELVE_DATA_API_TOKEN`
  - `TWELVE_DATA_BASE_URL` (optional, default `https://api.twelvedata.com`)
- Notes:
  - Free tier is typically rate-limited; keep refresh intervals conservative (for example `30s`+ in live mode).
  - Supports quote metadata like market-open status and optional bid/ask fields when available.

### Premium options
#### Metals-API (LBMA-aligned spot style feed)
- Provider key: `metalsapi`
- Env vars:
  - `METALS_API_TOKEN`
  - `METALS_API_BASE_URL` (optional, default `https://metals-api.com/api`)
- Notes:
  - Common plans have stricter request quotas than raw exchange feeds; avoid very tight polling loops.

#### Polygon snapshot proxy
- Provider key: `polygon`
- Env vars:
  - `POLYGON_API_TOKEN`
  - `POLYGON_BASE_URL` (optional, default `https://api.polygon.io`)
- Notes:
  - Requires a paid plan for reliable precious-metals proxy coverage in many accounts.

If a premium/free API provider is selected without credentials, the app raises an explicit configuration error. The CLI also auto-falls back to `stooq` when using `twelve`, `metalsapi`, or `polygon` with `--fallback-provider none`.
