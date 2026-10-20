"""India HeatWatch: historical heatwave and climate analytics mini-project.

Demonstrates eight Python lab topics using Streamlit, pandas, Plotly and SQLite.
This is a historical analytics tool, not a live forecast or official warning system.
"""
from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = APP_DIR / "india_heatwave_climate_dataset_50000.csv"
DB_PATH = APP_DIR / "heatwatch.db"
TABLE_NAME = "weather_records"

st.set_page_config(page_title="India HeatWatch", page_icon="🌡️", layout="wide")

# ------------------------------ Shared data layer ------------------------------
EXPECTED_NUMERIC = [
    "latitude", "longitude", "elevation_m", "max_temperature_c",
    "min_temperature_c", "avg_temperature_c", "relative_humidity_pct",
    "dew_point_c", "precipitation_mm", "wind_speed_kmh",
    "surface_pressure_hpa", "solar_radiation_mj_m2", "heatwave_flag_derived",
]


def clean_weather_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean known columns while keeping additional dataset columns intact."""
    data = frame.copy()
    data.columns = [str(c).strip() for c in data.columns]
    for col in ("city", "state", "station_id", "heatwave_severity_derived"):
        if col in data.columns:
            data[col] = data[col].astype("string").str.strip()
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
    for col in EXPECTED_NUMERIC:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")
    if "heatwave_flag_derived" in data.columns:
        data["heatwave_flag_derived"] = data["heatwave_flag_derived"].fillna(0).astype(int)
    return data


def load_csv(uploaded_file=None) -> pd.DataFrame:
    if uploaded_file is not None:
        return clean_weather_data(pd.read_csv(uploaded_file))
    if not DEFAULT_CSV.exists():
        raise FileNotFoundError(
            f"Could not find {DEFAULT_CSV.name}. Put the CSV beside app.py or upload it in the sidebar."
        )
    return clean_weather_data(pd.read_csv(DEFAULT_CSV))


def save_to_sqlite(data: pd.DataFrame, db_path: Path = DB_PATH) -> None:
    """Persist the current dataset to SQLite; dates are stored as ISO text."""
    db_frame = data.copy()
    if "date" in db_frame.columns:
        db_frame["date"] = db_frame["date"].dt.strftime("%Y-%m-%d")
    with sqlite3.connect(db_path) as conn:
        db_frame.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_weather_city ON weather_records(city)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_weather_date ON weather_records(date)")


def query_sqlite(sql: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def format_number(value: Any, suffix: str = "", digits: int = 1) -> str:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


# ------------------------------ Experiment 1: OOP ------------------------------
class WeatherRecord:
    """A single weather observation, represented as an object."""
    def __init__(self, city: str, date: Any, max_temperature: float, avg_temperature: float):
        self.city = str(city)
        self.date = str(date)
        self.max_temperature = float(max_temperature)
        self.avg_temperature = float(avg_temperature)

    def temperature_range(self) -> float:
        return self.max_temperature - self.avg_temperature

    def summary(self) -> str:
        return (f"{self.city} on {self.date}: maximum {self.max_temperature:.1f}°C, "
                f"average {self.avg_temperature:.1f}°C.")


# -------------------------- Experiment 3: inheritance --------------------------
class ClimateReport:
    """Base class for formatted report types."""
    def __init__(self, title: str):
        self.title = title

    def render(self, data: pd.DataFrame) -> str:
        return f"{self.title}: {len(data):,} records"


class CityReport(ClimateReport):
    def render(self, data: pd.DataFrame) -> str:
        city_count = data["city"].nunique() if "city" in data else 0
        return f"{self.title}: {len(data):,} records across {city_count} cities"


class HeatwaveReport(ClimateReport):
    def render(self, data: pd.DataFrame) -> str:
        flags = int(data["heatwave_flag_derived"].fillna(0).sum()) if "heatwave_flag_derived" in data else 0
        return f"{self.title}: {flags:,} flagged records in the selected data"


# ---------------------- Experiment 4: abstraction / polymorphism ----------------------
class Analyzer(ABC):
    @abstractmethod
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a summary dataframe."""
        raise NotImplementedError


class CityTemperatureAnalyzer(Analyzer):
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        return (data.groupby("city", dropna=False)["max_temperature_c"]
                .agg(record_count="count", average_max="mean", highest_max="max")
                .reset_index().sort_values("highest_max", ascending=False))


class HeatwaveCityAnalyzer(Analyzer):
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        return (data.groupby("city", dropna=False)["heatwave_flag_derived"]
                .sum().reset_index(name="flagged_records")
                .sort_values("flagged_records", ascending=False))


