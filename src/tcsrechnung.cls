%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% tcsrechnung.cls - Rechnungen des TC Stetten                            %
%                                                                        %
% This program is free software: you can redistribute it and/or modify   %
% it under the terms of the GNU General Public License as published by   %
% the Free Software Foundation, either version 3 of the License, or      %
% (at your option) any later version.                                    %
%                                                                        %
% This program is distributed in the hope that it will be useful,        %
% but WITHOUT ANY WARRANTY; without even the implied warranty of         %
% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          %
% GNU General Public License for more details.                           %
%                                                                        %
% You should have received a copy of the GNU General Public License      %
% along with this program.  If not, see <http://www.gnu.org/licenses/>.  %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


% Briefklasse des Koma-Projektes als Ausgangsklasse
\LoadClass[
  foldmarks=true,                 % Markierungen zum Falten
  fromalign=left,                 % Absender im Briefkopf linksbündig
  fromlogo,                       % Setze Logo im Header
  fromrule=afteraddress,          % Linie unter Header
  enlargefirstpage=on,            % Erste Seite darf vergrößert werden
  version=last                    % Neueste Komaversion ohne Kompatibilität
]{scrlttr2}

% Verwendet den Standard LaTeX2e
\NeedsTeXFormat{LaTeX2e}

% Name dieser Klasse tcsrechnung
\ProvidesClass{tcsrechnung}

% Zeichensatz UTF8
\usepackage[utf8]{inputenc}

% T1 Schriften
\usepackage[T1]{fontenc}

% Silbentrennung nach neuer deutscher Rechtschreibung
\usepackage[ngerman]{babel}
% Füge Worttrennung für unbekannte Worte hinzu
\hyphenation{Bank-ver-bin-dung-en}

% lmodern Schrifttyp
\usepackage{lmodern}

% Mehr Kontrolle über Kopf- und Fußzeilen 
\usepackage{scrlayer-scrpage}

% Verbesserter Blocksatz
\usepackage{microtype}

% Grafikmanipulation (für das Logo)
\usepackage{graphicx}

% Eurosymbol
\usepackage{eurosym}

% Zeilenabstand in Tabellen vergrößern (Standard 1)
\renewcommand{\arraystretch}{1.25}

% Keine Einrückung bei neuen Absätzen
\setlength{\parindent}{0pt}
% Dafür größerer Abstand zwischen den Absätzen
\setlength{\parskip}{5pt}

% Definiere Umgebung, die keine Seitenumbrüche erlaubt
\newlength{\currentparindent}
\newlength{\currentparskip}
\newenvironment{samepage2}
  {\setlength{\currentparskip}{\parskip}
   \setlength{\currentparindent}{\parindent}
   \begin{minipage}{\textwidth}
   \setlength{\parskip}{\currentparskip}
   \setlength{\parindent}{\currentparindent}
  }
  {\end{minipage}}

% Nutze scrpage2 Fuß- und Kopfzeilen
\pagestyle{scrheadings}

% Absendername in riesigen fetten Buchstaben
\addtokomafont{fromname}{\bfseries\Huge}
\setkomavar{fromname}{Tennisclub Stetten/F. e.\,V.}

% Absenderadresse
\setkomavar{fromaddress}{Gräbleswiesenweg 50, 70771 Leinfelden-Echterdingen}

% Logo auf 3cm Breite geschrumpft
\setkomavar{fromlogo}{\includegraphics[width=3cm]{tcslogo}}

% Bankverbindung als Tabelle formatiert
\setkomavar{frombank}{%
  \begin{tabular}[t]{@{}l@{ }l@{ }l@{}}%
    Voba Filder, & IBAN DE38611616960260788007, & BIC GENODES1NHB\\
    Ksk Esslingen, & IBAN DE69611500200010781704, & BIC ESSLDE66XXX
  \end{tabular}%
}

% Steuerliche Daten als Tabelle formatiert
\newkomavar{fromtaxes}
\setkomavar{fromtaxes}{%
  \begin{tabular}[t]{@{}r@{ }r@{}}%
    USt.Id.Nr.: & DE147806294\\
    St.Nr.: & 99018/07643%
  \end{tabular}%
}

% Fußzeile auf erster Seite
\setkomavar{firstfoot}{%
  \parbox[t]{\textwidth}{%
    \normalfont\footnotesize
    \usekomavar{frombank}%
    \hfill
    \usekomavar{fromtaxes}%
  }%
}

% Fußzeilen ab der zweiten Zeile enthalten zusätzlich die Seitenzahl
% Bankdaten sind (ungefähr) auf derselben Höhe wie auf der ersten Seite
\setkomafont{pagefoot}{\normalfont\footnotesize}
\setkomafont{pagenumber}{\normalsize}

\setheadwidth{\useplength{firstheadwidth}}
\chead{}
\ihead{\usekomavar{fromname}\\\usekomavar{fromaddress}}
\ohead{\includegraphics[width=9mm]{tcslogo}}

