# India HeatWatch

A Python mini-project that analyses historical Indian weather observations and demonstrates eight lab topics using Streamlit, SQLite, pandas, Plotly and Tkinter.

## Files
- `app.py` — Streamlit dashboard with overview and eight experiment pages.
- `tkinter_demo.py` — standalone Tkinter Canvas demo for Experiment 7 (geometric shapes).
- `india_heatwave_climate_dataset_50000.csv` — source dataset.
- `heatwatch.db` — generated automatically on first app run.

## Run on Windows
1. Install Python 3.10 or newer.
2. Open Command Prompt in this folder.
3. (Recommended) create and activate a virtual environment:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```bat
   python -m pip install -r requirements.txt
   ```
5. Start the dashboard:
   ```bat
   python -m streamlit run app.py
   ```
6. To demonstrate Experiment 7, open a second terminal in this folder and run:
   ```bat
   python tkinter_demo.py
   ```

The app expects the CSV to be in the same folder as `app.py`. You can also upload a CSV through the sidebar. The local SQLite database is recreated from the currently loaded CSV at startup when necessary.

## The eight experiments
1. Classes, objects, constructors and methods: `WeatherRecord`.
2. Constructors and lists: create a list of `WeatherRecord` instances and filter them.
3. String handling and inheritance: clean city labels and use `CityReport` / `HeatwaveReport` derived classes.
4. Abstract classes and polymorphism: `Analyzer` with two implementations.
5. Exception handling, modules and multithreading: validated threshold input and a thread-based demonstration. This single-file version separates responsibilities into functions/classes; it can be split into modules if your course requires separate `.py` modules.
6. Collections and functional programming: dictionaries, sets, tuples, `filter`, `map` and `sorted`.
7. GUI geometric drawing: `tkinter_demo.py` draws rectangles, an oval and labels on a Canvas.
8. SQLite: imports data into `weather_records`, uses SQL aggregation and parameterised city queries.

## Notes
- The dataset covers historical observations; this app does not provide live forecasts or official heatwave alerts.
- Heatwave labels are provided by the dataset. They are not independently validated by this application.
- Missing severity values are retained as missing, not treated as a severity class.
- Tkinter opens a desktop window and therefore runs separately from Streamlit.
