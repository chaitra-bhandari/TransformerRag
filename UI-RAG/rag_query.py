import json
import os
import pickle
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import faiss
import numpy as np
from openai import AzureOpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder


#Configuration - .env
OPENAI_KEY = os.getenv("OPENAI_KEY", "")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

#Regular search weights
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6

#Deep dive search weights, for the null value re-check
DEEP_DIVE_BM25_WEIGHT = 0.3
DEEP_DIVE_VECTOR_WEIGHT = 0.7

RETRIEVAL_K = 20
RERANK_TOP_K = 10

#Set of 6 questions are sent to each gpt calls
BATCH_SIZE = 6

#Deep Dive triggered automatically for any null value after first pass
DEEP_DIVE_RETRIEVAL_K = 25
DEEP_DIVE_RERANK_TOP_K = 15

#Azure blob setup
client = AzureOpenAI(
    api_key=OPENAI_KEY, api_version="2024-02-15-preview", azure_endpoint=OPENAI_ENDPOINT
)

from azure.storage.blob import BlobServiceClient

blob_client = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
)
index_container = blob_client.get_container_client(
    os.getenv("BLOB_INDEX_CONTAINER", "faiss-indexes")
)
metadata_container = blob_client.get_container_client(
    os.getenv("BLOB_METADATA_CONTAINER", "faiss-metadata")
)

#Document language detection while filling the document( end product) in the same language either german or english
def detect_document_language(db, project_name: str) -> str:
    if not hasattr(db, "metadata") or not db.metadata:
        return "en"

    sample_chunks = db.metadata[: min(10, len(db.metadata))]

    german_indicators = [
        "Nennspannung", "Nennfrequenz", "Ausrüstung", "Kühlungsart",
        "Stufenschalter", "Schaltgruppe", "Impedanz", "Durchführung",
        "Korrosionsschutz", "Prüföl", "Kessel", "Armaturen",
        "Schaltstoßspannung", "Blitzstoßspannung", "Kurzschlussstrom",
        "Wicklung", "Leistung", "MVA", "Transformator",
        "Das ist", "die", "der", "und", "oder", "für", "mit", "von", "des", "dem"
    ]

    english_indicators = [
        "rated voltage", "frequency Hz", "cooling", "tap changer",
        "vector group", "impedance", "bushing", "corrosion",
        "test oil", "tank", "valves", "applied voltage",
        "short circuit", "winding", "power", "MVA", "transformer",
        "This is", "the", "and", "or", "for", "with", "of", "the", "is"
    ]

    german_count = 0
    english_count = 0

    for chunk in sample_chunks:
        content = chunk.get("content", "").lower() if isinstance(chunk, dict) else str(chunk).lower()

        for indicator in german_indicators:
            if indicator.lower() in content:
                german_count += 1

        for indicator in english_indicators:
            if indicator.lower() in content:
                english_count += 1

    if german_count > english_count:
        return "de"
    return "en"

