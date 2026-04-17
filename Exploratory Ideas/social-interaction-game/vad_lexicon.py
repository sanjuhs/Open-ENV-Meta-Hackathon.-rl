from __future__ import annotations

from pathlib import Path


DEFAULT_VAD_LEXICON = {
    "sorry": (0.42, 0.36, 0.34),
    "brutal": (0.18, 0.74, 0.31),
    "hard": (0.26, 0.58, 0.33),
    "rough": (0.24, 0.56, 0.35),
    "painful": (0.12, 0.66, 0.24),
    "hurt": (0.15, 0.63, 0.28),
    "numb": (0.22, 0.18, 0.21),
    "fired": (0.08, 0.78, 0.19),
    "embarrassed": (0.18, 0.71, 0.22),
    "anxious": (0.14, 0.81, 0.20),
    "upset": (0.18, 0.72, 0.27),
    "angry": (0.12, 0.84, 0.55),
    "fight": (0.11, 0.82, 0.58),
    "mom": (0.52, 0.38, 0.46),
    "minute": (0.50, 0.24, 0.34),
    "space": (0.61, 0.18, 0.44),
    "breathe": (0.68, 0.14, 0.41),
    "slow": (0.60, 0.13, 0.39),
    "gentle": (0.74, 0.20, 0.42),
    "steady": (0.71, 0.18, 0.48),
    "safe": (0.81, 0.16, 0.51),
    "here": (0.66, 0.24, 0.42),
    "with": (0.60, 0.22, 0.38),
    "support": (0.82, 0.36, 0.58),
    "care": (0.84, 0.34, 0.53),
    "listen": (0.72, 0.21, 0.47),
    "hear": (0.68, 0.22, 0.43),
    "understand": (0.73, 0.24, 0.49),
    "sense": (0.67, 0.20, 0.44),
    "together": (0.79, 0.34, 0.58),
    "tonight": (0.54, 0.30, 0.37),
    "relieved": (0.81, 0.30, 0.51),
    "proud": (0.90, 0.63, 0.72),
    "shipped": (0.78, 0.58, 0.69),
    "fix": (0.63, 0.57, 0.65),
    "bug": (0.36, 0.52, 0.40),
    "amazing": (0.94, 0.72, 0.66),
    "love": (0.96, 0.67, 0.68),
    "warm": (0.86, 0.30, 0.49),
    "good": (0.78, 0.44, 0.58),
    "glad": (0.82, 0.46, 0.56),
    "calm": (0.75, 0.12, 0.46),
    "plan": (0.54, 0.44, 0.61),
    "resume": (0.48, 0.50, 0.56),
    "networking": (0.53, 0.47, 0.54),
    "immediately": (0.38, 0.86, 0.71),
    "urgent": (0.30, 0.90, 0.64),
    "now": (0.47, 0.70, 0.58),
    "apologize": (0.52, 0.46, 0.44),
    "question": (0.51, 0.40, 0.52),
    "why": (0.44, 0.48, 0.50),
    "perform": (0.40, 0.63, 0.58),
    "alone": (0.20, 0.45, 0.22),
    "thank": (0.84, 0.38, 0.52),
    "thanks": (0.86, 0.40, 0.52),
    "happy": (0.94, 0.68, 0.64),
    "celebrate": (0.93, 0.72, 0.68),
    "tiny": (0.58, 0.20, 0.36),
    "annoying": (0.22, 0.60, 0.34),
    "done": (0.69, 0.31, 0.58),
    "whatever": (0.16, 0.44, 0.39),
    "dramatic": (0.10, 0.61, 0.51),
    "stupid": (0.06, 0.76, 0.49),
    "crazy": (0.08, 0.82, 0.48),
}


def load_vad_lexicon() -> dict:
    """
    Load an optional local NRC-style VAD TSV if the user adds one.

    Expected format:
    word<TAB>valence<TAB>arousal<TAB>dominance
    """
    data_path = Path(__file__).with_name("data") / "nrc_vad_lexicon.tsv"
    if not data_path.exists():
        return DEFAULT_VAD_LEXICON

    lexicon = {}
    with data_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 4:
                continue
            word, valence, arousal, dominance = parts
            try:
                lexicon[word.lower()] = (float(valence), float(arousal), float(dominance))
            except ValueError:
                continue
    return lexicon or DEFAULT_VAD_LEXICON
