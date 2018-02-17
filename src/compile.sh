#!/bin/sh

filename="rechnungen"

if [ $# -eq 1 ];
then
  filename="${1}"
fi
echo "${filename}"

python3 tcsrechnung.py -i "${filename}".xml -o tex -m mails.csv
rm -rf tmp/*.pdf
for i in tex/*.tex; do latexmk -pdf -outdir=tmp "${i}"; done
rm -rf pdf/
mkdir -p pdf/
cp tmp/*.pdf pdf/
