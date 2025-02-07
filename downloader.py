#!/usr/bin/env python3
"""
CLI interface for downloading PatentsView datasets.
Usage examples:
  # List available datasets:
  $ python downloader.py --list

  # Download and preview 5 rows of the g_patent table from the granted/minimal section:
  $ python downloader.py --section granted --subset minimal --table g_patent --nrows 5

  # Download the file and save it to disk:
  $ python downloader.py --section granted --subset minimal --table g_patent --save g_patent.tsv.zip
"""

import argparse
import logging
import sys

import pandas as pd
import requests
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class DownloaderError(Exception):
    """Custom exception for downloader errors."""
    pass


class Downloader:
    """
    Downloads datasets by constructing URLs from a YAML configuration.
    """

    def __init__(self, config):
        """
        Args:
            config (dict): Parsed YAML configuration.
        """
        self.config = config

    def list_datasets(self):
        """
        Print available sections, subsets, and their tables.
        """
        for section, subsets in self.config.items():
            print(f"Section: {section}")
            for subset, details in subsets.items():
                tables = details.get("tables", [])
                print(f"  Subset: {subset}")
                print("    Tables:", ", ".join(str(t) for t in tables))
            print()

    def get_url(self, section, subset, table):
        """
        Construct the download URL for the specified section/subset/table.

        Args:
            section (str): Top-level section (e.g., "granted").
            subset (str): Subsection (e.g., "minimal", "downloads").
            table (str): Table identifier.

        Returns:
            str: Fully constructed URL.

        Raises:
            DownloaderError: If the section, subset, or table is invalid.
        """
        if section not in self.config:
            raise DownloaderError(f"Section '{section}' not found.")
        if subset not in self.config[section]:
            raise DownloaderError(f"Subset '{subset}' not found in section '{section}'.")
        details = self.config[section][subset]
        allowed_tables = {str(t) for t in details.get("tables", [])}
        if str(table) not in allowed_tables:
            raise DownloaderError(
                f"Table '{table}' not allowed. Allowed tables: {', '.join(sorted(allowed_tables))}"
            )
        database = details["database"]
        url = details["url_template"].format(database=database, table=table)
        return url

    def download_to_file(self, url, output_path):
        """
        Download file from the URL and save it locally.

        Args:
            url (str): URL to download.
            output_path (str): Path to save the file.

        Raises:
            DownloaderError: If the download fails.
        """
        logging.info(f"Downloading from {url}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(output_path, "wb") as f_out:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f_out.write(chunk)
            logging.info(f"Saved file to {output_path}")
        except Exception as exc:
            raise DownloaderError(f"Error downloading file: {exc}") from exc

    def load_data(self, url, nrows=None):
        """
        Load the dataset into a Pandas DataFrame.

        Args:
            url (str): URL to download.
            nrows (int, optional): Number of rows to read (for preview).

        Returns:
            pandas.DataFrame: The loaded data.

        Raises:
            DownloaderError: If Pandas fails to load the data.
        """
        logging.info(f"Loading data from {url}")
        try:
            df = pd.read_csv(
                url,
                delimiter="\t",
                dtype=str,
                nrows=nrows,
                compression="zip"
            )
            return df
        except Exception as exc:
            raise DownloaderError(f"Error reading data with pandas: {exc}") from exc


def load_config(config_path):
    """
    Load YAML configuration from a file.

    Args:
        config_path (str): Path to the YAML config file.

    Returns:
        dict: The configuration dictionary.

    Raises:
        DownloaderError: If the config file cannot be loaded.
    """
    try:
        with open(config_path, "r") as f_in:
            config = yaml.safe_load(f_in)
        return config
    except Exception as exc:
        raise DownloaderError(f"Error loading config file: {exc}") from exc


def parse_arguments():
    """
    Parse CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="CLI interface for downloading PatentsView datasets."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file (default: config.yaml)."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available sections, subsets, and tables from the config."
    )
    parser.add_argument(
        "--section",
        type=str,
        help="Section name (e.g., 'granted' or 'pre-grant')."
    )
    parser.add_argument(
        "--subset",
        type=str,
        help="Subset name (e.g., 'minimal', 'downloads', etc.)."
    )
    parser.add_argument(
        "--table",
        type=str,
        help="Table name or identifier."
    )
    parser.add_argument(
        "--nrows",
        type=int,
        default=None,
        help="Number of rows to preview (for pandas)."
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="If provided, save the downloaded file to this path."
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    try:
        config = load_config(args.config)
    except DownloaderError as err:
        logging.error(err)
        sys.exit(1)

    downloader = Downloader(config)

    if args.list:
        downloader.list_datasets()
        sys.exit(0)

    if not (args.section and args.subset and args.table):
        logging.error("Please provide --section, --subset, and --table arguments (or use --list).")
        sys.exit(1)

    try:
        url = downloader.get_url(args.section, args.subset, args.table)
    except DownloaderError as err:
        logging.error(err)
        sys.exit(1)

    if args.save:
        try:
            downloader.download_to_file(url, args.save)
        except DownloaderError as err:
            logging.error(err)
            sys.exit(1)
    else:
        try:
            df = downloader.load_data(url, nrows=args.nrows)
            print("Data preview:")
            print(df.head() if args.nrows is None else df)
        except DownloaderError as err:
            logging.error(err)
            sys.exit(1)


if __name__ == "__main__":
    main()

