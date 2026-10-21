# ocean-plot

[![CI](https://github.com/1460197441-web/ocean-plot/actions/workflows/ci.yml/badge.svg)](https://github.com/1460197441-web/ocean-plot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/1460197441-web/ocean-plot/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/1460197441-web/ocean-plot/blob/main/LICENSE)

[中文](https://github.com/1460197441-web/ocean-plot/blob/main/README.md) · [Downloads](https://github.com/1460197441-web/ocean-plot/releases) · [Report a problem](https://github.com/1460197441-web/ocean-plot/issues)

**Ocean NetCDF plotting from the command line: SST maps, wind vectors and point time series, powered by xarray.**

A small Python CLI for students and researchers who need repeatable figures from rectilinear ocean datasets. Tested with local NOAA OISST and RSS CCMP subsets; includes an offline synthetic demo. It preserves missing values, requires explicit selection of multiple time/depth records, and rejects unsupported grids.

![NOAA OISST subset: Yellow Sea, January 1, 2025](https://raw.githubusercontent.com/1460197441-web/ocean-plot/v0.1.0/examples/gallery/oisst_20250101.png)

## Install and try

Requires Python 3.10+. Use a virtual environment.

```sh
python -m pip install "ocean-plot[netcdf4,maps] @ https://github.com/1460197441-web/ocean-plot/releases/download/v0.1.0/ocean_plot-0.1.0-py3-none-any.whl"
ocean-plot demo --output-dir demo
```

The demo requires no network or observational data. Its figures are explicitly marked **SYNTHETIC — not observations**. GitHub Releases are available; **the package is not yet on PyPI**.

Development install:

```sh
python -m pip install "git+https://github.com/1460197441-web/ocean-plot.git"
```

The basic installation uses SciPy for NetCDF3. Add `netCDF4` for NetCDF4/HDF5 and `cartopy` for coastlines, or use the extras in the release installation above.

## Your own data

```sh
ocean-plot inspect input.nc
ocean-plot sst oisst.nc --time-index 0 --bbox 118 126 30 40 --cartopy --output sst.png
ocean-plot wind ccmp.nc --time-index 0 --u uwnd --v vwnd --cartopy --output wind.pdf
ocean-plot timeseries oisst.nc --point 124 35 --output point.png --csv point.csv
```

- Recognizes common latitude/longitude, SST, and wind variable names; explicit overrides are available.
- Converts known Kelvin units to Celsius and validates geographic wind components in m/s. Arrows show where the wind blows **toward**, with a reference vector.
- Exports PNG/PDF at 300 dpi and CSV with actual selected coordinates and unrounded numeric values.
- Missing values stay missing. The tool does not interpolate or silently average extra dimensions.

![RSS CCMP wind subset: January 20, 2024](https://raw.githubusercontent.com/1460197441-web/ocean-plot/v0.1.0/examples/gallery/ccmp_20240120.png)

## Scope and limitations

Only 1D rectilinear geographic coordinates are supported. Reversed latitude and ordinary 0–360 longitude grids are reordered with their data. Dateline-crossing regional domains that become discontinuous are rejected before plotting; split the input first. A conservative gap check can also reject strongly irregular global grids. Curvilinear, staggered and rotated grids are unsupported.

Default output is a latitude/longitude coordinate plot without a coastline. `--cartopy` adds Natural Earth 50m coastlines and a visual land overlay; its first use downloads map data. The overlay does not change source values or replace the product's land mask.

Time series use the nearest in-range grid cell and support standard NumPy datetime calendars. NaN observations break the line; entirely absent timestamps do not. No sampling frequency is inferred and no dates are manufactured. See the [Chinese reference](https://github.com/1460197441-web/ocean-plot/blob/main/README.md) for full selection and validation rules.

## Development and feedback

```sh
python -m pip install -e ".[dev,netcdf4]"
pytest
python -m build
```

CI tests Python 3.10, 3.12 and 3.13. The current suite includes 42 tests covering scientific and CLI regressions.

If it helps your work, a Star or a reproducible issue is welcome. Include dataset/product metadata, coordinate names, units and the exact command; do not upload private data. [Contributions](https://github.com/1460197441-web/ocean-plot/blob/main/CONTRIBUTING.md) are welcome.

MIT applies to the code. External datasets retain their own licenses and attribution requirements.
