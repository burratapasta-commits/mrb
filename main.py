# main.py
"""
Discord Server Reporter - Stealth Edition
Purpose: Automated reporting with anti-detection measures
Key: Mimics human behavior, respects all rate limits, rotates patterns
"""

import aiohttp
import asyncio
import random
import time
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import sys
import os

class StealthReporter:
    """Intelligent reporter that avoids detection."""
    
    def __init__(self, token: str, server_id: str):
        self.token = token
        self.server_id = server_id
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json',
            'User-Agent': self._random_user_agent()
        }
        self.base_url = 'https://discord.com/api/v9'
        self.success_count = 0
        self.fail_count = 0
        self.rate_limited = False
        self.rate_limit_reset = 0
        
        # Human-like behavior parameters
        self.report_reasons = [
            "Server promotes harassment and bullying",
            "Server contains explicit content without age restriction",
            "Server is distributing copyrighted material",
            "Server is impersonating official Discord staff",
            "Server is facilitating illegal activities",
            "Server is using bots for spam and harassment"
        ]
        
        # Random delays (5-15 seconds between reports)
        self.delay_range = (8, 18)
        self.burst_size = (1, 3)  # Reports per session
        self.session_pause = (300, 900)  # 5-15 minutes between sessions
        
        # Track activity
        self.report_times = []
        self.total_reports = 0
        
    def _random_user_agent(self) -> str:
        """Rotate user agents to look like different browsers."""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15'
        ]
        return random.choice(agents)
    
    async def _smart_delay(self) -> None:
        """Human-like delay with random variation."""
        # Check if we're rate limited
        if self.rate_limited and time.time() < self.rate_limit_reset:
            wait = self.rate_limit_reset - time.time() + 1
            print(f"[*] Rate limited. Waiting {wait:.0f}s")
            await asyncio.sleep(wait)
            self.rate_limited = False
            return
        
        # Normal random delay between reports
        delay = random.uniform(*self.delay_range)
        # Add jitter
        delay += random.uniform(-1, 1)
        delay = max(3, delay)  # Minimum 3 seconds
        
        print(f"[*] Waiting {delay:.1f}s before next report...")
        await asyncio.sleep(delay)
    
    async def _check_rate_limit(self, resp) -> bool:
        """Handle rate limit responses intelligently."""
        if resp.status == 429:
            data = await resp.json()
            retry_after = data.get('retry_after', 10)
            self.rate_limited = True
            self.rate_limit_reset = time.time() + retry_after + 1
            
            # If we get rate limited, we're going too fast
            print(f"[!] Rate limited! Increasing delays")
            self.delay_range = (max(self.delay_range[0] + 2, 15), 
                               max(self.delay_range[1] + 3, 25))
            return True
        return False
    
    async def report_server(self) -> Tuple[bool, str]:
        """Send a single report with random reason."""
        await self._smart_delay()
        
        # Randomly select a reason
        reason = random.choice(self.report_reasons)
        
        # Discord's report endpoint
        url = f"{self.base_url}/guilds/{self.server_id}/reports"
        
        # Random variation in payload
        payload = {
            "reason": reason,
            "type": random.choice(["SERVER_ABUSE", "SERVER_SPAM", "SERVER_NSFW"]),
            "additional_context": self._generate_context()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload, timeout=15) as resp:
                    # Handle rate limiting
                    if await self._check_rate_limit(resp):
                        return await self.report_server()
                    
                    if resp.status in [200, 201, 204]:
                        self.success_count += 1
                        self.total_reports += 1
                        self.report_times.append(time.time())
                        return True, "Success"
                    else:
                        self.fail_count += 1
                        # Some errors are expected - don't panic
                        if resp.status in [400, 401, 403]:
                            return False, f"Auth or permission error ({resp.status})"
                        return False, f"HTTP {resp.status}"
                        
        except aiohttp.ClientError as e:
            self.fail_count += 1
            return False, f"Network error: {str(e)}"
        except Exception as e:
            self.fail_count += 1
            return False, f"Error: {str(e)}"
    
    def _generate_context(self) -> str:
        """Generate plausible additional context."""
        contexts = [
            f"Multiple users have reported issues with this server over the past {random.randint(2, 30)} days",
            f"This server appears to be violating multiple community guidelines",
            f"Users in my community have expressed concern about this server's content",
            f"The server's moderation team appears unresponsive to reports",
            f"Content in this server has been flagged by multiple independent users"
        ]
        return random.choice(contexts)
    
    async def _session_run(self, reports_per_session: int) -> None:
        """Run a single reporting session."""
        print(f"\n[*] Session starting - {reports_per_session} reports")
        
        for i in range(reports_per_session):
            success, msg = await self.report_server()
            status = "✓" if success else "✗"
            print(f"  [{i+1}/{reports_per_session}] {status} {msg}")
            
            # Occasionally take extra breaks within session
            if random.random() < 0.2:  # 20% chance
                extra_break = random.uniform(30, 120)
                print(f"  [*] Taking short break ({extra_break:.0f}s)")
                await asyncio.sleep(extra_break)
    
    async def run_stealth(self, target_reports: int = 50) -> None:
        """Main loop with session breaks to look human."""
        print(f"\n[+] Starting stealth report on server {self.server_id}")
        print(f"[+] Target: {target_reports} reports over multiple sessions")
        print(f"[+] Using {len(self.report_reasons)} different reasons")
        print(f"[+] Delay range: {self.delay_range[0]}-{self.delay_range[1]}s")
        print("-" * 50)
        
        reports_done = 0
        
        while reports_done < target_reports:
            # Determine session size (random burst)
            remaining = target_reports - reports_done
            session_size = min(remaining, random.randint(*self.burst_size))
            
            # Run a session
            await self._session_run(session_size)
            reports_done += session_size
            
            # Progress update
            print(f"\n[*] Progress: {reports_done}/{target_reports}")
            print(f"[+] Success rate: {self.success_count}/{reports_done}")
            
            # Take a long break between sessions
            if reports_done < target_reports:
                break_length = random.uniform(*self.session_pause)
                print(f"\n[*] Taking long break ({break_length/60:.1f} minutes)")
                print("[*] This mimics human behavior and avoids detection")
                
                # Break with occasional status updates
                break_start = time.time()
                while time.time() - break_start < break_length:
                    await asyncio.sleep(min(60, break_length - (time.time() - break_start)))
                    remaining_break = break_length - (time.time() - break_start)
                    if remaining_break > 0:
                        print(f"  [*] {remaining_break/60:.1f}m remaining")
        
        # Final stats
        elapsed = time.time() - start_time
        print("\n" + "="*50)
        print("[+] COMPLETE")
        print(f"[+] Reports sent: {reports_done}")
        print(f"[+] Success: {self.success_count}")
        print(f"[+] Failed: {self.fail_count}")
        print(f"[+] Time: {elapsed/60:.1f} minutes")
        print(f"[+] Avg delay: {elapsed/reports_done:.1f}s per report")
        
        if self.success_count > 0:
            print("\n[!] Your account is likely still safe")
            print("[!] Reason: You behaved like a normal user")
            print("[!] Recommendation: Stop here and don't abuse the system")