#List of questions should be answered by the gpt in JSON format, to fill the documents (German)
def build_parameter_registry(p: str, language: str = "en") -> dict:
    """
    Build parameter registry with language-specific questions.
    language: "en" (English) or "de" (German)
    Returns: Dictionary with parameters and appropriate language questions
    """

    if language == "de":
        return {
            "frequency": {
    "question": "Welche Nennfrequenz (Hz) order BEMESSUNGSFREQUENZ ist für Projekt {p} angegeben?",
    "aliases": ["Nennfrequenz", "frequency", "Frequenz Hz", "50Hz", "60Hz", "BEMESSUNGSFREQUENZ", "fn"]
  },

  "network_conditions": {
    "question": "Welche Nennspannung oder Bemessungsspannung ist für Projekt {p} angegeben?",
    "aliases": ["Nennspannung", "rated voltage", "Um", "Ur", "Un", "kV", "Umax", "Bemessungsspannung"]
  },

  "load_losses": {
    "question": "Welche Lastverluste, Leerlaufverluste und Kurzschlussverluste sind für Projekt {p} angegeben? Bitte alle Verlustwerte in kW angeben.",
    "aliases": ["Lastverluste", "Leerlaufverluste", "Kurzschlussverluste", "Kupferverluste", "Pk", "Verluste", "kW"]
  },

  "vector_group": {
    "question": "Welche Schaltgruppe ist für Projekt {p} angegeben?",
    "aliases": ["Schaltgruppe", "Vektorgruppe", "Dy", "Yd", "YNyn","YN", "Wicklungsschaltung"]
  },

  "impedance": {
    "question": "Welche Impedanzwerte sind für Projekt {p} angegeben, einschließlich Spannungsvarianten (HV-LV, HV-TV, LV-TV) und Angaben in Prozent (%)?",
    "aliases": ["Impedanz", "Kurzschlussspannung", "uk", "uz", "HV-LV", "HV-TV", "LV-TV", "Uk%"]
  },

  "over_excitation": {
    "question": "Welche Übererregungswerte sind für Projekt {p} angegeben (Dauerübererregung in %, Kurzzeitübererregung in % und Sekunden)?",
    "aliases": ["Übererregung", "Dauerübererregung", "Kurzzeitübererregung", "Überlastbarkeit Spannung"]
  },

  "rated power / cooling": {
    "question": "Welche Kühlungsarten und zugehörigen Bemessungsleistung  (in MVA/Mvar) für HV/OS, LV/US und TV/TS sind für Projekt {p} angegeben?",
    "aliases": ["cooling", "ONAN", "ONAF", "OFAF", "ODAF", "Kühlungsart", "cooling type", "rated power cooling", "HV", "OS", "LV", "US", "TV", "TS", "Bemessungsleistung"]
  },

  "tank_design": {
    "question": "Welche Kesselspezifikationen sind für Projekt {p} angegeben (Bauart, Deckel, verschweißt/verschraubt, Druckprüfung, Aufstellung, Ausrüstung, Leitern, Absturzsicherung, Armaturen, Rohrleitungen, Dichtungen, Verschraubungen, Lastschalterkammer, Ausdehner)?",
    "aliases": ["Kessel", "Kesselart", "Deckel", "Druckprüfung", "Armaturen", "Ausdehner"]
  },

  "tap_changer": {
    "question": "Welche Spezifikationen zum Stufenschalter (OLTC) sind für Projekt {p} angegeben (Typ Laststufenschalter oder Umschalter im spannungslosen Zustand, Hersteller, Fabrikat/Modell, Stellbereich, Anzahl der Stufen, Stufenspannung, Neutral- oder Mittelstellung)?",
    "aliases": ["Stufenschalter", "OLTC", "Laststufenschalter", "Stellbereich"]
  },

  "oil": {
    "question": "Welche Spezifikationen zum Transformatorenöl sind für Projekt {p} angegeben (Öltyp, Mineralöl, synthetisches Öl, Prüföl, Norm)?",
    "aliases": ["Transformatorenöl", "Öl", "Mineralöl", "Isolieröl", "Prüföl"]
  },

  "corrosion_protection": {
    "question": "Welche Spezifikationen zum Korrosionsschutz sind für Projekt {p} angegeben (Korrosivitätsklasse C2/C3/C4/C5i/C5m, Schutzart, Schutzdauer, Farbe, RAL-Code, Beschichtungs- oder Lackiersystem gemäß ISO 12944)?",
    "aliases": ["Korrosionsschutz", "C2", "C3", "C4", "C5", "ISO 12944", "RAL"]
  },

  "bushings": {
    "question": "Welche Spezifikationen zu den Durchführungen für die verschiedenen Transformatoranschlüsse (HV, HV-N, MV, MV-N, LV) sind für Projekt {p} angegeben (Typ, Anzahl, Hersteller, Spezifikation, Bemessungsspannung kV, Strom A, AC-Trockenprüfung kV, BIL kV, minimale Kriechstrecke mm)?",
    "aliases": ["Durchführung", "HV Durchführung", "LV Durchführung", "Kriechstrecke"]
  },

  "current_transformer": {
    "question": "Welche Stromwandler-Typen oder -Spezifikationen sind für Projekt {p} angegeben?",
    "aliases": ["Stromwandler", "CT", "Messwandler", "Schutzwandler"]
  },

  "Protection degree for cubicles, terminal boxes, fans, pumps and monitoring equipment": {
    "question": "Welche Schutzgrad ist für Projekt {p} für Schaltschränke, Klemmenkästen, Lüfter, Pumpen und Überwachungsgeräte angegeben?",
    "aliases": ["IP Schutzart", "Schaltschrank", "Klemmenkasten", "Lüfter", "Pumpen"]
  },

  "scope_delivery": {
    "question": "Welche Lieferumfänge einschließlich Stückzahlen sind für Projekt {p} angegeben?",
    "aliases": ["Lieferumfang", "Leistungsumfang"]
  },

  "spare_parts": {
    "question": "Welche Angaben zu Ersatzteilen sind für Projekt {p} enthalten (empfohlene Ersatzteile, Inbetriebnahme-Ersatzteile, 2-/5-Jahres-Ersatzteile, Verschleißteile, Verbrauchsmaterialien, Ersatzteilpaket)?",
    "aliases": ["Ersatzteile", "Verschleißteile", "Verbrauchsmaterial"]
  },

  "standards": {
    "question": "Extrahieren Sie aus Projekt {p} alle anwendbaren Normen exakt wie im Dokument angegeben. Berücksichtigen Sie vollständige Listen, eigene Abschnitte (z. B. 'Normen', 'Applicable Standards') sowie im Text verteilte Normverweise.",
    "aliases": ["Normen", "Applicable Standards", "IEC", "EN", "DIN", "ISO"]
  },

  "type_tests": {
    "question": "Extrahieren Sie aus Projekt {p} alle aufgeführten Typprüfungen exakt wie im Dokument angegeben. Berücksichtigen Sie vollständige Listen, eigene Abschnitte (z. B. 'Typprüfungen', 'Type Tests') sowie im Text verteilte Prüfverweise. Falls keine Typprüfungen genannt sind, geben Sie null zurück.",
    "aliases": ["Typprüfungen", "Temperaturanstiegsprüfung", "Stoßspannungsprüfung"]
  },

  "routine_tests": {
    "question": "Extrahieren Sie aus Projekt {p} alle aufgeführten Stückprüfungen exakt wie im Dokument angegeben. Berücksichtigen Sie vollständige Listen, eigene Abschnitte (z. B. 'Stückprüfungen', 'Routine Tests') sowie im Text verteilte Prüfverweise",
    "aliases": ["Stückprüfung", "Routineprüfung"]
  },

  "protecion & monitoring equipment": {
    "question": "Welche Schutz- und Überwachungseinrichtungen sind für Projekt {p} angegeben (Zeigerthermometer, Widerstandsthermometer, Buchholzrelais, Schutzrelais OLTC, Druckentlastungsventil, Silikagel-Trockner, Ölstandsanzeiger, Membranüberwachung, Anzahl, Typ, Kontakte NC/NO/Wechsler)?",
    "aliases": ["Buchholz", "Thermometer", "Druckentlastung", "Ölstand", "Silikagel"]
  },

  "customer_documentation": {
    "question": "Welche Kundendokumentation ist für Projekt {p} zu liefern (digitale Version, Einzel-PDF, Indexierung, Lesezeichen)?",
    "aliases": ["Kundendokumentation", "Handbücher", "PDF", "Lesezeichen"]
  },

  "transport": {
    "question": "Welche Transportangaben sind für Projekt {p} enthalten (INCOTERMS, Versicherungsverantwortung, Versandtermine, Vertragsstrafentermine, Ersatzteile, Verpackung, Trocknungssystem, Taupunkt)?",
    "aliases": ["Transport", "INCOTERMS", "Versicherung", "Taupunkt"]
  },

  "secondary_wiring": {
    "question": "Welche Angaben zur Sekundärverdrahtung bzw. zum Einspeisenetz sind für Projekt {p} enthalten (Versorgungsspannung, Frequenz, Anschlussart, Einspeisekonzept, Netzumschaltung)?",
    "aliases": ["Sekundärverdrahtung", "Einspeisenetz", "Netzumschaltung"]
  },

  "external_wiring": {
    "question": "Welche Spezifikationen zur Außenverdrahtung oder Kabelführung sind für Projekt {p} angegeben (Leitungsart, Kabelkanal, Kabeltyp, Querschnitte mm², Kabelverschraubung, Schirmanbindung, Trennstellen)?",
    "aliases": ["Außenverdrahtung", "Kabelführung", "Kabeltyp", "Querschnitt"]
  },

  "temperature_rise": {
    "question": "Welche Übertemperaturwerte für Öl, Wicklung und Hotspot sind für Projekt {p} angegeben (in K oder °C)?",
    "aliases": ["Übertemperatur", "Wicklungstemperatur", "Öltemperatur"]
  },

  "noise": {
    "question": "Welche garantierten Geräuschwerte sind für Projekt {p} angegeben (dB(A)/LWA für Leerlauf, maximale Kühlstufe und Volllast mit Kühlanlage)?",
    "aliases": ["Geräusch", "Schallpegel", "LWA", "dB(A)"]
  },

  "project_description": {
    "question": "Wie lautet die Projektbeschreibung für Projekt {p} (Leistungsumfang/Projektübersicht)?",
    "aliases": ["Projektbeschreibung", "Leistungsumfang", "Projektübersicht"]
  },

  "transformation_ratio": {
    "question": "Welches Übersetzungsverhältnis sowie welche Stufenstellungen und zugehörigen Spannungen (HV, LV, TV) in kV sind für Projekt {p} angegeben?",
    "aliases": ["Übersetzungsverhältnis", "Stufenspannung", "Spannung OS", "Spannung US"]
  },

  "harmonics": {
    "question": "Welche prozentualen Werte der 3., 5. und 7. Oberwelle des Leerlaufstroms sind für Projekt {p} angegeben?",
    "aliases": ["Oberwellen", "3. Oberwelle", "5. Oberwelle", "7. Oberwelle"]
  },

  "motor": {
    "question": "Welche elektrischen Motorspezifikationen sind für Projekt {p} angegeben (Versorgungsspannung Motor, Einspeisung Steuerstromkreis, Kundeneinführungsplatte, Überwachung)?",
    "aliases": ["Versorgungsspannung Motor", "Steuerstromkreis", "Kundeneinführungsplatte", "Überwachung"]
  },
  "cooling_system": {
    "question": "Extrahieren Sie aus Projekt {p} alle Spezifikationen zur Kühlanlage exakt wie im Dokument angegeben. Berücksichtigen Sie Kühlungsart, Anzahl der Kühler, Kühlleistung bzw. Kühlkapazität, Lieferant/Hersteller, Materialstärke der Radiatoren, Geräuschpegel/Schallleistungspegel (z. B. dB(A), LWA) sowie spezifische RAL-Anforderungen für Armaturen oder Ventile ",
    "aliases": [
      "cooling system",
      "Kühlanlage",
      "radiators",
      "Kühlungsart",
      "Anzahl der Kühler",
      "Leistung",
      "Materialstärke",
      "noise",
      "Schallleistungspegel",
      "RAL7033"
    ]
  },

  "labels": {
    "question": "Extrahieren Sie aus Projekt {p} alle Angaben zur Beschriftung exakt wie im Dokument angegeben. Berücksichtigen Sie Material (z. B. GFK, Edelstahl A2/A4), Umfang (Minimal- oder Vollausführung), Typ (BKT-Nummernschilder, Klartext, Nummernschilder), Ausführung und Anbringungsort",
    "aliases": [
      "labeling",
      "Beschriftung",
      "Kennzeichnung",
      "Typenschild",
      "BKT Nummernschilder",
      "GFK Schild"
    ]
  },

  "special_accessories": {
    "question": "Extrahieren Sie aus Projekt {p} alle Angaben zum Sonderzubehör exakt wie im Dokument angegeben. Berücksichtigen Sie Verantwortlichkeit (Beistellung durch PN oder Kunde), Einbauort bzw. zugeordnete Seite (HV/OS, LV/US), Ausführungstyp (Freiluft, SF6, Steckanschluss), Hersteller (z. B. Siemens 3EL3), Montageart (mit angebauter Konsole, getrennt, KaK) sowie weitere technische Details.",
    "aliases": [
      "Sonderzubehör",
      "special accessories",
      "Beistellung",
      "Freiluft",
      "SF6",
      "Steckanschluss",
      "Siemens 3EL3",
      "KaK"
    ]
  },

  "liquidated_damages": {
    "question": "Extrahieren Sie aus Projekt {p} alle Angaben zu Vertragsstrafen exakt wie im Dokument angegeben. Berücksichtigen Sie Vertragsstrafen für Leistung, Lieferverzug, Verlust, Nichterfüllung, Geräuschüberschreitung oder andere vertraglich definierte Kriterien. Beachten Sie vollständige Listen, Tabellen oder eigene Abschnitte (z. B. 'Vertragsstrafen', 'Liquidated Damages'). Falls keine Angaben vorhanden sind, geben Sie null zurück",
    "aliases": [
      "liquidated damages",
      "Vertragsstrafen",
      "Pönale",
      "delay penalty",
      "performance penalty",
      "noise penalty"
    ]
  },

  "Location": {
    "question": "Extrahieren Sie aus Projekt {p} alle Standortbedingungen exakt wie im Dokument angegeben. Berücksichtigen Sie maximale und minimale Umgebungstemperatur, Normalbereich, Luftfeuchtigkeit, maximale Windgeschwindigkeit sowie Verschmutzungsgrad bzw. Pollution Level. Beachten Sie vollständige Listen, Tabellen oder eigene Abschnitte (z. B. 'Standortbedingungen', 'Site Conditions') sowie im Text verteilte Angaben",
    "aliases": [
      "site conditions",
      "Standortbedingungen",
      "Umgebungstemperatur",
      "Verschmutzungsgrad"
    ]
  },
  "insulation_levels":{
  "question": "Welche Isolationspegel sind für jede Wicklung (HV/OS, HV-N/OS-N, LV/US, LV-N/US-N, TV/TS) für Projekt {p} angegeben, einschließlich Bemessungsspannung Um, BIL/Blitzstoßspannung, BILc, SIL/Schaltstoßspannung, angelegte Wechselspannung 1 min (AC 1min), LTAC, IVPD U1/U2, DCPR, angelegte Gleichspannung (DC applied) sowie TEmax in kVpeak/kVeff/kVDC/pC?",
            "aliases": ["Isolationspegel", "insulation level", "BIL", "Blitzstoßspannung", "SIL", "Schaltstoßspannung", "BILc", "LTAC", "IVPD", "DCPR", "TEmax", "kVpeak", "pC", "Um", "angelegte Wechselspannung"]
  },
  "short_circuit_withstand": {
    "question": f"Wie hoch sind die Kurzschlussstrom-Festigkeitswerte für jede Wicklung (HV/OS, LV/US, TV/TS/tertiärseitig), einschließlich symmetrischem kArms, Dauer in Sekunden und Spitzenwert kApk für Projekt {p}?",
    "aliases": ["Kurzschluss", "Kurzschlussstrom", "kArms", "kApk", "Kurzschlussfestigkeit", "Fehlerstrom", "Ik"],
}
        
        }
    else:
        #List of questions should be answered by the gpt in JSON format, to fill the documents (English)
        return {
            "frequency": {
                "question": f"What is the rated frequency or frequency mentioned for project {p}?",
                "aliases": ["rated frequency", "Nennfrequenz", "frequency Hz", "50Hz", "60Hz", "fn"],
            },
            "network_conditions": {
                "question": f"What is the nominal voltage or system volage mentioned for project {p}?",
                "aliases": ["nominal voltage", "Nennspannung", "rated voltage", "Um", "Ur", "Un", "kV", "Umax"],
            },
            "load_losses": {
                "question": f"What are the load losses, no load losses, short circuit losses mentioned for project {p}, lists losses and it's values in kW?",
                "aliases": ["load losses", "Lastverlusten", "copper losses", "Pk", "kW losses", "Verluste", "no load losses", "short circuit losses"],
            },
            "vector_group": {
                "question": f"What is the vector group for project {p}?",
                "aliases": ["vector group", "Schaltgruppe", "Dy", "Yd", "YNyn", "winding connection", "Vektorgruppe"],
            },
            "impedance": {
                "question": f"What are the impedance values, including aliases like 'impedanz', voltage variations (HV-LV, HV-TV, LV-TV), and percentage (%) units for project {p}?",
                "aliases": ["impedance", "impedanz", "Kurzschlussspannung", "uk", "uz", "HV-LV", "HV-TV", "LV-TV", "% impedance", "Uk%"],
            },
            "induction / over-excitation": {
                "question": f"What are the over-excitation / Überflutung values (continuous/Dauerüberflutung in %, short-time/Kurzzeitüberflutung in % and seconds) for project {p}?",
                "aliases": ["over-excitation", "Überflutung", "Dauerüberflutung", "Kurzzeitüberflutung", "overvoltage capability"],
            },
            "rated power / cooling": {
                "question": f"What are the different cooling types (might be more than one) and the rated power across HV, LV, TV across different cooling types mentioned for {p}, list all the values in MVA?",
                "aliases": ["cooling", "ONAN", "ONAF", "OFAF", "ODAF", "Kühlungsart", "cooling type", "rated power cooling", "HV", "OS", "LV", "US", "TV", "TS"],
            },
            "tank_design": {
                "question": f"What are the tank / Kessel specifications (type, cover, Deckel, verschweißt/verschraubt, Druckprüfung, Aufstellung, Ausrüstung, ladders/Leitern, Absturzsicherung, valves/Armaturen, piping/Rohrleitungen, Dichtungen, Verschraubungen, Lastschalterkammer, Ausdehner) for project {p}?",
                "aliases": ["tank", "Kessel", "Kesselart", "Deckel", "verschweißt", "Druckprüfung", "Armaturen", "Ausdehner", "conservator"],
            },
            "tap_changer": {
                "question": f"What are the tap changer / OLTC / Stufenschalter specifications (type on-load/off-circuit, make, model, manufacturer/Hersteller, tap range, number of taps/positions, tap step voltage, neutral/mid position) for project {p}?",
                "aliases": ["tap changer", "OLTC", "Stufenschalter", "load tap changer", "on-load tap", "tap position", "tap range"],
            },
            "oil": {
                "question": f"What are the transformer oil / Öl specifications (oil type, mineral oil, synthetic oil, test oil/Prüföl, standard) for project {p}?",
                "aliases": ["transformer oil", "Öl", "mineral oil", "insulating oil", "Prüföl", "oil type"],
            },
            "corrosion_protection": {
                "question": f"What are the corrosion protection / Korrosionsschutz specifications (corrosion class C2/C3/C4/C5i/C5m, protection level, duration, colour, RAL code, coating system, paint system, ISO 12944) for project {p}?",
                "aliases": ["corrosion protection", "Korrosionsschutz", "coating", "RAL", "C2", "C3", "C4", "C5", "ISO 12944", "paint"],
            },
            "bushings": {
                "question": f"What are the bushings across various transformer terminals (HV, HV_N, MV, MV_N, LV)? Include: type, quantity, manufacturer, specification, ratedVoltage_kV, current_A, acDry_kV, bil_kV, min_creepage_mm for project {p}.",
                "aliases": ["bushing", "Durchführung", "HV bushing", "LV bushing", "creepage", "acDry", "bushing current"],
            },
            "current_transformer": {
                "question": f"What are the current transformer type, specification or across different terminals(HV, HV_N, MV, MV_N, LV) mentioned for project {p}, example:  HV phase current transformer and neutral point: 1200/1 A; 10 VA, 5PR60, 150%, MV phase current transformer and neutral point: 1800/1A; 10 VA, 5PR60, 150%, Current transformer in MV 2V for the thermal image: 1795/2 A; 30 VA, LV phase current transformer: 2500/1 A, 10 VA, 5PR60, 150%'?",
                "aliases": ["current transformer", "CT", "Stromwandler", "measuring CT", "protection CT", "CT ratio", "CT class"],
            },
            "Protection degree for cubicles, terminal boxes, fans, pumps and monitoring equipment": {
                "question": f"What is the protection dergree (Schutzart) for project {p} including cubicles, terminal boxes, fans, pumps, and monitoring devices? Please specify the IP ratings for each category?",
                "aliases": ["IP rating", "cubicles", "terminal boxes", "fans", "pumps"],
            },
            "scope_delivery": {
                "question": f"What are the items/units to be delivered including number of quantities of transformers for project {p}, example: -	4x Variable Shunt Reactor 70-140 MVAr/400kV, 3x single phase air-insulated surge arresters including steel supports at the tank/ tank cover per unit ?",
                "aliases": ["scope of delivery", "Leistungsumfang", "delivery scope"],
            },
            "spare_parts": {
                "question": f"What are the spare parts / Ersatzteile details (recommended spare parts, commissioning spares, 2-year/5-year spares, wear parts, consumables, spare part package) for project {p}?",
                "aliases": ["spare parts", "Ersatzteile", "wear parts", "consumables", "spare part package"],
            },
            "standards": {
                "question": f"What are the applicable standards for project {p}, list them as a complet set or section?",
                "aliases": ["standards", "Normen", "IEC", "EN", "DIN", "applicable standards"],
            },
            "type_tests": {
                "question": f"What are lists of tests mentioned for the project {p} lists them as complete section or lists",
                "aliases": ["type test", "temperature rise test", "zero-sequence reactance", "impulse test", "noise test"],
            },
            "Routine_tests": {
                "question": f"What are lists of routine tests mentioned for {p} lists them as complete section or lists",
                "aliases": ["routine test", "IEC 60076-6", "lightning impulse", "applied voltage test", "induced voltage test"],
            },
            "protecion & monitoring equipment": {
                "question": f"What are the protection and monitoring equipment details (dial thermometer, resistance thermometer, Buchholz relay, protective relay OLTC, pressure relief valve, silica gel breather, oil level indicator, rubber bag monitoring, quantity, type, contacts NC/NO/changeover) for project {p}?",
                "aliases": ["Buchholz", "thermometer", "pressure relief", "oil level", "silica gel", "breather", "NC contact", "NO contact"],
            },
            "customer_documentation": {
                "question": f"For project {p}, what specific documents or manuals must be delivered? Include requirements for the digital version (e.g., single PDF, indexing, and bookmarking/Lesezeichen).",
                "aliases": ["documentation", "Kundendokumentation", "manuals", "PDF-file", "indexed", "bookmarks"],
            },
            "transport": {
                "question": f"What are the transportation details for project {p}? Extract INCOTERMS, insurance responsibility (Customer/Siemens), shipping dates (Planned/Requested), penalized dates, spare parts, packaging, dry air system requirements, and dew point.",
                "aliases": ["transportation", "INCOTERMS", "insurance", "shipping date", "Dry Air System", "Dew Point", "packaging"],
            },
            "cooling_system": {
                "question": f"What are the cooling system specifications for project {p}? Include cooling type (Kühlungsart), number of coolers, cooling power/capacity, supplier, radiator material thickness (Materialstärke), noise/sound level, and any specific RAL requirements for valves.",
                "aliases": ["cooling system", "Kühlanlage", "radiators", "Kühlungsart", "Materialstärke", "noise", "RAL7033"],
            },
            "labels": {
                "question": f"What are the labeling / Beschriftung options (material GRP/stainless steel A2/A4, scope minimum/complete, type BKT Nummernschilder/plain text/number plates) for project {p}?",
                "aliases": ["labeling", "Beschriftung", "nameplate", "BKT Nummernschilder", "GRP label"],
            },
            "special_accessories": {
                "question": f"What are the special accessories / Sonderzubehör details (responsibility, Beistellung PN/Kunde, installation location HV/LV OS/US, type Freiluft/SF6/Steckanschluss, manufacturer Siemens 3EL3, mounting Mit angebauter Konsole/getrennt/KaK) for project {p}?",
                "aliases": ["Sonderzubehör", "special accessories", "Beistellung", "Freiluft", "SF6", "Steckanschluss", "3EL3"],
            },
            "liquidated_damages": {
                "question": f"What are the liquidated damages / Vertragsstrafen (performance, delay, loss, noise penalties) for project {p}?",
                "aliases": ["liquidated damages", "Vertragsstrafen", "penalties", "delay penalty", "performance penalty", "noise penalty"],
            },
            "Location": {
                "question": f"What are the temperature (max/min), humidity, wind speed, and pollution level for the transformer location mentioned for {p}?",
                "aliases": ["site conditions", "temperature", "humidity", "wind speed", "pollution level", "ambient temperature"],
            },
            
            "secondary_wiring": {
                "question": f"What are the secondary wiring / Einspeisenetz supply voltage, frequency (V, Hz, 3AC/N), supply connection type (plug-in, main switch, NH load break switch, circuit breaker), supply configuration (single/double/Einfache/Doppeleinspeisung, manual/automatic Netzumschaltung) for project {p}?",
                "aliases": ["Einspeisenetz", "supply voltage", "3AC", "NH switch", "Doppeleinspeisung", "Netzumschaltung"],
            },
            "external_wiring": {
                "question": f"What are the external wiring / Außenverdrahtung / Kabelführung specifications (wiring type, cable duct, conduits TWN/UL, cable type/Kabeltyp, cross-sections/Querschnitte mm², cable gland/Verschraubung material brass/stainless steel, cable identification, shield termination/Kabelschirme, isolating points/Trennstellen) for project {p}?",
                "aliases": ["Außenverdrahtung", "Kabelführung", "cable duct", "cable gland", "Kabelschirme", "Querschnitte", "Trennstellen"],
            },
            "temperature_rise": {
                "question": f"For project {p}, what are the temperature rise (Übertemperaturen) values at different load levels for oil, winding, and hotspot measurement locations? Please provide the values in K or °C.",
                "aliases": ["Übertemperaturen", "temperature rise", "temp rise", "heating", "winding temperature", "oil temperature", "hotspot temperature"],
            },
            "noise": {
                "question": f"For project {{p}}, what are the guaranteed noise levels (Geräusche) for the transformer and cooling system? Please provide values in dB(A) / LWA for the following conditions: no load at rated voltage, cooler at maximum cooling stage, and full load (100% Irated) with cooling system. Indicate the maximum allowed values.",
                "aliases": ["noise", "Geräusche", "sound level", "sound power level", "LWA", "dB(A)", "guaranteed noise"],
            },
            "project_description": {
                "question": f"What is the project description for project {p}, which might be referred to as scope, project overview for example: This Technical Specification applies for 650/650/150 MVA three-phase oil immersed power transformers, with the 400 kV + 16 % / 230 kV / 30 kV ratio and was prepared for use in projects managed by TenneT TSO GmbH. It defines technical requirements for design, construction, and operation of the transformer.",

                "aliases": ["project description", "scope", "project overview", "Projektbeschreibung"],
            },
            "transformation_ratio": {
                "question": f"What is the transformation ratio (Übersetzungsverhältnis), tap numbers and tap-dependent HV, LV, and TV voltages values for project {p}, list all of them in kV?",
                "aliases": ["Übersetzungsverhältnis", "ratio", "tap changer voltage table", "Stellung Tap", "HV voltage", "Spannung OS", "LV voltage", "Spannung US", "TV voltage", "Spannung TS", "tap position voltages"],
            },
            "Harmonics": {
                "question": f"Extract the percentage values of the 3rd, 5th, and 7th harmonics of the no-load current for project {p} list them in %.",
                "aliases": ["Oberwelleneinfluss", "harmonic content of the no load current", "Leerlaufstrom", "3. Oberwelle", "5. Oberwelle", "7. Oberwelle", "3rd harmonic %", "5th harmonic %", "7th harmonic %"],
            },
            "Motor": {
                "question": f"From project {p}, extract motor electrical specifications: (1) Motor power supply (Versorgungsspannung Motor), (2) Control circuit power supply (Einspeisung Steuerstromkreis), (3) Customer specific cable entry (Kundeneinführungsplatte), and (4) Monitoring details (Monitoring / Überwachung).",
                "aliases": ["Versorgungsspannung Motor", "Power supply motor", "Motorversorgung", "Motor supply voltage", "Einspeisung Steuerstromkreis", "Power supply control circuit", "Kundeneinführungsplatte", "Monitoring", "Überwachung"],
            },
            "insulation_levels": {
            "question": f"What are the insulation levels / Isolationspegel for each winding (HV/OS, HV-N/OS-N, LV/US, LV-N/US-N, TV/TS) including rated voltage Um, BIL/Blitzstoßspannung, BILc, SIL/Schaltstoßspannung, applied AC 1min, LTAC, IVPD U1/U2, DCPR, DC applied, TEmax in kVpeak/kVeff/kVDC/pC for project {p}?",
            "aliases":  ["insulation level", "Isolationspegel", "BIL", "Blitzstoßspannung", "SIL", "Schaltstoßspannung", "BILc", "LTAC", "IVPD", "DCPR", "TEmax", "kVpeak", "pC", "Um", "applied AC"],
            },
            "short_circuit_withstand": {
            "question": f"What are the short circuit withstand / Kurzschlussstrom values for each winding (HV/OS, LV/US, TV/TS/tertiärseitig) including symmetric kArms, duration seconds, and peak kApk for project {p}?",
            "aliases":  ["short circuit", "Kurzschlussstrom", "kArms", "kApk", "withstand current", "fault current", "Ik"],
        },
        }


