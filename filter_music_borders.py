"""
Remove sentences from sg_sentences.json that are immediately followed by
a music/non-speech segment in the same episode, since those get cut off early.
"""
import json
from pathlib import Path

CACHE_DIR  = "cache"
INPUT      = "sg_sentences.json"
OUTPUT     = "sg_sentences.json"

with open(INPUT, encoding="utf-8") as f:
    sentences = json.load(f)

print(f"Loaded {len(sentences)} sentences")

# Group sentences by episode for efficient lookup
by_episode = {}
for s in sentences:
    by_episode.setdefault(s["episode"], []).append(s)

# Load cache per episode and mark sentences that precede music
episode_segs = {}

def load_segs(ep):
    if ep in episode_segs:
        return episode_segs[ep]
    p = Path(CACHE_DIR) / f"sg{ep}.json"
    if p.exists():
        data = json.loads(p.read_text())
        episode_segs[ep] = data.get("segments", [])
    else:
        episode_segs[ep] = []
    return episode_segs[ep]

def next_seg_is_music(ep, end_sec, gap=1.5):
    """True if the segment starting within `gap` seconds after end_sec has high no_speech_prob."""
    for seg in load_segs(ep):
        seg_start = seg.get("start", 0)
        if end_sec - 0.1 <= seg_start <= end_sec + gap:
            if seg.get("no_speech_prob", 0) > 0.5:
                return True
            # Also flag very short text segments (likely music)
            words = seg.get("text", "").strip().split()
            duration = seg.get("end", 0) - seg_start
            if len(words) < 3 and duration > 2:
                return True
    return False

kept = []
removed = 0
for s in sentences:
    if next_seg_is_music(s["episode"], s["end_sec"]):
        removed += 1
    else:
        kept.append(s)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(kept, f, ensure_ascii=False, indent=2)

print(f"Removed {removed} sentences (preceded music)")
print(f"Kept    {len(kept)} sentences")
print(f"Saved to {OUTPUT}")
