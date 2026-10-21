"""Coordinate validation and explicit selection; never fill or average data."""
import numpy as np
import xarray as xr


ALIASES = {
    "lon": ("longitude", "lon", "LONGITUDE"),
    "lat": ("latitude", "lat", "LATITUDE"),
    "time": ("time", "TIME"),
    "depth": ("depth", "zlev", "lev", "level", "deptht"),
    "sst": ("sst", "analysed_sst", "sea_surface_temperature", "tos"),
    "u": ("uwnd", "u10", "eastward_wind", "u"),
    "v": ("vwnd", "v10", "northward_wind", "v"),
}


def normalized_unit(value):
    """Ignore spelling separators, while retaining direction and unit meaning."""
    return "".join(str(value).casefold().split()).replace("_", "")


def identify(ds, role, explicit=None, required=True):
    if explicit:
        if explicit not in ds:
            raise ValueError(f"{role}: {explicit!r} not found")
        return explicit
    matches = [name for name in ALIASES[role] if name in ds]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous {role}: {matches}; specify explicitly")
    if not matches:
        if required:
            raise ValueError(f"No {role} found; specify its name explicitly")
        return None
    return matches[0]


def geographic(ds, lon=None, lat=None):
    lon, lat = identify(ds, "lon", lon), identify(ds, "lat", lat)
    for mapping in ds.variables.values():
        if mapping.attrs.get("grid_mapping_name", "latitude_longitude") != "latitude_longitude":
            raise ValueError("Rotated/projected grids are unsupported; regrid to geographic latitude/longitude")
    for name, role in ((lon, "longitude"), (lat, "latitude")):
        coord = ds[name]
        if coord.ndim != 1 or coord.dims != (name,):
            raise ValueError(f"{role} must be a 1D dimension coordinate; curvilinear/staggered grids unsupported")
        values = np.asarray(coord.values, dtype=float)
        if not values.size or not np.isfinite(values).all():
            raise ValueError(f"Invalid {role} coordinates")
        if role == "latitude" and np.any(np.abs(values) > 90):
            raise ValueError("Latitude outside [-90, 90]")
        if role == "longitude" and np.any((values < -180) | (values > 360)):
            raise ValueError("Longitude outside supported [-180, 360] range")
        unit = normalized_unit(coord.attrs.get("units", ""))
        directional = {"degreeseast", "degreeeast", "degreese", "degreee"} if role == "longitude" else {"degreesnorth", "degreenorth", "degreesn", "degreen"}
        if unit and unit not in directional | {"degree", "degrees"}:
            raise ValueError(f"{role} units must be geographic degrees, got {unit!r}")
    attrs = ds[lon].attrs.copy()
    ds = ds.assign_coords({lon: ((ds[lon] + 180) % 360) - 180})
    ds[lon].attrs = attrs
    ds = ds.sortby(lon).sortby(lat)
    for name in (lon, lat):
        if len(np.unique(ds[name])) != ds.sizes[name]:
            raise ValueError(f"Duplicate {name} coordinates (including cyclic longitude endpoints)")
    # pcolormesh infers edges between adjacent centers. A regional Pacific
    # slice becomes two pieces after normalization: it must not bridge the
    # unobserved sector. A uniform global grid, in contrast, remains contiguous.
    longitude = np.asarray(ds[lon].values, dtype=float)
    if longitude.size > 1:
        gaps = np.diff(longitude)
        seam = 360.0 - (longitude[-1] - longitude[0])
        typical = np.median(np.append(gaps, seam))
        largest = gaps.max()
        if largest > 180.0 or (largest > 3.0 * typical and largest > seam + 1e-8):
            raise ValueError(
                "Longitude normalization leaves a dateline/discontinuous grid gap; "
                "split dateline regions into separate files before plotting. "
                "Strongly irregular global grids may also need splitting or regridding."
            )
    return ds, lon, lat


def crop(ds, lon, lat, bbox=None):
    if bbox is None:
        return ds
    west, east, south, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bbox requires -180 <= west < east <= 180 and -90 <= south < north <= 90; split dateline regions")
    ds = ds.sel({lon: slice(west, east), lat: slice(south, north)})
    if not ds.sizes[lon] or not ds.sizes[lat]:
        raise ValueError("Empty spatial crop: no grid cells in bbox")
    return ds


def select(da, spatial, time=None, time_index=None, depth=None, depth_index=None, keep_time=False):
    if not np.issubdtype(da.dtype, np.number):
        raise ValueError(f"Variable {da.name!r} must contain numeric values")
    for role, value, index in (("time", time, time_index), ("depth", depth, depth_index)):
        names = [n for n in ALIASES[role] if n in da.dims]
        if len(names) > 1:
            raise ValueError(f"Ambiguous {role} dimensions: {names}")
        if not names:
            if value is not None or index is not None:
                raise ValueError(f"Variable has no {role} dimension")
            continue
        name = names[0]
        if index is not None:
            if not 0 <= index < da.sizes[name]:
                raise ValueError(f"{role} index out of bounds")
            da = da.isel({name: index})
        elif value is not None:
            # A date string may select a range in xarray; reject non-scalar results.
            da = da.sel({name: value})
            if name in da.dims:
                if da.sizes[name] != 1:
                    raise ValueError(f"{role} selector matches multiple records; use an exact timestamp or index")
                da = da.isel({name: 0})
        elif role == "time" and keep_time:
            continue
        elif da.sizes[name] == 1:
            da = da.isel({name: 0})
        else:
            raise ValueError(f"Select {role} explicitly with --{role} or --{role}-index ({da.sizes[name]} records)")
    allowed = set(spatial) | (set(ALIASES["time"]) if keep_time else set())
    extra = set(da.dims) - allowed
    if extra:
        raise ValueError(f"Unselected extra dimensions: {sorted(extra)}; select them before plotting")
    if not set(spatial).issubset(da.dims):
        raise ValueError("Variable does not use both geographic coordinates")
    if any(da.sizes[name] == 0 for name in da.dims):
        raise ValueError("Selection contains an empty dimension")
    return da


def celsius(da):
    units = normalized_unit(da.attrs.get("units", ""))
    if units in {"k", "kelvin", "kelvins", "degreekelvin", "degreeskelvin"}:
        result = da - 273.15
    elif units in {"degc", "c", "°c", "celsius", "degreecelsius", "degreescelsius", "degreec", "degreesc"}:
        result = da.copy()
    else:
        raise ValueError(f"Unknown temperature units {da.attrs.get('units')!r}; provide valid source metadata")
    result.attrs = {**da.attrs, "units": "degC"}
    return result


def wind_components(u, v):
    accepted = {"m/s", "ms-1", "ms^-1", "ms**-1", "metersecond-1", "meterspersecond"}
    for da, expected in ((u, "eastward_wind"), (v, "northward_wind")):
        units = str(da.attrs.get("units", "")).lower().replace(" ", "")
        if units not in accepted:
            raise ValueError(f"Wind {da.name} requires m/s units, got {da.attrs.get('units')!r}")
        standard = da.attrs.get("standard_name", "")
        if standard and standard != expected:
            raise ValueError(f"Wind components must be geographic eastward/northward, got {standard!r}")
    try:
        u, v = xr.align(u, v, join="exact")
    except ValueError as exc:
        raise ValueError("Wind component coordinates are inconsistent") from exc
    if u.dims != v.dims or not u.coords.equals(v.coords):
        raise ValueError("Wind component dimensions/coordinates are inconsistent")
    return u, v
