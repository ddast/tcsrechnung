#!/usr/bin/env python3

##########################################################################
# tcsrechnung.py - Rechnungsauswertung des TC Stetten                    #
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
import datetime
import calendar
import argparse

MWST_VOLL = 0.19
MWST_ERM = 0.07


class TCSRechnungError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


WOCHENTAGE_DIC = {
    "Montag": 0,
    "Dienstag": 1,
    "Mittwoch": 2,
    "Donnerstag": 3,
    "Freitag": 4,
    "Samstag": 5,
    "Sonntag": 6,
}
MONATE_DIC = {
    "Januar": 1,
    "Februar": 2,
    "März": 3,
    "April": 4,
    "Mai": 5,
    "Juni": 6,
    "Juli": 7,
    "August": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Dezember": 12,
}


def _get_all_elems(parent: ET.Element, field_name: str) -> list[ET.Element]:
    elems = parent.findall(field_name)
    if elems is None:
        raise TCSRechnungError(f"Element <{field_name}> in Block <{parent.tag}> fehlt")
    return elems


def _get_elem(parent: ET.Element, field_name: str) -> ET.Element:
    elem = parent.find(field_name)
    if elem is None:
        raise TCSRechnungError(f"Element <{field_name}> in Block <{parent.tag}> fehlt")
    return elem


def _get_text(parent: ET.Element, field_name: str) -> str:
    elem = _get_elem(parent, field_name)
    if elem.text is None:
        raise TCSRechnungError(
            f"Element <{field_name}> in Block <{parent.tag}> fehlt oder ist leer"
        )
    return elem.text


def _get_int(parent: ET.Element, field_name: str) -> int:
    text = _get_text(parent, field_name)
    try:
        return int(text)
    except ValueError:
        raise TCSRechnungError(
            f"Element <{field_name}>='{text}' in Block <{parent.tag}> ist keine gültige"
            " Zahl"
        )


class Metadaten:
    def __init__(self, root: ET.Element) -> None:
        self.jahr = _get_int(root, "jahr")
        self.jahr_cur = datetime.date.today().year
        self.von_monat = _get_text(root, "von")
        self.bis_monat = _get_text(root, "bis")

        self.stdlohn60 = []
        for p in ["p1", "p2", "p3", "p4", "p5"]:
            elem_stdkosten = _get_elem(root, "stdkosten60")
            self.stdlohn60.append(_get_int(elem_stdkosten, p))

        self.stdlohn40 = []
        for p in ["p1", "p2", "p3", "p4"]:
            elem_stdkosten = _get_elem(root, "stdkosten40")
            self.stdlohn40.append(_get_int(elem_stdkosten, p))

        self.stdlohn60n = [i / (1.0 + MWST_VOLL) for i in self.stdlohn60]
        self.stdlohn40n = [i / (1.0 + MWST_VOLL) for i in self.stdlohn40]

        self.stdhalle = _get_int(root, "hallenkosten")
        self.stdhalle_netto = self.stdhalle / (1.0 + MWST_ERM)

        self.hallensaison = False
        self.wochentage_cnt = [0] * 7
        self._init_hallensaison(root)

    def _init_hallensaison(self, root: ET.Element) -> None:
        von_datum = datetime.date(self.jahr, MONATE_DIC[self.von_monat], 1)
        bis_datum = datetime.date(
            self.jahr,
            MONATE_DIC[self.bis_monat],
            calendar.monthrange(self.jahr, MONATE_DIC[self.bis_monat])[1],
        )
        beginn_halle_str = _get_text(root, "beginn_halle")
        try:
            beginn_halle = datetime.datetime.strptime(
                beginn_halle_str, "%d-%m-%Y"
            ).date()
        except ValueError:
            raise TCSRechnungError(
                f"<beginn_halle>='{beginn_halle_str}' hat ungültiges Format (erwartet:"
                " DD-MM-YYYY)"
            )
        ende_halle = beginn_halle + datetime.timedelta(30 * 7 - 1)
        if (beginn_halle < bis_datum < ende_halle) or (
            beginn_halle < von_datum < ende_halle
        ):
            print("Im Rechnungszeitraum ist Hallensaison.")
            self.hallensaison = True
        else:
            print("Im Rechnungszeitraum ist keine Hallensaison.")
            self.hallensaison = False

        for i in range(7):
            cur_datum = von_datum + datetime.timedelta(i)
            cnt = 0
            woche_delta = datetime.timedelta(7)
            while cur_datum <= ende_halle and cur_datum <= bis_datum:
                cnt += 1
                cur_datum += woche_delta
            self.wochentage_cnt[cur_datum.weekday()] = cnt


