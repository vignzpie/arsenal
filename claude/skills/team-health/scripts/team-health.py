#!/usr/bin/env python3
"""Health check for Claude Code teams: a lead session in tmux, its members,
its Discord bot, its timers and the machine it runs on.

Read-only. It reads tmux panes and process lists, systemd state, local files,
and makes GET requests to the Discord and GitHub APIs. With --alert it may also
POST one message to the alert channel set in the config. See --help.
"""

import argparse
import base64
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

VERSION = "1"
OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"
RANK = {SKIP: 0, OK: 0, WARN: 1, FAIL: 2}

DEFAULT_CONFIG = os.path.expanduser(
    os.environ.get("TEAM_HEALTH_CONFIG", "~/.config/team-health/teams.json"))
DEFAULT_STATE = os.path.expanduser(
    os.environ.get("TEAM_HEALTH_STATE", "~/.local/state/team-health"))

USAGE_EPILOG = """\
checks (each one runs only when the config gives it something to check):
  session    the tmux session/window exists; claude runs in it (re-checked once
             after 10s, so the restart loop's sleep isn't a false alarm); the pane
             isn't stuck on the folder-trust dialog, a login screen, or a
             "No conversation found to continue" loop
  pane       WARN on a usage-limit banner, a waiting permission prompt, or typed
             text left unsubmitted in the input box since the last run
  channels   when claude runs with --channels, the Discord plugin process is up
  rc         a team marked remote_control runs with --remote-control
  discord    bot token valid, Message Content intent on, bot can view, send and
             read history in its channel, and it answered the owner's last
             message (WARN if not, after reply_window_min, while the pane is idle)
  hearing    each member's bot accepts messages from the lead's bot in the shared
             channel, and the other way round; FAIL if the listener's Discord
             plugin build ignores all messages from bots
  agent      an on-demand agent's definition file exists with name + description
  timer      a timer is active and enabled; its job's last result, an optional
             status file, and lines matching fail_regex added to an optional log
             since the last --alert run (other runs don't use them up)
  boot       the session's systemd unit is enabled, and restores Remote Control
  gh         the gh login is the expected account; the repo has a local
             commit email
  host       free disk space (skipped with --team); tmux installed and its server
             up (reported once, not per session)

output:  one line per check on stdout ("FAIL team/member check: detail"), or
         JSON with --json. Diagnostics go to stderr.
exit:    0 nothing failed (warnings allowed), 1 at least one FAIL,
         2 bad usage or an unreadable config.
config:  $TEAM_HEALTH_CONFIG or ~/.config/team-health/teams.json
state:   $TEAM_HEALTH_STATE or ~/.local/state/team-health (cache + last results)
"""


def log(msg):
    print(msg, file=sys.stderr)


def run(cmd, env=None, timeout=20):
    """Run a command; return (exit code, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]}: timed out after {timeout}s"


def expand(path):
    return os.path.expandvars(os.path.expanduser(path)) if path else path


class Report:
    def __init__(self):
        self.items = []

    def add(self, team, who, check, status, detail=""):
        self.items.append({"team": team, "member": who, "check": check,
                           "status": status, "detail": detail})

    def worst(self):
        return max((RANK[i["status"]] for i in self.items), default=0)


# ---------------------------------------------------------------- state

class State:
    def __init__(self, directory, use_cache=True):
        self.dir = directory
        self.path = os.path.join(directory, "state.json")
        self.use_cache = use_cache
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}
        for k in ("cache", "pending_text", "log_offsets", "alerts"):
            self.data.setdefault(k, {})

    def cached(self, key, max_age_s):
        if not self.use_cache:
            return None
        hit = self.data["cache"].get(key)
        if hit and time.time() - hit.get("at", 0) < max_age_s:
            return hit.get("value")
        return None

    def put(self, key, value):
        self.data["cache"][key] = {"at": time.time(), "value": value}

    def save(self):
        try:
            os.makedirs(self.dir, mode=0o700, exist_ok=True)
            os.chmod(self.dir, 0o700)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=1, sort_keys=True)
            os.replace(tmp, self.path)
        except OSError as e:
            log(f"warning: couldn't save state to {self.path}: {e}")


# ---------------------------------------------------------------- processes

def process_table():
    """pid -> (ppid, elapsed seconds, args). Works with Linux and BSD ps."""
    code, out, _ = run(["ps", "-A", "-o", "pid=", "-o", "ppid=", "-o", "etime=", "-o", "args="])
    table = {}
    if code != 0:
        return table
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            table[int(parts[0])] = (int(parts[1]), parse_etime(parts[2]), parts[3])
        except ValueError:
            continue
    return table


def parse_etime(s):
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        days = int(d)
    nums = [int(x) for x in s.split(":")]
    while len(nums) < 3:
        nums.insert(0, 0)
    h, m, sec = nums
    return days * 86400 + h * 3600 + m * 60 + sec


def descendants(table, root, depth=3):
    out, frontier = [], [root]
    for _ in range(depth):
        nxt = [pid for pid, (ppid, _, _) in table.items() if ppid in frontier]
        out += nxt
        frontier = nxt
    return out


CLAUDE_RE = re.compile(r"(^|/)claude(\s|$)")


def find_claude(table, pane_pid):
    for pid in descendants(table, pane_pid):
        args = table[pid][2]
        if CLAUDE_RE.search(args.split(" --", 1)[0]):
            return pid
    return None


def find_plugin(table, claude_pid):
    for pid in descendants(table, claude_pid, depth=2):
        args = table[pid][2]
        if "bun" in args and "discord" in args:
            return pid
    return None


def plugin_dir(args):
    """The Discord plugin's folder, from its process's '--cwd <dir>' argument."""
    m = re.search(r"--cwd[ =](\S+)", args)
    return m.group(1) if m else None


DROPS_BOTS = re.compile(r"author\.bot\b[^\n]{0,40}\breturn\b")


def plugin_drops_bots(directory):
    """True if this plugin build ignores every message whose author is a bot.
    None if the source can't be read."""
    try:
        with open(os.path.join(directory, "server.ts"), encoding="utf-8") as f:
            return bool(DROPS_BOTS.search(f.read()))
    except OSError:
        return None


