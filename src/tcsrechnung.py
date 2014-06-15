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
import xml.etree.ElementTree as ET
import datetime
import calendar


# Wörterbücher
wochentage_dic = {'Montag': 0, 'Dienstag': 1, 'Mittwoch': 2,\
    'Donnerstag': 3, 'Freitag': 4, 'Samstag': 5, 'Sonntag': 6}
monate_dic = {'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5,\
    'Juni': 6, 'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10,\
    'November': 11, 'Dezember': 12}

# Globale Variablen für gesamte Rechnungsstellung gültig
# Jahr der Rechnungsstellung
jahr=0
# Erster Monat
von_monat=""
# Letzer Monat
bis_monat=""
# Brutto Stundenlohn für 60 und 40 Minuten
stdlohn60 = []
stdlohn40 = []
# Netto Stundenlohn für 60 und 40 Minuten
stdlohn60n = []
stdlohn40n = []
# Ist im Zeitraum Hallensaison?
hallensaison=0
# Brutto Hallenkosten für eine Stunde
stdhalle=0
# Netto Hallenkosten für eine Stunde
stdhalle_netto=0
# Wochentage in der Schnittmenge Hallensaison und Rechnungszeitraum
wochentage_cnt = [0]*7


def erstelle_posten(training, nettopreise, bruttopreise):
  """Erzeugt Posten aus einem Trainingsblock.

     @training: xml-tree eines Trainingselements
     @nettopreise: Rückgabeliste für Nettopreise (Cent Genauigkeit)
     @bruttopreise: Rückgabeliste für Bruttopreise (Cent Genauigkeit)
  """

  # Trainingsdauer
  dauer = int(training.find('dauer').text)

  # Teilnehmerzahl
  teilnehmerzahl = int(training.find('teilnehmerzahl').text)

  # Berechne Gesamtpreis
  gesamtpreis = 0
  for preis in training.findall('preis'):
    gesamtpreis += int(preis.text)
  gesamtpreis_netto = gesamtpreis/(teilnehmerzahl*1.19)

  # Stundenlohn
  if dauer == 60:
    stdlohn = stdlohn60[teilnehmerzahl-1]
    stdlohn_netto = stdlohn60n[teilnehmerzahl-1]
  elif dauer == 40:
    stdlohn = stdlohn40[teilnehmerzahl-1]
    stdlohn_netto = stdlohn40n[teilnehmerzahl-1]
  else:
    print('Keine gültige Trainingsdauer angegeben', file=sys.stderr)
    return 0

  # Zahl der Trainingseinheiten
  if gesamtpreis%stdlohn == 0:
    einheiten = int(gesamtpreis/stdlohn)
  else:
    print('Gesamtpreis ist kein Vielfaches des Stundenlohns', file=sys.stderr)

  # Förderung und Zahlbetrag
  if training.find('foerderung').text == 'ja':
    foerderung = gesamtpreis_netto
    zahlbetrag = 0.
    zahlbetrag_brutto = 0.
  else:
    foerderung = 0.
    zahlbetrag = gesamtpreis_netto
    zahlbetrag_brutto = gesamtpreis/teilnehmerzahl

  # Speicher Preise in Liste für spätere Auswertung
  nettopreise.append(round(zahlbetrag,2))
  bruttopreise.append(round(zahlbetrag_brutto,2))

  # Erstelle Latex Kommando für einen Posten und gib dieses zurück
  posten = '\Posten{' +\
    training.find('tag').text + '}{' +\
    str(einheiten) + '}{' +\
    '{:.2f}'.format(stdlohn_netto*60/dauer).replace('.',',') + '}{' +\
    str(teilnehmerzahl) + '}{' +\
    str(dauer) + '}{' +\
    '{:.2f}'.format(gesamtpreis_netto).replace('.',',') + '}{' +\
    '{:.2f}'.format(foerderung).replace('.',',') + '}{' +\
    '{:.2f}'.format(zahlbetrag).replace('.',',') + '}'
  return posten


