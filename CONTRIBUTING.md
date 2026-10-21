# Contributing

Small, reproducible improvements are welcome: compatibility fixes, documented examples, clearer errors and scientific-correctness tests.

Before a change, open an issue describing the use case or bug. For bugs include the product/version, relevant variable and coordinate metadata, exact command, expected result and error message. Use a small synthetic reproduction where possible; do not attach credentials or private datasets.

Use a branch, keep the change focused, and run:

```sh
python -m pip install -e ".[dev,netcdf4]"
pytest
python -m build
```

Explain scientific assumptions and limitations. Never fill missing values or silently choose a time/depth record to make a figure look complete. Changes to coordinate handling, units or exports need regression tests. Please disclose if an example is synthetic.

By contributing code, you agree it may be distributed under the repository's MIT license. External data and map assets retain their own terms.
