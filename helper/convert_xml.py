#!/usr/bin/env python3

##########################################################################
# convert_xml.py - Convert old XML format to new format                  #
#                                                                        #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
##########################################################################

import sys
import os
import xml.etree.ElementTree as ET
import argparse


def convert_training(training: ET.Element) -> None:
    foerderung_elem = training.find("foerderung")
    if foerderung_elem is None or foerderung_elem.text is None:
        raise ValueError("Training ohne <foerderung> Element")

    foerderung = foerderung_elem.text.strip()

    teilnehmerzahl_elem = training.find("teilnehmerzahl")
    if teilnehmerzahl_elem is None or teilnehmerzahl_elem.text is None:
        raise ValueError("Training ohne <teilnehmerzahl> Element")

    tag_elem = training.find("tag")
    if tag_elem is None or tag_elem.text is None:
        raise ValueError("Training ohne <tag> Element")

    dauer_elem = training.find("dauer")
    if dauer_elem is None or dauer_elem.text is None:
        raise ValueError("Training ohne <dauer> Element")

    halleneinheiten_elem = training.find("halleneinheiten")

    existing_preise = [p.text for p in training.findall("preis") if p.text]

    for child in list(training):
        training.remove(child)

    training.append(tag_elem)

    new_foerderung = ET.Element("foerderung")
    new_foerderung.text = foerderung
    training.append(new_foerderung)

    if foerderung == "ja":
        for preis_text in existing_preise:
            foerderbetrag = ET.Element("foerderbetrag_gruppe")
            foerderbetrag.text = preis_text
            training.append(foerderbetrag)

        foerderkinder = ET.Element("foerderkinder")
        foerderkinder.text = teilnehmerzahl_elem.text
        training.append(foerderkinder)
    else:
        foerderbetrag = ET.Element("foerderbetrag_gruppe")
        training.append(foerderbetrag)

        foerderkinder = ET.Element("foerderkinder")
        training.append(foerderkinder)

    training.append(teilnehmerzahl_elem)
    training.append(dauer_elem)

    if halleneinheiten_elem is not None:
        training.append(halleneinheiten_elem)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="convert_xml", description="Konvertiere altes XML Format in neues Format"
    )
    parser.add_argument("eingabedatei", help="Eingabedatei (altes XML Format)")
    args = parser.parse_args()

    if not os.path.exists(args.eingabedatei):
        print(f"Eingabedatei existiert nicht: {args.eingabedatei}", file=sys.stderr)
        sys.exit(1)

    base, ext = os.path.splitext(args.eingabedatei)
    ausgabe = f"{base}_converted{ext}"

    if os.path.exists(ausgabe):
        print(f"Ausgabedatei existiert bereits: {ausgabe}", file=sys.stderr)
        sys.exit(1)

    try:
        tree = ET.parse(args.eingabedatei)
    except ET.ParseError as e:
        print(f"Fehlerhaftes XML-Format: {e}", file=sys.stderr)
        sys.exit(1)

    root = tree.getroot()

    for rechnung in root.findall("rechnung"):
        for kind in rechnung.findall("kind"):
            for training in kind.findall("training"):
                try:
                    convert_training(training)
                except ValueError as e:
                    print(f"Fehler: {e}", file=sys.stderr)
                    sys.exit(1)

    ET.indent(tree, space="  ")

    with open(ausgabe, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n')
        tree.write(f, encoding="unicode", xml_declaration=False, short_empty_elements=False)

    print(f"Konvertiert: {args.eingabedatei} -> {ausgabe}")


if __name__ == "__main__":
    main()
