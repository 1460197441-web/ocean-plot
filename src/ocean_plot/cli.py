"""argparse command interface."""
import argparse
from pathlib import Path
import sys
import numpy as np
import xarray as xr
from .data import identify, geographic, crop, select, celsius, wind_components
from .plotting import field, series, annotation


def parser():
    p = argparse.ArgumentParser(description="Plot rectilinear geographic ocean NetCDF data without implicit averaging.")
    sub = p.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Display dimensions, coordinate and variable metadata")
    inspect.add_argument("input", type=Path)
    demo = sub.add_parser("demo", help="Create offline synthetic examples (not observations)")
    demo.add_argument("--output-dir", type=Path, default=Path("examples/output"))
    for command in ("sst", "wind", "timeseries"):
        s = sub.add_parser(command)
        s.add_argument("input", type=Path)
        s.add_argument("--output", type=Path, required=True)
        s.add_argument("--lon", help="Longitude coordinate name")
        s.add_argument("--lat", help="Latitude coordinate name")
        s.add_argument("--bbox", nargs=4, type=float, metavar=("WEST", "EAST", "SOUTH", "NORTH"))
        depth = s.add_mutually_exclusive_group()
        depth.add_argument("--depth", type=float, help="Exact depth coordinate value in source units")
        depth.add_argument("--depth-index", type=int)
        if command != "timeseries":
            t = s.add_mutually_exclusive_group()
            t.add_argument("--time", help="Exact decoded time coordinate label")
            t.add_argument("--time-index", type=int)
            s.add_argument("--cartopy", action="store_true", help="Use Cartopy coastline (may download Natural Earth)")
        if command == "wind":
            s.add_argument("--u", help="Geographic eastward wind variable")
            s.add_argument("--v", help="Geographic northward wind variable")
            s.add_argument("--stride", type=int, default=3)
        else:
            s.add_argument("--var", help="Temperature variable name")
        if command == "timeseries":
            s.add_argument("--point", nargs=2, type=float, required=True, metavar=("LON", "LAT"))
            s.add_argument("--csv", type=Path, help="Default: output basename with .csv suffix")
    return p


def execute(args):
    if args.command == "demo":
        return demo(args.output_dir)
    if args.command != "inspect":
        if args.output.suffix.lower() not in {".png", ".pdf"}:
            raise ValueError("Output must be .png or .pdf")
        outputs = [args.output]
        if args.command == "timeseries":
            csv_path = args.csv or args.output.with_suffix(".csv")
            if csv_path.suffix.lower() != ".csv":
                raise ValueError("CSV output must have .csv extension")
            outputs.append(csv_path)
        paths = [args.input.resolve(), *(p.resolve() for p in outputs)]
        if len(set(paths)) != len(paths):
            raise ValueError("Input, figure output and CSV output must be distinct paths")
    with xr.open_dataset(args.input) as original:
        if args.command == "inspect":
            print(original)
            for name, value in original.variables.items():
                print(f"{name}: dims={value.dims}; attrs={value.attrs}")
            return
        ds, lon, lat = geographic(original, args.lon, args.lat)
        ds = crop(ds, lon, lat, args.bbox)
        selection = dict(depth=args.depth, depth_index=args.depth_index)
        if args.command != "timeseries":
            selection.update(time=args.time, time_index=args.time_index)
        if args.command == "wind":
            if args.stride < 1:
                raise ValueError("stride must be at least 1")
            u = select(ds[identify(ds, "u", args.u)], (lon, lat), **selection)
            v = select(ds[identify(ds, "v", args.v)], (lon, lat), **selection)
            u, v = wind_components(u, v)
            speed = np.hypot(u, v)
            speed.name = "Wind speed"
            speed.attrs["units"] = "m/s"
            if original.attrs.get("synthetic"):
                speed.attrs["synthetic"] = True
            print(f"Selection: {annotation(u)}")
            field(speed, lon, lat, args.output, args.cartopy, (u, v), args.stride)
        else:
            da = select(ds[identify(ds, "sst", args.var)], (lon, lat), keep_time=args.command == "timeseries", **selection)
            da = celsius(da)
            if original.attrs.get("synthetic"):
                da.attrs["synthetic"] = True
            if args.command == "sst":
                print(f"Selection: {annotation(da)}")
                field(da, lon, lat, args.output, args.cartopy)
            else:
                x, y = args.point
                if not (-180 <= x <= 180 and -90 <= y <= 90):
                    raise ValueError("point must be geographic longitude [-180, 180], latitude [-90, 90]")
                if not (float(ds[lon].min()) <= x <= float(ds[lon].max()) and float(ds[lat].min()) <= y <= float(ds[lat].max())):
                    raise ValueError("Requested point outside coordinate range; refusing distant extrapolation")
                da = da.sel({lon: x, lat: y}, method="nearest")
                print(f"Actual grid point: longitude={float(da[lon])}, latitude={float(da[lat])}")
                series(da, lon, lat, args.output, args.csv or args.output.with_suffix(".csv"), "degC")
        print(f"Saved: {args.output}")


def demo(directory):
    directory.mkdir(parents=True, exist_ok=True)
    time = np.arange("2025-01-01", "2025-02-01", dtype="datetime64[D]")
    lat, lon = np.linspace(30, 40, 31), np.linspace(118, 128, 41)
    xx, yy = np.meshgrid(lon, lat)
    temp = 290 - 0.8 * (yy - 30) + 1.5 * np.sin((xx - 118) / 3)
    values = temp[None, :, :] + np.sin(np.arange(len(time))[:, None, None] / 5)
    values[:, :5, :8] = np.nan
    values[10:13, 15, 20] = np.nan
    ds = xr.Dataset({
        "sst": (("time", "latitude", "longitude"), values, {"units": "K", "long_name": "Synthetic sea surface temperature"}),
        "uwnd": (("time", "latitude", "longitude"), np.broadcast_to(3 + np.sin(yy), values.shape).copy(), {"units": "m s-1", "standard_name": "eastward_wind"}),
        "vwnd": (("time", "latitude", "longitude"), np.broadcast_to(4 + np.cos(xx), values.shape).copy(), {"units": "m s-1", "standard_name": "northward_wind"}),
    }, coords={"time": time, "latitude": lat, "longitude": lon}, attrs={"title": "SYNTHETIC demonstration; not observational data", "synthetic": 1})
    ds.latitude.attrs["units"] = "degrees_north"
    ds.longitude.attrs["units"] = "degrees_east"
    source = directory / "synthetic.nc"
    ds.to_netcdf(source, engine="scipy")
    p = parser()
    for command, extra in (("sst", ["--time-index", "0"]), ("wind", ["--time-index", "0"]), ("timeseries", ["--point", "123", "35"])):
        execute(p.parse_args([command, str(source), "--output", str(directory / f"synthetic_{command}.png"), *extra]))
    execute(p.parse_args(["sst", str(source), "--time-index", "0", "--output", str(directory / "synthetic_sst.pdf")]))
    print("Synthetic demonstration only; not observations.")


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        execute(args)
    except (ValueError, KeyError, IndexError, OSError, ImportError) as exc:
        print(f"ocean-plot: error: {exc}", file=sys.stderr)
        return 2
    return 0
