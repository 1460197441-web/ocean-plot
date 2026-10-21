"""Headless figure output. Missing samples remain missing."""
from pathlib import Path
import csv
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
import numpy as np


def annotation(da):
    selected = []
    for name, coord in da.coords.items():
        if coord.ndim != 0:
            continue
        if np.issubdtype(coord.dtype, np.datetime64):
            value = np.datetime_as_string(coord.values, unit="s").replace("T", " ")
        elif np.issubdtype(coord.dtype, np.number):
            value = f"{coord.item():.6g}"
        else:
            value = str(coord.values)
        selected.append(f"{name}={value}")
    note = "; ".join(selected) or "No time/depth coordinate"
    return ("SYNTHETIC - not observations; " if da.attrs.get("synthetic") else "") + note


def save(fig, output):
    output = Path(output)
    if output.suffix.lower() not in {".png", ".pdf"}:
        raise ValueError("Output must be .png or .pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def axes(da, lon, lat, cartopy=False):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    kwargs = {}
    if cartopy:
        try:
            import cartopy.crs as ccrs
            import cartopy.feature as cfeature
        except ImportError as exc:
            raise ValueError("Install ocean-plot[maps] for --cartopy") from exc
        projection = ccrs.PlateCarree()
        fig, ax = plt.subplots(figsize=(8, 5.5), subplot_kw={"projection": projection}, layout="constrained")
        ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#e6e2d8", edgecolor="none", zorder=3)
        ax.coastlines(resolution="50m", linewidth=0.6, zorder=4)
        grid = ax.gridlines(draw_labels=True, linewidth=0.4, alpha=0.4)
        grid.top_labels = False
        grid.right_labels = False
        grid.xlocator = MaxNLocator(nbins=4)
        grid.ylocator = MaxNLocator(nbins=5)
        grid.xlabel_style = {"size": 9}
        grid.ylabel_style = {"size": 9}
        kwargs["transform"] = projection
        note = "Geographic map (Cartopy; Natural Earth coastline/land overlay)"
    else:
        fig, ax = plt.subplots(figsize=(8, 5.5), layout="constrained")
        ax.set_xlabel("Longitude (degrees east)")
        ax.set_ylabel("Latitude (degrees north)")
        mean_lat = float(da[lat].mean())
        ax.set_aspect(1 / max(np.cos(np.deg2rad(mean_lat)), 0.05))
        note = "Latitude-longitude coordinate plot; no coastline"
    ax.set_facecolor("#e9edf0")
    fig.supxlabel(note + "; missing cells shown in grey", fontsize=8)
    return fig, ax, kwargs


def field(da, lon, lat, output, cartopy=False, wind=None, stride=3):
    da = da.transpose(lat, lon)
    if not np.isfinite(da.values).any():
        raise ValueError("Selected field contains no finite observations")
    fig, ax, kwargs = axes(da, lon, lat, cartopy)
    mesh = ax.pcolormesh(da[lon], da[lat], da.values, shading="auto", cmap="viridis" if wind else "RdYlBu_r", **kwargs)
    label = "Wind speed (m/s)" if wind else f"{da.name or 'SST'} (degC)"
    fig.colorbar(mesh, ax=ax, label=label, shrink=0.85)
    ax.set_title(f"{label}\n{annotation(da)}", fontsize=11)
    if wind:
        u, v = [x.transpose(lat, lon) for x in wind]
        s = (slice(None, None, stride), slice(None, None, stride))
        xx, yy = np.meshgrid(da[lon], da[lat])
        # angles='uv': on a geographic east/north map the arrow points toward
        # the physical vector bearing; lengths are in m/s, not grid degrees.
        q = ax.quiver(xx[s], yy[s], u.values[s], v.values[s], angles="uv", scale=180, width=0.003, **kwargs)
        ax.add_patch(Rectangle((0.015, 0.015), 0.56, 0.10, transform=ax.transAxes, facecolor="white", edgecolor="none", alpha=0.9, zorder=5))
        ax.quiverkey(q, 0.08, 0.065, 10, "10 m/s (toward)", coordinates="axes", labelpos="E", fontproperties={"size": 9}, zorder=6)
    save(fig, output)


def series(da, lon, lat, output, csv_output, units):
    times = [name for name in ("time", "TIME") if name in da.dims]
    if len(times) != 1 or da.ndim != 1:
        raise ValueError("Time series requires exactly one time dimension")
    time = times[0]
    da = da.sortby(time)
    if not np.issubdtype(da[time].dtype, np.datetime64):
        raise ValueError("Time series currently requires a decoded standard datetime calendar")
    if not np.isfinite(da.values).any():
        raise ValueError("Selected point contains no finite observations")
    csv_output = Path(csv_output)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", "latitude", "longitude", "variable", "units", "value"])
        for t, value in zip(da[time].values, da.values):
            writer.writerow([np.datetime_as_string(t), float(da[lat]), float(da[lon]), da.name, units, "" if not np.isfinite(value) else float(value)])
    fig, ax = plt.subplots(figsize=(9, 3.8), layout="constrained")
    ax.plot(da[time], da.values, color="#236b8e", linewidth=1.2)
    ax.set_ylabel(f"{da.name} ({units})")
    ax.set_xlabel("Time (source calendar)")
    locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_title(f"Nearest grid point: {float(da[lat]):.4f} N, {float(da[lon]):.4f} E\n{annotation(da)}", fontsize=10)
    ax.grid(alpha=0.2)
    save(fig, output)
