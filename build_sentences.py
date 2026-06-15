import whisperx, json, os, re
from pathlib import Path

AUDIO_DIR  = "/home/youssefokab/Desktop/workspace/slow_german/audio"
CACHE_DIR  = "/home/youssefokab/Desktop/workspace/slow_german/cache"
OUTPUT     = "/home/youssefokab/Desktop/workspace/slow_german/sg_sentences.json"
DEVICE     = "cuda"
LANG       = "de"
SKIP_START = 30   # skip first 30s (intro jingle)
SKIP_END   = 30   # skip last  30s (outro jingle)

Path(CACHE_DIR).mkdir(exist_ok=True, parents=True)

# ── Music / singing detection ──────────────────────────────────────────────────
def is_music(seg, words):
    text     = seg.get("text", "").strip()
    start    = seg["start"]
    end      = seg["end"]
    duration = end - start

    if not text:
        return True

    # Whisper flagged it as non-speech
    if seg.get("no_speech_prob", 0) > 0.6:
        return True

    word_list = text.split()

    # Too few words for the duration  (singing drags words out)
    if len(word_list) < 3 and duration > 3:
        return True

    # Average word duration too long  (>1.5 s/word = drawn-out singing)
    seg_words = [w for w in words if start - 0.1 <= w["start"] <= end + 0.1]
    if seg_words:
        avg_dur = duration / len(seg_words)
        if avg_dur > 1.5:
            return True

    # Highly repetitive text (la la la / na na na style)
    unique_ratio = len(set(w.lower() for w in word_list)) / len(word_list)
    if unique_ratio < 0.4:
        return True

    return False

# ── Load models once, lazily ───────────────────────────────────────────────────
_model = _align_model = _align_meta = None

def get_models():
    global _model, _align_model, _align_meta
    if _model is None:
        print("Loading WhisperX models (one-time)…")
        _model = whisperx.load_model("large-v3", DEVICE, language=LANG, compute_type="float16")
        _align_model, _align_meta = whisperx.load_align_model(language_code=LANG, device=DEVICE)
    return _model, _align_model, _align_meta

# ── Main loop ──────────────────────────────────────────────────────────────────
all_sentences = []

for ep_num in range(1, 320):
    audio_path = f"{AUDIO_DIR}/sg{ep_num}.mp3"
    if not os.path.exists(audio_path):
        continue

    cache_path = f"{CACHE_DIR}/sg{ep_num}.json"

    if os.path.exists(cache_path):
        print(f"[sg{ep_num:>3}] cache hit")
        with open(cache_path) as f:
            cached   = json.load(f)
        segments = cached["segments"]
        words    = cached["words"]
        duration = cached["duration"]

    else:
        model, align_model, align_meta = get_models()
        print(f"[sg{ep_num:>3}] transcribing…", end="", flush=True)

        audio    = whisperx.load_audio(audio_path)
        duration = len(audio) / 16000

        result   = model.transcribe(audio, batch_size=4, language=LANG)

        # Save no_speech_prob keyed by start time before alignment may shift things
        nsp_by_start = {round(s["start"], 2): s.get("no_speech_prob", 0)
                        for s in result["segments"]}

        result   = whisperx.align(result["segments"], align_model, align_meta,
                                  audio, DEVICE, return_char_alignments=False)

        segments = []
        for seg in result["segments"]:
            segments.append({
                "text":          seg.get("text", "").strip(),
                "start":         round(seg.get("start", 0), 3),
                "end":           round(seg.get("end",   0), 3),
                "no_speech_prob": nsp_by_start.get(round(seg.get("start", 0), 2), 0),
            })

        words = []
        for seg in result["segments"]:
            for w in seg.get("words", []):
                if "start" in w and "end" in w:
                    words.append({
                        "word":  w["word"].strip(),
                        "start": round(w["start"], 3),
                        "end":   round(w["end"],   3),
                    })

        with open(cache_path, "w") as f:
            json.dump({"segments": segments, "words": words, "duration": duration},
                      f, ensure_ascii=False)
        print(f" {len(segments)} segments cached")

    # ── Extract sentences from this episode ─────────────────────────────────
    ep_count = 0
    for seg in segments:
        start = seg["start"]
        end   = seg["end"]
        text  = seg["text"]

        # Skip intro and outro windows
        if start < SKIP_START:
            continue
        if end > duration - SKIP_END:
            continue

        # Skip very short or empty
        if not text or len(text.split()) < 2:
            continue

        # Skip singing / music
        if is_music(seg, words):
            print(f"  [music filtered] {text[:60]}")
            continue

        all_sentences.append({
            "episode":    ep_num,
            "audio_file": f"sg{ep_num}.mp3",
            "text":       text,
            "start_sec":  round(start, 3),
            "end_sec":    round(end,   3),
            "start_ms":   int(start * 1000),
            "end_ms":     int(end   * 1000),
            "match_score": 1.0,
        })
        ep_count += 1

    print(f"[sg{ep_num:>3}] {ep_count} sentences  (total so far: {len(all_sentences)})")

    # Save after every episode so crashes don't lose progress
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_sentences, f, ensure_ascii=False, indent=2)

print(f"\nDone!  {len(all_sentences)} sentences across {len(set(s['episode'] for s in all_sentences))} episodes")
print(f"Output: {OUTPUT}")
