# Mini AI Business Intelligence Assistant

A small web application that answers a defined set of natural-language sales questions using **real SQL queries against SQLite**. It uses FastAPI for the API and a lightweight HTML/CSS/JavaScript frontend.

> This is a transparent, rule-based natural-language query mapper rather than an LLM-based system. That keeps the SQL safe and makes every answer reproducible. It can be extended with an LLM later, while still validating queries and using the database as the source of truth.

## Features

- Imports the supplied CSV into a local SQLite database at startup.
- Validates dates and numeric values, skips duplicates, invalid rows and non-completed transactions.
- Provides a browser UI with example questions and a SQL viewer.
- Provides JSON API endpoints: `GET /api/health`, `GET /api/summary`, and `POST /api/ask`.
- Handles blank, unsupported, too-long and malformed requests.
- Supports total revenue, top-revenue product, monthly revenue trend, top region, month-specific revenue and month-to-month revenue comparison.

## Requirements

- Python 3.10+
- `pip`

## Run on Windows

Open Command Prompt in the project folder.

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

Then open:

- App: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs
- Health/data-load report: http://127.0.0.1:8000/api/health

If `python` is not recognized on your computer, use `py` as shown above. Keep the terminal running while using the app.

## Example API request

```bash
curl -X POST http://127.0.0.1:8000/api/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What is the total revenue?\"}"
```

Example request body:

```json
{
  "question": "Which product generated the highest revenue?"
}
```

A successful response includes `answer`, `metric`, `data`, the executed SQL statement, and bound parameters. Unsupported questions return HTTP 400 with examples. Empty question bodies and invalid request shapes are validated by FastAPI.

## Data model and revenue definition

The `sales_transactions` table stores one row per accepted transaction:

| Column | Meaning |
|---|---|
| `transaction_id` | Unique transaction ID / primary key |
| `order_date` | ISO date (`YYYY-MM-DD`) |
| `month` | Month key (`YYYY-MM`) for grouping |
| `product`, `category`, `region`, `sales_channel` | Transaction dimensions |
| `quantity`, `unit_price`, `discount_amount` | Numeric sales fields |
| `status` | Transaction status |
| `revenue` | Stored calculated revenue |

**Revenue formula:** `quantity * unit_price - discount_amount`.

For this demo, only `Completed` transactions with a valid date, non-empty transaction ID/product, positive quantity and unit price, and a nonnegative discount are included. Returned transactions are excluded from revenue. Rows with invalid/missing required values and duplicate transaction IDs are excluded. A missing discount is treated as zero. These are simple demo rules and can be adjusted for the business's accounting policy.

The CSV is the source file in `data/sales_data.csv`. On each application startup the database table is rebuilt from this CSV so that changes in the source are picked up. The generated `sales.db` is local and ignored by Git.

## How questions become answers

1. The user submits a question to `POST /api/ask`.
2. The backend normalizes the text and maps it to a supported query intent.
3. The backend runs a parameterized SQL query against SQLite.
4. The backend returns a structured JSON response and a human-readable answer.
5. The frontend displays the answer, result data and SQL used.

Month comparisons use parameterized month values; user text is never concatenated into SQL. This small project intentionally supports a defined set of question patterns rather than arbitrary SQL generation.

## Supported example questions

- `What is the total revenue?`
- `Which product generated the highest revenue?`
- `What is the monthly revenue trend?`
- `Which region generated the highest sales?`
- `How did revenue change between January and February?`
- `Compare revenue between 2026-01 and 2026-02.`
- `What was the revenue in March 2026?`

## API summary

### `GET /api/health`
Returns server status and CSV import counts.

### `GET /api/summary`
Returns valid transaction count, total revenue, product count and region count.

### `POST /api/ask`
Request:

```json
{"question": "What is the monthly revenue trend?"}
```

Successful response (shape):

```json
{
  "ok": true,
  "question": "What is the monthly revenue trend?",
  "answer": "Monthly revenue trend retrieved from the database.",
  "metric": "monthly_revenue",
  "data": [{"month": "2026-01", "revenue": 12345.0}],
  "sql": "SELECT ...",
  "params": []
}
```

Numbers above are illustrative response-shape examples only; the running application calculates actual values from the CSV.

## Project structure

```text
mini_ai_bi_assistant/
├── app/
│   ├── __init__.py
│   ├── assistant.py       # Intent mapping and SQL query execution
│   ├── database.py        # CSV cleaning and SQLite loading
│   └── main.py            # FastAPI endpoints
├── data/
│   └── sales_data.csv     # Supplied dataset
├── static/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── tests/
├── .gitignore
├── README.md
└── requirements.txt
```

## Limitations / possible improvements

- Natural language support is intent-based and limited to the documented questions.
- Add automated tests, authentication, pagination and deployment configuration for a larger application.
- For broader language support, add an LLM to classify questions or propose SQL, but validate the query against a strict schema/allowlist and execute only read-only queries. Keep database results as the source of truth.
