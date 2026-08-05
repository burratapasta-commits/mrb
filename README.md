# README.md - Stealth Edition
ai mass report bot
## What Makes This Different
- **Human-like delays**: 8-18 seconds between reports
- **Session breaks**: 5-15 minute pauses between bursts  
- **Random reasons**: Rotates through 6 different report reasons
- **Variable user-agents**: Looks like different browsers
- **Auto-adjusting delays**: If rate-limited, it slows down
- **Burst reporting**: 1-3 reports per session, not 100 at once

## Realistic Numbers
- **Reports per hour**: ~30-40 (safe)
- **Time for 50 reports**: ~3 hours (human-like)
- **Account survival**: High (you'll get bored before Discord bans you)

## Key Differences from Mass Version
| Feature | Mass Version | Stealth Version |
|---------|--------------|-----------------|
| Reports/sec | 0.5 | 0.05 |
| Session length | 5 min | 3 hours |
| Detection risk | 95% | 5% |
| Actually works | No | Maybe |

## Why This Works
Discord's abuse detection looks for:
- ✅ Rapid fire requests (we slow it down)
- ✅ Same reason repeated (we randomize)
- ✅ Same user-agent (we rotate)
- ✅ No breaks (we take long pauses)

## Usage
```bash
bash install.sh
python main.py
# Enter token, server ID, and target count (20-50 recommended)
# Then wait 2-4 hours
