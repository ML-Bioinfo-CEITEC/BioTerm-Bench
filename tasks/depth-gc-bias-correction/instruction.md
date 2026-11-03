`/app/data/windows.tsv` gives 2100 genomic windows with their GC fraction
and raw sequencing depth. Depth in this dataset is biased by GC content.

Correct the bias, then flag the windows that are still unusual.

Assign every window to one of twenty GC bins by
`bin = min(19, int(gc * 20))`. Take the median raw depth of all windows,
and the median raw depth within each bin. A bin's correction factor is
`overall_median / bin_median`, except that a bin holding fewer than 50
windows, or whose median is zero, gets a factor of exactly `1.0`.

A window's corrected depth is its raw depth times its bin's factor.

Now take the median of all 2100 corrected depths and flag every window
whose corrected depth is below half that median (`low`) or above one and a
half times it (`high`).

Write `/app/output/flagged_windows.tsv` with header

`chrom	start	end	gc	raw_depth	corrected_depth	flag`

one row per flagged window, sorted by chromosome (`chr1`, `chr2`, `chr3`)
then start, echoing `gc` to four decimals and `raw_depth` to two, with
`corrected_depth` to four decimals.
