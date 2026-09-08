# KAIZEN AI V0.8.5 — Windows Launcher Hotfix

Build: `20260815-v085-orch1`

## Fixed

- Corrected an inverted launcher port range (`9270–9264`) that caused immediate startup failure.
- Local port search is now `9270–9304`.
- Added an explicit invalid-port-range guard in `scripts/launch.py`.
- `START_KAIZEN.bat` now checks the launcher exit code and **pauses on every startup failure** instead of closing silently.
- PowerShell startup now has the same persistent error boundary.
- Startup banners now report the correct release version and port range.

No analytical, Gemini-tool, causal-firewall, simulation, or optimization logic changed from V0.8.2.