\setfootwidth{\useplength{firstfootwidth}}
\cfoot{}
\ifoot{\\[28.4mm]\usekomavar{frombank}}
\ofoot{\\[28.4mm]\usekomavar{fromtaxes}}

% Rücksendeadresse
\setkomavar{backaddress}{Donald Duck\\
                         Blumenweg 13\\
                         123456 Entenhausen}

% Kontakt
\setkomavar{location}{\raggedleft%
  \sffamily\scriptsize
  \textbf{Kontakt}\\
  Donald Duck\\
  Tel.: 0123\,4567890\\
  Mobil: 0987\,6543210\\
  donald@duck.de%
}

% Ort und Datum
\setkomavar{date}{\today}
\setkomavar{place}{Stetten}

% Definiert Empfänger der Rechnung
% \Empfaenger{Name}{Straße}{Ort}
\newcommand{\Empfaenger}[3]{
  \begin{letter}{#1\\#2\\#3}
}

% Erzeugt Referenzzeile, Betreff und Tabelle bis zum ersten Rechnungsposten
% \Referenz{Rechnungsnr}{erster Monat}{letzter Monat}{Namen der Kinder}
\newcommand{\Referenz}[4]{
  \setkomavar{invoice}{#1}
  \setkomavar{subject}{Training #2 bis #3\\#4}
  \opening{}
  \begin{center}
    \begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} lrrrrrrr }
      \hline
      \scriptsize{Tag} & \scriptsize{Einheiten}  & \scriptsize{Preis/Std}
      & \scriptsize{Gruppe} & \scriptsize{Dauer} & \scriptsize{Preis}
      & \scriptsize{Förderung} & \scriptsize{Gesamt} \\
      \hline
}

% Schreibt den Kostentyp in die Tabelle
% \Kostentyp{Diese und jene Kosten}
\newcommand{\Kostentyp}[1]{
  \multicolumn{8}{@{\extracolsep{\fill}} c}{\textbf{#1}} \\
}

% Erzeugt einen Rechnungsposten (eine Zeile) in der Tabelle
% Die Einheiten (Eurozeichen, min) dürfen nicht angegeben werden
% \Posten{Tag}{Einheiten}{Preis/Std}{Gruppe}{Dauer}{Preis}{Förderung}{Gesamt}
\newcommand{\Posten}[8]{
  #1 & #2 & \EUR{#3} & #4 & #5\,min & \EUR{#6} & \EUR{#7} & \EUR{#8}\\
}

% Schreibt die Rechnungssummen in die Tabelle
% Im Winter mit 7% MwSt, im Sommer ohne
% \SummeWinter{Summe netto}{MwSt 19%}{MwSt 7%}{Summe brutto}
\newcommand{\SummeWinter}[4]{
      \hline\hline
      \multicolumn{7}{@{\extracolsep{\fill}} l}{Summe ohne MwSt.} & \EUR{#1} \\
      \hline
      \multicolumn{7}{@{\extracolsep{\fill}} l}{MwSt. 19\%} & \EUR{#2} \\
      \multicolumn{7}{@{\extracolsep{\fill}} l}{MwSt. 7\%} & \EUR{#3} \\
      \hline\hline
      \multicolumn{7}{@{\extracolsep{\fill}} l}%
        {\textbf{Gesamtsumme inkl. MwSt.}} & \textbf{\EUR{#4}}
      \\
      \hline
    \end{tabular*}
  \end{center}
}
% \SummeSommer{Summe netto}{MwSt 19%}{Summe brutto}
\newcommand{\SummeSommer}[3]{
      \hline\hline
      \multicolumn{7}{@{\extracolsep{\fill}} l}{Summe ohne MwSt.} & \EUR{#1} \\
      \hline
      \multicolumn{7}{@{\extracolsep{\fill}} l}{MwSt. 19\%} & \EUR{#2} \\
      \hline\hline
      \multicolumn{7}{@{\extracolsep{\fill}} l}%
        {\textbf{Gesamtsumme inkl. MwSt.}} & \textbf{\EUR{#3}}
      \\
      \hline
    \end{tabular*}
  \end{center}
}

% Schreibt den Text unterhalb der Tabelle
% \Schluss{erster Monat}{letzter Monat}{kommende Saison}
\newcommand{\Schluss}[3]{
    \begin{samepage2}
      Fördergelder des Vereins TC Stetten im Jugend- und Aktivenbereich, welche
      in der Zeit von #1 bis #2 geleistet wurden, sind vollständig zurück zu
      erstatten, falls der/die Spieler/in den Verein zur Saison #3 verlassen
      sollte.
      
      \textbf{Mit der Bezahlung der Rechnung werden diese Bedingungen
      anerkannt.}

      Bitte überweisen Sie den Rechnungsbetrag auf eine unserer unten
      angeführten Bankverbindungen. Vielen Dank!
    \end{samepage2}
  \end{letter}
}
