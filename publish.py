#!/usr/bin/env python3
"""Build and publish Yoshi's sake vocabulary lessons as a static GitHub Pages site.

Source of truth (read-only here):
  ~/.hermes/profiles/inosuke/workspace/vocab/lessons/YYYY-MM-DD.md
  ~/.hermes/profiles/inosuke/workspace/vocab/taught.json
Output (this repo): index.html (static shell), data.json, lessons/*.md (raw copies)

Usage: python3 publish.py            # build, commit, push
       python3 publish.py --no-push  # build only
"""
import html, json, os, re, shutil, subprocess, sys

HOME = os.path.expanduser("~")
VOCAB = os.path.join(HOME, ".hermes/profiles/inosuke/workspace/vocab")
REPO = os.path.dirname(os.path.abspath(__file__))


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\|\|(.+?)\|\|", r'<span class="spoiler" tabindex="0" title="Tap to reveal">\1</span>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def md_to_html(md):
    out, in_list, title = [], False, None
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                out.append("</ul>"); in_list = False
            continue
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>"); in_list = False
        m = re.fullmatch(r"\*\*(.+)\*\*", line.strip())
        if m and title is None and "今日の酒ことば" in m.group(1):
            title = m.group(1)
            continue  # rendered by the page as the card heading
        if m:
            out.append(f"<h3>{inline(m.group(1))}</h3>")
        elif line.startswith("#"):
            out.append(f"<h3>{inline(line.lstrip('#').strip())}</h3>")
        else:
            out.append(f"<p>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    return title, "\n".join(out)


def build():
    ledger = json.load(open(os.path.join(VOCAB, "taught.json"), encoding="utf-8"))
    topic_by_date = {l["date"]: l.get("topic", "") for l in ledger.get("lessons", [])}
    ldir = os.path.join(VOCAB, "lessons")
    out_ldir = os.path.join(REPO, "lessons")
    os.makedirs(out_ldir, exist_ok=True)
    lessons = []
    for name in sorted(os.listdir(ldir)):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", name):
            continue
        date = name[:-3]
        md = open(os.path.join(ldir, name), encoding="utf-8").read()
        shutil.copyfile(os.path.join(ldir, name), os.path.join(out_ldir, name))
        title, body = md_to_html(md)
        text = re.sub(r"[*|#\-]", " ", md)
        lessons.append({"date": date, "topic": topic_by_date.get(date, ""), "title": title or date,
                        "html": body, "text": text})
    data = {
        "lessons": lessons,
        "kanji": ledger.get("kanji", []),
        "words": ledger.get("words", []),
        "topics": ledger.get("topics", []),
        "exhausted": ledger.get("exhausted", False),
    }
    with open(os.path.join(REPO, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    open(os.path.join(REPO, ".nojekyll"), "w").close()
    print(f"built: {len(lessons)} lessons, {len(data['kanji'])} kanji, {len(data['words'])} words")


def git(*args, check=True):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, check=check)


def publish():
    git("add", "-A")
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        print("no changes to publish")
        return
    latest = sorted(os.listdir(os.path.join(REPO, "lessons")))[-1][:-3]
    git("commit", "-m", f"Lessons through {latest}")
    r = git("push", "origin", "HEAD:main", check=False)
    if r.returncode != 0:
        print("PUSH FAILED:\n" + r.stderr, file=sys.stderr)
        sys.exit(1)
    print("published")


if __name__ == "__main__":
    build()
    if "--no-push" not in sys.argv:
        publish()
