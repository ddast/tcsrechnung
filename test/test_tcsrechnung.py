#!/usr/bin/env python3

##########################################################################
# test_tcsrechnung.py - Tests for tcsrechnung.py                         #
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from tcsrechnung import (
    TCSRechnungError,
    Metadaten,
    _get_elem,
    _get_text,
    _get_int,
    _get_all_elems,
    erstelle_posten,
    erstelle_hallenposten,
    erstelle_rechnung,
    erstelle_mail,
    get_mail_header,
    MWST_VOLL,
    MWST_ERM,
)


class TestHelperFunctions:
    def test_get_elem_success(self):
        parent = ET.fromstring("<root><child>text</child></root>")
        elem = _get_elem(parent, "child")
        assert elem.text == "text"

    def test_get_elem_missing(self):
        parent = ET.fromstring("<root></root>")
        with pytest.raises(TCSRechnungError) as exc_info:
            _get_elem(parent, "missing")
        assert "Element <missing> in Block <root> fehlt" in str(exc_info.value)

    def test_get_text_success(self):
        parent = ET.fromstring("<root><name>Test</name></root>")
        assert _get_text(parent, "name") == "Test"

    def test_get_text_empty(self):
        parent = ET.fromstring("<root><name></name></root>")
        with pytest.raises(TCSRechnungError) as exc_info:
            _get_text(parent, "name")
        assert "fehlt oder ist leer" in str(exc_info.value)

    def test_get_int_success(self):
        parent = ET.fromstring("<root><count>42</count></root>")
        assert _get_int(parent, "count") == 42

    def test_get_int_invalid(self):
        parent = ET.fromstring("<root><count>abc</count></root>")
        with pytest.raises(TCSRechnungError) as exc_info:
            _get_int(parent, "count")
        assert "ist keine gültige Zahl" in str(exc_info.value)

    def test_get_all_elems_success(self):
        parent = ET.fromstring("<root><item>1</item><item>2</item></root>")
        elems = _get_all_elems(parent, "item")
        assert len(elems) == 2
        assert elems[0].text == "1"
        assert elems[1].text == "2"

    def test_get_all_elems_empty(self):
        parent = ET.fromstring("<root></root>")
        elems = _get_all_elems(parent, "item")
        assert elems == []


class TestMetadaten:
    def create_metadata_xml(
        self,
        jahr: int = 2024,
        von: str = "Oktober",
        bis: str = "Dezember",
        beginn_halle: str = "01-10-2024",
        hallenkosten: int = 14,
        rechnungsnummer: int = 0,
    ) -> ET.Element:
        return ET.fromstring(f"""<data>
            <von>{von}</von>
            <bis>{bis}</bis>
            <jahr>{jahr}</jahr>
            <stdkosten60>
                <p1>48</p1>
                <p2>52</p2>
                <p3>54</p3>
                <p4>56</p4>
                <p5>60</p5>
            </stdkosten60>
            <stdkosten40>
                <p1>36</p1>
                <p2>40</p2>
                <p3>42</p3>
                <p4>48</p4>

            </stdkosten40>
            <beginn_halle>{beginn_halle}</beginn_halle>
            <hallenkosten>{hallenkosten}</hallenkosten>
            <rechnungsnummer>{rechnungsnummer}</rechnungsnummer>
        </data>""")

    def test_basic_initialization(self):
        root = self.create_metadata_xml()
        meta = Metadaten(root)

        assert meta.jahr == 2024
        assert meta.von_monat == "Oktober"
        assert meta.bis_monat == "Dezember"
        assert meta.jahr_cur == datetime.date.today().year

        assert meta.stdlohn60 == [48, 52, 54, 56, 60]
        assert meta.stdlohn40 == [36, 40, 42, 48]

        assert meta.stdlohn60n[0] == 48 / (1 + MWST_VOLL)
        assert meta.stdlohn40n[0] == 36 / (1 + MWST_VOLL)

        assert meta.stdhalle == 14
        assert meta.stdhalle_netto == 14 / (1 + MWST_ERM)

    def test_hallensaison_winter_detected(self, capsys):
        root = self.create_metadata_xml(
            von="Oktober", bis="Dezember", beginn_halle="01-10-2024"
        )
        meta = Metadaten(root)

        captured = capsys.readouterr()
        assert "Im Rechnungszeitraum ist Hallensaison" in captured.out
        assert meta.hallensaison is True

    def test_hallensaison_summer_no_halle(self, capsys):
        root = self.create_metadata_xml(
            von="April", bis="Juni", jahr=2024, beginn_halle="01-10-2024"
        )
        meta = Metadaten(root)

        captured = capsys.readouterr()
        assert "Im Rechnungszeitraum ist keine Hallensaison" in captured.out
        assert meta.hallensaison is False

    def test_invalid_beginn_halle_format(self):
        root = self.create_metadata_xml(beginn_halle="invalid-date")
        with pytest.raises(TCSRechnungError) as exc_info:
            Metadaten(root)
        assert "hat ungültiges Format (erwartet: DD-MM-YYYY)" in str(exc_info.value)