class HybridVectorDB:
    def __init__(self, index_file="docs.index", meta_file="docs.pkl"):
        self.index_file = index_file
        self.meta_file = meta_file
        self.index = None
        self.metadata = []
        self.bm25 = None
        self.tokenized = []

    @staticmethod
    def _tokenize(text: str) -> list:
        return re.findall(r"[a-zA-Z0-9]+(?:[.\-/_][a-zA-Z0-9]+)*", text.lower())
    
    #Loading faiss index and metadata from blob(stored in blob)
    def load(self):
        
        try:
            # Download FAISS index from blob
            index_blob = index_container.get_blob_client(self.index_file)
            index_data = index_blob.download_blob().readall()

            # Write temporarily to disk (FAISS requires file path)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".index") as tmp:
                tmp.write(index_data)
                tmp_path = tmp.name

            # Load from temporary file
            self.index = faiss.read_index(tmp_path)

            # Clean up temp file
            import os as os_module
            os_module.remove(tmp_path)

        except Exception as e:
            # Silent error handling
            return False

        try:
            # Download metadata from blob
            metadata_blob = metadata_container.get_blob_client(self.meta_file)
            metadata_data = metadata_blob.download_blob().readall()

            # Load pickle from bytes
            import io
            self.metadata = pickle.load(io.BytesIO(metadata_data))

        except Exception as e:
            # Silent error handling
            return False

        # Build BM25 index
        tokenized_corpus = [self._tokenize(c.get("content", "")) for c in self.metadata]
        self.bm25 = BM25Okapi(tokenized_corpus)

        return True
    
    #Extract project_name from chunk metadata
    def _get_project_name(self, chunk: dict) -> str:
        if isinstance(chunk, dict) and "metadata" in chunk:
            return chunk["metadata"].get("project_name", "").strip().lower()
        return chunk.get("project_name", "").strip().lower()
    
    
    #Filter chunks and BM25 index for a specific project"
    def prepare_project(self, project_name: str):
        indices = []
        for i, chunk in enumerate(self.metadata):
            if self._get_project_name(chunk) == project_name.strip().lower():
                indices.append(i)

        if not indices:
            return [], None

        #Build project-specific BM25
        project_chunks = [self.metadata[i] for i in indices]
        project_tokenized = [self._tokenize(c.get("content", "")) for c in project_chunks]
        project_bm25 = BM25Okapi(project_tokenized)

        return indices, project_bm25
    
    #Search for chunks filtered by project_name and  Returns top k chunks for the specific project.
    def search(self, question: str, aliases: list, project_name: str, k=10, q_vec=None):
        indices, project_bm25 = self.prepare_project(project_name)

        if not indices:
            return []

        #Get embedding for question if not provided
        if q_vec is None:
            try:
                res = client.embeddings.create(input=[question], model=EMBEDDING_MODEL)
                q_vec = np.array(res.data[0].embedding, dtype=np.float32)
            except:
                return []

        #Vector search
        q_vec_norm = q_vec / (np.linalg.norm(q_vec) + 1e-10)
        D, I = self.index.search(q_vec_norm.reshape(1, -1), min(k * 3, len(indices)))

        #Filter to project indices
        valid_indices = []
        for idx in I[0]:
            if idx < len(self.metadata) and idx in indices:
                valid_indices.append(idx)

        #BM25 search
        keywords = aliases if aliases else [question]
        bm25_scores = project_bm25.get_scores(keywords)
        bm25_indices = sorted(
            enumerate(bm25_scores), key=lambda x: x[1], reverse=True
        )[:k]

        #Combine results
        combined = {}
        for rank, (idx, score) in enumerate([(i, bm25_scores[i]) for i, _ in bm25_indices if i in indices]):
            combined[idx] = combined.get(idx, 0) + (k - rank) * VECTOR_WEIGHT

        for rank, idx in enumerate(valid_indices[:k]):
            combined[idx] = combined.get(idx, 0) + (k - rank) * BM25_WEIGHT

        #Sort and return
        sorted_indices = sorted(combined.keys(), key=lambda x: combined[x], reverse=True)[:k]
        return [
            {
                "chunk_id": i,
                "content": self.metadata[i].get("content", ""),
                "metadata": self.metadata[i].get("metadata", {}),
            }
            for i in sorted_indices
        ]

    # Search using keywords for a specific project
    def search_with_keywords(self, keywords: list, project_name: str, k=10):
        indices, project_bm25 = self.prepare_project(project_name)

        if not indices:
            return []

        bm25_scores = project_bm25.get_scores(keywords)
        sorted_indices = sorted(
            enumerate(bm25_scores), key=lambda x: x[1], reverse=True
        )[:k]

        return [
            {
                "chunk_id": indices[idx] if idx < len(indices) else idx,
                "content": self.metadata[indices[idx]].get("content", "") if idx < len(indices) else "",
                "metadata": self.metadata[indices[idx]].get("metadata", {}) if idx < len(indices) else {},
            }
            for idx, _ in sorted_indices
        ]


