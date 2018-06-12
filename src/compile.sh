#!/bin/bash

if [ "${#}" -eq 1 ]; then
  xmlfile="${1}"
elif [ "${#}" -eq 2 ]; then
  xmlfile="${1}"
  option="${2}"
else
  echo "Verwendung: ${0} xmldatei argument"
  echo "xmldate: Enthält xml Beschreibung der Rechnungen"
  echo "argument: Ein weiteres Argument, das an tcsrechung weitergegeben wird"
  exit 1
fi

texdir="tex"
pdfdir="pdf"
mailfile="mails.csv"
builddir="tmp"

if [ ! -f "${xmlfile}" ]; then
  echo "Datei existiert nicht: ${xmlfile}"
  exit 1
fi

rm -rf "${texdir}" "${pdfdir}" "${builddir}" "${mailfile}"

if [ -z "${option}" ]; then
  tcsrechnung -i "${xmlfile}" -o "${texdir}" -m "${mailfile}" -p "${pdfdir}"
else
  tcsrechnung -i "${xmlfile}" -o "${texdir}" -m "${mailfile}" -p "${pdfdir}" "${option}"
fi

for i in "${texdir}"/*.tex; do
  latexmk -silent -interaction=nonstopmode -pdf -outdir="${builddir}" "${i}"
done

mkdir "${pdfdir}"
mv "${builddir}"/*.pdf "${pdfdir}"


rm -r "${texdir}" "${builddir}"
