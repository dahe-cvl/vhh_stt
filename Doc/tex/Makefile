FILE=report

all: $(FILE).pdf

.PHONY: clean
clean:
	rm -f *.aux *.bbl *.bcf *.blg *.log *.run.xml *.synctex.gz *.toc *.lof *.out

$(FILE).pdf: $(FILE).tex $(wildcard chapters/*.tex)
	texfot pdflatex -synctex=1 -interaction=nonstopmode $(FILE)
	biber $(FILE)
	# makeindex $(FILE).nlo -s nomencl.ist -o $(FILE).nls
	texfot pdflatex -synctex=1 -interaction=nonstopmode $(FILE)
	rm -f *.aux *.bbl *.bcf *.blg *.log *.run.xml *.synctex.gz *.toc *.lof *.out
	evince $(FILE).pdf & 