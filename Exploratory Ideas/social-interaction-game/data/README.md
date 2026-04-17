Drop an optional `nrc_vad_lexicon.tsv` file here if you want to replace the bundled seed VAD lexicon with a fuller NRC-style lexicon.

Expected TSV format:

```text
word<TAB>valence<TAB>arousal<TAB>dominance
```

If this file is absent, the prototype falls back to the bundled lexicon in [vad_lexicon.py](/Users/sanju/Desktop/coding/python/open-env-meta/Exploratory%20Ideas/social-interaction-game/vad_lexicon.py).