def erstelle_hallenposten(training, nettopreise, bruttopreise):
  """Erzeugt Hallenposten aus einem Trainingsblock.

     @training: xml-tree eines Trainingselements
     @nettopreise: Rückgabeliste für Nettopreise (Cent Genauigkeit)
     @bruttopreise: Rückgabeliste für Bruttopreise (Cent Genauigkeit)
  """
  # Wochentag
  wochentag = training.find('tag').text

  # Zahl der Halleneinheiten
  # Falls explizit angegeben wird dieser Wert übernommen, ansonsten der gesamte
  # Zeitraum angenommen.
  einheiten = 0
  halleneinheiten = training.find('halleneinheiten')
  if halleneinheiten is None:
    einheiten = wochentage_cnt[wochentage_dic[wochentag]]
  else:
    einheiten = int(halleneinheiten.text)

  # Teilnehmerzahl
  teilnehmerzahl = int(training.find('teilnehmerzahl').text)

  # Trainingsdauer
  dauer = int(training.find('dauer').text)

  # Gesamtpreis netto
  gesamtpreis_netto = einheiten*stdhalle_netto*dauer/(60*teilnehmerzahl)

  # Speicher Preise in Liste für spätere Auswertung
  nettopreise.append(round(gesamtpreis_netto,2))
  bruttopreise.append(round(einheiten*stdhalle*dauer/(60*teilnehmerzahl),2))

  # Erstelle Latex Kommando für einen Posten und gib dieses zurück
  posten = '\Posten{' +\
    wochentag + '}{' +\
    str(einheiten) + '}{' +\
    '{:.2f}'.format(stdhalle_netto).replace('.',',') + '}{' +\
    str(teilnehmerzahl) + '}{' +\
    str(dauer) + '}{' +\
    '{:.2f}'.format(gesamtpreis_netto).replace('.',',') + '}{' +\
    '{:.2f}'.format(0).replace('.',',') + '}{' +\
    '{:.2f}'.format(gesamtpreis_netto).replace('.',',') + '}'
  return posten

def erstelle_rechnung(rechnung, rechnungsnummer):
  """Erstellt eine Rechnung.

     @rechnung: xml-tree eines Rechnungelements
     @rechnungsnummer: fortlaufende Rechnungsnummer
     Die Funktion erzeugt sämtliche Latex Kommandos zu einer Rechnung.
  """

  # Empfängerzeile
  print('\Empfaenger{', rechnung.find('name').text, '}{',
      rechnung.find('strasse').text, '}{',
      rechnung.find('ort').text, '}',
      sep='')

  # Speichere und zähle alle Kinder, die zu einer Rechnung gehören
  kinder = ''
  kindercnt = 0

  # Iteriere über alle Kinder um Referenzzeile zu erstellen
  for kind in rechnung.findall('kind'):
    # Speichere alle Kindername in @kinder
    kindercnt += 1
    if kindercnt > 1:
      kinder += ', '
    kinder += kind.find('name').text

  # Gib Referenzzeile aus
  jahr_current = datetime.date.today().year
  print('\Referenz{', jahr_current-2000, '/{:04d}'.format(rechnungsnummer),
      '}{', von_monat, '}{', bis_monat, ' ', jahr, '}{', kinder, '}', sep='')

  # Variablen zum Zwischenspeichern der Brutto und Nettobeträge gerundet
  # auf zwei Nachkommastellen
  nettopreise16 = []
  bruttopreise16 = []
  nettopreise7 = []
  bruttopreise7 = []

  # Iteriere über alle Kinder um Posten zu berechnen
  for kind in rechnung.findall('kind'):

    # Berechne Trainings und Hallenposten
    posten_training = []
    posten_halle = []
    for training in kind.findall('training'):
      if training.find('bezahlt').text != 'ja':
        posten_training.append(erstelle_posten(training,
          nettopreise16, bruttopreise16))
      posten_halle.append(erstelle_hallenposten(training,
        nettopreise7, bruttopreise7))

    # Name des Kindes
    name = kind.find('name').text

    # Trainingskosten ausgeben, falls posten_training nicht leer ist
    # Falls mehrere Kinder gib Name des Kindes in Klammern an
    if posten_training:
      if kindercnt > 1:
        print('\Kostentyp{Trainingskosten (' + name + ')}')
      else:
        print('\Kostentyp{Trainingskosten}')
      for posten in posten_training:
        print(posten)

    # Hallenkosten ausgeben falls Hallensaison ist
    # Falls mehrere Kinder gib Name des Kindes in Klammern an
    if hallensaison:
      if kindercnt > 1:
        print('\Kostentyp{Hallenkosten (' + name + ')}')
      else:
        print('\Kostentyp{Hallenkosten}')
      for posten in posten_halle:
        print(posten)

  # Summe mit und ohne MwSt
  sumnp16 = sum(nettopreise16)
  sumbp16 = sum(bruttopreise16)
  sumnp7 = sum(nettopreise7)
  sumbp7 = sum(bruttopreise7)

  # Nur in der Wintersaison wird 7% MwSt ausgegeben
  if hallensaison:
    print('\SummeWinter{',
        '{:.2f}'.format(sumnp16+sumnp7).replace('.',','), '}{',
        '{:.2f}'.format(sumbp16-sumnp16).replace('.',','), '}{',
        '{:.2f}'.format(sumbp7-sumnp7).replace('.',','), '}{',
        '{:.2f}'.format(sumbp16+sumbp7).replace('.',','), '}',
        sep='')
  else:
    print('\SummeSommer{',
        '{:.2f}'.format(sumnp16).replace('.',','), '}{',
        '{:.2f}'.format(sumbp16-sumnp16).replace('.',','), '}{',
        '{:.2f}'.format(sumbp16).replace('.',','), '}',
        sep='')
    


  # Abschluss der Rechnung
  print('\Schluss{', von_monat, '}{', bis_monat, ' ', jahr, '}{', jahr+1, '}',
      sep='')

  print()

