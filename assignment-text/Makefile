.PHONY: default

default: worm-assignment.pdf ../README.md \
    ../README.html\
    ../worm_gate/README.html\
    ../python_zip_example/README.html\

worm-assignment.pdf: worm-assignment.md $(wildcard *.bib) $(wildcard *.csl)
	pandoc --filter pandoc-citeproc $< -o $@

../README.md: worm-assignment.md $(wildcard *.bib) $(wildcard *.csl)
	pandoc -s --toc --shift-heading-level-by=1 --webtex --filter pandoc-citeproc $< --to gfm -o $@

%.html: %.md
	pandoc $< -o $@
