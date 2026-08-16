# XML Bridge

XML Bridge converts early-music score data between a project-specific CMME XML model, MEI XML, and JSON. The repository includes a Flask web interface, an HTTP API, validators, sample scores, dataset tools, and conversion evaluation tools.

## Supported conversions

The standard converter supports these paths:

| Source | Targets |
| --- | --- |
| CMME | MEI, JSON |
| MEI | CMME, JSON |
| JSON | CMME, MEI |

The converter handles metadata, parts or staves, measures, notes, rests, chords, clefs, key signatures, time or mensuration data, and selected early-music attributes.

## Project scope

This project is a research prototype. Keep the source file when you convert scholarly data, and review the generated file before you use it.

- CMME support covers the XML structure and features used by this repository. It is not a complete implementation of every CMME feature.
- MEI support uses the project validator unless you supply a schema to the parser. The repository does not include an official MEI schema.
- JSON input uses a top-level `metadata` object and `parts` array. Each part must contain an `id` or `name` and a `measures` array.
- Interactive conversion and conversion-quality scores are experimental. The quality score is a project heuristic, not an independent proof of semantic equivalence.

## Requirements

- Python 3.10 or later
- `pip`

The dependency versions are in `requirements.txt`.

## Installation

Clone the repository and enter its directory:

```bash
git clone https://github.com/Shetta/XML-Bridge.git
cd XML-Bridge
```

Create and activate a virtual environment on Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies and start the application:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open <http://localhost:8000>. Set the `PORT` environment variable to use a different port. Set `DEBUG=true` only for local development.

## Use the API

The `/transform` endpoint accepts a multipart file upload. The `type` query parameter uses the form `source-to-target`.

```bash
curl -sS -X POST \
  -F "file=@samples/basic/cmme/basic_example.cmme" \
  "http://localhost:8000/transform?type=cmme-to-mei" \
  > response.json
```

The endpoint returns a JSON object. On success, the converted document is in the `result` field:

```json
{
  "status": "success",
  "result": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>..."
}
```

Other main endpoints include:

- `POST /validate?type=cmme|mei|json`
- `POST /metadata?type=cmme|mei|json`
- `POST /evaluate/conversion?source_format=...&target_format=...`

## Run the tests

Run all tests with the standard-library test runner:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the same command on Python 3.10 and 3.12 for pushes and pull requests.

## Repository layout

- `app.py`: Flask application and API routes
- `backend/`: parsers, converters, validation, evaluation, and data management
- `templates/` and `static/`: web interface
- `samples/`: example CMME, MEI, and JSON files
- `tests/`: automated tests

## Contributing

Contributions are welcome. Useful areas include broader MEI and CMME coverage, schema-backed validation, round-trip property tests, clearer interactive decisions, and more representative public-domain fixtures.

Before you submit a change, run the full test command and describe any notation feature that the change can add, remove, or reinterpret.

## Citation

If you use this project in research, cite:

> XML Bridge: A Tool for Converting Early Music Notation Between Formats. <https://github.com/Shetta/XML-Bridge>

## License

XML Bridge is available under the [MIT License](LICENSE).

## Acknowledgments

This project draws on the work of the Music Encoding Initiative community, the Computerized Mensural Music Editing project, and researchers and practitioners in early-music notation.
