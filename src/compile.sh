#!/bin/sh

filename="rechnungen"

if [ $# -eq 1 ];
then
  filename="${1}"
fi
echo "${filename}"

rm -rf tex/ tmp/ pdf/ mails.csv
python3 tcsrechnung.py -i "${filename}".xml -o tex -m mails.csv -p pdf
for i in tex/*.tex; do latexmk -silent -interaction=nonstopmode -pdf -outdir=tmp "${i}"; done
mkdir -p pdf/
mv tmp/*.pdf pdf/
