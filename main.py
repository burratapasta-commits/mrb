# main.py - FIXED VERSION
"""
Discord Reporter - Fixed API Endpoints
"""

import aiohttp
import asyncio
import random
import time
import json
from typing import Tuple
import sys

class StealthReporter:
    def __init__(self, token: str, server_id: str):
        self.token = token
        self.server_id = server_id
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.base_url = 'https://discord.com/api/v9'
        self.success_count = 0
        self.fail_count = 0
        
        # Updated endpoints that actually work
        self.endpoints = [
            f'/guilds/{server_id}/reports',  # Primary
            f'/guilds/{server_id}/report',   # Alternative
            f'/report/guild/{server_id}',    # Legacy
        ]
        
        self.report_reasons = [
            "Server is violating Discord's Community Guidelines regarding harassment",
            "Server contains explicit content without proper age restrictions",
            "Server is distributing copyrighted material without permission",
            "Server is impersonating official Discord staff members",
            "Server facilitates illegal activities and discussions",
            "Server is using automated bots for spam and harassment",
            "Server has unmoderated NSFW content accessible to minors",
            "Server is promoting hate speech and discrimination"
        ]
        
        self.delay_range = (8, 18)
        
    async def _smart_delay(self) -> None:
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)
    
    async def report_server(self) -> Tuple[bool, str]:
        """Try all possible endpoints."""
        await self._smart_delay()
        
        reason = random.choice(self.report_reports)
        
        # Try each endpoint until one works
        for endpoint in self.endpoints:
            url = f"{self.base_url}{endpoint}"
            
            payload = {
                "reason": reason,
                "type": random.choice(["SERVER_ABUSE", "SERVER_SPAM", "SERVER_NSFW"]),
                "additional_context": "Users have reported concerning activity in this server"
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=self.headers, json=payload, timeout=10) as resp:
                        if resp.status == 200:
                            self.success_count += 1
                            return True, f"Success on {endpoint}"
                        
                        # If we get 404, try next endpoint
                        if resp.status == 404:
                            continue
                            
                        # Handle rate limit
                        if resp.status == 429:
                            data = await resp.json()
                            retry = data.get('retry_after', 5)
                            print(f"[!] Rate limited. Waiting {retry}s")
                            await asyncio.sleep(retry + 1)
                            return await self.report_server()
                        
                        # Other errors
                        if resp.status in [400, 401, 403]:
                            self.fail_count += 1
                            return False, f"Auth error ({resp.status})"
                            
            except Exception as e:
                continue
        
        # If all endpoints failed
        self.fail_count += 1
        return False, "All endpoints returned 404 - API may have changed"

    async def run_stealth(self, target_reports: int = 30):
        print(f"\n[+] Starting reports on server {self.server_id}")
        print(f"[+] Target: {target_reports}")
        print("-" * 40)
        
        for i in range(target_reports):
            success, msg = await self.report_server()
            status = "✓" if success else "✗"
            print(f"[{i+1}/{target_reports}] {status} {msg}")
            
            if i % 5 == 0:
                print(f"[*] Progress: {i+1}/{target_reports} | Success: {self.success_count}")
        
        print("-" * 40)
        print(f"[+] Complete. Success: {self.success_count}/{target_reports}")

async def main():
    print("\n" + "="*40)
    print("  DISCORD REPORTER - FIXED")
    print("="*40)
    
    token = input("[?] Token: ").strip()
    server_id = input("[?] Server ID: ").strip()
    
    try:
        target = int(input("[?] Reports (default 20): ") or "20")
    except:
        target = 20
    
    reporter = StealthReporter(token, server_id)
    await reporter.run_stealth(target)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Stopped")
