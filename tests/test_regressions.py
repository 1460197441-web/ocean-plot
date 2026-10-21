"""Scientific regressions from review: dateline domains, units and CSV precision."""
import csv
import numpy as np
import pytest
import xarray as xr
from ocean_plot.cli import main
from ocean_plot.data import geographic, celsius
from ocean_plot.plotting import series


@pytest.mark.parametrize("longitudes", [
    np.arange(170., 191.),
    np.r_[np.arange(-180., -169.), np.arange(170., 180.)],
    [170., 190.], [-170., 170.], np.arange(80., 281.),
])
def test_dateline_domains_rejected_in_either_convention(longitudes):
    ds = xr.Dataset(coords={"lon": longitudes, "lat": [30., 31.]})
    with pytest.raises(ValueError, match="split dateline regions"):
        geographic(ds)


@pytest.mark.parametrize("longitudes", [
    np.arange(360.), np.arange(-180., 180.), [240., 241., 242.],
    [0., 1., 2., 20.], [0., 45., 100., 180., 270.],
])
def test_supported_longitude_domains_keep_values(longitudes):
    ds = xr.Dataset({"marker": ("lon", np.asarray(longitudes))},
                    coords={"lon": longitudes, "lat": [31., 30.]})
    result, lon, lat = geographic(ds)
    np.testing.assert_allclose((result.marker.values + 180) % 360 - 180, result[lon])
    np.testing.assert_array_equal(result[lat], [30., 31.])


@pytest.mark.parametrize("units,expected", [
    ("degrees Celsius", 273.15), ("degree Celsius", 273.15),
    ("degrees_celsius", 273.15), ("kelvins", 0.),
    (" Degrees Kelvin ", 0.), ("K", 0.),
])
def test_temperature_unit_spellings(units, expected):
    value = xr.DataArray([273.15, np.nan], attrs={"units": units})
    np.testing.assert_allclose(celsius(value), [expected, np.nan], atol=1e-10)


@pytest.mark.parametrize("lon_units,lat_units", [
    ("degrees", "degrees"), ("degrees east", "degrees north"),
    (" DEGREES_EAST ", " Degrees North "),
])
def test_geographic_unit_spellings(lon_units, lat_units):
    ds = xr.Dataset(coords={"lon": [120., 121.], "lat": [30., 31.]})
    ds.lon.attrs["units"], ds.lat.attrs["units"] = lon_units, lat_units
    geographic(ds)


@pytest.mark.parametrize("coordinate,unit", [
    ("lon", "radians"), ("lon", "degrees north"), ("lat", "degrees east"),
])
def test_geographic_units_still_validate_direction(coordinate, unit):
    ds = xr.Dataset(coords={"lon": [120., 121.], "lat": [30., 31.]})
    ds[coordinate].attrs["units"] = unit
    with pytest.raises(ValueError, match="units must be geographic degrees"):
        geographic(ds)


@pytest.mark.parametrize("command,extra", [
    ("sst", []), ("sst", ["--cartopy"]),
    ("wind", []), ("wind", ["--cartopy"]),
    ("timeseries", ["--point", "175", "30"]),
])
def test_dateline_cli_fails_before_creating_outputs(tmp_path, capsys, command, extra):
    longitude = np.arange(170., 191.)
    values = np.ones((2, longitude.size))
    ds = xr.Dataset({
        "sst": (("lat", "lon"), values, {"units": "degrees Celsius"}),
        "uwnd": (("lat", "lon"), values, {"units": "m s**-1"}),
        "vwnd": (("lat", "lon"), values, {"units": "m s**-1"}),
    }, coords={"lon": longitude, "lat": [30., 31.]})
    path, output = tmp_path / "pacific.nc", tmp_path / "plot.png"
    ds.to_netcdf(path, engine="scipy")
    assert main([command, str(path), "--output", str(output), *extra]) == 2
    assert "split dateline regions" in capsys.readouterr().err
    assert not output.exists() and not output.with_suffix(".csv").exists()


def test_csv_time_is_readable_without_losing_subseconds(tmp_path):
    stamps = np.array(["2025-01-01T00:00:00.000000000", "2025-01-02T00:00:00.123400001"], dtype="datetime64[ns]")
    ds = xr.Dataset({"sst": (("time", "lat", "lon"), np.ones((2, 1, 1)), {"units": "degrees Celsius"})},
                    coords={"time": stamps, "lat": [30.], "lon": [120.]})
    output = tmp_path / "point.png"
    # NetCDF3 cannot represent nanosecond int64 timestamps. Exercise the CSV
    # writer directly to keep this precision test independent of NetCDF4.
    series(ds.sst.sel(lat=30., lon=120.), "lon", "lat", output, output.with_suffix(".csv"), "degC")
    rows = list(csv.DictReader(output.with_suffix(".csv").open()))
    assert rows[0]["time"] == "2025-01-01T00:00:00"
    assert rows[1]["time"] == "2025-01-02T00:00:00.123400001"
    np.testing.assert_array_equal(np.array([r["time"] for r in rows], dtype="datetime64[ns]"), stamps)
