# Preprint build

Generate the current core-25 tables and compile the paper from the repository
root:

```bash
python scripts/summarize_bioterm_v2.py
make -C paper
```

The build requires Tectonic. Generated tables are checked in so the manuscript
can also be compiled without access to the ignored local `jobs/` receipts. The
main paper target is five to eight rendered pages; inspect all pages after every
substantive table or figure update.
