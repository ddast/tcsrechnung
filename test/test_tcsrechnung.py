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
    """Tests for XML helper functions."""

    def test_get_elem_success(self):
        """Test _get_elem with existing element."""
        parent = ET.fromstring("<root><child>text</child></root>")
        elem = _get_elem(parent, "child")
        assert elem.text == "text"

    def test_get_elem_missing(self):
        """Test _get_elem raises error for missing element."""
        parent = ET.fromstring("<root></root>")
        with pytest.raises(TCSRechnungError) as exc_info:
            _get_elem(parent, "missing")
        assert "Element <missing> in Block <root> fehlt" in str(exc_info.value)

    def test_get_text_success(self):
        """Test _get_text with valid text."""
        parent = ET.fromstring("<root><name>Test</name></root>")
        assert _get_text(parent, "name") == "Test"

    def test_get_text_empty(self):
        """Test _get_text raises error for empty element."""
        parent = ET.fromstring("<root><name></name></root>")
        with pytest.raises(TCSRechnungError) as exc_info:
            _get_text(parent, "name")
        assert "fehlt oder ist leer" in str(exc_info.value)

    def test_get_int_success(self):
        """Test _get_int with valid integer."""
        parent = ET.fromstring("<root><count>42</count></root>")
        assert _get_int(parent, "count") == 42

    def test_get_int_invalid(self):
        """Test _get_int raises error for non-integer."""
        parent = ET.fromstring("<root><count>abc</count></root>")
        with pytest.raises(TCSRechnungError) as exc_info:
            _get_int(parent, "count")
        assert "ist keine gültige Zahl" in str(exc_info.value)

    def test_get_all_elems_success(self):
        """Test _get_all_elems returns all matching elements."""
        parent = ET.fromstring("<root><item>1</item><item>2</item></root>")
        elems = _get_all_elems(parent, "item")
        assert len(elems) == 2
        assert elems[0].text == "1"
        assert elems[1].text == "2"

    def test_get_all_elems_empty(self):
        """Test _get_all_elems returns empty list for no matches."""
        parent = ET.fromstring("<root></root>")
        elems = _get_all_elems(parent, "item")
        assert elems == []


class TestMetadaten:
    """Tests for Metadaten class."""

    def create_metadata_xml(
        self,
        jahr=2024,
        von="Oktober",
        bis="Dezember",
        beginn_halle="01-10-2024",
        hallenkosten=14,
        rechnungsnummer=0,
    ):
        """Create a sample XML root for Metadaten testing."""
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
        """Test basic Metadaten initialization."""
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
        """Test hallensaison detection for winter period."""
        # Billing period overlaps with hall season (Oct-Dec)
        root = self.create_metadata_xml(
            von="Oktober", bis="Dezember", beginn_halle="01-10-2024"
        )
        meta = Metadaten(root)

        captured = capsys.readouterr()
        assert "Im Rechnungszeitraum ist Hallensaison" in captured.out
        assert meta.hallensaison is True

    def test_hallensaison_summer_no_halle(self, capsys):
        """Test hallensaison detection for summer period."""
        # Billing period in summer (Apr-Jun), no overlap with hall season
        root = self.create_metadata_xml(
            von="April", bis="Juni", jahr=2024, beginn_halle="01-10-2024"
        )
        meta = Metadaten(root)

        captured = capsys.readouterr()
        assert "Im Rechnungszeitraum ist keine Hallensaison" in captured.out
        assert meta.hallensaison is False

    def test_invalid_beginn_halle_format(self):
        """Test error handling for invalid date format."""
        root = self.create_metadata_xml(beginn_halle="invalid-date")
        with pytest.raises(TCSRechnungError) as exc_info:
            Metadaten(root)
        assert "hat ungültiges Format (erwartet: DD-MM-YYYY)" in str(exc_info.value)


