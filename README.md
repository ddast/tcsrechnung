# TCS Rechnung

Rechnungsgenerierung für den Tennisclub Stetten/F. e.V.

## Überblick

Dieses Tool generiert aus XML-Eingabedaten LaTeX-Rechnungen mit PDF-Ausgabe.  Es unterstützt die Abrechnung von Trainings- und Hallenkosten für Trainingsgruppen mit und ohne Förderung.

Normalerweise muss nur die XML-Datei angepasst werden.  Die Python- und LaTeX-Dateien bleiben unverändert.

## Voraussetzungen

- Python 3
- LaTeX-Distribution (z.B. TeX Live) mit KOMA-Klasse `scrlttr2` und `latexmk`
- Für Entwicklung die Python-Pakete: `pytest`, `mypy`, `black`

## Verwendung

### Vollständige Verarbeitung (XML → PDF)

```bash
./src/compile.sh rechnungen.xml
```

Dies erzeugt im Verzeichnis `pdf/` die fertigen Rechnungen als PDF-Dateien.  Optionen an `src/compile.sh` werden an `src/tcsrechnung.py` weitergereicht.

### Nur Python (XML → LaTeX)

```bash
python3 src/tcsrechnung.py -i rechnungen.xml -o tex -m mails.csv
```

Optionen:
- `--nosingle`: Keine einzelnen Rechnungsdateien erzeugen, sondern nur eine gesamte Datei für schnellere PDF Erzeugung.

### Nur LaTeX (TeX → PDF)

```bash
latexmk -pdf -outdir=build tex/*.tex
```

## XML-Format

Siehe `test/rechnungen.xml` für ein Beispiel der XML-Struktur.

## Entwicklung

### Tests ausführen

```bash
pytest test/ -v
```

### Typprüfung

```bash
mypy --strict src/
mypy --ignore-missing-imports test/
```

### Code-Formatierung

```bash
black src/ test/
```