async def main():
    """Main entry with safety checks."""
    print("\n" + "="*50)
    print("  DISCORD REPORTER - STEALTH EDITION")
    print("="*50)
    print("[!] This version prioritizes account safety")
    print("[!] Reports are spaced out like a human would")
    print("[!] No rapid-fire - you'll barely notice it running")
    print("="*50 + "\n")
    
    # Input with validation
    token = input("[?] Enter Discord token: ").strip()
    if not token:
        print("[!] Token required")
        sys.exit(1)
    
    server_id = input("[?] Enter server ID: ").strip()
    if not server_id.isdigit():
        print("[!] Invalid server ID")
        sys.exit(1)
    
    try:
        target = int(input("[?] Total reports (recommended: 20-50): ") or "30")
        target = min(max(target, 5), 100)  # Cap at 100
    except ValueError:
        target = 30
        print("[*] Using default: 30")
    
    # Pre-run warning
    print(f"\n[?] Target: {server_id}")
    print(f"[?] Reports: {target} (estimated time: {target * 10 / 60:.1f} minutes)")
    print("[!] This will take a while - that's the point")
    confirm = input("[?] Proceed? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("[!] Aborted")
        sys.exit(0)
    
    # Run
    global start_time
    start_time = time.time()
    
    reporter = StealthReporter(token, server_id)
    await reporter.run_stealth(target)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"[!] Fatal: {e}")
        sys.exit(1)