# ---------------------------------- UI helpers ----------------------------------
def section_title(title: str, description: str) -> None:
    st.title(title)
    st.caption(description)


def safe_metric(label: str, value: Any, suffix: str = "", digits: int = 1) -> None:
    st.metric(label, format_number(value, suffix, digits))


def filtered_data(data: pd.DataFrame, city: str, year_range: tuple[int, int]) -> pd.DataFrame:
    result = data.copy()
    if city != "All cities" and "city" in result:
        result = result[result["city"].astype(str) == city]
    if "date" in result:
        years = result["date"].dt.year
        result = result[years.between(year_range[0], year_range[1])]
    return result


# ------------------------------------ Sidebar -----------------------------------
st.sidebar.title("🌡️ India HeatWatch")
st.sidebar.caption("HISTORICAL CLIMATE INTELLIGENCE")
uploaded = st.sidebar.file_uploader("Upload weather CSV (optional)", type=["csv"])
try:
    raw_data = load_csv(uploaded)
except Exception as exc:
    st.error(f"Could not load the dataset: {exc}")
    st.info("Place india_heatwave_climate_dataset_50000.csv in the same folder as app.py, or upload it above.")
    st.stop()

required = {"city", "date", "max_temperature_c", "avg_temperature_c", "heatwave_flag_derived"}
missing = required - set(raw_data.columns)
if missing:
    st.error("This CSV is missing columns required by this project: " + ", ".join(sorted(missing)))
    st.stop()

# Persist once per dataset fingerprint in this app session.
fingerprint = (len(raw_data), str(raw_data["date"].min()), str(raw_data["date"].max()), tuple(raw_data.columns))
if st.session_state.get("db_fingerprint") != fingerprint or not DB_PATH.exists():
    try:
        save_to_sqlite(raw_data)
        st.session_state["db_fingerprint"] = fingerprint
    except Exception as exc:
        st.error(f"SQLite initialisation failed: {exc}")
        st.stop()

valid_dates = raw_data["date"].dropna()
min_year = int(valid_dates.dt.year.min()) if not valid_dates.empty else 2010
max_year = int(valid_dates.dt.year.max()) if not valid_dates.empty else 2019
cities = sorted(raw_data["city"].dropna().astype(str).unique().tolist())
selected_city = st.sidebar.selectbox("City filter", ["All cities"] + cities)
year_range = st.sidebar.slider("Year range", min_year, max_year, (min_year, max_year))
data = filtered_data(raw_data, selected_city, year_range)

pages = [
    "Overview Dashboard",
    "Experiment 1 — OOP Fundamentals",
    "Experiment 2 — Constructors & Lists",
    "Experiment 3 — Strings & Inheritance",
    "Experiment 4 — Abstraction & Polymorphism",
    "Experiment 5 — Exceptions & Multithreading",
    "Experiment 6 — Collections & Functional Programming",
    "Experiment 7 — Tkinter GUI Drawing",
    "Experiment 8 — SQLite Database",
]
page = st.sidebar.radio("Navigate", pages)
st.sidebar.divider()
st.sidebar.caption("Dataset: 2010–2019 historical observations")
st.sidebar.caption("Not a live forecast or official alert service.")

