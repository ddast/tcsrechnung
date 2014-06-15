all: rechnungen.pdf

clean:
	rm -rf rechnungen*.pdf tmp *.tex

.PHONY: all clean

%.pdf: %.xml
	python3 tcsrechnung.py $*.xml > $*.tex
	mkdir -p tmp
	pdflatex -output-directory=tmp $*.tex
	pdflatex -output-directory=tmp $*.tex
	mv tmp/$*.pdf .
	rm -rf tmp $*.tex 