def erstelle_posten(
    training: ET.Element,
    meta: Metadaten,
    nettopreise: list[float],
    bruttopreise: list[float],
) -> str | None:
    # Create invoice for training only for Förderkinder.  Non-Förderkinder pay the training directly.
    is_foerderung = _get_text(training, "foerderung")
    if is_foerderung == "nein":
        elem_foerderbetrag = training.find("foerderbetrag_gruppe")
        if elem_foerderbetrag is not None and elem_foerderbetrag.text is not None:
            raise TCSRechnungError(
                "<foerderbetrag_gruppe> hat Wert {elem_foerderbetrag.text}, aber darf"
                " keinen gültigen Wert haben wenn <foerderung>=nein"
            )
        elem_foerderkinder = training.find("foerderkinder")
        if elem_foerderkinder is not None and elem_foerderkinder.text is not None:
            raise TCSRechnungError(
                "<foerderkinder> hat Wert {elem_foerderkinder.text}, aber darf keinen"
                " gültigen Wert haben wenn <foerderung>=nein"
            )
        return None
    elif is_foerderung != "ja":
        raise TCSRechnungError(
            f"Ungültiger Eintrag <foerderung>={is_foerderung}.  Erlaubte Werte"
            " sind 'ja' und 'nein'."
        )

    gesamtfoerderung = 0
    for foerderbetrag in _get_all_elems(training, "foerderbetrag_gruppe"):
        if foerderbetrag.text is None:
            raise TCSRechnungError(f"<{foerderbetrag.tag}> ist leer")
        try:
            gesamtfoerderung += int(foerderbetrag.text)
        except ValueError:
            raise TCSRechnungError(
                f"<{foerderbetrag.tag}>='{foerderbetrag.text}' ist keine gültige Zahl"
            )

    dauer = _get_int(training, "dauer")
    teilnehmerzahl = _get_int(training, "teilnehmerzahl")
    if dauer == 60:
        stdlohn = meta.stdlohn60[teilnehmerzahl - 1]
        stdlohn_netto = meta.stdlohn60n[teilnehmerzahl - 1]
    elif dauer == 40:
        stdlohn = meta.stdlohn40[teilnehmerzahl - 1]
        stdlohn_netto = meta.stdlohn40n[teilnehmerzahl - 1]
    else:
        raise TCSRechnungError(f"Ungültige Trainingsdauer={dauer}")

    foerderkinder = _get_int(training, "foerderkinder")
    if gesamtfoerderung * teilnehmerzahl % stdlohn * foerderkinder != 0:
        raise TCSRechnungError(
            f"Gesamtfoerderung={gesamtfoerderung} ist kein Vielfaches von"
            f" stdlohn={stdlohn}"
        )
    einheiten = int(gesamtfoerderung / stdlohn)

    foerderung_pp_netto = gesamtfoerderung / (foerderkinder * (1.0 + MWST_VOLL))
    zahlbetrag_netto = 0.0
    zahlbetrag_brutto = 0.0

    nettopreise.append(zahlbetrag_netto)
    bruttopreise.append(zahlbetrag_brutto)

    posten = (
        "\\Posten{"
        + _get_text(training, "tag")
        + "}{"
        + str(einheiten)
        + "}{"
        + "{:.2f}".format(stdlohn_netto * 60 / dauer).replace(".", ",")
        + "}{"
        + str(teilnehmerzahl)
        + "}{"
        + str(dauer)
        + "}{"
        + "{:.2f}".format(foerderung_pp_netto).replace(".", ",")
        + "}{"
        + "{:.2f}".format(foerderung_pp_netto).replace(".", ",")
        + "}{"
        + "{:.2f}".format(zahlbetrag_netto).replace(".", ",")
        + "}\n"
    )
    return posten