class TestErstellePosten:
    def create_training_xml(
        self,
        tag: str = "Montag",
        foerderbetraege: list[int] | None = None,
        foerderkinder: int | None = None,
        teilnehmerzahl: int = 4,
        dauer: int = 60,
        foerderung: str = "nein",
    ) -> ET.Element:
        if foerderung == "ja":
            if foerderbetraege is None:
                foerderbetraege = [224]
            if foerderkinder is None:
                foerderkinder = 1
            foerderbetrag_xml = "".join(
                [
                    f"<foerderbetrag_gruppe>{p}</foerderbetrag_gruppe>"
                    for p in foerderbetraege
                ]
            )
            foerderkinder_xml = f"<foerderkinder>{foerderkinder}</foerderkinder>"
        else:
            foerderbetrag_xml = "<foerderbetrag_gruppe></foerderbetrag_gruppe>"
            foerderkinder_xml = "<foerderkinder></foerderkinder>"

        return ET.fromstring(f"""<training>
            <tag>{tag}</tag>
            <foerderung>{foerderung}</foerderung>
            {foerderbetrag_xml}
            {foerderkinder_xml}
            <teilnehmerzahl>{teilnehmerzahl}</teilnehmerzahl>
            <dauer>{dauer}</dauer>
        </training>""")

    def create_metadata(self) -> Metadaten:
        root = ET.fromstring("""<data>
            <von>Oktober</von>
            <bis>Dezember</bis>
            <jahr>2024</jahr>
            <stdkosten60>
                <p1>48</p1>
                <p2>52</p2>
                <p3>54</p3>
                <p4>56</p4>
                <p5>60</p5>
            </stdkosten60>
            <stdkosten40>
                <p1>36</p1>
                <p2>40</p2>
                <p3>42</p3>
                <p4>48</p4>

            </stdkosten40>
            <beginn_halle>01-10-2024</beginn_halle>
            <hallenkosten>14</hallenkosten>
            <rechnungsnummer>0</rechnungsnummer>
        </data>""")
        return Metadaten(root)

    def test_posten_60min_4teilnehmer_with_foerderung(self):
        meta = self.create_metadata()
        training = self.create_training_xml(
            tag="Montag",
            foerderbetraege=[224],
            foerderkinder=1,
            teilnehmerzahl=4,
            dauer=60,
            foerderung="ja",
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_posten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Montag}{4}{" in result

        assert nettopreise == [0.0]
        assert bruttopreise == [0.0]

    def test_posten_no_foerderung_returns_none(self):
        meta = self.create_metadata()
        training = self.create_training_xml(
            tag="Montag",
            teilnehmerzahl=4,
            dauer=60,
            foerderung="nein",
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_posten(training, meta, nettopreise, bruttopreise)

        assert result is None
        assert nettopreise == []
        assert bruttopreise == []

    def test_posten_40min_with_foerderung(self):
        meta = self.create_metadata()
        training = self.create_training_xml(
            tag="Dienstag",
            foerderbetraege=[126],
            foerderkinder=1,
            teilnehmerzahl=3,
            dauer=40,
            foerderung="ja",
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_posten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Dienstag}{3}{" in result

        assert nettopreise == [0.0]
        assert bruttopreise == [0.0]

    def test_posten_multiple_foerderbetraege(self):
        meta = self.create_metadata()
        training = self.create_training_xml(
            tag="Mittwoch",
            foerderbetraege=[108, 72, 108],
            foerderkinder=2,
            teilnehmerzahl=3,
            dauer=60,
            foerderung="ja",
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_posten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Mittwoch}{5}{" in result

        assert nettopreise == [0.0]
        assert bruttopreise == [0.0]

    def test_posten_invalid_dauer(self):
        meta = self.create_metadata()
        training = self.create_training_xml(
            dauer=90,
            foerderung="ja",
            foerderbetraege=[224],
            foerderkinder=1,
        )

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "Ungültige Trainingsdauer" in str(exc_info.value)

    def test_posten_invalid_foerderung(self):
        meta = self.create_metadata()
        training = self.create_training_xml(foerderung="invalid")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "Ungültiger Eintrag <foerderung>" in str(exc_info.value)

    def test_posten_foerderung_not_multiple_of_stdlohn(self):
        meta = self.create_metadata()
        training = self.create_training_xml(
            foerderbetraege=[100],
            foerderkinder=1,
            teilnehmerzahl=4,
            dauer=60,
            foerderung="ja",
        )

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "ist kein Vielfaches von stdlohn" in str(exc_info.value)

    def test_posten_empty_foerderbetrag_gruppe(self):
        meta = self.create_metadata()
        training = ET.fromstring("""<training>
            <tag>Montag</tag>
            <foerderung>ja</foerderung>
            <foerderbetrag_gruppe></foerderbetrag_gruppe>
            <foerderkinder>1</foerderkinder>
            <teilnehmerzahl>4</teilnehmerzahl>
            <dauer>60</dauer>
        </training>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "ist leer" in str(exc_info.value)

    def test_posten_invalid_foerderbetrag_value(self):
        meta = self.create_metadata()
        training = ET.fromstring("""<training>
            <tag>Montag</tag>
            <foerderung>ja</foerderung>
            <foerderbetrag_gruppe>abc</foerderbetrag_gruppe>
            <foerderkinder>1</foerderkinder>
            <teilnehmerzahl>4</teilnehmerzahl>
            <dauer>60</dauer>
        </training>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "ist keine gültige Zahl" in str(exc_info.value)

    def test_posten_foerderung_nein_with_foerderbetrag_value(self):
        meta = self.create_metadata()
        training = ET.fromstring("""<training>
            <tag>Montag</tag>
            <foerderung>nein</foerderung>
            <foerderbetrag_gruppe>224</foerderbetrag_gruppe>
            <foerderkinder></foerderkinder>
            <teilnehmerzahl>4</teilnehmerzahl>
            <dauer>60</dauer>
        </training>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "<foerderbetrag_gruppe> hat Wert" in str(exc_info.value)
        assert "darf keinen gültigen Wert haben" in str(exc_info.value)

    def test_posten_foerderung_nein_with_foerderkinder_value(self):
        meta = self.create_metadata()
        training = ET.fromstring("""<training>
            <tag>Montag</tag>
            <foerderung>nein</foerderung>
            <foerderbetrag_gruppe></foerderbetrag_gruppe>
            <foerderkinder>2</foerderkinder>
            <teilnehmerzahl>4</teilnehmerzahl>
            <dauer>60</dauer>
        </training>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "<foerderkinder> hat Wert" in str(exc_info.value)
        assert "darf keinen gültigen Wert haben" in str(exc_info.value)

    def test_posten_missing_foerderkinder(self):
        meta = self.create_metadata()
        training = ET.fromstring("""<training>
            <tag>Montag</tag>
            <foerderung>ja</foerderung>
            <foerderbetrag_gruppe>224</foerderbetrag_gruppe>
            <teilnehmerzahl>4</teilnehmerzahl>
            <dauer>60</dauer>
        </training>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "Element <foerderkinder>" in str(exc_info.value)
        assert "fehlt" in str(exc_info.value)


class TestErstelleHallenposten:
    def create_training_xml(
        self,
        tag: str = "Montag",
        teilnehmerzahl: int = 4,
        dauer: int = 60,
        halleneinheiten: int | None = None,
    ) -> ET.Element:
        halleneinheiten_xml = ""
        if halleneinheiten is not None:
            halleneinheiten_xml = (
                f"<halleneinheiten>{halleneinheiten}</halleneinheiten>"
            )
        else:
            halleneinheiten_xml = "<halleneinheiten></halleneinheiten>"

        return ET.fromstring(f"""<training>
            <tag>{tag}</tag>
            <teilnehmerzahl>{teilnehmerzahl}</teilnehmerzahl>
            <dauer>{dauer}</dauer>
            <bezahlt>nein</bezahlt>
            {halleneinheiten_xml}
        </training>""")

    def create_metadata_with_wochentage(
        self, wochentage_cnt: list[int] | None = None
    ) -> Metadaten:
        if wochentage_cnt is None:
            wochentage_cnt = [10, 10, 10, 10, 10, 10, 10]

        root = ET.fromstring("""<data>
            <von>Oktober</von>
            <bis>Dezember</bis>
            <jahr>2024</jahr>
            <stdkosten60>
                <p1>48</p1>
                <p2>52</p2>
                <p3>54</p3>
                <p4>56</p4>
                <p5>60</p5>
            </stdkosten60>
            <stdkosten40>
                <p1>36</p1>
                <p2>40</p2>
                <p3>42</p3>
                <p4>48</p4>

            </stdkosten40>
            <beginn_halle>01-10-2024</beginn_halle>
            <hallenkosten>14</hallenkosten>
            <rechnungsnummer>0</rechnungsnummer>
        </data>""")

        meta = Metadaten(root)
        meta.wochentage_cnt = wochentage_cnt
        return meta

    def test_hallenposten_auto_calculated_units(self):
        meta = self.create_metadata_with_wochentage([10, 10, 10, 10, 10, 10, 10])
        training = self.create_training_xml(tag="Montag", teilnehmerzahl=4, dauer=60)

        nettopreise = []
        bruttopreise = []
        result = erstelle_hallenposten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Montag}{10}{" in result

        expected_netto = round(10 * (14 / (1 + MWST_ERM)) * 60 / (60 * 4), 2)
        expected_brutto = round(10 * 14 * 60 / (60 * 4), 2)

        assert nettopreise == [expected_netto]
        assert bruttopreise == [expected_brutto]

    def test_hallenposten_manual_override(self):
        meta = self.create_metadata_with_wochentage([10, 10, 10, 10, 10, 10, 10])
        training = self.create_training_xml(
            tag="Montag", teilnehmerzahl=4, dauer=60, halleneinheiten=5
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_hallenposten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Montag}{5}{" in result

    def test_hallenposten_40min_duration(self):
        meta = self.create_metadata_with_wochentage([10, 10, 10, 10, 10, 10, 10])
        training = self.create_training_xml(tag="Dienstag", teilnehmerzahl=2, dauer=40)

        nettopreise = []
        bruttopreise = []
        result = erstelle_hallenposten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Dienstag}{10}{" in result
        assert "}{2}{40}{" in result

        expected_netto = round(10 * (14 / (1 + MWST_ERM)) * 40 / (60 * 2), 2)
        assert nettopreise == [expected_netto]

    def test_hallenposten_invalid_weekday(self):
        meta = self.create_metadata_with_wochentage([10, 10, 10, 10, 10, 10, 10])
        training = ET.fromstring("""<training>
            <tag>UnbekannterTag</tag>
            <teilnehmerzahl>4</teilnehmerzahl>
            <dauer>60</dauer>
            <halleneinheiten></halleneinheiten>
        </training>""")

        with pytest.raises(KeyError):
            erstelle_hallenposten(training, meta, [], [])


class TestErstelleRechnung:
    def create_rechnung_xml(
        self, name: str = "Familie Test", kinder_data: list[dict] | None = None
    ) -> ET.Element:
        if kinder_data is None:
            kinder_data = [
                {
                    "name": "Max",
                    "trainings": [
                        {
                            "tag": "Montag",
                            "foerderbetraege": [224],
                            "foerderkinder": 1,
                            "teilnehmerzahl": 4,
                            "dauer": 60,
                            "foerderung": "ja",
                            "halleneinheiten": None,
                        }
                    ],
                }
            ]

        kinder_xml = ""
        for kind in kinder_data:
            trainings_xml = ""
            for training in kind["trainings"]:
                halleneinheiten_xml = ""
                if training.get("halleneinheiten") is not None:
                    halleneinheiten_xml = f"<halleneinheiten>{training['halleneinheiten']}</halleneinheiten>"
                else:
                    halleneinheiten_xml = "<halleneinheiten></halleneinheiten>"

                if training["foerderung"] == "ja":
                    foerderbetrag_xml = "".join(
                        [
                            f"<foerderbetrag_gruppe>{p}</foerderbetrag_gruppe>"
                            for p in training["foerderbetraege"]
                        ]
                    )
                    foerderkinder_xml = (
                        f"<foerderkinder>{training['foerderkinder']}</foerderkinder>"
                    )
                else:
                    foerderbetrag_xml = "<foerderbetrag_gruppe></foerderbetrag_gruppe>"
                    foerderkinder_xml = "<foerderkinder></foerderkinder>"

                trainings_xml += f"""<training>
                    <tag>{training['tag']}</tag>
                    <foerderung>{training['foerderung']}</foerderung>
                    {foerderbetrag_xml}
                    {foerderkinder_xml}
                    <teilnehmerzahl>{training['teilnehmerzahl']}</teilnehmerzahl>
                    <dauer>{training['dauer']}</dauer>
                    {halleneinheiten_xml}
                </training>"""

            kinder_xml += f"""<kind>
                <name>{kind['name']}</name>
                {trainings_xml}
            </kind>"""

        return ET.fromstring(f"""<rechnung>
            <name>{name}</name>
            <strasse>Teststraße 1</strasse>
            <ort>12345 Teststadt</ort>
            <email>test@example.com</email>
            {kinder_xml}
        </rechnung>""")

    def create_metadata(self) -> Metadaten:
        root = ET.fromstring("""<data>
            <von>Oktober</von>
            <bis>Dezember</bis>
            <jahr>2024</jahr>
            <stdkosten60>
                <p1>48</p1>
                <p2>52</p2>
                <p3>54</p3>
                <p4>56</p4>
                <p5>60</p5>
            </stdkosten60>
            <stdkosten40>
                <p1>36</p1>
                <p2>40</p2>
                <p3>42</p3>
                <p4>48</p4>

            </stdkosten40>
            <beginn_halle>01-10-2024</beginn_halle>
            <hallenkosten>14</hallenkosten>
            <rechnungsnummer>0</rechnungsnummer>
        </data>""")
        return Metadaten(root)

    def test_single_kind_single_training(self):
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml()

        result = erstelle_rechnung(rechnung, 1, meta)

        assert "\\Empfaenger{Familie Test}{Teststraße 1}{12345 Teststadt}" in result
        assert "\\Referenz{" in result
        assert "Oktober}{Dezember" in result
        assert "Trainingskosten}" in result
        assert "\\SummeWinter{" in result
        assert "\\Schluss{Oktober}{Dezember" in result

    def test_multiple_kinder(self):
        meta = self.create_metadata()
        kinder_data = [
            {
                "name": "Max",
                "trainings": [
                    {
                        "tag": "Montag",
                        "foerderbetraege": [224],
                        "foerderkinder": 1,
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "ja",
                        "halleneinheiten": None,
                    }
                ],
            },
            {
                "name": "Lisa",
                "trainings": [
                    {
                        "tag": "Dienstag",
                        "foerderbetraege": [224],
                        "foerderkinder": 1,
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "ja",
                        "halleneinheiten": None,
                    }
                ],
            },
        ]
        rechnung = self.create_rechnung_xml(kinder_data=kinder_data)

        result = erstelle_rechnung(rechnung, 1, meta)

        assert "Max, Lisa}" in result or "Max und Lisa}" in result
        assert "Trainingskosten (Max)}" in result
        assert "Trainingskosten (Lisa)}" in result
        assert "Hallenkosten (Max)}" in result
        assert "Hallenkosten (Lisa)}" in result

    def test_no_foerderung_skips_training_costs(self):
        meta = self.create_metadata()
        kinder_data = [
            {
                "name": "Max",
                "trainings": [
                    {
                        "tag": "Montag",
                        "foerderbetraege": [],
                        "foerderkinder": 0,
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "nein",
                        "halleneinheiten": None,
                    },
                    {
                        "tag": "Dienstag",
                        "foerderbetraege": [224],
                        "foerderkinder": 1,
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "ja",
                        "halleneinheiten": None,
                    },
                ],
            }
        ]
        rechnung = self.create_rechnung_xml(kinder_data=kinder_data)

        result = erstelle_rechnung(rechnung, 1, meta)

        parts = result.split("\\Kostentyp{")

        training_section = None
        hall_section = None
        for part in parts:
            if part.startswith("Trainingskosten"):
                training_section = part
            elif part.startswith("Hallenkosten"):
                hall_section = part

        assert training_section is not None, "Training section missing"
        assert (
            "\\Posten{Dienstag}" in training_section
        ), "Dienstag training should appear"
        assert (
            "\\Posten{Montag}" not in training_section
        ), "Montag training should not appear (no foerderung)"

        assert hall_section is not None, "Hall section missing"
        assert "\\Posten{Montag}" in hall_section, "Montag hall costs should appear"
        assert "\\Posten{Dienstag}" in hall_section, "Dienstag hall costs should appear"

    def test_summer_season_summeSommer(self):
        root = ET.fromstring("""<data>
            <von>April</von>
            <bis>Juni</bis>
            <jahr>2024</jahr>
            <stdkosten60>
                <p1>48</p1>
                <p2>52</p2>
                <p3>54</p3>
                <p4>56</p4>
                <p5>60</p5>
            </stdkosten60>
            <stdkosten40>
                <p1>36</p1>
                <p2>40</p2>
                <p3>42</p3>
                <p4>48</p4>
            </stdkosten40>
            <beginn_halle>01-10-2024</beginn_halle>
            <hallenkosten>14</hallenkosten>
            <rechnungsnummer>0</rechnungsnummer>
        </data>""")
        meta = Metadaten(root)
        assert meta.hallensaison is False

        kinder_data = [
            {
                "name": "Max",
                "trainings": [
                    {
                        "tag": "Montag",
                        "foerderbetraege": [224],
                        "foerderkinder": 1,
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "ja",
                        "halleneinheiten": None,
                    }
                ],
            }
        ]
        rechnung = self.create_rechnung_xml(kinder_data=kinder_data)

        result = erstelle_rechnung(rechnung, 1, meta)

        assert "\\SummeSommer{" in result
        assert "\\SummeWinter{" not in result
        assert "Trainingskosten}" in result
        assert "Hallenkosten}" not in result

    def test_missing_rechnung_name(self):
        meta = self.create_metadata()
        rechnung = ET.fromstring("""<rechnung>
            <strasse>Teststraße 1</strasse>
            <ort>12345 Teststadt</ort>
            <email>test@example.com</email>
            <kind>
                <name>Max</name>
            </kind>
        </rechnung>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_rechnung(rechnung, 1, meta)
        assert "Element <name>" in str(exc_info.value)
        assert "fehlt" in str(exc_info.value)

    def test_missing_rechnung_strasse(self):
        meta = self.create_metadata()
        rechnung = ET.fromstring("""<rechnung>
            <name>Familie Test</name>
            <ort>12345 Teststadt</ort>
            <email>test@example.com</email>
            <kind>
                <name>Max</name>
            </kind>
        </rechnung>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_rechnung(rechnung, 1, meta)
        assert "Element <strasse>" in str(exc_info.value)
        assert "fehlt" in str(exc_info.value)

    def test_missing_kind_name(self):
        meta = self.create_metadata()
        rechnung = ET.fromstring("""<rechnung>
            <name>Familie Test</name>
            <strasse>Teststraße 1</strasse>
            <ort>12345 Teststadt</ort>
            <email>test@example.com</email>
            <kind>
                <training>
                    <tag>Montag</tag>
                    <foerderung>ja</foerderung>
                    <foerderbetrag_gruppe>224</foerderbetrag_gruppe>
                    <foerderkinder>1</foerderkinder>
                    <teilnehmerzahl>4</teilnehmerzahl>
                    <dauer>60</dauer>
                </training>
            </kind>
        </rechnung>""")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_rechnung(rechnung, 1, meta)
        assert "Element <name>" in str(exc_info.value)


class TestErstelleMail:
    def create_rechnung_xml(
        self,
        name: str = "Familie Test",
        email: str = "test@example.com",
        kinder: list[str] | None = None,
    ) -> ET.Element:
        if kinder is None:
            kinder = ["Max"]

        kinder_xml = "".join([f"<kind><name>{k}</name></kind>" for k in kinder])

        return ET.fromstring(f"""<rechnung>
            <name>{name}</name>
            <email>{email}</email>
            {kinder_xml}
        </rechnung>""")

    def create_metadata(self) -> Metadaten:
        root = ET.fromstring("""<data>
            <von>Oktober</von>
            <bis>Dezember</bis>
            <jahr>2024</jahr>
            <stdkosten60>
                <p1>48</p1>
                <p2>52</p2>
                <p3>54</p3>
                <p4>56</p4>
                <p5>60</p5>
            </stdkosten60>
            <stdkosten40>
                <p1>36</p1>
                <p2>40</p2>
                <p3>42</p3>
                <p4>48</p4>

            </stdkosten40>
            <beginn_halle>01-10-2024</beginn_halle>
            <hallenkosten>14</hallenkosten>
            <rechnungsnummer>0</rechnungsnummer>
        </data>""")
        return Metadaten(root)

    def test_mail_familie(self):
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Familie Müller", kinder=["Max"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0001.tex")

        assert (
            result
            == "Liebe Familie"
            " Müller;test@example.com;Max;Oktober;Dezember;2024;24_0001.pdf\n"
        )

    def test_mail_frau(self):
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Frau Schmidt", kinder=["Lisa"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0002.tex")

        assert (
            result
            == "Liebe Frau"
            " Schmidt;test@example.com;Lisa;Oktober;Dezember;2024;24_0002.pdf\n"
        )

    def test_mail_herr(self):
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Herr Meyer", kinder=["Tom"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0003.tex")

        assert (
            result
            == "Lieber Herr"
            " Meyer;test@example.com;Tom;Oktober;Dezember;2024;24_0003.pdf\n"
        )

    def test_mail_other(self):
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Dr. Test", kinder=["Anna"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0004.tex")

        assert (
            result
            == "Liebe/r Dr."
            " Test;test@example.com;Anna;Oktober;Dezember;2024;24_0004.pdf\n"
        )

    def test_mail_multiple_kinder(self):
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(
            name="Familie Test", kinder=["Max", "Lisa", "Tom"]
        )

        result = erstelle_mail(rechnung, meta, "/path/to/24_0005.tex")

        assert (
            result
            == "Liebe Familie Test;test@example.com;Max, Lisa und"
            " Tom;Oktober;Dezember;2024;24_0005.pdf\n"
        )

    def test_mail_two_kinder(self):
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Familie Test", kinder=["Max", "Lisa"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0006.tex")

        assert (
            result
            == "Liebe Familie Test;test@example.com;Max und"
            " Lisa;Oktober;Dezember;2024;24_0006.pdf\n"
        )


class TestIntegration:
    def test_actual_rechnungen_xml(self):
        xml_path = Path(__file__).parent / "rechnungen.xml"

        if not xml_path.exists():
            pytest.skip("rechnungen.xml not found")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        meta = Metadaten(root)

        rechnungsnummer = 0
        for rechnung in root.findall("rechnung"):
            rechnungsnummer += 1
            result = erstelle_rechnung(rechnung, rechnungsnummer, meta)

            assert "\\Empfaenger{" in result
            assert "\\Referenz{" in result
            assert "\\Schluss{" in result
            assert result.endswith("}\n\n")


class TestMailHeader:
    def test_mail_header(self):
        result = get_mail_header()
        assert result == "Anrede;Email;Kinder;Von_Monat;Bis_Monat;Jahr;Anhang\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
