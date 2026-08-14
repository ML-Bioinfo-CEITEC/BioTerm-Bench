PDF=main.pdf

.PHONY: all pdf clean

all: pdf

pdf: $(PDF)

$(PDF): main.tex references.bib generated/table_headline.tex generated/table_exclusions.tex generated/table_hardest_tasks.tex generated/table_v2_selection.tex
	tectonic main.tex

clean:
	rm -f main.pdf main.aux main.bbl main.blg main.log main.out main.synctex.gz
