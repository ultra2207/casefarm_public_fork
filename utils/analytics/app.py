import sys

import yaml


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)

import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st
from log_ingester import LogIngester

from utils.logger import get_custom_logger

logger = get_custom_logger()

# Page configuration
st.set_page_config(page_title="CaseFarm Analytics", page_icon="📊", layout="wide")
"""
to run it:
streamlit run utils/analytics/app.py
"""


class Dashboard:
    def __init__(self):
        self.db_path = (
            r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\ingester.db"
        )
        self.log_path = (
            r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\logs\stage_1.log"
        )
        self.ingester = LogIngester(self.db_path)
        logger.info("Dashboard initialized")

    def get_data(self, query: str) -> pd.DataFrame:
        """Execute query and return DataFrame"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            logger.info(f"Query executed successfully, returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            st.error(f"Database query failed: {e}")
            return pd.DataFrame()

    def auto_refresh_on_launch(self):
        """Automatically refresh data when the app launches"""
        # Use session state to ensure refresh only happens once per session
        if "data_refreshed" not in st.session_state:
            st.session_state.data_refreshed = False

        if not st.session_state.data_refreshed:
            with st.spinner("🔄 Loading latest data..."):
                try:
                    events_processed = self.ingester.run_ingestion(self.log_path)
                    logger.info(
                        f"Auto-refresh on launch completed: {events_processed} events processed"
                    )

                    if events_processed > 0:
                        st.success(f"✅ Loaded {events_processed} new events")
                    else:
                        st.info("📊 Data is up to date")

                    st.session_state.data_refreshed = True

                except Exception as e:
                    st.error(f"❌ Auto-refresh failed: {e}")
                    logger.error(f"Auto-refresh on launch failed: {e}")
                    st.session_state.data_refreshed = (
                        True  # Mark as tried to avoid infinite loops
                    )

    def run_dashboard(self):
        st.title("🎮 CaseFarm Analytics Dashboard")
        logger.info("Dashboard started")

        # Auto-refresh data on launch
        self.auto_refresh_on_launch()

        # Sidebar
        st.sidebar.header("⚙️ Controls")

        # Manual refresh button (still available)
        if st.sidebar.button("🔄 Manual Refresh"):
            logger.info("Manual data refresh initiated")
            with st.spinner("Processing logs..."):
                try:
                    events_processed = self.ingester.run_ingestion(self.log_path)
                    st.sidebar.success(f"✅ Processed {events_processed} new events")
                    logger.info(
                        f"Manual refresh completed: {events_processed} events processed"
                    )
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ Refresh failed: {e}")
                    logger.error(f"Manual refresh failed: {e}")

        # External costs management
        st.sidebar.header("💰 External Costs")
        self.external_costs_section()

        # Time period selector for both graph and table
        st.header("📊 Profit Analysis")

        col1, col2 = st.columns(2)

        with col1:
            graph_period = st.selectbox(
                "Graph Time Period", ["Daily", "Weekly", "Monthly"], key="graph_period"
            )

        with col2:
            table_period = st.selectbox(
                "Table Time Period", ["Daily", "Weekly", "Monthly"], key="table_period"
            )

        # Main content
        self.show_profit_graph(graph_period)
        self.show_profit_table(table_period)

    def external_costs_section(self):
        """External costs input section"""
        try:
            # Get current costs
            current_costs = self.get_data("""
                SELECT farmlabs_cost_eur, vm_cost_usd, panel_cost_usd, date
                FROM external_costs 
                ORDER BY date DESC 
                LIMIT 1
            """)

            if not current_costs.empty:
                current = current_costs.iloc[0]
                farmlabs_default = current["farmlabs_cost_eur"]
                vm_default = current["vm_cost_usd"]
                standard_panel_default = current["panel_cost_usd"]
                st.sidebar.info(f"Last updated: {current['date']}")
                logger.info(
                    f"Current external costs loaded: Farmlabs €{farmlabs_default}, VM ${vm_default}, Standard Panel ${standard_panel_default}"
                )
            else:
                farmlabs_default = 17.5
                vm_default = 17.0
                standard_panel_default = 15.0
                logger.warning("No external costs found in database, using defaults")

            # Input fields
            farmlabs_cost = st.sidebar.number_input(
                "Farmlabs Cost (EUR)", min_value=0.0, value=farmlabs_default, step=0.5
            )

            vm_cost = st.sidebar.number_input(
                "VM Cost (USD)", min_value=0.0, value=vm_default, step=1.0
            )

            standard_panel_cost = st.sidebar.number_input(
                "Standard Panel Cost (USD)",
                min_value=0.0,
                value=standard_panel_default,
                step=1.0,
            )

            if st.sidebar.button("💾 Update Costs"):
                try:
                    self.ingester.update_external_costs(
                        farmlabs_cost, vm_cost, standard_panel_cost
                    )
                    self.ingester.calculate_daily_metrics()
                    st.sidebar.success("✅ Costs updated!")
                    logger.info(
                        f"External costs updated via UI: Farmlabs €{farmlabs_cost}, VM ${vm_cost}, Standard Panel ${standard_panel_cost}"
                    )
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ Update failed: {e}")
                    logger.error(f"Failed to update external costs via UI: {e}")

        except Exception as e:
            st.sidebar.error(f"❌ Error loading costs: {e}")
            logger.error(f"Error in external costs section: {e}")

    def get_period_data(self, period: str) -> pd.DataFrame:
        """Get aggregated data based on time period"""
        try:
            if period == "Daily":
                query = """
                    SELECT 
                        date as period,
                        SUM(gross_profit_inr * success_rate) as gross_profit,
                        SUM(net_theoretical_profit_inr * success_rate) as net_theoretical_profit
                    FROM events
                    GROUP BY date
                    ORDER BY date
                """
            elif period == "Weekly":
                query = """
                    SELECT 
                        strftime('%Y-W%W', date) as period,
                        SUM(gross_profit_inr * success_rate) as gross_profit,
                        SUM(net_theoretical_profit_inr * success_rate) as net_theoretical_profit
                    FROM events
                    GROUP BY strftime('%Y-W%W', date)
                    ORDER BY strftime('%Y-W%W', date)
                """
            else:  # Monthly
                query = """
                    SELECT 
                        strftime('%Y-%m', date) as period,
                        SUM(gross_profit_inr * success_rate) as gross_profit,
                        SUM(net_theoretical_profit_inr * success_rate) as net_theoretical_profit
                    FROM events
                    GROUP BY strftime('%Y-%m', date)
                    ORDER BY strftime('%Y-%m', date)
                """

            data = self.get_data(query)

            if not data.empty and period == "Daily":
                data["period"] = pd.to_datetime(data["period"])

            return data

        except Exception as e:
            logger.error(f"Failed to get {period.lower()} data: {e}")
            return pd.DataFrame()

    def show_profit_graph(self, period: str):
        """Show profit line graph"""
        st.subheader(f"📈 {period} Profit Trends")

        data = self.get_period_data(period)

        if not data.empty:
            # Create line chart with visible markers/points
            fig = px.line(
                data,
                x="period",
                y=["gross_profit", "net_theoretical_profit"],
                title=f"{period} Profit Analysis",
                labels={
                    "period": "Time Period",
                    "value": "Profit (₹)",
                    "variable": "Profit Type",
                },
                markers=True,  # This adds visible points
            )

            # Update trace names
            fig.data[0].name = "Gross Profit"
            fig.data[1].name = "Net Theoretical Profit"

            # Optionally customize marker appearance
            fig.update_traces(
                marker=dict(size=8),  # Adjust point size
                line=dict(width=2),  # Adjust line width
            )

            # Update layout
            fig.update_layout(
                yaxis_title="Profit (₹)",
                xaxis_title="Time Period",
                hovermode="x unified",
            )

            st.plotly_chart(fig, use_container_width=True)

            # Show summary stats
            col1, col2, col3 = st.columns(3)

            with col1:
                total_gross = data["gross_profit"].sum()
                st.metric("Total Gross Profit", f"₹{total_gross:,.2f}")

            with col2:
                total_net = data["net_theoretical_profit"].sum()
                st.metric("Total Net Theoretical Profit", f"₹{total_net:,.2f}")

            with col3:
                avg_gross = data["gross_profit"].mean()
                st.metric(f"Average {period} Gross Profit", f"₹{avg_gross:,.2f}")

            logger.info(
                f"Profit graph displayed for {period} period with {len(data)} data points"
            )
        else:
            st.info(f"No {period.lower()} data available for the graph")
            logger.warning(f"No {period.lower()} data available for graph")

    def show_profit_table(self, period: str):
        """Show profit data table"""
        st.subheader(f"📋 {period} Profit Table")

        data = self.get_period_data(period)

        if not data.empty:
            # Format the data for display
            display_data = data.copy()
            display_data["gross_profit"] = display_data["gross_profit"].apply(
                lambda x: f"₹{x:,.2f}"
            )
            display_data["net_theoretical_profit"] = display_data[
                "net_theoretical_profit"
            ].apply(lambda x: f"₹{x:,.2f}")

            # Rename columns for display
            column_names = {
                "period": "Time Period",
                "gross_profit": "Gross Profit",
                "net_theoretical_profit": "Net Theoretical Profit",
            }

            display_data = display_data.rename(columns=column_names)

            # Show the table
            st.dataframe(display_data, use_container_width=True, hide_index=True)

            # Download button
            csv = data.to_csv(index=False)
            st.download_button(
                label=f"📥 Download {period} Data as CSV",
                data=csv,
                file_name=f"casefarm_{period.lower()}_profits.csv",
                mime="text/csv",
            )

            logger.info(
                f"Profit table displayed for {period} period with {len(data)} rows"
            )
        else:
            st.info(f"No {period.lower()} data available for the table")
            logger.warning(f"No {period.lower()} data available for table")


if __name__ == "__main__":
    try:
        dashboard = Dashboard()
        dashboard.run_dashboard()
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        st.error(f"Failed to start dashboard: {e}")