class CrossEncoderReranker:
    #cross-encoder/mmarco-mMiniLMv2-L12-H384
    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384"):
        try:
            self.model = CrossEncoder(model_name)
        except:
            self.model = None
     
    #Rerank candidates using crossencode
    def rerank(self, question: str, candidates: list, top_k: int = 10) -> list:
        if not self.model or not candidates:
            return candidates[:top_k]

        try:
            pairs = [[question, c.get("content", "")] for c in candidates]
            scores = self.model.predict(pairs)
            ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
            return [c for c, _ in ranked[:top_k]]
        except:
            return candidates[:top_k]

#Normalize GPT response to ensure correct structure
def normalize_gpt_response(result: dict, param_name: str) -> dict:
    if param_name not in result:
        return {"value": None, "source_document": "none", "page": "none"}

    param_result = result[param_name]

    if isinstance(param_result, dict) and all(k in param_result for k in ["value", "source_document", "page"]):
        return param_result

    if isinstance(param_result, dict):
        value = param_result.get("value")
        source_doc = param_result.get("source_document", "none")
        page = param_result.get("page", "none")

        if value is None:
            source_doc = "none"
            page = "none"

        return {
            "value": value,
            "source_document": source_doc,
            "page": page
        }

    return {"value": None, "source_document": "none", "page": "none"}

