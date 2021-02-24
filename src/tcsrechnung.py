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

WOCHENTAGE_DIC = {
    'Montag': 0, 'Dienstag': 1, 'Mittwoch': 2,
    'Donnerstag': 3, 'Freitag': 4, 'Samstag': 5, 'Sonntag': 6
    }
MONATE_DIC = {
    'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5,
    'Juni': 6, 'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10,
    'November': 11, 'Dezember': 12
    }


class Metadaten():
    """Für gesamte Rechungsstellung gültige Metadaten.

    Attribute:
        jahr: Jahr der Rechnung
        jahr_cur: Jahr in dem Rechnung verschickt wird
        von_monat: Erster Monat
        bis_monat: Letzer Monat
        stdlohn60: Bruttostundenlohn für 60 Minuten
        stdlohn40: Bruttostundenlohn für 40 Minuten
        stdlohn60n: Nettostundenlohn für 60 Minuten
        stdlohn40n: Nettostundenlohn für 40 Minuten
        hallensaison: Ist im Zeitraum Hallensaison?
        stdhalle: Bruttohallenkosten für eine Stunde
        stdhalle_netto: Nettohallenkosten für eine Stunde
        wochentage_cnt: Wochentage in der Schnittmenge Hallensaison und
                        Rechnungszeitraum
     """

    def __init__(self, root):
        """Initialisiere verwendete Variablen.

        @root: Wurzel xml-tree aller Rechnungen
        """
        self.jahr = int(root.find('jahr').text)
        self.jahr_cur = datetime.date.today().year
        self.von_monat = root.find('von').text
        self.bis_monat = root.find('bis').text
        self.stdlohn60 = [int(root.find('stdkosten60').find(p).text)
                          for p in ['p1', 'p2', 'p3', 'p4', 'p5']]
        self.stdlohn40 = [int(root.find('stdkosten40').find(p).text)
                          for p in ['p1', 'p2', 'p3', 'p4']]
        self.stdlohn60n = [i / (1.0 + MWST_VOLL) for i in self.stdlohn60]
        self.stdlohn40n = [i / (1.0 + MWST_VOLL) for i in self.stdlohn40]
        self.stdhalle = int(root.find('hallenkosten').text)
        self.stdhalle_netto = self.stdhalle/(1.0+MWST_ERM)

        self.hallensaison = False
        self.wochentage_cnt = [0]*7
        self._init_hallensaison(root)

    def _init_hallensaison(self, root):
        """Initialisiert self.hallensaison und self.wochentage_cnt."""
        von_datum = datetime.date(self.jahr, MONATE_DIC[self.von_monat], 1)
        bis_datum = datetime.date(
                self.jahr, MONATE_DIC[self.bis_monat],
                calendar.monthrange(self.jahr, MONATE_DIC[self.bis_monat])[1])
        beginn_halle_str = root.find('beginn_halle').text
        beginn_halle = datetime.datetime.strptime(beginn_halle_str,
                                                  '%d-%m-%Y').date()
        ende_halle = beginn_halle + datetime.timedelta(30*7-1)
        if ((beginn_halle < bis_datum < ende_halle) or
                (beginn_halle < von_datum < ende_halle)):
            print('Im Rechnungszeitraum ist Hallensaison.')
            self.hallensaison = True
        else:
            print('Im Rechnungszeitraum ist keine Hallensaison.')
            self.hallensaison = False

        for i in range(7):
            cur_datum = von_datum + datetime.timedelta(i)
            cnt = 0
            woche_delta = datetime.timedelta(7)
            while cur_datum <= ende_halle and cur_datum <= bis_datum:
                cnt += 1
                cur_datum += woche_delta
            self.wochentage_cnt[cur_datum.weekday()] = cnt


def erstelle_posten(training, meta, nettopreise, bruttopreise):
    """Erzeugt Posten aus einem Trainingsblock.

       @training: xml-tree eines Trainingselements
       @meta: Metadaten gültig für alle Rechnungen
       @nettopreise: Rückgabeliste für Nettopreise (Cent Genauigkeit)
       @bruttopreise: Rückgabeliste für Bruttopreise (Cent Genauigkeit)
    """
    dauer = int(training.find('dauer').text)
    teilnehmerzahl = int(training.find('teilnehmerzahl').text)

    gesamtpreis = 0
    for preis in training.findall('preis'):
        gesamtpreis += int(preis.text)
    gesamtpreis_netto = gesamtpreis/(teilnehmerzahl*(1.0+MWST_VOLL))

    if dauer == 60:
        stdlohn = meta.stdlohn60[teilnehmerzahl-1]
        stdlohn_netto = meta.stdlohn60n[teilnehmerzahl-1]
    elif dauer == 40:
        stdlohn = meta.stdlohn40[teilnehmerzahl-1]
        stdlohn_netto = meta.stdlohn40n[teilnehmerzahl-1]
    else:
        print('Keine gültige Trainingsdauer angegeben', file=sys.stderr)
        return 0

    if gesamtpreis % stdlohn == 0:
        einheiten = int(gesamtpreis/stdlohn)
    else:
        print('Gesamtpreis ist kein Vielfaches des Stundenlohns',
              file=sys.stderr)

    if training.find('foerderung').text == 'ja':
        foerderung = gesamtpreis_netto
        zahlbetrag = 0.
        zahlbetrag_brutto = 0.
    else:
        foerderung = 0.
        zahlbetrag = gesamtpreis_netto
        zahlbetrag_brutto = gesamtpreis/teilnehmerzahl

    nettopreise.append(round(zahlbetrag, 2))
    bruttopreise.append(round(zahlbetrag_brutto, 2))

    posten = ('\\Posten{' +
              training.find('tag').text + '}{' +
              str(einheiten) + '}{' +
              '{:.2f}'.format(stdlohn_netto*60/dauer).replace('.', ',') +
              '}{' + str(teilnehmerzahl) + '}{'
              + str(dauer) + '}{' +
              '{:.2f}'.format(gesamtpreis_netto).replace('.', ',') + '}{' +
              '{:.2f}'.format(foerderung).replace('.', ',') + '}{' +
              '{:.2f}'.format(zahlbetrag).replace('.', ',') + '}\n')
    return posten