# ---------------------------------------------------------------- tmux

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

PANE_FAIL = [
    (re.compile(r"trust the files in this folder|project you created or one you trust", re.I),
     "stuck on the folder-trust dialog (its default is 'No, exit': answer with Down, then Enter)"),
    (re.compile(r"No conversation found to continue", re.I),
     "restart loop is spinning on 'No conversation found to continue': relaunch without --continue"),
    (re.compile(r"Please run /login|Select login method|OAuth token (has )?expired|Invalid API key", re.I),
     "waiting at a login screen: log in again in that session"),
]
PANE_WARN = [
    (re.compile(r"Do you want to proceed\?|Do you want to (make|create|allow)", re.I),
     "a permission prompt is waiting for an answer"),
]
USAGE_LIMIT = re.compile(r"usage limit|limit reached|hit your limit|out of (usage|credits)", re.I)
USAGE_RESET = re.compile(r"\bresets?\b|try again (at|in)", re.I)
BUSY = re.compile(r"esc to interrupt", re.I)
PROMPT = "❯"  # the input box's prompt character


def tmux_sessions():
    code, out, _ = run(["tmux", "list-sessions", "-F", "#{session_name}"])
    return (code == 0), set(out.splitlines())


def pane_of(target):
    code, out, _ = run(["tmux", "list-panes", "-t", target, "-F", "#{pane_pid} #{pane_dead}"])
    if code != 0 or not out.strip():
        return None
    pid, dead = out.split()[0], out.split()[1]
    return None if dead == "1" else int(pid)


def capture(target):
    code, out, _ = run(["tmux", "capture-pane", "-e", "-p", "-t", target, "-S", "-60"])
    return out if code == 0 else ""


def typed_input(raw):
    """Text after the prompt that the user typed (not a dimmed ghost suggestion)."""
    for line in reversed(raw.splitlines()):
        plain = ANSI.sub("", line)
        if plain.lstrip().startswith(PROMPT):
            text = plain.lstrip()[1:].strip()
            if not text:
                return ""
            after = line.split(PROMPT, 1)[1]
            if after.lstrip("  ").startswith("\x1b[2m"):
                return ""  # ghost suggestion
            if text.startswith("Try \""):
                return ""
            return text
    return ""


# ---------------------------------------------------------------- discord

API = "https://discord.com/api/v10"
VIEW, SEND, HISTORY, ADMIN = 1 << 10, 1 << 11, 1 << 16, 1 << 3
INTENT_BITS = (1 << 18) | (1 << 19)