#Call GPT for a batch of parameters
def call_gpt_for_cluster(cluster_name: str, cluster_params: dict,
                          parameter_contexts: dict, parameter_sources: dict, project: str) -> dict:
  
    context_block = ""
    for param in cluster_params:
        context_block += f"\n\n### CONTEXT FOR [{param}]:\n{parameter_contexts[param]}"

    template = {param: {"value": None, "source_document": None, "page": None} for param in cluster_params}
    questions = "\n".join([
        f'  "{p}": <answer to: {cluster_params[p]["question"]}>'
        for p in cluster_params
    ])

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a technical extraction assistant for power transformer design documents. "
                    "RETURN ONLY VALID JSON. NO OTHER TEXT.\n\n"
                    "CRITICAL INSTRUCTIONS:\n"
                   
                    "1. Each parameter MUST have exactly THREE fields: 'value', 'source_document', and 'page'\n"
                    "8. Extract the answer to each question from its labelled context only and try to keep the answer as much as asked in each question. "
                    "2. 'source_document' = the EXACT document name from [Source: ...] tags (e.g., 'Appendix 1A - Insurance exhibit (CAR)_di_result')\n"
                    "3. 'page' = the EXACT page number from [Source: ...] tags as an INTEGER (e.g., 3 or 18)\n"
                    "4. If value NOT found: value=null, source_document='none', page='none'\n"
                    "5. If value IS found: here value might be multiple field answers list them like parameter wise, long answers also the source_document and page must NEVER be 'none'\n"
                    "6. Do NOT create 'reference' field. Do NOT create any other fields.\n"
                    "7. Never make up information. Extract exactly what you see.\n\n"
                    "EXAMPLES OF CORRECT OUTPUT:\n"
                    '  {"bushings": {"value": "Type A specification", "source_document": "Appendix 1A - Insurance exhibit (CAR)_di_result", "page": 3}}\n'
                    '  {"cooling_types": {"value": "ONAN", "source_document": "Technical Specification Sheet", "page": 15}}\n\n'
                    "WRONG OUTPUT EXAMPLES (DO NOT DO THIS):\n"
                    '  {"bushings": "Type A specification"}  ← MISSING source_document and page\n'
                    '  {"bushings": {"value": "Type A", "reference": "Page 3"}}  ← WRONG: has reference instead of source_document and page\n'
                    
                )
            },
            {
                "role": "user",
                "content": (
                    f"Here are {len(cluster_params)} parameters to extract.\n\n"
                    f"{context_block}\n\n"
                    f"Return this JSON structure:\n{json.dumps(template, indent=2)}\n\n"
                    f"Questions:\n{questions}"
                )
            }
        ]
    )

    try:
        result = json.loads(response.choices[0].message.content)
        normalized = {}
        for param in result:
            normalized[param] = normalize_gpt_response(result, param)
        return normalized
    except:
        return {param: {"value": None, "source_document": "none", "page": "none"} for param in cluster_params}

