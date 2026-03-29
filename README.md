# TCS Rechnung

Rechnungsgenerierung für den Tennisclub Stetten/F. e.V.

## Überblick

Dieses Tool generiert aus XML-Eingabedaten LaTeX-Rechnungen mit PDF-Ausgabe.  Es unterstützt die Abrechnung von Trainings- und Hallenkosten für Trainingsgruppen mit und ohne Förderung.

Normalerweise muss nur die XML-Datei angepasst werden.  Die Python- und LaTeX-Dateien bleiben unverändert.

## Voraussetzungen

- Python 3
- LaTeX-Distribution (z.B. TeX Live) mit KOMA-Klasse `scrlttr2` und `latexmk`
- Für Entwicklung die Python-Pakete: `pytest`, `mypy`, `black`

## Einrichtung

### Script installieren

Zur Verwendung von `compile.sh` muss `tcsrechnung.py` als `tcsrechnung` ausführbar sein.  Falls `~/bin' bereits im `$PATH` ist:

```bash
ln -s $(pwd)/src/tcsrechnung.py ~/bin/tcsrechnung
```

### LaTeX-Klasse installieren

Um `compile.sh` von beliebigen Orten aus aufrufen zu können, muss die LaTeX-Klasse `tcsrechnung.cls` in einem Verzeichnis installiert werden, das LaTeX durchsucht:

```bash
mkdir -p ~/texmf/tex/latex/tcsrechnung
ln -s $(pwd)/src/tcsrechnung.cls ~/texmf/tex/latex/tcsrechnung/
ln -s $(pwd)/src/tcslogo.pdf ~/texmf/tex/latex/tcsrechnung/
```

Nach der Installation muss die TeX-Datei-Datenbank aktualisiert werden:

```bash
# Für TeX Live
texhash ~/texmf

# Oder falls texhash nicht verfügbar:
# Die Klasse wird beim ersten LaTeX-Lauf automatisch gefunden
```

### Persönliche Daten konfigurieren

Die LaTeX-Klasse benötigt persönliche Daten (Rücksendeadresse, Kontakt). Diese werden aus einer separaten Konfigurationsdatei geladen, die nicht im Repository enthalten ist:

```bash
cp src/personal-config.template.tex src/personal-config.tex
ln -s $(pwd)/src/personal-config.tex ~/texmf/tex/latex/tcsrechnung/
# personal-config.tex mit einem Texteditor anpassen
```

## Verwendung

### Vollständige Verarbeitung (XML → PDF)

```bash
./src/compile.sh rechnungen.xml
```

Dies erzeugt im Verzeichnis `pdf/` die fertigen Rechnungen als PDF-Dateien.  Optionen an `src/compile.sh` werden an `src/tcsrechnung.py` weitergereicht.

### Nur Python (XML → LaTeX)

```bash
python3 src/tcsrechnung.py -o tex -m mails rechnungen.xml
```

Optionen:
- `--nosingle`: Keine einzelnen Rechnungsdateien erzeugen, sondern nur eine gesamte Datei für schnellere PDF Erzeugung.

### Nur LaTeX (TeX → PDF)

```bash
latexmk -pdf -outdir=build tex/*.tex
```

## XML-Format

Siehe `test/rechnungen.xml` für ein Beispiel der XML-Struktur.

### Wurzelelement `<data>`

| Element | Beschreibung |
|---------|--------------|
| `<von>` | Startmonat des Abrechnungszeitraums (z.B. "Oktober") |
| `<bis>` | Endmonat des Abrechnungszeitraums (z.B. "Dezember") |
| `<jahr>` | Jahr des Abrechnungszeitraums |
| `<stdkosten60>` | Stundensätze für 60-Minuten-Training nach Teilnehmerzahl (1–5) |
| `<stdkosten60><p1>` | Stundensatz bei 1 Teilnehmer (brutto inkl. 19% MwSt) |
| `<stdkosten60><p2>` | Stundensatz bei 2 Teilnehmern |
| `<stdkosten60><p3>` | Stundensatz bei 3 Teilnehmern |
| `<stdkosten60><p4>` | Stundensatz bei 4 Teilnehmern |
| `<stdkosten60><p5>` | Stundensatz bei 5 Teilnehmern |
| `<stdkosten40>` | Stundensätze für 40-Minuten-Training nach Teilnehmerzahl (1–4) |
| `<stdkosten40><p1>` | Stundensatz bei 1 Teilnehmer (brutto inkl. 19% MwSt) |
| `<stdkosten40><p2>` | Stundensatz bei 2 Teilnehmern |
| `<stdkosten40><p3>` | Stundensatz bei 3 Teilnehmern |
| `<stdkosten40><p4>` | Stundensatz bei 4 Teilnehmern |
| `<beginn_halle>` | Startdatum der Hallensaison im Format TT-MM-JJJJ |
| `<hallenkosten>` | Hallenkosten pro Stunde pro Teilnehmer (brutto inkl. 7% MwSt) |
| `<rechnungsnummer>` | Rechnungsnummer der letzten ausgestellten Rechnung.  Diese wird für jede Rechnung hochgezählt und die erste Nummer ist der angegebene Wert + 1. |

### Rechnung `<rechnung>`

Jede `<rechnung>`-Block enthält die Daten einer Rechnung.

| Element | Beschreibung |
|---------|--------------|
| `<name>` | Name des Rechnungsempfängers (z.B. "Familie Berger") |
| `<strasse>` | Straße und Hausnummer |
| `<ort>` | Postleitzahl und Ort |
| `<email>` | E-Mail-Adresse für den Versand der Rechnung |

### Kind `<kind>`

Jedes `<kind>`-Element innerhalb einer Rechnung beschreibt ein Kind mit seinen Trainings.

| Element | Beschreibung |
|---------|--------------|
| `<name>` | Vorname des Kindes |

### Training `<training>`

Jedes `<training>`-Element innerhalb eines Kindes beschreibt ein Training.

| Element | Beschreibung |
|---------|--------------|
| `<tag>` | Wochentag des Trainings (z.B. "Dienstag", "Mittwoch") |
| `<foerderung>` | Wird das Kind gefördert: "ja" oder "nein" |
| `<foerderbetrag_gruppe>` | Förderbetrag für die gesamte Gruppe.  Mehrere Elemente möglich, sodass der Förderbetrag für jeden Monat einzeln angegeben werden kann.  Die Summe dieser Elemente ergibt den Förderbetrag für den gesamten Rechnungszeitraum. |
| `<foerderkinder>` | Anzahl der geförderten Kinder in der Gruppe |
| `<teilnehmerzahl>` | Anzahl der Teilnehmer in der Trainingsgruppe (1–5) |
| `<dauer>` | Trainingsdauer in Minuten (40 oder 60) |
| `<halleneinheiten>` | Optionale Anzahl der Halleneinheiten (Überschreibt die automatische Berechnung aus dem Abrechnungszeitraum) |

## Entwicklung

### Tests ausführen

```bash
pytest test/ -v
```

### Typprüfung

```bash
mypy --strict src/ helper/
mypy --ignore-missing-imports test/
```

### Code-Formatierung

```bash
black --preview --enable-unstable-feature=string_processing src/ helper/ test/
```
