#!/usr/bin/env python3
"""
Flask app for downloading PatentsView datasets.
Uses a YAML config (e.g., config.yaml) to build URLs.
Provides an awesome Bootstrap5 GUI.
"""

import io
import logging
import requests
import yaml
import pandas as pd

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

app = Flask(__name__)
app.secret_key = "super-secret-key"  # Change in production

CONFIG_FILE = "config.yaml"


def load_config(config_file):
    """
    Load the YAML configuration from file.
    """
    try:
        with open(config_file, "r") as f_in:
            return yaml.safe_load(f_in)
    except Exception as exc:
        raise Exception(f"Error loading config file {config_file}: {exc}") from exc


config = load_config(CONFIG_FILE)


class DownloaderError(Exception):
    """Custom exception for downloader errors."""
    pass


class Downloader:
    """
    Constructs download URLs from the config and retrieves data.
    """

    def __init__(self, config):
        self.config = config

    def list_datasets(self):
        """
        Returns the full configuration (used to populate the GUI).
        """
        return self.config

    def get_url(self, section, subset, table):
        """
        Build the download URL for the chosen section/subset/table.
        """
        if section not in self.config:
            raise DownloaderError(f"Section '{section}' not found.")
        if subset not in self.config[section]:
            raise DownloaderError(
                f"Subset '{subset}' not found in section '{section}'."
            )
        details = self.config[section][subset]
        allowed_tables = {str(t) for t in details.get("tables", [])}
        if str(table) not in allowed_tables:
            raise DownloaderError(
                f"Table '{table}' not allowed. Allowed: "
                f"{', '.join(sorted(allowed_tables))}"
            )
        database = details["database"]
        url = details["url_template"].format(database=database, table=table)
        return url

    def load_data(self, url, nrows=None):
        """
        Load data via Pandas.
        """
        df = pd.read_csv(
            url,
            delimiter="\t",
            dtype=str,
            nrows=nrows,
            compression="zip",
        )
        return df


downloader = Downloader(config)


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Render the main GUI.
    On POST, process the form and either preview or download data.
    """
    datasets = downloader.list_datasets()

    if request.method == "POST":
        section = request.form.get("section")
        subset = request.form.get("subset")
        table = request.form.get("table")
        action = request.form.get("action")
        nrows = request.form.get("nrows")

        try:
            url = downloader.get_url(section, subset, table)
        except DownloaderError as err:
            flash(str(err), "danger")
            return redirect(url_for("index"))

        if action == "preview":
            try:
                nrows_val = int(nrows) if nrows and nrows.isdigit() else None
                df = downloader.load_data(url, nrows=nrows_val)
                # Convert dataframe to HTML table with Bootstrap classes.
                html_table = df.to_html(
                    classes="table table-striped table-hover", index=False, border=0
                )
                return render_template(
                    "preview.html",
                    table_name=table,
                    url=url,
                    data=html_table,
                )
            except Exception as exc:
                flash(f"Error loading preview: {exc}", "danger")
                return redirect(url_for("index"))
        elif action == "download":
            try:
                # Download file content and send it as an attachment.
                resp = requests.get(url, stream=True)
                resp.raise_for_status()
                file_data = io.BytesIO(resp.content)
                filename = f"{table}.tsv.zip"
                return send_file(
                    file_data,
                    as_attachment=True,
                    download_name=filename,
                    mimetype="application/zip",
                )
            except Exception as exc:
                flash(f"Error downloading file: {exc}", "danger")
                return redirect(url_for("index"))
        else:
            flash("Invalid action.", "danger")
            return redirect(url_for("index"))

    return render_template("index.html", datasets=datasets)


if __name__ == "__main__":
    app.run(debug=True)