class TestErstellePosten:
    """Tests for erstelle_posten function (training items)."""

    def create_training_xml(
        self,
        tag="Montag",
        preise=None,
        teilnehmerzahl=4,
        dauer=60,
        foerderung="nein",
        bezahlt="nein",
    ):
        """Create a sample training XML element."""
        if preise is None:
            preise = [224]

        preis_xml = "".join([f"<preis>{p}</preis>" for p in preise])
        return ET.fromstring(f"""<training>
            <tag>{tag}</tag>
            {preis_xml}
            <teilnehmerzahl>{teilnehmerzahl}</teilnehmerzahl>
            <dauer>{dauer}</dauer>
            <foerderung>{foerderung}</foerderung>
            <bezahlt>{bezahlt}</bezahlt>
        </training>""")

    def create_metadata(self):
        """Create a sample Metadaten object for testing."""
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

    def test_posten_60min_4teilnehmer_no_foerderung(self):
        """Test training posten: 60min, 4 participants, no förderung."""
        meta = self.create_metadata()
        training = self.create_training_xml(
            tag="Montag",
            preise=[224],  # 4 hours * 56 (p4 rate for 60min)
            teilnehmerzahl=4,
            dauer=60,
            foerderung="nein",
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_posten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Montag}{4}{" in result
        assert "}{4}{60}{" in result

        # gesamtpreis = 224, teilnehmerzahl = 4
        # gesamtpreis_netto = 224 / (4 * 1.19) = 47.058823...
        # zahlbetrag = gesamtpreis_netto (no förderung)
        # zahlbetrag_brutto = 224 / 4 = 56
        expected_netto = round(224 / (4 * (1 + MWST_VOLL)), 2)
        expected_brutto = round(224 / 4, 2)

        assert nettopreise == [expected_netto]
        assert bruttopreise == [expected_brutto]

    def test_posten_40min_3teilnehmer_with_foerderung(self):
        """Test training posten: 40min, 3 participants, with förderung."""
        meta = self.create_metadata()
        training = self.create_training_xml(
            tag="Dienstag",
            preise=[126],  # 3 hours * 42 (p3 rate for 40min)
            teilnehmerzahl=3,
            dauer=40,
            foerderung="ja",
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_posten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Dienstag}{3}{" in result
        assert "}{3}{40}{" in result

        # With förderung: zahlbetrag = 0, foerderung = gesamtpreis_netto
        assert nettopreise == [0.0]
        assert bruttopreise == [0.0]

    def test_posten_multiple_preise(self):
        """Test training posten with multiple price entries."""
        meta = self.create_metadata()
        # Total = 312 = 6 * 52 (p2 rate for 60min with 2 participants)
        training = self.create_training_xml(
            tag="Mittwoch",
            preise=[100, 200, 12],  # Total = 312
            teilnehmerzahl=2,
            dauer=60,
            foerderung="nein",
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_posten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Mittwoch}{6}{" in result  # 312 / 52 = 6 units
        expected_netto = round(312 / (2 * (1 + MWST_VOLL)), 2)
        expected_brutto = round(312 / 2, 2)
        assert nettopreise == [expected_netto]
        assert bruttopreise == [expected_brutto]

    def test_posten_invalid_dauer(self):
        """Test error handling for invalid training duration."""
        meta = self.create_metadata()
        training = self.create_training_xml(dauer=90)

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "Ungültige Trainingsdauer" in str(exc_info.value)

    def test_posten_invalid_foerderung(self):
        """Test error handling for invalid foerderung value."""
        meta = self.create_metadata()
        training = self.create_training_xml(foerderung="invalid")

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "Ungültiger Eintrag <foerderung>" in str(exc_info.value)

    def test_posten_price_not_multiple(self):
        """Test error when price is not multiple of stdlohn."""
        meta = self.create_metadata()
        training = self.create_training_xml(
            preise=[100],  # 100 is not divisible by 56 (p4 rate for 60min)
            teilnehmerzahl=4,
            dauer=60,
        )

        with pytest.raises(TCSRechnungError) as exc_info:
            erstelle_posten(training, meta, [], [])
        assert "ist kein Vielfaches von stdlohn" in str(exc_info.value)


class TestErstelleHallenposten:
    """Tests for erstelle_hallenposten function (hall items)."""

    def create_training_xml(
        self,
        tag="Montag",
        teilnehmerzahl=4,
        dauer=60,
        halleneinheiten=None,
    ):
        """Create a sample training XML element for hall testing."""
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

    def create_metadata_with_wochentage(self, wochentage_cnt=None):
        """Create a sample Metadaten object with specific weekday counts."""
        if wochentage_cnt is None:
            wochentage_cnt = [10, 10, 10, 10, 10, 10, 10]  # 10 weeks for each day

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
        """Test hall posten with auto-calculated units."""
        # Monday (index 0) has 10 units
        meta = self.create_metadata_with_wochentage([10, 10, 10, 10, 10, 10, 10])
        training = self.create_training_xml(tag="Montag", teilnehmerzahl=4, dauer=60)

        nettopreise = []
        bruttopreise = []
        result = erstelle_hallenposten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Montag}{10}{" in result

        # einheiten = 10, stdhalle_netto = 14/1.07, dauer = 60, teilnehmerzahl = 4
        # gesamtpreis_netto = 10 * (14/1.07) * 60 / (60 * 4) = 10 * 13.0841 / 4 = 32.71
        expected_netto = round(10 * (14 / (1 + MWST_ERM)) * 60 / (60 * 4), 2)
        expected_brutto = round(10 * 14 * 60 / (60 * 4), 2)

        assert nettopreise == [expected_netto]
        assert bruttopreise == [expected_brutto]

    def test_hallenposten_manual_override(self):
        """Test hall posten with manual halleneinheiten override."""
        meta = self.create_metadata_with_wochentage([10, 10, 10, 10, 10, 10, 10])
        training = self.create_training_xml(
            tag="Montag", teilnehmerzahl=4, dauer=60, halleneinheiten=5
        )

        nettopreise = []
        bruttopreise = []
        result = erstelle_hallenposten(training, meta, nettopreise, bruttopreise)

        # Should use manual value 5, not auto-calculated 10
        assert "\\Posten{Montag}{5}{" in result

    def test_hallenposten_40min_duration(self):
        """Test hall posten with 40-minute duration."""
        meta = self.create_metadata_with_wochentage([10, 10, 10, 10, 10, 10, 10])
        training = self.create_training_xml(tag="Dienstag", teilnehmerzahl=2, dauer=40)

        nettopreise = []
        bruttopreise = []
        result = erstelle_hallenposten(training, meta, nettopreise, bruttopreise)

        assert "\\Posten{Dienstag}{10}{" in result
        assert "}{2}{40}{" in result

        # 10 * (14/1.07) * 40 / (60 * 2) = 43.61
        expected_netto = round(10 * (14 / (1 + MWST_ERM)) * 40 / (60 * 2), 2)
        assert nettopreise == [expected_netto]


class TestErstelleRechnung:
    """Tests for erstelle_rechnung function."""

    def create_rechnung_xml(self, name="Familie Test", kinder_data=None):
        """Create a sample rechnung XML element."""
        if kinder_data is None:
            kinder_data = [
                {
                    "name": "Max",
                    "trainings": [
                        {
                            "tag": "Montag",
                            "preise": [224],
                            "teilnehmerzahl": 4,
                            "dauer": 60,
                            "foerderung": "nein",
                            "bezahlt": "nein",
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

                preise_xml = "".join(
                    [f"<preis>{p}</preis>" for p in training["preise"]]
                )
                trainings_xml += f"""<training>
                    <tag>{training['tag']}</tag>
                    {preise_xml}
                    <teilnehmerzahl>{training['teilnehmerzahl']}</teilnehmerzahl>
                    <dauer>{training['dauer']}</dauer>
                    <foerderung>{training['foerderung']}</foerderung>
                    <bezahlt>{training['bezahlt']}</bezahlt>
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

    def create_metadata(self):
        """Create a sample Metadaten object."""
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
        """Test rechnung with single child and single training."""
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
        """Test rechnung with multiple children."""
        meta = self.create_metadata()
        kinder_data = [
            {
                "name": "Max",
                "trainings": [
                    {
                        "tag": "Montag",
                        "preise": [224],
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "nein",
                        "bezahlt": "nein",
                        "halleneinheiten": None,
                    }
                ],
            },
            {
                "name": "Lisa",
                "trainings": [
                    {
                        "tag": "Dienstag",
                        "preise": [224],
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "nein",
                        "bezahlt": "nein",
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

    def test_bezahlt_skips_training(self):
        """Test that bezahlt='ja' skips the training in output."""
        meta = self.create_metadata()
        kinder_data = [
            {
                "name": "Max",
                "trainings": [
                    {
                        "tag": "Montag",
                        "preise": [224],
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "nein",
                        "bezahlt": "ja",
                        "halleneinheiten": None,
                    },
                    {
                        "tag": "Dienstag",
                        "preise": [224],
                        "teilnehmerzahl": 4,
                        "dauer": 60,
                        "foerderung": "nein",
                        "bezahlt": "nein",
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
        ), "Montag training should be skipped"

        assert hall_section is not None, "Hall section missing"
        assert "\\Posten{Montag}" in hall_section, "Montag hall costs should appear"
        assert "\\Posten{Dienstag}" in hall_section, "Dienstag hall costs should appear"


class TestErstelleMail:
    """Tests for erstelle_mail function."""

    def create_rechnung_xml(
        self, name="Familie Test", email="test@example.com", kinder=None
    ):
        """Create a sample rechnung XML element."""
        if kinder is None:
            kinder = ["Max"]

        kinder_xml = "".join([f"<kind><name>{k}</name></kind>" for k in kinder])

        return ET.fromstring(f"""<rechnung>
            <name>{name}</name>
            <email>{email}</email>
            {kinder_xml}
        </rechnung>""")

    def create_metadata(self):
        """Create a sample Metadaten object."""
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
        """Test mail generation for 'Familie' salutation."""
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Familie Müller", kinder=["Max"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0001.tex")

        assert (
            result
            == "Liebe Familie"
            " Müller;test@example.com;Max;Oktober;Dezember;2024;24_0001.pdf\n"
        )

    def test_mail_frau(self):
        """Test mail generation for 'Frau' salutation."""
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Frau Schmidt", kinder=["Lisa"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0002.tex")

        assert (
            result
            == "Liebe Frau"
            " Schmidt;test@example.com;Lisa;Oktober;Dezember;2024;24_0002.pdf\n"
        )

    def test_mail_herr(self):
        """Test mail generation for 'Herr' salutation."""
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Herr Meyer", kinder=["Tom"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0003.tex")

        assert (
            result
            == "Lieber Herr"
            " Meyer;test@example.com;Tom;Oktober;Dezember;2024;24_0003.pdf\n"
        )

    def test_mail_other(self):
        """Test mail generation for other salutations."""
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Dr. Test", kinder=["Anna"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0004.tex")

        assert (
            result
            == "Liebe/r Dr."
            " Test;test@example.com;Anna;Oktober;Dezember;2024;24_0004.pdf\n"
        )

    def test_mail_multiple_kinder(self):
        """Test mail generation with multiple children."""
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
        """Test mail generation with exactly two children."""
        meta = self.create_metadata()
        rechnung = self.create_rechnung_xml(name="Familie Test", kinder=["Max", "Lisa"])

        result = erstelle_mail(rechnung, meta, "/path/to/24_0006.tex")

        assert (
            result
            == "Liebe Familie Test;test@example.com;Max und"
            " Lisa;Oktober;Dezember;2024;24_0006.pdf\n"
        )


class TestIntegration:
    """Integration tests using actual XML files."""

    def test_actual_rechnungen_xml(self):
        """Test processing of the actual rechnungen.xml file."""
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
    """Tests for get_mail_header function."""

    def test_mail_header(self):
        """Test mail header format."""
        result = get_mail_header()
        assert result == "Anrede;Email;Kinder;Von_Monat;Bis_Monat;Jahr;Anhang\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