class Discord:
    def __init__(self, token):
        self.token = token

    def get(self, path, tries=2):
        req = urllib.request.Request(API + path, headers={
            "Authorization": "Bot " + self.token,
            "User-Agent": f"DiscordBot (team-health, {VERSION})"})
        for _ in range(tries):
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    return r.status, json.loads(r.read().decode() or "null")
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    try:
                        wait = float(e.headers.get("Retry-After", "1") or 1)
                    except ValueError:
                        wait = 1.0
                    time.sleep(min(max(wait, 0), 10))
                    continue
                return e.code, None
            except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
                return 0, None
        return 429, None

    def post(self, path, body):
        req = urllib.request.Request(API + path, method="POST", data=json.dumps(body).encode(), headers={
            "Authorization": "Bot " + self.token, "Content-Type": "application/json",
            "User-Agent": f"DiscordBot (team-health, {VERSION})"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except (urllib.error.URLError, http.client.HTTPException, OSError):
            return 0


def read_token(state_dir):
    return read_token_file(os.path.join(state_dir, ".env"))


def bot_id_from_token(token):
    """A bot token's first segment is the bot's user ID, base64-encoded."""
    try:
        seg = token.split(".", 1)[0]
        return base64.b64decode(seg + "=" * (-len(seg) % 4)).decode()
    except (ValueError, UnicodeDecodeError):
        return None


def read_access(state_dir):
    try:
        with open(os.path.join(state_dir, "access.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def effective_perms(guild, roles, member, channel, bot_id):
    if guild.get("owner_id") == bot_id:
        return -1
    by_id = {r["id"]: int(r["permissions"]) for r in roles}
    perms = by_id.get(guild["id"], 0)
    for rid in member.get("roles", []):
        perms |= by_id.get(rid, 0)
    if perms & ADMIN:
        return -1
    ow = {o["id"]: o for o in channel.get("permission_overwrites", [])}
    if guild["id"] in ow:
        perms = (perms & ~int(ow[guild["id"]]["deny"])) | int(ow[guild["id"]]["allow"])
    allow = deny = 0
    for rid in member.get("roles", []):
        if rid in ow:
            allow |= int(ow[rid]["allow"])
            deny |= int(ow[rid]["deny"])
    perms = (perms & ~deny) | allow
    if bot_id in ow:
        perms = (perms & ~int(ow[bot_id]["deny"])) | int(ow[bot_id]["allow"])
    return perms


# ---------------------------------------------------------------- checker

class Checker:
    def __init__(self, cfg, state, report, offline, commit_offsets=False):
        self.cfg = cfg
        self.commit_offsets = commit_offsets  # only a real --alert run moves log offsets
        self.plugins = {}  # (team, who) -> Discord plugin folder of that session
        self.state = state
        self.r = report
        self.offline = offline
        self.table = process_table()
        self.tmux_ok, self.sessions = tmux_sessions()
        self.bots = {}  # state_dir -> {"id":..., "client": Discord}
        self.owner = str(cfg.get("owner_id", "")) or None

    # -- host
    def host(self):
        for d in self.cfg.get("disk", [{"path": "/", "min_free_pct": 10}]):
            path = expand(d.get("path", "/"))
            try:
                u = shutil.disk_usage(path)
            except OSError as e:
                self.r.add("host", "", "disk", WARN, f"{path}: {e}")
                continue
            free = 100.0 * u.free / u.total
            need = float(d.get("min_free_pct", 10))
            st = FAIL if free < need / 2 else WARN if free < need else OK
            self.r.add("host", "", "disk", st, f"{path} {free:.0f}% free (want {need:.0f}%)")

    def tmux_server(self):
        """One line for a missing tmux or a dead server, instead of one per session."""
        if not shutil.which("tmux"):
            self.r.add("host", "", "tmux", FAIL, "tmux isn't installed or isn't on PATH; sessions can't be checked")
        elif not self.tmux_ok and any(self._targets()):
            self.r.add("host", "", "tmux", FAIL,
                       "no tmux server is running, so every session is down. Relaunch the teams")

    def _targets(self):
        for t in self.teams:
            if t.get("session"):
                yield t["session"]
            for m in t.get("members", []):
                if m.get("session"):
                    yield m["session"]

    # -- session
    def session(self, team, who, spec):
        """Checks a tmux-hosted claude session. Returns the claude pid or None."""
        name = spec["session"]
        target = name + (":" + str(spec["window"]) if spec.get("window") is not None else "")
        exact = "=" + target  # tmux would otherwise prefix-match "cc" to "cc-other"
        if not self.tmux_ok:
            return None, None  # reported once, as host/tmux
        if name not in self.sessions:
            self.r.add(team, who, "session", FAIL, f"tmux session {name} isn't running")
            return None, None
        pane = pane_of(exact)
        if pane is None:
            self.r.add(team, who, "session", FAIL, f"no live pane at {target}")
            return None, None
        claude = find_claude(self.table, pane)
        if claude is None:
            time.sleep(10)  # the restart loop sleeps a few seconds between runs
            self.table = process_table()
            claude = find_claude(self.table, pane)
        if claude is None:
            self.r.add(team, who, "session", FAIL, f"claude isn't running in {target} (checked twice, 10s apart)")
            return None, exact
        raw = capture(exact)
        plain = ANSI.sub("", raw)
        tail = "\n".join(plain.splitlines()[-25:])
        stuck = [msg for rx, msg in PANE_FAIL if rx.search(tail)]
        if stuck:
            for msg in stuck:
                self.r.add(team, who, "session", FAIL, f"{target}: {msg}")
        else:
            self.r.add(team, who, "session", OK, f"{target}: claude running")
        self.pane_warnings(team, who, target, raw, tail)
        self.channels(team, who, claude, spec, (team, who))
        self.remote_control(team, who, claude, spec)
        return claude, exact

    def pane_warnings(self, team, who, target, raw, tail):
        bottom = "\n".join(tail.splitlines()[-15:])  # old banners in scrollback don't count
        if USAGE_LIMIT.search(bottom) and USAGE_RESET.search(bottom):
            self.r.add(team, who, "pane", WARN,
                       f"{target}: usage-limit banner on screen; it resumes when the limit resets")
        for rx, msg in PANE_WARN:
            if rx.search(tail):
                self.r.add(team, who, "pane", WARN, f"{target}: {msg}")
        text = typed_input(raw)
        if text:  # store a hash, never the text itself (it could be a pasted secret)
            text = hashlib.sha256(text.encode()).hexdigest()
        pend = self.state.data["pending_text"]
        if text and pend.get(target) == text and not BUSY.search(tail):
            self.r.add(team, who, "pane", WARN,
                       f"{target}: typed text has sat unsubmitted since the last run; send Enter if it's meant to go")
        if text:
            pend[target] = text
        else:
            pend.pop(target, None)

    def busy(self, target):
        if not target:
            return False
        tail = "\n".join(ANSI.sub("", capture(target)).splitlines()[-8:])
        return bool(BUSY.search(tail))

    def channels(self, team, who, claude, spec, key):
        args = self.table[claude][2]
        if "--channels" not in args or "discord" not in args:
            if spec.get("discord"):
                self.r.add(team, who, "channels", FAIL,
                           "a bot is configured but claude runs without --channels for the Discord plugin")
            return
        plugin = find_plugin(self.table, claude)
        if plugin:
            self.plugins[key] = plugin_dir(self.table[plugin][2])
            self.r.add(team, who, "channels", OK, "Discord plugin running")
        elif self.table[claude][1] < 60:
            self.r.add(team, who, "channels", SKIP, "claude started under 60s ago; plugin not judged yet")
        else:
            self.r.add(team, who, "channels", FAIL,
                       "the Discord plugin isn't running. A bot without Message Content intent exits "
                       "silently; check the discord results, then restart the session")

    def remote_control(self, team, who, claude, spec):
        if not spec.get("remote_control"):
            return
        args = self.table[claude][2]
        if re.search(r"(^|\s)--(remote-control|rc)(\s|=|$)", args):
            self.r.add(team, who, "rc", OK, "Remote Control on")
        else:
            self.r.add(team, who, "rc", WARN, "configured for Remote Control but running without it")

    # -- discord
    def bot(self, team, who, spec, target):
        d = spec.get("discord")
        if not d:
            return None
        sdir = expand(d["state_dir"])
        token = read_token(sdir)
        if not token:
            self.r.add(team, who, "discord", FAIL, f"no DISCORD_BOT_TOKEN in {sdir}/.env")
            return None
        info = {"id": bot_id_from_token(token), "client": Discord(token), "channel": str(d.get("channel", ""))}
        self.bots[sdir] = info
        if self.offline:
            return info
        c = info["client"]
        st, me = c.get("/users/@me")
        if st == 401:
            self.r.add(team, who, "discord", FAIL, "bot token rejected (401): reset it in the Developer Portal")
            return info
        if st != 200:
            self.r.add(team, who, "discord", WARN, f"couldn't reach Discord (status {st}); bot not checked")
            return info
        info["id"] = me["id"]
        info["healthy"] = True
        key = f"intent:{me['id']}"
        flags = self.state.cached(key, 86400)
        if flags is None:
            st, app = c.get("/applications/@me")
            if st == 200:
                flags = app.get("flags", 0)
                if flags & INTENT_BITS:
                    self.state.put(key, flags)  # cache "on" only, so a fix shows up next run
        if flags is not None and not flags & INTENT_BITS:
            self.r.add(team, who, "discord", FAIL,
                       "Message Content intent is off: turn it on under Bot > Privileged Gateway Intents")
        ch_id = info["channel"]
        if not ch_id:
            self.r.add(team, who, "discord", OK, f"bot {me['username']} token valid")
            return info
        st, ch = c.get(f"/channels/{ch_id}")
        if st in (0, 429):
            self.r.add(team, who, "discord", WARN, f"couldn't reach Discord to read channel {ch_id} (status {st})")
            return info
        if st != 200:
            self.r.add(team, who, "discord", FAIL,
                       f"bot can't see channel {ch_id} (status {st}): invite it to the server or fix channel permissions")
            return info
        missing = self.perms(c, ch, me["id"])
        if missing:
            self.r.add(team, who, "discord", FAIL, f"bot lacks {', '.join(missing)} in its channel")
        else:
            self.r.add(team, who, "discord", OK, f"bot {me['username']} can read and post in its channel")
            self.answered(team, who, c, d, me["id"], target)
        return info

    def perms(self, c, ch, bot_id):
        gid = ch.get("guild_id")
        if not gid:
            return []
        st1, guild = c.get(f"/guilds/{gid}")
        st2, roles = c.get(f"/guilds/{gid}/roles")
        st3, member = c.get(f"/guilds/{gid}/members/{bot_id}")
        if st1 != 200 or st2 != 200 or st3 != 200:
            return []  # can't compute; the channel read above already passed
        p = effective_perms(guild, roles, member, ch, bot_id)
        if p == -1:
            return []
        names = [("View Channel", VIEW), ("Send Messages", SEND), ("Read Message History", HISTORY)]
        return [n for n, bit in names if not p & bit]

    def answered(self, team, who, c, d, bot_id, target):
        if not self.owner:
            return
        st, msgs = c.get(f"/channels/{d['channel']}/messages?limit=50")
        if st != 200 or not isinstance(msgs, list):
            return
        mention_only = d.get("require_mention", False)
        last_owner, replied = None, False
        for m in msgs:  # newest first
            if m["author"]["id"] != self.owner:
                continue
            mentioned = {u["id"] for u in m.get("mentions", [])}
            if bot_id in mentioned or m.get("mention_everyone"):
                # Addressed to this bot: only this bot's reply or reaction answers it.
                later = [x for x in msgs if int(x["id"]) > int(m["id"]) and x["author"]["id"] == bot_id]
            elif mentioned or mention_only:
                continue  # addressed to someone else, or this bot only answers mentions
            else:
                # Unaddressed, in a channel other bots may share: any bot's reply answers it.
                later = [x for x in msgs if int(x["id"]) > int(m["id"]) and x["author"].get("bot")]
            last_owner = m
            # A reaction counts too; "me" is this bot, since we read with its token.
            replied = bool(later) or any(r.get("me") for r in m.get("reactions", []))
            break
        if not last_owner:
            return
        age_min = (time.time() - snowflake_time(last_owner["id"])) / 60
        window = float(d.get("reply_window_min", 20))
        if not replied and age_min > window and not self.busy(target):
            self.r.add(team, who, "discord", WARN,
                       f"owner's last message has no reply after {age_min:.0f} min and the session is idle: "
                       "the session may be wedged or the bot's send path stalled (try /reload-plugins there)")

    # -- hearing
    def hearing(self, team, lead_spec, member, mspec):
        ld, md = lead_spec.get("discord"), mspec.get("discord")
        if not ld or not md:
            return
        lead, mem = self.bots.get(expand(ld["state_dir"])), self.bots.get(expand(md["state_dir"]))
        chan = str(md.get("channel") or ld.get("channel") or "")
        if not lead or not mem or not chan:
            return
        for speaker, listener, sdir, pdir, label in (
                (lead, mem, expand(md["state_dir"]), self.plugins.get((team, member)), "lead -> member"),
                (mem, lead, expand(ld["state_dir"]), self.plugins.get((team, "lead")), "member -> lead")):
            self.r.add(team, member, "hearing", *self.hears(listener, speaker, sdir, chan, label, pdir))

    @staticmethod
    def hears(listener, speaker, sdir, chan, label, pdir=None):
        if pdir and plugin_drops_bots(pdir):
            return FAIL, (f"{label}: the listener's Discord plugin build ({pdir}) ignores every message "
                          "from a bot, whatever access.json says; bot-to-bot dispatch can't work with it")
        acc = read_access(sdir)
        if acc is None:
            return FAIL, f"{label}: can't read {sdir}/access.json"
        if acc.get("dmPolicy") == "disabled":
            return FAIL, f"{label}: listener's dmPolicy is 'disabled', so it drops everything"
        g = acc.get("groups", {}).get(chan)
        if g is None:
            return FAIL, f"{label}: listener's access.json has no entry for channel {chan}, so it ignores the channel"
        allow = [str(x) for x in g.get("allowFrom", [])]
        if allow and speaker["id"] not in allow:
            return FAIL, f"{label}: speaker's bot ID isn't in the listener's allowFrom for {chan}"
        if g.get("requireMention", True):
            how = "a real <@id> mention, a reply to it"
            if acc.get("mentionPatterns"):
                how += ", or text matching its mentionPatterns"
            return OK, f"{label}: allowed; needs {how} (plain '@Name' text isn't a mention)" + unchecked(pdir)
        return OK, f"{label}: allowed" + unchecked(pdir)

    # -- agents
    def agent(self, team, who, spec):
        path = expand(spec["file"])
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read(8192)
        except OSError:
            self.r.add(team, who, "agent", FAIL, f"definition {path} not found")
            return
        m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
        fm = m.group(1) if m else ""
        missing = [k for k in ("name", "description") if not re.search(rf"^{k}:\s*\S", fm, re.M)]
        if missing:
            self.r.add(team, who, "agent", FAIL, f"{path} frontmatter lacks {', '.join(missing)}")
        else:
            self.r.add(team, who, "agent", OK, "definition present")

    # -- timers
    def timer(self, team, who, spec):
        unit = spec["unit"]
        if spec.get("oneshot"):
            self.r.add(team, who, "timer", SKIP, f"{unit} is a one-shot timer")
            return
        props = systemctl_show(unit, "ActiveState", "UnitFileState", "LastTriggerUSec", "Unit")
        if props is None:
            self.r.add(team, who, "timer", WARN, f"couldn't query {unit} (is systemd --user available?)")
            return
        if props.get("ActiveState") != "active":
            self.r.add(team, who, "timer", FAIL, f"{unit} isn't active: systemctl --user enable --now {unit}")
            return
        if props.get("UnitFileState") not in ("enabled", "static", "enabled-runtime"):
            self.r.add(team, who, "timer", WARN, f"{unit} is running but not enabled, so it stops at reboot")
        max_age = float(spec.get("max_age_min", 120)) * 60
        problems = []
        if spec.get("status_file"):
            problems += self.status_file(expand(spec["status_file"]), max_age)
        else:
            svc = props.get("Unit") or unit.rsplit(".", 1)[0] + ".service"
            sp = systemctl_show(svc, "Result") or {}
            if sp.get("Result") not in (None, "", "success"):
                problems.append(f"last run of {svc} ended with '{sp['Result']}': journalctl --user -u {svc}")
            last = parse_systemd_time(props.get("LastTriggerUSec", ""))
            if not last:
                self.r.add(team, who, "timer", WARN, f"{unit} hasn't run yet")
                return
            if time.time() - last > max_age:
                problems.append(f"last ran {int((time.time() - last) / 60)} min ago (expected within {int(max_age / 60)})")
        if spec.get("log_file") and spec.get("fail_regex"):
            hits = self.new_log_hits(expand(spec["log_file"]), spec["fail_regex"])
            if hits:
                problems.append(f"{hits} new line(s) in {spec['log_file']} match {spec['fail_regex']!r}")
        if problems:
            self.r.add(team, who, "timer", FAIL, f"{unit}: " + "; ".join(problems))
        else:
            self.r.add(team, who, "timer", OK, f"{unit} healthy")

    @staticmethod
    def status_file(path, max_age):
        try:
            with open(path, encoding="utf-8") as f:
                s = json.load(f)
        except (OSError, ValueError):
            return [f"status file {path} missing or not JSON"]
        out = []
        last = s.get("last_run")
        if isinstance(last, str):
            last = parse_iso(last)
        if not isinstance(last, (int, float)) or time.time() - last > max_age:
            out.append(f"status file {path} is stale")
        try:
            failures = int(s.get("failures") or 0)
        except (TypeError, ValueError):
            return out + [f"status file {path} has a non-numeric 'failures'"]
        if s.get("ok") is False or failures > 0:
            out.append(f"last run reported failures ({s.get('failures', '?')})")
        return out

    def new_log_hits(self, path, pattern):
        offsets = self.state.data["log_offsets"]
        try:
            size = os.path.getsize(path)
        except OSError:
            return 0
        start = offsets.get(path)
        if start is None or start > size:
            if self.commit_offsets or start is None:
                offsets[path] = size
            return 0  # first run (or the log was rotated): start counting from here
        if self.commit_offsets:
            offsets[path] = size  # other runs report the same lines without using them up
        with open(path, "rb") as f:
            f.seek(start)
            chunk = f.read(size - start).decode("utf-8", "replace")
        rx = re.compile(pattern)
        return sum(1 for line in chunk.splitlines() if rx.search(line))

    # -- boot / gh
    def boot(self, team, spec):
        unit = spec.get("boot_unit")
        if unit is None:
            if not spec.get("boot_optional"):
                self.r.add(team, "", "boot", WARN, "no boot_unit configured, so the session won't come back after a reboot")
            return
        code, out, _ = run(["systemctl", "--user", "is-enabled", unit])
        if code == 127:
            self.r.add(team, "", "boot", WARN, "systemctl isn't available; boot unit not checked")
            return
        if out.strip() != "enabled":
            self.r.add(team, "", "boot", WARN,
                       f"{unit} isn't enabled ({out.strip() or 'unknown'}), so the session won't come back after a reboot")
            return
        if spec.get("remote_control") and not spec.get("boot_restores_rc"):
            props = systemctl_show(unit, "ExecStart") or {}
            if not re.search(r"--rc\b|--remote-control", props.get("ExecStart", "")):
                self.r.add(team, "", "boot", WARN,
                           f"{unit} starts the session without Remote Control, so a reboot drops it")
                return
        self.r.add(team, "", "boot", OK, f"{unit} enabled")

    def gh(self, team, spec):
        g = spec.get("gh")
        if not g:
            return
        env = dict(os.environ)
        for k in ("GH_TOKEN", "GITHUB_TOKEN", "GH_HOST"):
            env.pop(k, None)
        if g.get("config_dir"):
            env["GH_CONFIG_DIR"] = expand(g["config_dir"])
        if self.offline:
            return
        code, out, err = run(["gh", "api", "user", "-q", ".login"], env=env)
        want = g.get("login")
        if code == 0 and (want is None or out.strip() == want):
            self.r.add(team, "", "gh", OK, f"gh logged in as {out.strip()}")
        elif code == 0:
            self.r.add(team, "", "gh", FAIL, f"gh is logged in as {out.strip()}, expected {want}")
        elif code == 127:
            self.r.add(team, "", "gh", WARN, "gh isn't installed or isn't on PATH; login not checked")
        elif "auth login" in err or "401" in err or "Bad credentials" in err:
            self.r.add(team, "", "gh", FAIL, f"gh isn't logged in for this team: GH_CONFIG_DIR={g.get('config_dir', '~/.config/gh')} gh auth login")
        else:
            self.r.add(team, "", "gh", WARN, "couldn't reach GitHub to check the login")
        repo = expand(g.get("repo", ""))
        if repo and g.get("require_commit_email"):
            code, out, _ = run(["git", "-C", repo, "config", "--local", "user.email"])
            if code == 127:
                self.r.add(team, "", "gh", WARN, "git isn't on PATH; commit email not checked")
            elif not out.strip():
                self.r.add(team, "", "gh", WARN,
                           f"{repo} has no local user.email, so commits fall back to the global identity")

    # -- team
    def team(self, t):
        name = t["name"]
        lead_target = None
        if t.get("session"):
            _, lead_target = self.session(name, "lead", t)
        if t.get("discord"):
            self.bot(name, "lead", t, lead_target)
        self.boot(name, t)
        self.gh(name, t)
        for m in t.get("members", []):
            who = m.get("name", "?")
            kind = m.get("kind", "session")
            if kind == "session":
                _, target = self.session(name, who, m)
                if m.get("discord"):
                    self.bot(name, who, m, target)
                    self.hearing(name, t, who, m)
            elif kind == "agent":
                self.agent(name, who, m)
            elif kind == "timer":
                self.timer(name, who, m)
            else:
                self.r.add(name, who, "config", FAIL, f"unknown member kind '{kind}' (use session, agent or timer)")


def unchecked(pdir):
    return "" if pdir else " (listener's plugin build not checked: its session isn't running)"


def snowflake_time(sid):
    return ((int(sid) >> 22) + 1420070400000) / 1000.0


def parse_iso(s):
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_systemd_time(s):
    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", s or "")
    if not m:
        return None
    return time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))


def systemctl_show(unit, *props):
    code, out, _ = run(["systemctl", "--user", "show", unit] + [f"-p{p}" for p in props])
    if code != 0:
        return None
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


# ---------------------------------------------------------------- alerting

def local_now(tz_name):
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_name)) if tz_name else datetime.now().astimezone()
    except (ImportError, KeyError, ValueError):
        log(f"alert.timezone '{tz_name}' isn't a known time zone; using the machine's")
        from datetime import datetime
        return datetime.now().astimezone()


