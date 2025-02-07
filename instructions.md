Here are several example commands you can run from the terminal (assuming your YAML config is saved as `config.yaml`):

List all available datasets:
```bash
python downloader.py --config config.yaml --list
```

Download and preview five rows of the basic granted patent table:
```bash
python downloader.py --config config.yaml --section granted --subset minimal --table g_patent --nrows 5
```

Download and save the granted patent table to disk:
```bash
python downloader.py --config config.yaml --section granted --subset minimal --table g_patent --save g_patent.tsv.zip
```

Download and preview the brief summary text for granted patents from the year 2000:
```bash
python downloader.py --config config.yaml --section granted --subset brief_summary --table 2000 --nrows 5
```

Download and save a pre-grant publication table:
```bash
python downloader.py --config config.yaml --section pre-grant --subset minimal --table pg_published_application --save pg_published_application.tsv.zip
```

Each command uses the configuration to construct the proper URL and then either prints a preview with Pandas (using `--nrows`) or saves the downloaded ZIP file (using `--save`). Feel free to modify the section, subset, or table values according to your needs.
