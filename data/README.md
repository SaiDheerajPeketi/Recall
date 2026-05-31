# Corpus data

`sources.json` pins every public source by URL, license, retrieval date, local note, and SHA-256 content hash. The Markdown files are concise support notes derived from the linked primary sources; issue text is paraphrased rather than copied wholesale.

The bootstrap service verifies every hash before chunking or embedding. Headings and issue/resolution boundaries are preserved, long sections are split into 500-token windows with 60-token overlap, and the resulting corpus version is deterministic. Qdrant is rebuilt only when that version changes.

Generated embeddings and indexes are local-only and live in the Qdrant named volume.