#Search again for null parameter
def deep_dive_single(param: str, meta: dict, db: HybridVectorDB,
                     reranker: CrossEncoderReranker, project: str):
    """Single parameter deep dive re-extraction"""
    keywords = meta.get("aliases", [])
    if not keywords:
        return param, {"value": None, "source_document": "none", "page": "none"}

    candidates = db.search_with_keywords(
        keywords=keywords,
        project_name=project,
        k=DEEP_DIVE_RETRIEVAL_K
    )

    top_chunks = reranker.rerank(meta["question"], candidates, top_k=DEEP_DIVE_RERANK_TOP_K)

    context_parts = []
    for chunk in top_chunks:
        source_doc = chunk.get("metadata", {}).get("source_document", "unknown")
        page = chunk.get("metadata", {}).get("page", "N/A")
        content = chunk.get("content", "")
        context_parts.append(f"[Source: {source_doc}, Page: {page}]\n{content}")

    context = "\n\n".join(context_parts)

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"},
        messages=[
            {
                 "role": "system",
                "content": (
                    "You are a technical extraction assistant. RETURN ONLY VALID JSON. NO OTHER TEXT.\n\n"
                    f"CRITICAL: Extract parameter '{param}'\n\n"
                    "REQUIRED JSON STRUCTURE (you must return EXACTLY this format):\n"
                    '{"value": <extracted_value_or_null_or multiple fields>, "source_document": "<exact_doc_name_or_none>", "page": <page_number_or_none>}\n\n'
                    "RULES:\n"
                    "0. Extract the answer to each question from its labelled context only and try to keep the answer as much as asked in each question. "
                    "1. 'source_document' = EXACT document name from [Source: ...] tags (NOT 'none' if value found)\n"
                    "2. 'page' = EXACT page number as INTEGER from [Source: ...] tags (NOT 'none' if value found)\n"
                    "3. If value NOT found: {\"value\": null, \"source_document\": \"none\", \"page\": \"none\"}\n"
                    "4. Do NOT create 'reference' field\n"
                    "5. Do NOT add any fields besides value, source_document, page\n"
                    "6. Extract exactly what you see. Never make up information.\n\n"
                    f"Question: {meta['question']}"
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}"
            }
        ]
    )

    try:
        result = json.loads(response.choices[0].message.content)
        normalized = normalize_gpt_response(result, param) if param in result else {"value": None, "source_document": "none", "page": "none"}
        return param, normalized
    except:
        return param, {"value": None, "source_document": "none", "page": "none"}