# -------------------------------- Overview page ---------------------------------
if page == "Overview Dashboard":
    section_title("Climate Overview", "Explore historical temperature patterns and heatwave-flagged records across Indian cities.")
    st.info("This dashboard analyses historical records. It does not issue live weather forecasts or official heatwave warnings.")
    c1, c2, c3, c4 = st.columns(4)
    with c1: c1.metric("Weather records", f"{len(data):,}")
    with c2: safe_metric("Highest recorded maximum", data["max_temperature_c"].max(), "°C")
    with c3: c3.metric("Cities represented", f"{data['city'].nunique():,}")
    with c4: c4.metric("Flagged records", f"{int(data['heatwave_flag_derived'].sum()):,}")

    left, right = st.columns(2)
    with left:
        st.subheader("Maximum temperature over time")
        trend = data.dropna(subset=["date", "max_temperature_c"]).copy()
        if not trend.empty:
            trend["month"] = trend["date"].dt.to_period("M").dt.to_timestamp()
            monthly = trend.groupby("month", as_index=False)["max_temperature_c"].mean()
            fig = px.line(monthly, x="month", y="max_temperature_c", markers=True,
                          labels={"month": "Month", "max_temperature_c": "Average daily maximum (°C)"})
            fig.update_layout(margin=dict(l=10, r=10, t=25, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else: st.warning("No valid date/temperature values for this filter.")
    with right:
        st.subheader("Cities by average maximum temperature")
        city_stats = data.groupby("city", as_index=False)["max_temperature_c"].mean().nlargest(12, "max_temperature_c")
        if not city_stats.empty:
            fig = px.bar(city_stats.sort_values("max_temperature_c"), x="max_temperature_c", y="city", orientation="h",
                         labels={"city": "City", "max_temperature_c": "Average maximum (°C)"})
            fig.update_layout(margin=dict(l=10, r=10, t=25, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else: st.warning("No temperature values available.")

    left, right = st.columns(2)
    with left:
        st.subheader("Heatwave-flagged records by city")
        flagged = data.groupby("city", as_index=False)["heatwave_flag_derived"].sum().sort_values("heatwave_flag_derived", ascending=False).head(12)
        fig = px.bar(flagged, x="city", y="heatwave_flag_derived", labels={"heatwave_flag_derived": "Flagged records", "city": "City"})
        fig.update_layout(margin=dict(l=10, r=10, t=25, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Temperature vs humidity")
        if "relative_humidity_pct" in data:
            sample = data.dropna(subset=["max_temperature_c", "relative_humidity_pct"]).head(4000)
            if not sample.empty:
                fig = px.scatter(sample, x="relative_humidity_pct", y="max_temperature_c", color="heatwave_flag_derived",
                                 labels={"relative_humidity_pct": "Relative humidity (%)", "max_temperature_c": "Maximum temperature (°C)", "heatwave_flag_derived": "Flagged"},
                                 opacity=0.65)
                fig.update_layout(margin=dict(l=10, r=10, t=25, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No paired humidity and temperature values.")

    st.subheader("Recent matching observations")
    st.dataframe(data.sort_values("date", ascending=False).head(15), use_container_width=True, hide_index=True)
    st.download_button("Download filtered records as CSV", data.to_csv(index=False).encode("utf-8"), "heatwatch_filtered.csv", "text/csv")

# -------------------------- Experiment 1: class/object --------------------------
elif page == "Experiment 1 — OOP Fundamentals":
    section_title("Experiment 1 — OOP Fundamentals", "Demonstrates classes, objects, constructors, instance methods and calculated results.")
    st.markdown("**Concepts:** `WeatherRecord` is a class; a selected row becomes an object; `__init__` is its constructor; `summary()` and `temperature_range()` are instance methods.")
    candidates = data.dropna(subset=["city", "date", "max_temperature_c", "avg_temperature_c"])
    if candidates.empty:
        st.warning("No complete records available under the current filters.")
    else:
        idx = st.selectbox("Choose a weather observation", candidates.index.tolist(), format_func=lambda i: f"{candidates.loc[i, 'city']} — {candidates.loc[i, 'date'].date()}")
        row = candidates.loc[idx]
        record = WeatherRecord(row["city"], row["date"].date(), row["max_temperature_c"], row["avg_temperature_c"])
        st.success(record.summary())
        a, b = st.columns(2)
        a.metric("Max minus average", f"{record.temperature_range():.2f} °C")
        b.metric("Object class", record.__class__.__name__)
        st.code("record = WeatherRecord(city, date, max_temperature, avg_temperature)\nrecord.summary()\nrecord.temperature_range()", language="python")

# -------------------------- Experiment 2: lists/constructor ---------------------
elif page == "Experiment 2 — Constructors & Lists":
    section_title("Experiment 2 — Constructors & Lists", "Create objects from records and use lists to manage and filter observations.")
    st.markdown("Each row is converted into a `WeatherRecord` object using its constructor, then stored in a Python list.")
    limit = st.slider("Number of records to load into the demonstration list", 5, 100, 20)
    subset = data.dropna(subset=["city", "date", "max_temperature_c", "avg_temperature_c"]).head(limit)
    records = [WeatherRecord(r.city, r.date.date(), r.max_temperature_c, r.avg_temperature_c) for r in subset.itertuples()]
    threshold = st.slider("Show list objects with max temperature at least (°C)", 0, 50, 30)
    hot_records = list(filter(lambda obj: obj.max_temperature >= threshold, records))
    st.metric("Objects created", len(records))
    st.metric("Objects matching threshold", len(hot_records))
    st.dataframe(pd.DataFrame([{"City": r.city, "Date": r.date, "Maximum (°C)": r.max_temperature, "Average (°C)": r.avg_temperature} for r in hot_records]), use_container_width=True, hide_index=True)
    st.code("records = [WeatherRecord(...) for row in rows]\nhot_records = [r for r in records if r.max_temperature >= threshold]", language="python")

# ------------------------- Experiment 3: strings/inheritance --------------------
elif page == "Experiment 3 — Strings & Inheritance":
    section_title("Experiment 3 — String Handling & Inheritance", "Format text fields and use inherited report classes for different report types.")
    if "city" in data:
        raw_city = st.selectbox("Choose a city", sorted(data["city"].dropna().astype(str).unique()))
        cleaned_city = " ".join(raw_city.strip().split()).title()
        st.write("Original city string:", raw_city)
        st.write("Cleaned/display city string:", cleaned_city)
        city_data = data[data["city"].astype(str) == raw_city]
        city_report = CityReport(f"City report — {cleaned_city}")
        heat_report = HeatwaveReport(f"Heatwave report — {cleaned_city}")
        st.success(city_report.render(city_data))
        st.info(heat_report.render(city_data))
        st.caption("CityReport and HeatwaveReport inherit from ClimateReport and override its render() method.")
        st.code("class CityReport(ClimateReport):\n    def render(self, data):\n        return ...", language="python")

# ------------------------- Experiment 4: abstract/polymorphism ------------------
elif page == "Experiment 4 — Abstraction & Polymorphism":
    section_title("Experiment 4 — Abstraction & Polymorphism", "Use an abstract Analyzer interface with interchangeable analysis implementations.")
    report_choice = st.radio("Choose analyzer", ["City temperature analysis", "Heatwave-flag analysis"], horizontal=True)
    analyzer: Analyzer = CityTemperatureAnalyzer() if report_choice == "City temperature analysis" else HeatwaveCityAnalyzer()
    result = analyzer.analyze(data)
    st.write(f"Active implementation: `{analyzer.__class__.__name__}`")
    st.dataframe(result, use_container_width=True, hide_index=True)
    if not result.empty:
        value_col = "highest_max" if "highest_max" in result.columns else "flagged_records"
        fig = px.bar(result.head(15).sort_values(value_col), x=value_col, y="city", orientation="h",
                     labels={value_col: value_col.replace("_", " ").title(), "city": "City"})
        st.plotly_chart(fig, use_container_width=True)
    st.caption("Polymorphism: the same analyze(data) call behaves differently depending on the concrete analyzer object.")

# ------------------------- Experiment 5: errors/modules/threads -----------------
elif page == "Experiment 5 — Exceptions & Multithreading":
    section_title("Experiment 5 — Exception Handling, Modules & Multithreading", "Explore safe input validation and a background analysis task.")
    st.markdown("In the complete application, data handling, report classes and database operations are separated into functions/classes (modules can be split into files later).")
    threshold_text = st.text_input("Enter a maximum-temperature threshold", "35")
    if st.button("Validate and analyse"):
        try:
            threshold = float(threshold_text)
            if not -20 <= threshold <= 60:
                raise ValueError("Enter a threshold between -20°C and 60°C.")
            matches = data[data["max_temperature_c"] >= threshold]
            st.success(f"Found {len(matches):,} records with maximum temperature ≥ {threshold:.1f}°C.")
            st.dataframe(matches.head(100), use_container_width=True, hide_index=True)
        except ValueError as exc:
            st.error(f"Invalid input: {exc}")
        except Exception as exc:
            st.error(f"Unexpected processing error: {exc}")

    st.subheader("Background task demonstration")
    if st.button("Run a background record count"):
        result_box: dict[str, int] = {}
        errors: list[str] = []
        def worker() -> None:
            try:
                result_box["count"] = int(data["heatwave_flag_derived"].sum())
            except Exception as err:
                errors.append(str(err))
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=5)
        if thread.is_alive(): st.warning("The task is still running; try again shortly.")
        elif errors: st.error(errors[0])
        else: st.success(f"Background thread completed. Flagged records in filtered data: {result_box.get('count', 0)}")
    st.caption("This short demo illustrates Thread creation and exception handling. A full production app would use a task queue or cached background worker for long jobs.")

# ---------------------- Experiment 6: collections/functions ---------------------
elif page == "Experiment 6 — Collections & Functional Programming":
    section_title("Experiment 6 — Collections & Functional Programming", "Use dictionaries, sets, tuples, filter(), map() and sorted() on climate observations.")
    city_counts = data["city"].value_counts().to_dict()  # dictionary
    unique_states = set(data["state"].dropna().astype(str)) if "state" in data else set()  # set
    date_span = (str(data["date"].min().date()), str(data["date"].max().date())) if not data.empty and data["date"].notna().any() else ("N/A", "N/A")  # tuple
    a, b, c = st.columns(3)
    a.metric("Unique states", len(unique_states))
    b.metric("Unique cities", data["city"].nunique())
    c.metric("Records", f"{len(data):,}")
    st.write("Date span stored as a tuple:", date_span)
    st.subheader("City counts from a dictionary")
    st.dataframe(pd.DataFrame(city_counts.items(), columns=["City", "Record count"]).sort_values("Record count", ascending=False), use_container_width=True, hide_index=True)
    st.subheader("Functional filter: hottest observations")
    top_n = st.slider("Number of records to show", 5, 30, 10)
    hot = list(filter(lambda row: pd.notna(row[1]), enumerate(data["max_temperature_c"].tolist())))
    hot_sorted = sorted(hot, key=lambda pair: pair[1], reverse=True)[:top_n]
    mapped = list(map(lambda pair: {"Row index": pair[0], "Maximum temperature (°C)": pair[1]}, hot_sorted))
    st.dataframe(pd.DataFrame(mapped), use_container_width=True, hide_index=True)
    st.caption("filter() selects valid temperature values; sorted() ranks them; map() transforms tuples into display dictionaries.")

# ------------------------------ Experiment 7: Tkinter ----------------------------
elif page == "Experiment 7 — Tkinter GUI Drawing":
    section_title("Experiment 7 — GUI Applications & Geometric Shapes", "A real Tkinter Canvas demo draws geometric shapes representing temperature ranges.")
    st.warning("Tkinter opens a separate desktop window, so it must be launched as a separate Python program rather than inside the Streamlit browser page.")
    st.markdown("**How to run:** stop or leave Streamlit running, open a second terminal in the project folder, and execute:")
    st.code("python tkinter_demo.py", language="bash")
    st.markdown("The demo uses a Tkinter Canvas to draw a circle, rectangle and temperature bar. It also lets you enter a temperature and redraw the indicator.")
    st.subheader("Concept preview")
    temperature = st.slider("Preview temperature (°C)", 0, 50, 35, key="tk_preview_temp")
    st.write(f"Selected temperature: **{temperature}°C**")
    st.progress(min(temperature / 50, 1.0), text="Temperature scale preview (0–50°C)")
    st.caption("The Streamlit preview is illustrative; the actual geometric drawing is performed by Tkinter in tkinter_demo.py.")

# ------------------------------- Experiment 8: SQLite ----------------------------
elif page == "Experiment 8 — SQLite Database":
    section_title("Experiment 8 — Database-Driven System Using SQLite", "The CSV is imported into a local SQLite database and this page reads results using SQL.")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
            columns = pd.read_sql_query(f"PRAGMA table_info({TABLE_NAME})", conn)
        a, b = st.columns(2)
        a.metric("Rows stored in SQLite", f"{count:,}")
        b.metric("Database columns", len(columns))
        st.subheader("SQL: top cities by average maximum temperature")
        sql = f"""SELECT city, COUNT(*) AS record_count,
                         ROUND(AVG(max_temperature_c), 2) AS average_max_c,
                         ROUND(MAX(max_temperature_c), 2) AS highest_max_c
                  FROM {TABLE_NAME}
                  WHERE city IS NOT NULL
                  GROUP BY city
                  ORDER BY average_max_c DESC
                  LIMIT 16"""
        st.dataframe(query_sqlite(sql), use_container_width=True, hide_index=True)
        st.subheader("Run a safe, parameterised city query")
        sql_city = st.selectbox("City to query", ["All cities"] + cities, key="sql_city")
        if sql_city == "All cities":
            result = query_sqlite(f"SELECT * FROM {TABLE_NAME} ORDER BY date DESC LIMIT 100")
        else:
            result = query_sqlite(f"SELECT * FROM {TABLE_NAME} WHERE city = ? ORDER BY date DESC LIMIT 100", (sql_city,))
        st.dataframe(result, use_container_width=True, hide_index=True)
        with st.expander("View database schema"):
            st.dataframe(columns, use_container_width=True, hide_index=True)
        st.caption(f"Database file: {DB_PATH.name}. It is created automatically when the app starts.")
    except sqlite3.Error as exc:
        st.error(f"SQLite error: {exc}")

st.sidebar.divider()
st.sidebar.caption("India HeatWatch • Python Mini-Project")
