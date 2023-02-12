#!/bin/sh

if [ "$#" -ge 1 ]; then
  xmlfile="$1"
  shift
else
  echo "Verwendung: $0 xmldatei arguments"
  echo "xmldatei: Enthält xml Beschreibung der Rechnungen"
  echo "argument: Weitere Argumente, die an tcsrechung weitergegeben werden"
  exit 1
fi

texdir="tex"
pdfdir="pdf"
mailfile="mails.csv"
builddir="tmp"

if [ ! -f "$xmlfile" ]; then
  echo "Datei existiert nicht: $xmlfile"
  exit 1
fi

rm -rf "$texdir" "$pdfdir" "$builddir" "$mailfile"

tcsrechnung -i "$xmlfile" -o "$texdir" -m "$mailfile" "$@"

for i in "$texdir"/*.tex; do
  latexmk -silent -interaction=nonstopmode -pdf -outdir="$builddir" "$i"
done

mkdir "$pdfdir"
mv "$builddir"/*.pdf "$pdfdir"

rm -r "$texdir" "$builddir"