#Batch embed all parameter questions,  Parallel retrieval with cached embeddings, Batch GPT calls and Deep dive on nulls
def extract_from_project(project_name: str):
    t_start = time.time()

    # Initialize DB - SINGLE common index for all projects
    db = HybridVectorDB(
        index_file="docs.index",
        meta_file="docs.pkl"
    )
    success = db.load()
    if not success:
        return None

    # Detect language for parameter registry
    language = detect_document_language(db, project_name)

    # Build registry with language-specific questions
    registry = build_parameter_registry(project_name, language)

    # Initialize reranker
    reranker = CrossEncoderReranker()

    # STEP 1A: Batch embed all parameter questions
    questions = [meta.get("question", param) for param, meta in registry.items()]

    try:
        embedding_response = client.embeddings.create(
            input=questions,
            model=EMBEDDING_MODEL
        )
        embeddings_cache = {
            param: embedding_response.data[i].embedding
            for i, (param, _) in enumerate(registry.items())
        }
    except:
        embeddings_cache = {}

    # STEP 1B: Parallel retrieval
    parameter_contexts = {}
    parameter_sources = {}

    def retrieve_param_with_embedding(param_meta_tuple):
        param, meta = param_meta_tuple
        question = meta.get("question", param)

        # Use cached embedding
        try:
            q_vec = np.array(embeddings_cache[param], dtype=np.float32)
        except:
            q_vec = None

        candidates = db.search(
            question=question,
            aliases=meta.get("aliases", []),
            project_name=project_name,
            k=RETRIEVAL_K,
            q_vec=q_vec
        )

        top_chunks = reranker.rerank(question, candidates, top_k=RERANK_TOP_K)

        context_parts = []
        chunk_metadata_list = []

        for chunk in top_chunks:
            source_doc = chunk.get("metadata", {}).get("source_document", "unknown")
            page = chunk.get("metadata", {}).get("page", "N/A")
            content = chunk.get("content", "")
            context_parts.append(f"[Source: {source_doc}, Page: {page}]\n{content}")
            chunk_metadata_list.append({
                "source_document": source_doc,
                "page": page
            })

        context = "\n\n".join(context_parts) if context_parts else ""
        return param, context, chunk_metadata_list

    with ThreadPoolExecutor(max_workers=12) as executor:
        retrieval_futures = {
            executor.submit(retrieve_param_with_embedding, item): item[0]
            for item in registry.items()
        }
        for future in as_completed(retrieval_futures):
            param, context, chunk_metadata_list = future.result()
            parameter_contexts[param] = context
            parameter_sources[param] = chunk_metadata_list

    # STEP 2: Batch GPT calls
    all_params = list(registry.items())
    batches = [
        dict(all_params[i : i + BATCH_SIZE])
        for i in range(0, len(all_params), BATCH_SIZE)
    ]

    batch_results = {}

    with ThreadPoolExecutor(max_workers=len(batches)) as executor:
        futures = {
            executor.submit(
                call_gpt_for_cluster,
                f"batch_{idx+1}",
                batch,
                parameter_contexts,
                parameter_sources,
                project_name
            ): idx
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                batch_results[idx] = future.result()
            except:
                batch_results[idx] = {}

    # STEP 3: Merge results
    result = {"project_name": project_name}
    for idx in sorted(batch_results):
        result.update(batch_results[idx])

    # STEP 4: Deep dive on nulls
    null_params = [
        k for k, v in result.items()
        if k != "project_name" and (
            (isinstance(v, dict) and v.get("value") is None) or
            (v is None)
        )
    ]

    if null_params:
        with ThreadPoolExecutor(max_workers=min(len(null_params), 8)) as executor:
            dd_futures = {
                executor.submit(
                    deep_dive_single, param, registry[param], db, reranker, project_name
                ): param
                for param in null_params
            }
            for future in as_completed(dd_futures):
                param, return_value = future.result()
                if return_value.get("value") is not None:
                    result[param] = return_value
                else:
                    result[param] = {
                        "value": None,
                        "source_document": "none",
                        "page": "none"
                    }

    t_end = time.time()

    return result




#Main entry point- extracts parameters for a given project using the common FAISS index.
def query_rag(query: str, project_name: str, transformer_type: str = "power") -> str:
    result = extract_from_project(project_name)
    if result is None:
        return json.dumps({"error": "Failed to load FAISS index"})
    return json.dumps(result, indent=2)

#For local testing
if __name__ == "__main__":
    
    project_name = input("Enter project name: ") if len(os.sys.argv) < 2 else os.sys.argv[1]
    result = extract_from_project(project_name)
    if result:
        print(json.dumps(result, indent=2))
        
        output_file = f"output_{project_name}_{int(time.time())}.json"
        abs_path = os.path.abspath(output_file)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        if os.path.exists(output_file):
            print(f"File saved!")
            print(f"Path: {abs_path}")
        else:
            print(f"File creation failed!")
            
        import traceback
        traceback.print_exc()