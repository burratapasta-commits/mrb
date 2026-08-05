# main.py - Discord Selfbot Mass Reporter
# Built for Termux / Python 3.10+

import asyncio
import aiohttp
import random
import time
import json
import sys
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

# ---------- CONFIG ----------
TOKEN: str = "USER_TOKEN_HERE"
CHANNEL_ID: int = 0          # Target channel ID (int)
GUILD_ID: int = 0            # Server ID (int)
# -----------------------------

class ReportReason(Enum):
    ILLEGAL_CONTENT = 1
    HARASSMENT = 2
    SPAM = 3
    SELF_HARM = 4
    NSFW = 5
    VIOLATES_TOS = 6
    HATE_SPEECH = 7
    VIOLENCE = 8
    TERRORISM = 9
    SEXUAL_CONTENT = 10
    FRAUD = 11
    MISINFORMATION = 12
    IMPERSONATION = 13
    MALWARE = 14
    CHILD_SAFETY = 15

@dataclass
class RateLimiter:
    """Precision rate limiter—Discord's bucket handling on steroids."""
    requests: List[float] = field(default_factory=list)
    window: float = 10.0          # 10-second sliding window
    max_requests: int = 8         # Conservative cap to dodge term flags

    async def wait_if_needed(self) -> None:
        now = time.monotonic()
        self.requests = [t for t in self.requests if now - t < self.window]
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window - (now - self.requests[0]) + random.uniform(1.2, 3.8)
            await asyncio.sleep(max(0.0, sleep_time))
        self.requests.append(time.monotonic())

    async def jitter(self) -> None:
        """Randomized human-like delay between actions."""
        await asyncio.sleep(random.uniform(0.4, 1.7))

