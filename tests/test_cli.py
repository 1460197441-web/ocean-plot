import csv
import numpy as np
import xarray as xr
from ocean_plot.cli import main


def source(tmp_path, **kwargs):
    values = np.array([[[273.15, 274.15], [275.15, 276.15]], [[np.nan, 278.15], [279.15, 280.15]]])
    ds = xr.Dataset({"sst": (("time", "lat", "lon"), values, {"units": "K"})}, coords={"time": np.array(["2025-01-01", "2025-01-02"], dtype="datetime64[D]"), "lat": [30., 31.], "lon": [120., 121.]})
    if kwargs.get("missing"):
        ds.sst.values[:] = np.nan
    if kwargs.get("bad_units"):
        ds.sst.attrs["units"] = "unknown"
    path = tmp_path / "input.nc"
    ds.to_netcdf(path, engine="scipy")
    return str(path)


def test_timeseries_actual_point_and_missing_csv(tmp_path):
    path = source(tmp_path)
    output = tmp_path / "point.png"
    assert main(["timeseries", path, "--point", "120.1", "30.1", "--output", str(output)]) == 0
    rows = list(csv.DictReader(output.with_suffix(".csv").open()))
    assert rows[0]["latitude"] == "30.0" and rows[0]["longitude"] == "120.0"
    assert float(rows[0]["value"]) == 0
    assert rows[1]["value"] == ""
    assert output.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_cli_failures_are_clear(tmp_path, capsys):
    path = source(tmp_path)
    base = ["sst", path, "--output", str(tmp_path / "bad.png")]
    assert main(base) == 2
    assert "Select time explicitly" in capsys.readouterr().err
    assert main(base + ["--time-index", "0", "--bbox", "0", "1", "0", "1"]) == 2
    assert "Empty spatial crop" in capsys.readouterr().err
    assert main(["timeseries", path, "--point", "0", "0", "--output", str(tmp_path / "bad.png")]) == 2
    assert "outside coordinate range" in capsys.readouterr().err
    path = source(tmp_path, bad_units=True)
    assert main(["sst", path, "--time-index", "0", "--output", str(tmp_path / "bad.png")]) == 2
    assert "Unknown temperature" in capsys.readouterr().err
    path = source(tmp_path, missing=True)
    assert main(["sst", path, "--time-index", "0", "--output", str(tmp_path / "bad.png")]) == 2
    assert "no finite observations" in capsys.readouterr().err
    assert not (tmp_path / "bad.png").exists()


def test_demo_offline_png_pdf_csv_and_no_filled_gap(tmp_path):
    assert main(["demo", "--output-dir", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("*.png"))) == 3
    assert (tmp_path / "synthetic_sst.pdf").read_bytes().startswith(b"%PDF")
    rows = list(csv.DictReader((tmp_path / "synthetic_timeseries.csv").open()))
    assert len(rows) == 31 and sum(r["value"] == "" for r in rows) == 3
    with xr.open_dataset(tmp_path / "synthetic.nc") as ds:
        assert "SYNTHETIC" in ds.attrs["title"]


def test_inspect_and_single_cell_map(tmp_path, capsys):
    path = source(tmp_path)
    assert main(["inspect", path]) == 0
    assert "units" in capsys.readouterr().out
    assert main(["sst", path, "--time-index", "0", "--bbox", "119.9", "120.1", "29.9", "30.1", "--output", str(tmp_path / "one.png")]) == 0


def test_output_paths_checked_before_writing(tmp_path, capsys):
    path = source(tmp_path)
    before = (tmp_path / "input.nc").read_bytes()
    base = ["timeseries", path, "--point", "120", "30"]
    assert main(base + ["--output", str(tmp_path / "bad.svg")]) == 2
    assert not (tmp_path / "bad.csv").exists()
    assert main(base + ["--output", str(tmp_path / "point.png"), "--csv", path]) == 2
    assert (tmp_path / "input.nc").read_bytes() == before
    assert not (tmp_path / "point.png").exists()