def in_quiet_hours(now, spec):
    """spec like "23:00-08:00"; an empty spec means never quiet."""
    if not spec:
        return False
    try:
        a, b = [int(h) * 60 + int(m) for h, m in (x.split(":") for x in spec.split("-"))]
    except ValueError:
        log(f"alert.quiet_hours '{spec}' isn't HH:MM-HH:MM; ignoring it")
        return False
    t = now.hour * 60 + now.minute
    return a <= t < b if a < b else (t >= a or t < b)


def line(i):
    who = f"{i['team']}/{i['member']}" if i["member"] else i["team"]
    return f"{who}: {i['check']}: {i['detail']}"


def alert(cfg, state, report, chk, dry_run, checked):
    """Decide what to send, then post it (or hold it during quiet hours).

    FAILs go out when new or recovered, and again every repeat_hours while still
    open. WARNs never push: they go in one daily digest, only if any exist.
    """
    a = cfg.get("alert") or {}
    now_ts = time.time()
    now = local_now(a.get("timezone"))
    seen = state.data["alerts"]
    # Several FAIL lines can share a key (e.g. two pane problems); keep them all.
    by_key = {}
    for i in report.items:
        if i["status"] == FAIL:
            by_key.setdefault(f"{i['team']}/{i['member']}/{i['check']}", []).append(i)

    new = []
    for key, items in sorted(by_key.items()):
        detail = " | ".join(i["detail"] for i in items)
        prev = seen.get(key)
        if prev is None or prev.get("detail") != detail or \
                now_ts - prev.get("at", 0) > float(a.get("repeat_hours", 12)) * 3600:
            new += [line(i) for i in items]
            seen[key] = {"at": now_ts, "detail": detail}
    # Only teams checked in this run can have recovered (a --team run leaves the rest alone).
    for key in [k for k in seen if k not in by_key and k.split("/", 1)[0] in checked]:
        team, member, check = key.split("/", 2)
        new.append(f"{team}/{member}: {check}: recovered" if member else f"{team}: {check}: recovered")
        del seen[key]

    if new and a.get("on_fail_cmd"):
        run_hook(a["on_fail_cmd"], "\n".join(new) + "\n", dry_run)

    held = state.data.setdefault("held", [])
    quiet = in_quiet_hours(now, a.get("quiet_hours", ""))
    if quiet:
        held += new
        return
    out = held + new
    state.data["held"] = []

    today = now.strftime("%Y-%m-%d")
    digest_at = int(a.get("digest_hour", 8))
    if state.data.get("digest_day") != today and now.hour >= digest_at:
        state.data["digest_day"] = today
        warns = [line(i) for i in report.items if i["status"] == WARN]
        if warns:
            out += ["daily warnings:"] + warns

    if not out:
        return
    text = "\n".join(out)
    if dry_run:
        print("--- would post ---\n" + text)
        return
    if not post(a, chk, text):
        state.data["held"] = out  # try again next run


