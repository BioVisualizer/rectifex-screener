# =============================================================================
# Aethelon - Help Texts
# VERSION 56.0: "Full Transparency Update"
# - FEATURE: A critical new section "Limits of Analysis" has been added to
#   clarify the difference between relative and absolute valuation.
# - IMPROVEMENT: The disclaimer has been enhanced.
# =============================================================================

HELP_TEXT_DE = """
# Aethelon - Global Stock Screener

Ein Open-Source Aktien-Analysewerkzeug für Linux, das fundamentale Unternehmensdaten nutzt, um Aktien nach verschiedenen Investment-Strategien zu bewerten und zu ranken.

*Built by Lukas Morcinek.*

---

## Was ist Aethelon?

Aethelon ist ein Werkzeug für die **relative Analyse**. Es beantwortet die Frage: *"Welche Unternehmen sind im Vergleich zu allen anderen im Analyse-Universum gerade jetzt am attraktivsten nach meiner gewählten Strategie?"* Die Antwort ist immer tagesaktuell, da sie auf dem aktuellen Aktienkurs basiert.

---

## Wichtiger Hinweis: Grenzen der Analyse

Aethelon berechnet **keinen "fairen Wert"** für eine Aktie. Die Scores basieren ausschließlich auf historischen, quantitativen Daten.

Ein hoher `Value_Score` bedeutet beispielsweise nur, dass eine Aktie im Vergleich zu anderen *quantitativ* günstig ist. Er berücksichtigt **keine qualitativen, zukunftsgerichteten Risiken**.

**Beispiel:** Eine Autofirma mag einen hohen Value-Score haben, weil ihr KGV niedrig ist. Die App kann aber nicht bewerten, ob das Unternehmen die Umstellung auf E-Mobilität erfolgreich meistern wird. Diese qualitative Einschätzung musst du als Nutzer selbst treffen.

---

## Die Investment-Strategien

*   **Balanced:** Ein ausgewogener Allround-Ansatz.
*   **High Growth:** Fokus auf Umsatzwachstum und Profitabilität.
*   **Deep Value:** Fokus auf aktuell günstig bewertete Aktien.
*   **Quality Dividend:** Fokus auf profitable, stabile Dividendenzahler.

---

## Transparenz: Die 6 Dimensionen & ihre Metriken

1.  **Qualität:** `ROE_Avg3Y` (Durchschnittliche Eigenkapitalrendite der letzten 3 Jahre).
2.  **Wert:** `PE` (KGV) & `PB` (KBV).
3.  **Wachstum:** `RevGrowth3YCAGR` (Ø jährliches Umsatzwachstum der letzten 3 Jahre).
4.  **Momentum:** `Momentum6M` (Kursperformance der letzten 6 Monate).
5.  **Dividende:** `DivYield` (Dividendenrendite).
6.  **Sicherheit:** `Volatility` & `DebtEquity` (Verschuldungsgrad).

---

## Disclaimer

Dieses Programm dient ausschließlich zu Bildungs- und Informationszwecken. Die Ergebnisse stellen **keine Anlageberatung oder Kaufempfehlung** dar. Alle Daten stammen von Drittanbieter-APIs (`yfinance`) und können Fehler enthalten. Jede Investitionsentscheidung, die auf diesen Daten basiert, erfolgt ausschließlich auf eigenes Risiko. **Triff niemals eine Anlageentscheidung nur auf Basis dieser App.**
"""

HELP_TEXT_EN = """
# Aethelon - Global Stock Screener

An open-source stock analysis tool for Linux that uses fundamental company data to rate and rank stocks according to various investment strategies.

*Built by Lukas Morcinek.*

---

## What is Aethelon?

Aethelon is a tool for **relative analysis**. It answers the question: *"Which companies, compared to all others in the analysis universe, are currently the most attractive based on my chosen strategy?"* This answer is always up-to-date as it is based on the current stock price.

---

## Important Note: Limits of this Analysis

Aethelon **does not calculate a "fair value"** for a stock. The scores are based exclusively on historical, quantitative data.

For example, a high `Value_Score` only means that a stock is *quantitatively* cheap compared to others. It **does not account for qualitative, forward-looking risks**.

**Example:** A car company might have a high Value Score because its P/E ratio is low. However, the app cannot assess whether the company will successfully manage the transition to electric vehicles. This qualitative judgment must be made by you, the user.

---

## The Investment Strategies

*   **Balanced:** A well-rounded approach.
*   **High Growth:** Focus on revenue growth and profitability.
*   **Deep Value:** Focus on currently cheaply valued stocks.
*   **Quality Dividend:** Focus on profitable, stable dividend payers.

---

## Transparency: The 6 Dimensions & Their Metrics

1.  **Quality:** `ROE_Avg3Y` (Average Return on Equity over the last 3 years).
2.  **Value:** `PE` (Price-to-Earnings Ratio) & `PB` (Price-to-Book Ratio).
3.  **Growth:** `RevGrowth3YCAGR` (Compound Annual Growth Rate of revenue over the last 3 years).
4.  **Momentum:** `Momentum6M` (Price performance of the last 6 months).
5.  **Dividend:** `DivYield` (Dividend Yield).
6.  **Safety:** `Volatility` & `DebtEquity` (Debt-to-Equity Ratio).

---

## Disclaimer

This program is for educational and informational purposes only. The results **do not constitute investment advice or a recommendation to buy or sell.** All data is sourced from third-party APIs (`yfinance`) and may contain errors. Any investment decision based on this data is made solely at your own risk. **Never make an investment decision based on this app alone.**
"""
