import numpy as np
import pytest
import xarray as xr
from ocean_plot.data import geographic, crop, select, celsius, wind_components


@pytest.fixture
def dataset():
    return xr.Dataset({"sst": (("time", "depth", "lat", "lon"), np.arange(24.).reshape(2, 2, 2, 3), {"units": "K"})}, coords={"time": np.array(["2025-01-01", "2025-01-02"], dtype="datetime64[D]"), "depth": [0, 10], "lat": [40, 30], "lon": [240, 241, 242]})


def test_geographic_reorders_values_and_normalizes_longitude(dataset):
    ds, lon, lat = geographic(dataset)
    np.testing.assert_array_equal(ds[lon], [-120, -119, -118])
    np.testing.assert_array_equal(ds[lat], [30, 40])
    assert ds.sst.isel(time=0, depth=0, lat=0, lon=0).item() == 3


def test_selection_is_explicit(dataset):
    with pytest.raises(ValueError, match="Select time explicitly"):
        select(dataset.sst, ("lat", "lon"))
    with pytest.raises(ValueError, match="Select depth explicitly"):
        select(dataset.sst, ("lat", "lon"), time_index=0)
    result = select(dataset.sst, ("lat", "lon"), time="2025-01-02", depth=10)
    assert result.dims == ("lat", "lon")
    assert result[0, 0].item() == 18
    with pytest.raises(ValueError, match="multiple records"):
        select(dataset.sst, ("lat", "lon"), time="2025-01", depth=0)


def test_unknown_extra_dimension_not_averaged(dataset):
    da = dataset.sst.isel(time=0, depth=0).expand_dims(member=[0, 1])
    with pytest.raises(ValueError, match="extra dimensions"):
        select(da, ("lat", "lon"))


def test_celsius_conversion_preserves_missing():
    da = xr.DataArray([273.15, np.nan, 283.15], attrs={"units": "Kelvin"}, name="sst")
    result = celsius(da)
    np.testing.assert_allclose(result, [0, np.nan, 10], atol=1e-10)
    assert result.name == "sst" and result.attrs["units"] == "degC"
    da.attrs["units"] = "Celsius"
    np.testing.assert_allclose(celsius(da), da)
    da.attrs["units"] = "unknown"
    with pytest.raises(ValueError, match="Unknown temperature"):
        celsius(da)


def test_crop_empty_and_dateline_rejected(dataset):
    ds, lon, lat = geographic(dataset)
    with pytest.raises(ValueError, match="Empty spatial crop"):
        crop(ds, lon, lat, [0, 10, 0, 10])
    with pytest.raises(ValueError, match="split dateline"):
        crop(ds, lon, lat, [170, -170, 0, 10])


def test_bad_geographic_grid(dataset):
    dataset["crs"] = xr.DataArray(0, attrs={"grid_mapping_name": "rotated_latitude_longitude"})
    with pytest.raises(ValueError, match="Rotated"):
        geographic(dataset)
    ds = xr.Dataset(coords={"lon": (("y", "x"), [[1, 2]]), "lat": (("y", "x"), [[3, 4]])})
    with pytest.raises(ValueError, match="1D"):
        geographic(ds)
    ds = xr.Dataset(coords={"lat": [30, 40], "lon": [0, 360]})
    with pytest.raises(ValueError, match="Duplicate"):
        geographic(ds)


def test_wind_rejects_unit_coordinate_and_orientation_errors():
    u = xr.DataArray([3., 3.], dims="lon", coords={"lon": [1, 2]}, attrs={"units": "m s-1", "standard_name": "eastward_wind"})
    v = u.copy()
    v.attrs = {"units": "m/s", "standard_name": "northward_wind"}
    uu, vv = wind_components(u, v)
    np.testing.assert_allclose(np.hypot(uu, vv), np.sqrt(18))
    with pytest.raises(ValueError, match="coordinates"):
        wind_components(u, v.assign_coords(lon=[2, 3]))
    v.attrs["units"] = "knots"
    with pytest.raises(ValueError, match="requires m/s"):
        wind_components(u, v)
    v.attrs = {"units": "m/s", "standard_name": "grid_northward_wind"}
    with pytest.raises(ValueError, match="geographic"):
        wind_components(u, v)


def test_empty_or_nonnumeric_selection_is_rejected(dataset):
    with pytest.raises(ValueError, match="empty dimension"):
        select(dataset.sst.isel(time=slice(0, 0), depth=0), ("lat", "lon"), keep_time=True)
    with pytest.raises(ValueError, match="numeric"):
        select(xr.DataArray([["bad"]], dims=("lat", "lon")), ("lat", "lon"))


def test_annotation_reports_source_time_and_synthetic_label(dataset):
    from ocean_plot.plotting import annotation
    da = dataset.sst.isel(time=0, depth=0)
    da.attrs["synthetic"] = True
    label = annotation(da)
    assert "SYNTHETIC - not observations" in label
    assert "2025-01-01 00:00:00" in label
    assert ".000000000" not in label