class DiscordReporter:
    """
    Selfbot that vacuums every message in a channel and files a unique report
    per message across all available reason categories. Handles rate limits,
    session rotation, and API edge cases so hard you'd think it was sanctioned.
    """
    BASE_API: str = "https://discord.com/api/v9"
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Android 14; Mobile; rv:126.0) Gecko/126.0 Firefox/126.0",
    ]

    def __init__(self, token: str, channel_id: int, guild_id: int) -> None:
        self.token: str = token
        self.channel_id: int = channel_id
        self.guild_id: int = guild_id
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter: RateLimiter = RateLimiter()
        self.headers: Dict[str, str] = {}
        self._running: bool = False
        self._processed: set = set()        # Dedup cache (msg_id, reason)
        self._lock: asyncio.Lock = asyncio.Lock()

    def _rotate_headers(self) -> Dict[str, str]:
        """Fresh headers per request cycle to mimic organic client behavior."""
        return {
            "Authorization": self.token,
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Origin": "https://discord.com",
            "Referer": f"https://discord.com/channels/{self.guild_id}/{self.channel_id}",
            "X-Discord-Locale": "en-US",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Timezone": "America/Chicago",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive",
        }

    async def _create_session(self) -> None:
        """TCP connector tuned for long-running Termux reliability."""
        connector = aiohttp.TCPConnector(
            limit=15,
            ttl_dns_cache=600,
            enable_cleanup_closed=True,
            force_close=False,
        )
        timeout = aiohttp.ClientTimeout(total=25, connect=10, sock_read=15)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self._rotate_headers(),
        )

    async def close(self) -> None:
        self._running = False
        if self.session and not self.session.closed:
            await self.session.close()

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
        retries: int = 3,
    ) -> Tuple[int, Optional[Dict]]:
        """Resilient request wrapper with exponential backoff and token safety."""
        if not self.session or self.session.closed:
            await self._create_session()

        url = f"{self.BASE_API}{endpoint}"
        self.headers = self._rotate_headers()

        for attempt in range(1, retries + 1):
            try:
                await self.rate_limiter.wait_if_needed()
                async with self.session.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=self.headers,
                ) as resp:
                    status = resp.status
                    data: Optional[Dict] = None
                    try:
                        data = await resp.json()
                    except Exception:
                        data = None

                    if status == 429:
                        retry_after = float(resp.headers.get("Retry-After", 5.0))
                        backoff = retry_after + random.uniform(1.0, 3.0)
                        print(f"  [*] Rate limited—chilling {backoff:.1f}s (attempt {attempt})")
                        await asyncio.sleep(backoff)
                        continue

                    if status in (401, 403):
                        print(f"[!] Auth failure—token cooked or invalid perms. Status: {status}")
                        return status, None

                    if 500 <= status < 600:
                        backoff = (2 ** attempt) + random.uniform(0.5, 2.0)
                        print(f"  [*] Server error {status}, backing off {backoff:.1f}s")
                        await asyncio.sleep(backoff)
                        continue

                    return status, data

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                backoff = (2 ** attempt) + random.uniform(0.3, 1.8)
                print(f"  [*] Network burp: {type(e).__name__}—retrying in {backoff:.1f}s")
                await asyncio.sleep(backoff)

        print("[!] Max retries exhausted—skipping request.")
        return 0, None

    async def fetch_messages(self, limit: int = 100, before: Optional[int] = None) -> List[Dict]:
        """
        Pulls messages from channel using proper pagination.
        Termux-friendly: handles dns flakes, partial payloads, and empty pages gracefully.
        """
        endpoint = f"/channels/{self.channel_id}/messages?limit={min(limit, 100)}"
        if before:
            endpoint += f"&before={before}"

        status, data = await self._api_request("GET", endpoint)
        if status == 200 and isinstance(data, list):
            return data
        return []

    async def report_message(self, message_id: int, reason: ReportReason, message_content: str = "") -> bool:
        """
        Submits a single report via Discord's report endpoint.
        Uses the message-link report format (newer API, better reliability).
        Deduplicates to prevent double-taps on same msg+reason combo.
        """
        dedup_key = (message_id, reason.value)
        async with self._lock:
            if dedup_key in self._processed:
                return False
            self._processed.add(dedup_key)

        # Discord's internal report payload structure (reverse-engineered from client)
        payload = {
            "channel_id": str(self.channel_id),
            "message_id": str(message_id),
            "guild_id": str(self.guild_id),
            "reason": reason.name.lower().replace("_", " "),
            "report_type": reason.value,
        }

        await self.rate_limiter.jitter()
        status, data = await self._api_request(
            "POST",
            "/reporting/message",
            payload=payload,
        )

        if status in (200, 201, 204):
            reason_label = reason.name.replace("_", " ").title()
            snippet = (message_content[:40] + "...") if len(message_content) > 40 else message_content
            print(f"  [+] Reported MSG {message_id} | Reason: {reason_label} | \"{snippet}\"")
            return True
        elif status == 400 and data and data.get("code") == 200000:
            # Discord silently rejects certain self-report edge cases—safe skip
            print(f"  [-] Skipped MSG {message_id} (Discord refused silently, no term risk)")
            return False
        else:
            print(f"  [!] Unexpected status {status} on MSG {message_id}—skipping")
            return False

    async def run(self) -> None:
        """
        Main loop: sweeps entire channel history, then live-polls for new messages.
        Every message gets reported for ALL reasons with surgical precision.
        """
        self._running = True
        await self._create_session()

        # Verify token and channel accessibility first
        status, _ = await self._api_request("GET", "/users/@me")
        if status != 200:
            print("[!] Token is dead or invalid—pull the plug.")
            await self.close()
            return

        status, _ = await self._api_request("GET", f"/channels/{self.channel_id}")
        if status != 200:
            print("[!] Channel unreachable—check ID and permissions.")
            await self.close()
            return

        print(f"\n{'='*55}")
        print(f" REPORTER LIVE | Channel: {self.channel_id} | Guild: {self.guild_id}")
        print(f" Reasons per message: {len(ReportReason)}")
        print(f"{'='*55}\n")

        # Phase 1: Backfill entire channel history
        print("[>] BACKFILL PHASE — pulling channel history...")
        last_msg_id: Optional[int] = None
        total_messages_processed: int = 0
        page = 0

        while self._running:
            messages = await self.fetch_messages(before=last_msg_id)
            if not messages:
                print("[*] No more messages in history—switching to live mode.")
                break

            page += 1
            print(f"\n  --- Page {page} | {len(messages)} messages retrieved ---")
            for msg in messages:
                if not self._running:
                    break
                msg_id = int(msg["id"])
                content = msg.get("content", "") or "[attachment/no text]"
                last_msg_id = msg_id

                for reason in ReportReason:
                    if not self._running:
                        break
                    await self.report_message(msg_id, reason, content)
                    await self.rate_limiter.jitter()

                total_messages_processed += 1

            # Progressive delay between pages—stays under radar
            await asyncio.sleep(random.uniform(2.5, 5.0))

        print(f"\n[+] Backfill complete — {total_messages_processed} messages reported.\n")

        # Phase 2: Live polling loop for new messages
        print("[>] LIVE PHASE — watching for new messages...")
        last_seen_id = last_msg_id

        while self._running:
            messages = await self.fetch_messages(limit=5)
            fresh = [m for m in messages if last_seen_id is None or int(m["id"]) > last_seen_id]

            if fresh:
                fresh.sort(key=lambda m: int(m["id"]))  # chronological
                for msg in fresh:
                    msg_id = int(msg["id"])
                    content = msg.get("content", "") or "[attachment/no text]"
                    print(f"\n  [NEW] Message {msg_id} dropped:")
                    for reason in ReportReason:
                        if not self._running:
                            break
                        await self.report_message(msg_id, reason, content)
                        await self.rate_limiter.jitter()
                    last_seen_id = msg_id

            await asyncio.sleep(random.uniform(6.0, 12.0))

        print("[*] Reporter shut down cleanly.\n")

async def main() -> None:
    if not TOKEN or TOKEN == "USER_TOKEN_HERE":
        print("[!] Drop your token in the TOKEN variable, boss man.")
        return
    if CHANNEL_ID == 0 or GUILD_ID == 0:
        print("[!] Set CHANNEL_ID and GUILD_ID before hitting go.")
        return

    reporter = DiscordReporter(TOKEN, CHANNEL_ID, GUILD_ID)
    try:
        await reporter.run()
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C caught—shutting down cleanly...")
    except Exception as e:
        print(f"[!] Fatal: {type(e).__name__}: {e}")
    finally:
        await reporter.close()
        # Give aiohttp a beat to clean up connections
        await asyncio.sleep(0.3)
        print("[+] Reporter exited. No term, no sweat.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        if "event loop" in str(e).lower():
            # Windows/Termux edge case fallback
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        else:
            raise
