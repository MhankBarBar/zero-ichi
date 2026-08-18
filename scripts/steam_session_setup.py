#!/usr/bin/env python3
"""Fill config.json steam_redeem from an EditThisCookie-style JSON array."""
import json
import sys
from pathlib import Path

cookie_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/steam_cookies.json")
config_path = Path(__file__).resolve().parent.parent / "config.json"

cookies: dict[str, str] = {}
for entry in json.loads(cookie_file.read_text()):
    name = entry.get("name")
    value = entry.get("value")
    if name and value is not None:
        cookies[name] = value

sessionid = cookies.get("sessionid", "")
steam_login_secure = cookies.get("steamLoginSecure", "")
if not sessionid or not steam_login_secure:
    print("ERROR: sessionid or steamLoginSecure missing")
    sys.exit(1)

extra_names = ["browserid", "timezoneOffset", "timezoneName", "recentapps", "ak_bmsc", "strResponsiveViewPrefs"]
extra = "; ".join(f"{n}={cookies[n]}" for n in extra_names if n in cookies)

cfg = json.loads(config_path.read_text())
cfg["steam_redeem"] = {
    "enabled": True,
    "sessionid": sessionid,
    "steam_login_secure": steam_login_secure,
    "extra_cookies": extra,
}
config_path.write_text(json.dumps(cfg, indent=1, ensure_ascii=False))
print(f"OK: steam_redeem configured (sessionid={len(sessionid)} chars, extra: {len(extra.split(';'))} cookies)")