def erstelle_hallenposten(training, meta, nettopreise, bruttopreise):
    """Erzeugt Hallenposten aus einem Trainingsblock.

       @training: xml-tree eines Trainingselements
       @meta: Metadaten gültig für alle Rechnungen
       @nettopreise: Rückgabeliste für Nettopreise (Cent Genauigkeit)
       @bruttopreise: Rückgabeliste für Bruttopreise (Cent Genauigkeit)
    """
    wochentag = training.find('tag').text

    einheiten = 0
    halleneinheiten = training.find('halleneinheiten')
    if halleneinheiten is None:
        einheiten = meta.wochentage_cnt[WOCHENTAGE_DIC[wochentag]]
    else:
        einheiten = int(halleneinheiten.text)

    teilnehmerzahl = int(training.find('teilnehmerzahl').text)

    dauer = int(training.find('dauer').text)

    gesamtpreis_netto = einheiten*meta.stdhalle_netto*dauer/(60*teilnehmerzahl)

    nettopreise.append(round(gesamtpreis_netto, 2))
    bruttopreise.append(
        round(einheiten * meta.stdhalle * dauer / (60 * teilnehmerzahl), 2))

    posten = ('\\Posten{' +
              wochentag + '}{' +
              str(einheiten) + '}{' +
              '{:.2f}'.format(meta.stdhalle_netto).replace('.', ',') + '}{' +
              str(teilnehmerzahl) + '}{' +
              str(dauer) + '}{' +
              '{:.2f}'.format(gesamtpreis_netto).replace('.', ',') + '}{' +
              '{:.2f}'.format(0).replace('.', ',') + '}{' +
              '{:.2f}'.format(gesamtpreis_netto).replace('.', ',') + '}\n')
    return posten


def erstelle_rechnung(rechnung, rechnungsnummer, meta):
    """Erstellt eine Rechnung.

       @rechnung: xml-tree eines Rechnungelements
       @rechnungsnummer: fortlaufende Rechnungsnummer
       @meta: Metadaten gültig für alle Rechnungen
    """
    latex_out = ('\\Empfaenger{' + rechnung.find('name').text + '}{'
                 + rechnung.find('strasse').text + '}{'
                 + rechnung.find('ort').text + '}\n')

    kinder = ''
    kindercnt = 0

    for kind in rechnung.findall('kind'):
        kindercnt += 1
        if kindercnt > 1:
            kinder += ', '
        kinder += kind.find('name').text

    latex_out += ('\\Referenz{' + str(meta.jahr_cur-2000)
                  + '/{:04d}'.format(rechnungsnummer)
                  + '}{' + meta.von_monat
                  + '}{' + meta.bis_monat + ' ' + str(meta.jahr)
                  + '}{' + kinder + '}\n')

    nettopreise16 = []
    bruttopreise16 = []
    nettopreise7 = []
    bruttopreise7 = []

    for kind in rechnung.findall('kind'):
        posten_training = []
        posten_halle = []
        for training in kind.findall('training'):
            if training.find('bezahlt').text != 'ja':
                posten_training.append(erstelle_posten(training, meta,
                                                       nettopreise16,
                                                       bruttopreise16))
            posten_halle.append(erstelle_hallenposten(training, meta,
                                                      nettopreise7,
                                                      bruttopreise7))

        name = kind.find('name').text

        if posten_training:
            if kindercnt > 1:
                latex_out += '\\Kostentyp{Trainingskosten (' + name + ')}\n'
            else:
                latex_out += '\\Kostentyp{Trainingskosten}\n'
            for posten in posten_training:
                latex_out += posten

        if meta.hallensaison:
            if kindercnt > 1:
                latex_out += '\\Kostentyp{Hallenkosten (' + name + ')}\n'
            else:
                latex_out += '\\Kostentyp{Hallenkosten}\n'
            for posten in posten_halle:
                latex_out += posten

    sumnp16 = sum(nettopreise16)
    sumbp16 = sum(bruttopreise16)
    sumnp7 = sum(nettopreise7)
    sumbp7 = sum(bruttopreise7)

    if meta.hallensaison:
        latex_out += ('\\SummeWinter{'
                      + '{:.2f}'.format(sumnp16 + sumnp7).replace('.', ',')
                      + '}{'
                      + '{:.2f}'.format(sumbp16 - sumnp16).replace('.', ',')
                      + '}{'
                      + '{:.2f}'.format(sumbp7 - sumnp7).replace('.', ',')
                      + '}{'
                      + '{:.2f}'.format(sumbp16 + sumbp7).replace('.', ',')
                      + '}\n')
    else:
        latex_out += ('\\SummeSommer{'
                      + '{:.2f}'.format(sumnp16).replace('.', ',')
                      + '}{'
                      + '{:.2f}'.format(sumbp16-sumnp16).replace('.', ',')
                      + '}{'
                      + '{:.2f}'.format(sumbp16).replace('.', ',')
                      + '}\n')

    latex_out += ('\\Schluss{' + meta.von_monat + '}{' + meta.bis_monat
                  + ' ' + str(meta.jahr) + '}{' + str(meta.jahr+1) + '}\n\n')
    return latex_out


