> 本文件为 image 通道契约文档（原 sn-search-image skill，2026-11-13 收编进 deep-research）。

# Serper Image Search

Use this skill to search for candidate images via Serper.dev.

## Commands

Standard image search:

```bash
python {baseDir}/scripts/serper_image_search.py "QUERY" --num 10
```

Image URLs only:

```bash
python {baseDir}/scripts/serper_image_search.py "QUERY" --num 10 --image-urls-only --limit 5
```

Page URLs only:

```bash
python {baseDir}/scripts/serper_image_search.py "QUERY" --num 10 --page-urls-only --limit 5
```

Raw JSON:

```bash
python {baseDir}/scripts/serper_image_search.py "QUERY" --num 10 --json
```

Save raw JSON to a file for later inspection:

```bash
python {baseDir}/scripts/serper_image_search.py "QUERY" --num 10 --save-json /tmp/serper-images.json
```

## Important

- This skill only performs image search and returns candidate result metadata.
- Run the command directly as shown above.
- Do not wrap it with `cd`, shell pipes, `python -c`, here-docs, or output redirection tricks.
- Use `--gl` and `--hl` when you need country or language bias.