def erstelle_hallenposten(
    training: ET.Element,
    meta: Metadaten,
    nettopreise: list[float],
    bruttopreise: list[float],
) -> str:
    wochentag = _get_text(training, "tag")

    einheiten = 0
    halleneinheiten = training.find("halleneinheiten")
    if halleneinheiten is None or halleneinheiten.text is None:
        einheiten = meta.wochentage_cnt[WOCHENTAGE_DIC[wochentag]]
    else:
        einheiten = _get_int(training, "halleneinheiten")

    teilnehmerzahl = _get_int(training, "teilnehmerzahl")
    dauer = _get_int(training, "dauer")

    gesamtpreis_netto = einheiten * meta.stdhalle_netto * dauer / (60 * teilnehmerzahl)

    nettopreise.append(round(gesamtpreis_netto, 2))
    bruttopreise.append(
        round(einheiten * meta.stdhalle * dauer / (60 * teilnehmerzahl), 2)
    )

    posten = (
        "\\Posten{"
        + wochentag
        + "}{"
        + str(einheiten)
        + "}{"
        + "{:.2f}".format(meta.stdhalle_netto).replace(".", ",")
        + "}{"
        + str(teilnehmerzahl)
        + "}{"
        + str(dauer)
        + "}{"
        + "{:.2f}".format(gesamtpreis_netto).replace(".", ",")
        + "}{"
        + "{:.2f}".format(0).replace(".", ",")
        + "}{"
        + "{:.2f}".format(gesamtpreis_netto).replace(".", ",")
        + "}\n"
    )
    return posten


def erstelle_rechnung(
    rechnung: ET.Element, rechnungsnummer: int, meta: Metadaten
) -> str:
    rechnung_name = _get_text(rechnung, "name")
    try:
        latex_out = (
            "\\Empfaenger{"
            + rechnung_name
            + "}{"
            + _get_text(rechnung, "strasse")
            + "}{"
            + _get_text(rechnung, "ort")
            + "}\n"
        )

        kinder = ""
        kindercnt = 0

        for kind in _get_all_elems(rechnung, "kind"):
            kindercnt += 1
            if kindercnt > 1:
                kinder += ", "
            kinder += _get_text(kind, "name")

        latex_out += (
            "\\Referenz{"
            + str(meta.jahr_cur - 2000)
            + "/{:04d}".format(rechnungsnummer)
            + "}{"
            + meta.von_monat
            + "}{"
            + meta.bis_monat
            + " "
            + str(meta.jahr)
            + "}{"
            + kinder
            + "}\n"
        )
    except TCSRechnungError as e:
        raise TCSRechnungError(f"Fehler in Rechnung für '{rechnung_name}': {str(e)}")

    nettopreise16: list[float] = []
    bruttopreise16: list[float] = []
    nettopreise7: list[float] = []
    bruttopreise7: list[float] = []

    for kind in _get_all_elems(rechnung, "kind"):
        kind_name = _get_text(kind, "name")
        posten_training = []
        posten_halle = []
        try:
            for training in _get_all_elems(kind, "training"):
                if (
                    current_posten := erstelle_posten(
                        training, meta, nettopreise16, bruttopreise16
                    )
                ) is not None:
                    posten_training.append(current_posten)

                posten_halle.append(
                    erstelle_hallenposten(training, meta, nettopreise7, bruttopreise7)
                )
        except TCSRechnungError as e:
            raise TCSRechnungError(
                f"Fehler in Rechnung für '{rechnung_name}',"
                f" Kind '{kind_name}': {str(e)}"
            )

        if posten_training:
            if kindercnt > 1:
                latex_out += "\\Kostentyp{Trainingskosten (" + kind_name + ")}\n"
            else:
                latex_out += "\\Kostentyp{Trainingskosten}\n"
            for posten in posten_training:
                latex_out += posten

        if meta.hallensaison:
            if kindercnt > 1:
                latex_out += "\\Kostentyp{Hallenkosten (" + kind_name + ")}\n"
            else:
                latex_out += "\\Kostentyp{Hallenkosten}\n"
            for posten in posten_halle:
                latex_out += posten

    sumnp16 = sum(nettopreise16)
    sumbp16 = sum(bruttopreise16)
    sumnp7 = sum(nettopreise7)
    sumbp7 = sum(bruttopreise7)

    if meta.hallensaison:
        latex_out += (
            "\\SummeWinter{"
            + "{:.2f}".format(sumnp16 + sumnp7).replace(".", ",")
            + "}{"
            + "{:.2f}".format(sumbp16 - sumnp16).replace(".", ",")
            + "}{"
            + "{:.2f}".format(sumbp7 - sumnp7).replace(".", ",")
            + "}{"
            + "{:.2f}".format(sumbp16 + sumbp7).replace(".", ",")
            + "}\n"
        )
    else:
        latex_out += (
            "\\SummeSommer{"
            + "{:.2f}".format(sumnp16).replace(".", ",")
            + "}{"
            + "{:.2f}".format(sumbp16 - sumnp16).replace(".", ",")
            + "}{"
            + "{:.2f}".format(sumbp16).replace(".", ",")
            + "}\n"
        )

    latex_out += (
        "\\Schluss{"
        + meta.von_monat
        + "}{"
        + meta.bis_monat
        + " "
        + str(meta.jahr)
        + "}{"
        + str(meta.jahr + 1)
        + "}\n\n"
    )
    return latex_out


