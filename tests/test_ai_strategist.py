"""Offline regression checks: python -m unittest test_ai_strategist -v."""

import copy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import duckdb
from groq import APITimeoutError
import httpx
import pandas as pd
from streamlit.testing.v1 import AppTest

from dashboard.agent import ai_strategist as agent


class FakeGroq:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=self)

    def with_options(self, **kwargs):
        return self

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        reply = next(self.replies)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])


def table_config():
    return {"chart_type": "Table", "x_col": "", "y_col": "", "color_col": None,
            "title": "Transaction results", "bullet_points": ["Returned **1** row.", "Review dispute exposure."]}


class StrategistChecks(unittest.TestCase):
    def test_groq_loads_project_env_and_preserves_server_key(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(agent, "__file__", str(root / "dashboard" / "agent" / "ai_strategist.py")), \
                    patch.dict(os.environ, {}, clear=True), patch.object(agent, "Groq") as groq:
                self.assertIsNone(agent.get_groq_client.__wrapped__())
                groq.assert_not_called()
                (root / ".env").write_text('GROQ_API_KEY="test-file-key"\n', encoding="utf-8-sig")
                agent.get_groq_client.__wrapped__()
                self.assertEqual(groq.call_args.kwargs["api_key"], "test-file-key")
                os.environ["GROQ_API_KEY"] = "test-server-key"
                agent.get_groq_client.__wrapped__()
                self.assertEqual(groq.call_args.kwargs["api_key"], "test-server-key")

    @classmethod
    def setUpClass(cls):
        cls.conn = agent.get_duckdb_connection.__wrapped__()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_registration_intent_and_read_only_boundary(self):
        for table, columns in agent.SCHEMA.items():
            self.assertEqual(list(self.conn.execute(f"SELECT * FROM {table} LIMIT 0").df()), columns)
        for column in agent.PRESETS:
            self.assertTrue(all(agent.validate_query_intent(q) for q in column))
        for question in ("What is the weather?", "fraud weather forecast", "Write a poem", "", "x" * 2001):
            client, conn = MagicMock(), MagicMock()
            with self.assertRaises(agent.StrategistError):
                agent.generate_sql_with_self_healing(question, client, conn)
            self.assertFalse(client.mock_calls)
            self.assertFalse(conn.mock_calls)
        for question in (
            "What is this dashboard all about?",
            "What does the dashboard do?",
            "What's this app about?",
            "Give me an overview of this dashboard",
            "Give me an executive overview",
            "What can you analyze?",
            "What data is available?",
        ):
            self.assertIsNotNone(agent.get_local_strategist_answer(question))
        self.assertIsNone(agent.get_local_strategist_answer("Show transaction volume by day"))
        unsafe = [
            "DROP TABLE transactions", "DELETE FROM transactions", "UPDATE transactions SET amount=0",
            "INSERT INTO transactions SELECT * FROM transactions", "ALTER TABLE transactions ADD x INT",
            "CREATE TABLE stolen AS SELECT * FROM transactions", "SELECT 1; DROP TABLE transactions",
            "COPY transactions TO 'stolen.csv'", "ATTACH 'other.duckdb' AS other", "PRAGMA database_list",
            "SELECT * FROM read_csv('secrets.csv')", "SELECT * FROM read_parquet('https://example.com/data')",
            "SELECT * FROM duckdb_settings()", "SELECT getenv('GROQ_API_KEY')", "SELECT nextval('seq')",
            "SELECT * FROM information_schema.tables", "SELECT * FROM transactions JOIN range(10) ON true",
            "WITH t AS (SELECT * FROM read_csv('secret')) SELECT * FROM t",
            "SELECT * FROM 'secrets.csv'", "SELECT * INTO stolen FROM transactions",
            "WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t) SELECT * FROM t",
        ]
        for sql in unsafe:
            with self.subTest(sql=sql), self.assertRaises((agent.StrategistError, duckdb.Error)):
                agent._validate_sql(sql, self.conn)
        # Semicolons and forbidden words inside string literals are safe.
        for sql in (
            "SELECT 'DROP; DELETE' AS label, COUNT(*) n FROM transactions",
            "WITH t AS (SELECT COUNT(*) n FROM transactions) SELECT * FROM t",
            "SELECT date_trunc('day', timestamp) AS day, sum(amount) AS volume FROM transactions GROUP BY 1",
            "SELECT * FROM 'transactions' LIMIT 1",
        ):
            self.conn.execute(agent._validate_sql(sql, self.conn)).df()
        self.assertFalse(self.conn.execute("SELECT current_setting('enable_external_access')").fetchone()[0])

    def test_sql_repairs_include_exact_error_and_are_bounded(self):
        bad = "SELECT missing_amount FROM transactions"
        try:
            self.conn.execute(f"SELECT * FROM (\n{bad}\n) AS strategist_result LIMIT 1001")
        except duckdb.Error as exc:
            exact_error = str(exc)
        client = FakeGroq([bad, "SELECT COUNT(*) AS n FROM transactions"])
        sql, df = agent.generate_sql_with_self_healing("Total transactions", client, self.conn)
        self.assertEqual(int(df.iloc[0, 0]), 20000)
        self.assertIn(exact_error, client.calls[1]["messages"][-1]["content"])
        self.assertIn(bad, client.calls[1]["messages"][-2]["content"])
        self.assertEqual(client.calls[0]["model"], agent.GROQ_MODEL)
        self.assertEqual(client.calls[0]["temperature"], 0.0)
        self.assertEqual(client.calls[0]["reasoning_effort"], "low")
        self.assertFalse(client.calls[0]["include_reasoning"])
        self.assertEqual(self.conn.execute(sql).fetchone()[0], 20000)
        client = FakeGroq([bad] * 3)
        with self.assertRaisesRegex(agent.StrategistError, "two retries"):
            agent.generate_sql_with_self_healing("Total transactions", client, self.conn)
        self.assertEqual(len(client.calls), 3)
        client = FakeGroq(["SELECT * FROM transactions"])
        with self.assertRaisesRegex(agent.StrategistError, "1,000"):
            agent.generate_sql_with_self_healing("List transactions", client, self.conn)
        client = FakeGroq(["OUT_OF_SCOPE"])
        conn = MagicMock()
        with self.assertRaisesRegex(agent.StrategistError, "UPI payments"):
            agent.generate_sql_with_self_healing("Tell me a fraud-themed story", client, conn)
        self.assertFalse(conn.mock_calls)

    def test_expensive_query_is_interrupted_and_connection_recovers(self):
        client = FakeGroq(["SELECT SUM(a.amount * b.amount) AS volume FROM transactions a CROSS JOIN transactions b"])
        with patch.object(agent, "QUERY_TIMEOUT", 0.02):
            with self.assertRaisesRegex(agent.StrategistError, "time or memory budget"):
                agent.generate_sql_with_self_healing("Total transaction volume", client, self.conn)
        self.assertEqual(self.conn.execute("SELECT 1").fetchone()[0], 1)

    def test_json_validation_and_api_failure_preserve_results(self):
        df = pd.DataFrame({"status": ["SUCCESS", "FAILED"], "count": [10, 2]})
        valid = {**table_config(), "chart_type": "Bar", "x_col": "status", "y_col": "count"}
        client = FakeGroq([json.dumps(valid)])
        self.assertEqual(agent.synthesize_visual_and_findings("Transaction status", "SELECT ...", df, client), valid)
        self.assertEqual(client.calls[0]["response_format"], {"type": "json_object"})
        self.assertEqual(client.calls[0]["model"], agent.GROQ_MODEL)
        self.assertEqual(client.calls[0]["reasoning_effort"], "low")
        self.assertFalse(client.calls[0]["include_reasoning"])
        self.assertEqual(client.calls[0]["temperature"], 0.1)
        for response in ("not json", "[]", json.dumps({**valid, "y_col": "invented"}),
                         json.dumps({**valid, "chart_type": "Heatmap"})):
            config = agent.synthesize_visual_and_findings("Transaction status", "SQL", df, FakeGroq([response]))
            self.assertEqual(config["chart_type"], "Table")
        timeout = APITimeoutError(request=httpx.Request("POST", "https://api.groq.com"))
        client = MagicMock()
        client.with_options.return_value.chat.completions.create.side_effect = timeout
        with self.assertRaisesRegex(agent.StrategistError, "timed out"):
            agent.generate_sql_with_self_healing("Total transactions", client, self.conn)
        config = agent.synthesize_visual_and_findings("Transaction status", "SQL", df, client)
        self.assertIn("timed out", config["bullet_points"][1])
        empty = agent.synthesize_visual_and_findings("Total transactions", "SQL", df.iloc[:0], MagicMock())
        self.assertIn("No matching records", empty["bullet_points"][1])
        missing = agent.synthesize_visual_and_findings("Average resolution time", "SQL",
                  pd.DataFrame({"average_resolution_days": [float("nan")]}), MagicMock())
        self.assertIn("cannot be measured", missing["bullet_points"][0])

    def test_all_chart_renderers(self):
        script = '''
import pandas as pd
from dashboard.agent.ai_strategist import render_plotly_viz
df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 6, 8]})
for chart in ['Bar', 'Line', 'Scatter', 'Donut', 'Metric', 'Table']:
    config = {'chart_type': chart, 'x_col': 'x', 'y_col': 'y', 'color_col': None,
              'title': chart, 'bullet_points': ['**3** rows.', 'Review risk.']}
    render_plotly_viz(df.head(1) if chart == 'Metric' else df, config)
'''
        app = AppTest.from_string(script).run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 4)
        self.assertEqual(len(app.metric), 1)
        self.assertEqual(len(app.dataframe), 1)

    def test_presets_state_reruns_and_rejection(self):
        script = '''
from dashboard.agent.ai_strategist import get_duckdb_connection, render_ai_strategist_tab
render_ai_strategist_tab(object(), get_duckdb_connection())
'''
        def reply(client, **kwargs):
            if "response_format" not in kwargs:
                return "SELECT COUNT(*) AS transaction_count FROM transactions"
            return json.dumps(table_config())
        with patch.object(agent, "_completion", side_effect=reply) as llm:
            app = AppTest.from_string(script).run(timeout=15)
            self.assertFalse(app.exception)
            self.assertEqual(llm.call_count, 0)
            self.assertEqual(len(app.button), 13)
            for column in agent.PRESETS:
                for preset in column:
                    app.button(key=f"strategist_{preset}").click().run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.text_input[0].value, preset)
                    self.assertEqual(app.session_state["strategist_result"][0], preset)
            self.assertEqual(llm.call_count, 24)
            app.run()
            self.assertEqual(llm.call_count, 24)
            self.assertTrue(app.code)
            app.text_input[0].set_value("What is this dashboard all about?").run()
            self.assertFalse(app.exception)
            self.assertFalse(app.warning)
            self.assertFalse(app.code)
            self.assertEqual(app.session_state["strategist_answer"][1], "About this dashboard")
            self.assertEqual(llm.call_count, 24)
            app.text_input[0].set_value("What is the weather?").run()
            self.assertFalse(app.exception)
            self.assertTrue(app.warning)
            self.assertFalse(app.code)
            self.assertEqual(llm.call_count, 24)


if __name__ == "__main__":
    unittest.main()