def run_hook(cmd, text, dry_run):
    argv = [expand(x) for x in (cmd if isinstance(cmd, list) else ["sh", "-c", cmd])]
    if dry_run:
        print(f"--- would run on_fail_cmd {argv[0]} with ---\n{text}", end="")
        return
    try:
        subprocess.run(argv, input=text, text=True, timeout=30, capture_output=True, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"on_fail_cmd didn't run: {e}")


def post(a, chk, text):
    """Post through the alert bot; if it can't, through any team bot whose checks passed."""
    if not a.get("channel_id"):
        log("--alert: set alert.channel_id in the config; nothing posted")
        return False
    tokens = []
    if a.get("token_file"):
        t = read_token_file(expand(a["token_file"]))
        if t:
            tokens.append(t)
        else:
            log(f"--alert: no token in {a['token_file']}")
    if a.get("fallback", True):
        tokens += [b["client"].token for b in chk.bots.values() if b.get("healthy")]
    for token in dict.fromkeys(tokens):
        client = Discord(token)
        ok = True
        for chunk in [text[i:i + 1900] for i in range(0, len(text), 1900)]:
            st = client.post(f"/channels/{a['channel_id']}/messages",
                             {"content": chunk, "allowed_mentions": {"parse": []}})
            if st not in (200, 201):
                ok = False
                break
        if ok:
            return True
    log("--alert: no bot could post to the alert channel; the alert is held for the next run")
    return False


