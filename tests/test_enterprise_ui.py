"""Visual-layer invariants: python -m unittest test_enterprise_ui -v."""

import copy
import unittest

import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest
from pathlib import Path

from dashboard.enterprise_theme import apply_enterprise_theme

APP_FILE = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")


class EnterpriseUIChecks(unittest.TestCase):
    def test_theme_preserves_graph_data_and_interactions(self):
        fig = go.Figure(go.Scatter(
            x=[0, 1, None, 2], y=[3, 4, None, 5], mode="markers+lines",
            text=["User", "Merchant", "", "Hub"],
            customdata=[10, 20, 0, 30], marker=dict(size=[12, 22, 0, 22]),
            hovertemplate="%{text}: %{customdata}<extra></extra>",
        ))
        fig.update_layout(xaxis=dict(showgrid=False, range=[-1, 3]),
                          yaxis=dict(showticklabels=False), height=550)
        original = copy.deepcopy(fig.to_plotly_json()["data"])
        self.assertIs(apply_enterprise_theme(fig), fig)
        self.assertEqual(fig.to_plotly_json()["data"], original)
        self.assertEqual(fig.layout.xaxis.range, (-1, 3))
        self.assertFalse(fig.layout.xaxis.showgrid)
        self.assertFalse(fig.layout.yaxis.showticklabels)
        self.assertEqual(fig.layout.height, 550)

    def test_navigation_export_and_all_tab_rendering(self):
        app = AppTest.from_file(APP_FILE).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 6)
        charts = app.get("plotly_chart")
        self.assertGreaterEqual(len(charts), 11)
        for index, tab in enumerate(app.tabs):
            app.button(key=f"nav_{index}").click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["intelligence_tabs"], tab.label)
            self.assertEqual(len(app.get("plotly_chart")), len(charts))
        app.button(key="sidebar_export").click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 1)

    def test_category_filter_updates_the_complete_merchant_view(self):
        app = AppTest.from_file(APP_FILE).run(timeout=60)
        app.selectbox(key="merchant_category_filter").select("Apparel").run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["intelligence_tabs"], "💳 Merchant Risk Center")
        merchant_table = app.dataframe[0].value
        self.assertTrue((merchant_table["merchant_category"] == "Apparel").all())
        self.assertTrue(any("Category: Apparel" in caption.value for caption in app.caption))


if __name__ == "__main__":
    unittest.main()