def erstelle_mail(rechnung, meta, texfile, folder):
    """Erstellt Mailausgabe

       @rechnung: xml-tree eines Rechnungelements
       @meta: Metadaten gültig für alle Rechnungen
    """
    email = rechnung.find('email')
    if email is None or email.text is None:
        return ''
    email_out = email.text

    name = rechnung.find('name').text
    anrede = name.split(' ', 1)[0]
    if anrede in ['Familie', 'Frau']:
        anrede_out = 'Liebe ' + name
    elif anrede == 'Herrn':
        anrede_out = 'Lieber Herr ' + name.split(' ', 1)[1]
    else:
        anrede_out = 'Liebe/r ' + name

    kinder = rechnung.findall('kind')
    kinder_out = kinder[0].find('name').text
    for kind in kinder[1:-1]:
        kinder_out += ', ' + kind.find('name').text
    if len(kinder) > 1:
        kinder_out += ' und ' + kinder[-1].find('name').text

    texfile = os.path.join(os.getcwd(), folder,
                           os.path.splitext(os.path.basename(texfile))[0]
                           + '.pdf')

    return (anrede_out + ';'
            + email_out + ';'
            + kinder_out + ';'
            + meta.von_monat + ';'
            + meta.bis_monat + ';'
            + str(meta.jahr) + ';'
            + texfile + '\n')


def get_mail_header():
    """Gibt den Header der csv Datei für die Mails zurück"""
    return "Anrede;Email;Kinder;Von_Monat;Bis_Monat;Jahr;Anhang\n"


def run():
    """Beginne Auswertung der xml-Datei und starte Rechnungserstellung
    """
    parser = argparse.ArgumentParser(
        prog='tcsrechnung',
        description='Erstelle LaTeX Datei für TCS Rechnungen')
    parser.add_argument('-i', required=True,
                        help='Eingabedatei (xml Format)')
    parser.add_argument('-o', required=True,
                        help='Ausgabeordner Rechnungen (tex Format)')
    parser.add_argument('-m', required=True,
                        help='Ausgabedatei Emails (csv Format)')
    parser.add_argument('-p', required=True,
                        help='Ausgabeordner Rechnungen (pdf Format)')
    parser.add_argument('--nosingle', action='store_true',
                        help='Erstelle keine einzelnen Rechnungsdateien')
    args = parser.parse_args()

    tree = ET.parse(args.i)
    root = tree.getroot()
    if not os.path.exists(args.o):
        os.makedirs(args.o)
    meta = Metadaten(root)

    texfile_all = os.path.join(args.o, 'rechnungen_' + str(meta.jahr)
                               + '_' + str(MONATE_DIC[meta.von_monat]) + '-'
                               + str(MONATE_DIC[meta.bis_monat]) + '.tex')
    with open(args.m, 'w') as f_mail, open(texfile_all, 'w') as f_tex_all:
        f_mail.write(get_mail_header())
        f_tex_all.write('\\documentclass{tcsrechnung}\n')
        f_tex_all.write('\\begin{document}\n')
        rechnungsnr = int(root.find('rechnungsnummer').text)
        for rechnung in root.findall('rechnung'):
            rechnungsnr += 1
            output = erstelle_rechnung(rechnung, rechnungsnr, meta)
            f_tex_all.write(output)
            if args.nosingle:
                continue
            texfile = os.path.join(args.o, str(meta.jahr_cur-2000)
                                   + '_{:04d}'.format(rechnungsnr) + '.tex')
            with open(texfile, 'w') as f_tex:
                f_tex.write('\\documentclass{tcsrechnung}\n')
                f_tex.write('\\begin{document}\n')
                f_tex.write(output)
                f_tex.write('\\end{document}\n')
            f_mail.write(erstelle_mail(rechnung, meta, texfile, args.p))
        f_tex_all.write('\\end{document}\n')


if __name__ == '__main__':
    run()