def erstelle_mail(rechnung: ET.Element, meta: Metadaten, texfile: str) -> str:
    email_out = _get_text(rechnung, "email")
    name = _get_text(rechnung, "name")
    anrede = name.split(" ", 1)[0]
    if anrede in ["Familie", "Frau"]:
        anrede_out = "Liebe " + name
    elif anrede == "Herr":
        anrede_out = "Lieber Herr " + name.split(" ", 1)[1]
    else:
        anrede_out = "Liebe/r " + name

    kinder = _get_all_elems(rechnung, "kind")
    kinder_out = _get_text(kinder[0], "name")
    for kind in kinder[1:-1]:
        kinder_out += ", " + _get_text(kind, "name")
    if len(kinder) > 1:
        kinder_out += " und " + _get_text(kinder[-1], "name")

    pdffile = os.path.join(os.path.splitext(os.path.basename(texfile))[0] + ".pdf")

    return (
        anrede_out
        + ";"
        + email_out
        + ";"
        + kinder_out
        + ";"
        + meta.von_monat
        + ";"
        + meta.bis_monat
        + ";"
        + str(meta.jahr)
        + ";"
        + pdffile
        + "\n"
    )


def get_mail_header() -> str:
    return "Anrede;Email;Kinder;Von_Monat;Bis_Monat;Jahr;Anhang\n"


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="tcsrechnung", description="Erstelle LaTeX Datei für TCS Rechnungen"
    )
    parser.add_argument("-i", required=True, help="Eingabedatei (xml Format)")
    parser.add_argument(
        "-o", required=True, help="Ausgabeordner Rechnungen (tex Format)"
    )
    parser.add_argument("-m", required=True, help="Ausgabedatei Emails (csv Format)")
    parser.add_argument(
        "--nosingle",
        action="store_true",
        help="Erstelle keine einzelnen Rechnungsdateien",
    )
    args = parser.parse_args()

    tree = ET.parse(args.i)
    root = tree.getroot()
    if not os.path.exists(args.o):
        os.makedirs(args.o)
    meta = Metadaten(root)

    texfile_all = os.path.join(
        args.o,
        "rechnungen_"
        + str(meta.jahr)
        + "_"
        + str(MONATE_DIC[meta.von_monat])
        + "-"
        + str(MONATE_DIC[meta.bis_monat])
        + ".tex",
    )
    filename_nomail = os.path.join(args.o, "rechnungen_nomail.txt")
    with open(args.m, "w") as f_mail, open(texfile_all, "w") as f_tex_all, open(
        filename_nomail, "w"
    ) as f_nomail:
        f_mail.write(get_mail_header())
        f_tex_all.write("\\documentclass{tcsrechnung}\n")
        f_tex_all.write("\\begin{document}\n")
        rechnungsnr = _get_int(root, "rechnungsnummer")
        for rechnung in _get_all_elems(root, "rechnung"):
            rechnungsnr += 1
            output = erstelle_rechnung(rechnung, rechnungsnr, meta)
            f_tex_all.write(output)
            if args.nosingle:
                continue
            texfile = os.path.join(
                args.o,
                str(meta.jahr_cur - 2000) + "_{:04d}".format(rechnungsnr) + ".tex",
            )
            with open(texfile, "w") as f_tex:
                f_tex.write("\\documentclass{tcsrechnung}\n")
                f_tex.write("\\begin{document}\n")
                f_tex.write(output)
                f_tex.write("\\end{document}\n")
            try:
                f_mail.write(erstelle_mail(rechnung, meta, texfile))
            except TCSRechnungError:
                pdffile = os.path.join(
                    os.path.splitext(os.path.basename(texfile))[0] + ".pdf"
                )
                f_nomail.write(pdffile + "\n")

        f_tex_all.write("\\end{document}\n")


if __name__ == "__main__":
    try:
        run()
    except TCSRechnungError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print("Fehlerhaftes Format der XML Datei: " + str(e), file=sys.stderr)
        sys.exit(1)