def run():
    """Beginne Auswertung der xml-Datei und starte Rechnungserstellung
    """
    # Werte Parameter aus
    if len(sys.argv) != 2:
      print('Verwendung:', sys.argv[0], 'daten.xml')
      sys.exit(1)

    # Öffne die xml-Daten, die als erstes Argument übergeben wurde
    tree = ET.parse(sys.argv[1])
    root = tree.getroot()

    # Jahr
    global jahr
    jahr = int(root.find('jahr').text)

    # Erster Monat
    global von_monat
    von_monat = root.find('von').text
    von_datum = datetime.date(jahr, monate_dic[von_monat], 1)

    # Letzter Monat
    global bis_monat
    bis_monat = root.find('bis').text
    bis_datum = datetime.date(jahr, monate_dic[bis_monat],
        calendar.monthrange(jahr, monate_dic[bis_monat])[1])

    # Trainingskosten für 1,2,3,4 Personen festlegen, für 60 und 40min
    global stdlohn60
    stdlohn60.append(int(root.find('stdkosten60').find('p1').text))
    stdlohn60.append(int(root.find('stdkosten60').find('p2').text))
    stdlohn60.append(int(root.find('stdkosten60').find('p3').text))
    stdlohn60.append(int(root.find('stdkosten60').find('p4').text))
    stdlohn60.append(int(root.find('stdkosten60').find('p5').text))
    global stdlohn40
    stdlohn40.append(int(root.find('stdkosten40').find('p1').text))
    stdlohn40.append(int(root.find('stdkosten40').find('p2').text))
    stdlohn40.append(int(root.find('stdkosten40').find('p3').text))
    stdlohn40.append(int(root.find('stdkosten40').find('p4').text))

    # Berechne Nettostundenlöhne
    global stdlohn60n
    for i in stdlohn60:
      stdlohn60n.append(i/1.19)
    global stdlohn40n
    for i in stdlohn40:
      stdlohn40n.append(i/1.19)

    # Beginn Hallensaison
    beginn_halle_str = root.find('beginn_halle').text
    beginn_halle = datetime.datetime.strptime(beginn_halle_str,
            '%d-%m-%Y').date()
    ende_halle = beginn_halle + datetime.timedelta(30*7-1)

    # Überprüfe ob Rechnungen im Hallenzeitraum erstellt werden
    global hallensaison
    if (bis_datum > beginn_halle and bis_datum < ende_halle) or\
        (von_datum > beginn_halle and von_datum < ende_halle):
      hallensaison = True
      print('Im Rechnungszeitraum ist Hallensaison', file=sys.stderr) 
    else:
      print('Im Rechnungszeitraum ist keine Hallensaison', file=sys.stderr) 
      hallensaison = False

    # Zähle Wochentage in der Schnittmenge Hallensaison und Rechnungszeitraum
    global wochentage_cnt
    for i in range(7):
      cur_datum = von_datum + datetime.timedelta(i)
      cnt = 0
      woche_delta = datetime.timedelta(7)
      while cur_datum <= ende_halle and cur_datum <= bis_datum:
        cnt += 1
        cur_datum += woche_delta
      wochentage_cnt[cur_datum.weekday()] = cnt

    # Hallenkosten für eine Stunde, brutto und netto
    global stdhalle
    stdhalle = int(root.find('hallenkosten').text)
    global stdhalle_netto
    stdhalle_netto = stdhalle/1.07

    # Rechnungsnummer der ersten Rechnung minus Eins
    rechnungsnummer = int(root.find('rechnungsnummer').text)

    # Beginne Latex-Document
    print("\\documentclass{tcsrechnung}\n\n\\begin{document}\n")
    # Iteriere über alle Rechnungsblöcke und erstelle zugehörige Latex-Kommandos
    for rechnung in root.findall('rechnung'):
      rechnungsnummer += 1
      erstelle_rechnung(rechnung, rechnungsnummer)
    
    print('\end{document}\n')


if __name__ == "__main__":
    run()

