The file `/app/data/reads.fastq.gz` is a gzipped single-end FASTQ.
The file `/app/data/adapter.txt` is a single line containing an
adapter DNA sequence (ASCII, uppercase).

Produce one output file:

- `/app/output/counts.json` — a JSON object with exactly these three
  keys and no others:

        {
          "total_reads":   <int>,
          "adapter_reads": <int>,
          "adapter_seq":   "<string>"
        }

Semantics:

- `total_reads` is the total number of FASTQ records in
  `reads.fastq.gz`.
- `adapter_reads` is the number of reads whose **sequence line**
  contains the adapter string as an exact, case-sensitive substring.
  Each qualifying read is counted once even if the adapter appears
  multiple times in the read.
- `adapter_seq` is the adapter string, copied verbatim from
  `adapter.txt` with any trailing newline stripped.

Emit the JSON with sorted keys and 2-space indentation so that the
file is deterministically formatted. A trailing newline is fine.