def read_token_file(path):
    """A file holding either DISCORD_BOT_TOKEN=<token> or just the token."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    for ln in text.splitlines():
        if ln.startswith("DISCORD_BOT_TOKEN="):
            return ln.split("=", 1)[1].strip().strip('"').strip("'")
    text = text.strip()
    return text if text and "\n" not in text and "=" not in text else None


# ---------------------------------------------------------------- main

def write_last(directory, report):
    """The latest full result, for anyone who wants it without rerunning."""
    try:
        os.makedirs(directory, mode=0o700, exist_ok=True)
        tmp = os.path.join(directory, "last.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"at": int(time.time()), "worst": [OK, WARN, FAIL][report.worst()],
                       "results": report.items}, f, indent=1)
        os.replace(tmp, os.path.join(directory, "last.json"))
    except OSError as e:
        log(f"warning: couldn't write {directory}/last.json: {e}")


def load_config(path):
    """Read and shape-check the config. Raises ConfigError with a readable message."""
    try:
        with open(expand(path), encoding="utf-8") as f:
            cfg = json.load(f)
    except OSError as e:
        raise ConfigError(f"can't read {path}: {e.strerror}. Copy the skill's "
                          "assets/teams.example.json there and edit it, or pass --config") from None
    except ValueError as e:
        raise ConfigError(f"{path} isn't valid JSON: {e}") from None
    if not isinstance(cfg, dict):
        raise ConfigError("the top level must be an object with a 'teams' list")
    teams = cfg.get("teams", [])
    if not isinstance(teams, list) or not all(isinstance(t, dict) for t in teams):
        raise ConfigError("'teams' must be a list of objects")
    for t in teams:
        if not t.get("name"):
            raise ConfigError("every team needs a 'name'")
        members = t.get("members", [])
        if not isinstance(members, list) or not all(isinstance(m, dict) for m in members):
            raise ConfigError(f"team {t['name']}: 'members' must be a list of objects")
        needs = {"session": "session", "agent": "file", "timer": "unit"}
        for m in members:
            field = needs.get(m.get("kind", "session"))
            if field and not m.get(field):
                raise ConfigError(f"team {t['name']}, member {m.get('name', '?')}: "
                                  f"a {m.get('kind', 'session')} member needs '{field}'")
        for spec in [t] + members:
            if spec.get("discord") is not None and not (isinstance(spec["discord"], dict)
                                                        and spec["discord"].get("state_dir")):
                raise ConfigError(f"team {t['name']}: 'discord' needs a 'state_dir'")
            if spec.get("fail_regex"):
                re.compile(spec["fail_regex"])
    return cfg


class ConfigError(Exception):
    pass


def main():
    ap = argparse.ArgumentParser(
        prog="team-health.py", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Check that a Claude Code team is up and can talk: its lead session, "
                    "members, Discord bots, timers and host. Read-only, except --alert.",
        epilog=USAGE_EPILOG)
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="teams file (default: %(default)s)")
    ap.add_argument("--team", action="append", help="check only this team (repeatable)")
    ap.add_argument("--json", action="store_true", help="print results as JSON")
    ap.add_argument("--quiet", action="store_true", help="print only WARN and FAIL lines")
    ap.add_argument("--offline", action="store_true", help="skip every network call (Discord, GitHub); not with --alert")
    ap.add_argument("--no-cache", action="store_true", help="re-check the cached Discord intent")
    ap.add_argument("--alert", action="store_true",
                    help="post new failures, recoveries and the daily warning digest to the config's "
                         "alert channel, and run its on_fail_cmd (a network write)")
    ap.add_argument("--alert-dry-run", action="store_true", help="print what --alert would post and run; post, run and save nothing")
    ap.add_argument("--state-dir", default=DEFAULT_STATE, help="cache and last-run state (default: %(default)s)")
    ap.add_argument("--version", action="version", version=f"team-health {VERSION}")
    args = ap.parse_args()
    if args.offline and args.alert:
        ap.error("--alert posts to Discord, so it can't be combined with --offline (use --alert-dry-run)")

    cfg = None
    try:
        cfg = load_config(args.config)
        return check(args, cfg)
    except (ConfigError, KeyError, TypeError, ValueError, AttributeError, re.error) as e:
        msg = f"config error: {e}; check it against references/config.md"
        log(msg)
        if args.alert and isinstance(cfg, dict):
            notify_config_error(cfg, msg)
        return 2


def notify_config_error(cfg, msg):
    """A broken config must not go quiet on a timer: post it, best effort."""
    try:
        a = cfg.get("alert") or {}
        token = read_token_file(expand(a.get("token_file", "")))
        if token and a.get("channel_id"):
            Discord(token).post(f"/channels/{a['channel_id']}/messages",
                                {"content": f"team-health: {msg}", "allowed_mentions": {"parse": []}})
    except (AttributeError, TypeError, ValueError, OSError):
        pass


def check(args, cfg):
    teams = cfg.get("teams", [])
    if args.team:
        unknown = set(args.team) - {t.get("name") for t in teams}
        if unknown:
            log(f"Unknown team(s): {', '.join(sorted(unknown))}. Known: "
                f"{', '.join(t.get('name', '?') for t in teams) or 'none'}")
            return 2
        teams = [t for t in teams if t.get("name") in args.team]

    real_alert = args.alert and not args.alert_dry_run
    state = State(args.state_dir, use_cache=not args.no_cache)
    report = Report()
    chk = Checker(cfg, state, report, args.offline, commit_offsets=real_alert)
    chk.teams = teams
    checked = {t["name"] for t in teams}
    chk.tmux_server()
    if not args.team:
        chk.host()
        checked.add("host")
    for t in teams:
        chk.team(t)

    if args.json:
        print(json.dumps({"worst": [OK, WARN, FAIL][report.worst()], "results": report.items}, indent=1))
    else:
        for i in report.items:
            if args.quiet and i["status"] in (OK, SKIP):
                continue
            who = f"{i['team']}/{i['member']}" if i["member"] else i["team"]
            print(f"{i['status'].upper():4}  {who} {i['check']}: {i['detail']}")
        n = {s: sum(1 for i in report.items if i["status"] == s) for s in (FAIL, WARN, OK)}
        if not args.quiet or n[FAIL] or n[WARN]:
            print(f"-- {n[FAIL]} fail, {n[WARN]} warn, {n[OK]} ok")
    if args.alert_dry_run:
        alert(cfg, state, report, chk, dry_run=True, checked=checked)
        return 1 if report.worst() == RANK[FAIL] else 0  # a dry run writes nothing
    if real_alert:
        alert(cfg, state, report, chk, dry_run=False, checked=checked)
    write_last(args.state_dir, report)
    state.save()
    return 1 if report.worst() == RANK[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
