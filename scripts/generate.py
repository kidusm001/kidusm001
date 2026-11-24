#!/usr/bin/env python3
"""Generate Kidus Mesfin Mekuria's animated 3D Isometric Hex Terrain GitHub profile SVGs & README.md."""

import datetime as dt
import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.environ.get("GITHUB_USER", "kidusm001")
ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

THEMES = {
    "dark": {
        "canvas": "#0D1117",
        "surface": "#151A21",
        "rule": "#232A34",
        "plinth_top": "#141920",
        "plinth_l": "#0F1319",
        "plinth_r": "#0A0D12",
        "plinth_edge": "#27303C",
        "ink": "#F0F3F6",
        "ink_mid": "#A8B1BC",
        "ink_dim": "#7D8794",
        "accent": "#4DA694",
        "hex_wire": "#2C3542",
        "hex_low":  ("#343E4B", "#272F3A", "#202730", "#1A2028"),
        "hex_mid":  ("#5C6A7B", "#455160", "#394350", "#2F3742"),
        "hex_hi":   ("#CDD5DE", "#9AA3AE", "#7F8893", "#67707B"),
        "hex_peak": ("#4DA694", "#3B8677", "#306F62", "#26594F"),
        "hex_stroke": "#0D1117",
        "hex_stroke_op": "0.75",
    },
    "light": {
        "canvas": "#FFFFFF",
        "surface": "#F6F7F8",
        "rule": "#E4E7EB",
        "plinth_top": "#F4F6F8",
        "plinth_l": "#E5E9EE",
        "plinth_r": "#D5DBE2",
        "plinth_edge": "#C8D0D9",
        "ink": "#111418",
        "ink_mid": "#454D57",
        "ink_dim": "#636C77",
        "accent": "#246B5C",
        "hex_wire": "#D0D6DE",
        "hex_low":  ("#C6CDD6", "#B3BBC6", "#A4ADB9", "#959FAA"),
        "hex_mid":  ("#828E9C", "#6C7886", "#5D6875", "#4F5965"),
        "hex_hi":   ("#38404A", "#2A3139", "#22282F", "#1B2026"),
        "hex_peak": ("#246B5C", "#1B5549", "#15453B", "#10362E"),
        "hex_stroke": "#181E25",
        "hex_stroke_op": "0.30",
    },
}

FONT_SANS = "Archivo, 'Helvetica Neue', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif"
FONT_MONO = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
    }
    pullRequests(states: MERGED) {
      totalCount
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
  repository(owner: $login, name: "rebuild-android") {
    latestRelease {
      tagName
    }
  }
}
"""


def fetch_github_stats() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is required to query GitHub GraphQL API.")

    payload = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{USERNAME}-profile-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))

    if res.get("errors"):
        raise RuntimeError(f"GraphQL errors: {res['errors']}")

    user = res["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    completed_weeks = weeks[:-1] if len(weeks) > 52 else weeks
    weekly_totals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in completed_weeks]
    daily_grid = [[d["contributionCount"] for d in w["contributionDays"]] for w in completed_weeks]
    active_weeks = sum(1 for x in weekly_totals if x > 0)
    max_day = max((c for w in daily_grid for c in w), default=1) or 1

    start_year = 2022
    cur_year = dt.date.today().year
    latest_tag = ((res["data"].get("repository") or {}).get("latestRelease") or {}).get("tagName") or "v0.4.1"

    return {
        "total_contribs": cal["totalContributions"],
        "merged_prs": user["pullRequests"]["totalCount"],
        "owned_repos": user["repositories"]["totalCount"],
        "active_weeks": active_weeks,
        "total_weeks": len(completed_weeks),
        "weekly_totals": weekly_totals,
        "daily_grid": daily_grid,
        "peak_week": max(weekly_totals, default=0),
        "max_day": max_day,
        "start_year": start_year,
        "cur_year": cur_year,
        "active_years": max(cur_year - start_year + 1, 1),
        "rebuild_tag": latest_tag,
    }


def small_hex_points(cx: float, cy: float, r: float) -> str:
    pts = []
    for k in range(6):
        ang = math.radians(60 * k)
        pts.append(f"{cx + r * math.cos(ang):.1f},{cy + r * math.sin(ang):.1f}")
    return " ".join(pts)


def hex_ring(cx: float, y: float, rx: float, ry: float):
    return [
        (cx + rx, y),
        (cx + rx * 0.5, y + ry),
        (cx - rx * 0.5, y + ry),
        (cx - rx, y),
        (cx - rx * 0.5, y - ry),
        (cx + rx * 0.5, y - ry),
    ]


def hex_prism_svg(cx, cy_base, rx, ry, h, colors, stroke_col, stroke_op="0.65", is_wire=False, strata=False) -> str:
    if is_wire or h <= 0.5:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in hex_ring(cx, cy_base, rx, ry))
        return f'<polygon points="{pts}" fill="none" stroke="{colors}" stroke-width="0.72" opacity="0.72"/>'

    top_col, fl_col, fc_col, fr_col = colors
    y_top = cy_base - h
    b = hex_ring(cx, cy_base, rx, ry)
    u = hex_ring(cx, y_top, rx, ry)

    def poly(points, fill, sw="0.5"):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        return f'<polygon points="{p}" fill="{fill}" stroke="{stroke_col}" stroke-opacity="{stroke_op}" stroke-width="{sw}" stroke-linejoin="round"/>'

    out = [
        poly([u[3], u[2], b[2], b[3]], fl_col),
        poly([u[2], u[1], b[1], b[2]], fc_col),
        poly([u[1], u[0], b[0], b[1]], fr_col),
        poly(u, top_col, sw="0.55"),
    ]

    if strata and h >= 32:
        step = 13.0
        cur_y = y_top + step
        while cur_y < cy_base - 6:
            s = hex_ring(cx, cur_y, rx, ry)
            d = f"M {s[3][0]:.1f},{s[3][1]:.1f} L {s[2][0]:.1f},{s[2][1]:.1f} L {s[1][0]:.1f},{s[1][1]:.1f} L {s[0][0]:.1f},{s[0][1]:.1f}"
            out.append(f'<path d="{d}" fill="none" stroke="{stroke_col}" stroke-width="0.45" opacity="0.20"/>')
            cur_y += step

    return "".join(out)


def hex_socket_clip(clip_id: str, cx: float, cy_base: float, rx: float, ry: float, h: float) -> str:
    """
    Exact hydraulic-piston clip polygon pinned to the prism's front-bottom hexagonal edge on the plinth.
    When the prism translates from translateY(h) -> translateY(0), its top hex cap starts 100% flush
    with the plinth at height 0 and extrudes cleanly upward with zero overhang below the plinth.
    """
    b = hex_ring(cx, cy_base, rx + 0.6, ry + 0.5)
    top_y = cy_base - h - 20.0
    pts = [
        (b[3][0], top_y),
        (b[0][0], top_y),
        b[0],
        b[1],
        b[2],
        b[3],
    ]
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<clipPath id="{clip_id}"><polygon points="{p}"/></clipPath>'


def make_header(t, suffix):
    emblem = []
    clips = []
    erx, ery = 19.5, 10.4
    cluster = [
        (0, -1, 20, t["hex_low"], False),
        (-1, 0, 32, t["hex_mid"], False),
        (1, -1, 14, t["hex_low"], False),
        (0, 0, 52, t["hex_peak"], True),
        (1, 0, 26, t["hex_hi"], False),
        (-1, 1, 16, t["hex_low"], False),
        (0, 1, 36, t["hex_hi"], True),
    ]
    placed = []
    for q, r, h, cols, strata in cluster:
        px = 758 + q * (erx * 1.54)
        py = 96 + (r + q * 0.5) * (ery * 2.04)
        placed.append((py, px, h, cols, strata))
    placed.sort(key=lambda item: item[0])
    for idx, (py, px, h, cols, strata) in enumerate(placed):
        cid = f"hc-{idx}"
        clips.append(hex_socket_clip(cid, px, py, erx, ery, h))
        el = hex_prism_svg(px, py, erx, ery, h, cols, t["hex_stroke"], t["hex_stroke_op"], strata=strata)
        emblem.append(
            f'<g clip-path="url(#{cid})">'
            f'<g class="h-grow" style="--h:{h:.1f}px;animation-delay:{60 + idx * 55}ms">{el}</g>'
            f'</g>'
        )

    anim = """
  <style>
    @keyframes hGrow {
      0% { transform: translateY(var(--h)); }
      100% { transform: translateY(0); }
    }
    .h-grow {
      animation: hGrow 750ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    @media (prefers-reduced-motion: reduce) {
      .h-grow { animation: none !important; transform: none !important; }
    }
  </style>
"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="142" viewBox="0 0 840 142">
  {anim}
  <defs>{''.join(clips)}</defs>
  <rect width="840" height="142" fill="{t['canvas']}"/>
  <text x="16" y="50" font-family="{FONT_SANS}" font-size="34" font-weight="700" letter-spacing="-0.8" fill="{t['ink']}">Kidus Mesfin Mekuria</text>
  <text x="16" y="82" font-family="{FONT_SANS}" font-size="15.5" fill="{t['ink_mid']}">Software engineer building full-stack applications and systems software.</text>
  <text x="16" y="110" font-family="{FONT_SANS}" font-size="13" fill="{t['ink_dim']}">Python  ·  TypeScript  ·  Kotlin  ·  C++  ·  Addis Ababa</text>
  {''.join(emblem)}
</svg>
"""
    (ASSETS_DIR / f"header-{suffix}.svg").write_text(svg)


def make_social_icon(t, suffix, name, icon_svg, fill_icon=False):
    # Clean standalone 42x36 clickable icon button (fixed pixel width in README — never breaks on GitHub!)
    g_attrs = (
        f'fill="{t["ink"]}" stroke="none"'
        if fill_icon
        else f'fill="none" stroke="{t["ink"]}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"'
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="42" height="36" viewBox="0 0 42 36">
  <rect x="0.5" y="0.5" width="41" height="35" rx="9" fill="{t['surface']}" stroke="{t['rule']}"/>
  <g transform="translate(12, 9)" {g_attrs}>
    {icon_svg}
  </g>
</svg>
"""
    (ASSETS_DIR / f"social-{name}-{suffix}.svg").write_text(svg)


def make_terrain_and_stats(t, suffix, stats):
    """
    Unified 840x430 SVG containing:
    1) Calm 3D Isometric Hex Terrain where every single column smoothly EXTRUDES UPWARD
       from height 0 flush on its own plinth socket (zero downward overhang, zero broken pieces!)
    2) Grounded Contributions plaque directly below the terrain (zero seam between them!).
    """
    grid = stats["daily_grid"]
    n_weeks = len(grid)
    max_day = max(stats["max_day"], 1)

    best_c, best_w, best_d = -1, 0, 0
    for w_idx, w in enumerate(grid):
        for d_idx, c in enumerate(w):
            if c >= best_c:
                best_c, best_w, best_d = c, w_idx, d_idx

    high_threshold = max(int(max_day * 0.45), 12)

    rx, ry = 7.4, 4.15
    ox, oy = 104.0, 140.0
    dx_w, dy_w = 13.7, 1.90
    dx_d, dy_d = -11.0, 7.6

    pad_w = 1.0
    pad_d = 0.85

    def pt(w, d):
        return (ox + w * dx_w + d * dx_d, oy + w * dy_w + d * dy_d)

    c_tl = pt(-pad_w, -pad_d)
    c_tr = pt(n_weeks - 1 + pad_w, -pad_d)
    c_br = pt(n_weeks - 1 + pad_w, 6 + pad_d)
    c_bl = pt(-pad_w, 6 + pad_d)
    slab_th = 6.5

    def pstr(pts):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    plinth = "".join([
        f'<polygon points="{pstr([c_tl, c_bl, (c_bl[0], c_bl[1] + slab_th), (c_tl[0], c_tl[1] + slab_th)])}" fill="{t["plinth_l"]}" stroke="{t["plinth_edge"]}" stroke-width="0.75"/>',
        f'<polygon points="{pstr([c_bl, c_br, (c_br[0], c_br[1] + slab_th), (c_bl[0], c_bl[1] + slab_th)])}" fill="{t["plinth_r"]}" stroke="{t["plinth_edge"]}" stroke-width="0.75"/>',
        f'<polygon points="{pstr([c_tl, c_tr, c_br, c_bl])}" fill="{t["plinth_top"]}" stroke="{t["plinth_edge"]}" stroke-width="0.85"/>',
    ])

    prisms = []
    summit_xy = None
    for w_idx in range(n_weeks):
        for d_idx in range(len(grid[w_idx])):
            c = grid[w_idx][d_idx]
            stagger = 0.35 if (w_idx % 2 == 1) else 0.0
            sx = ox + w_idx * dx_w + (d_idx + stagger) * dx_d
            sy = oy + w_idx * dy_w + (d_idx + stagger) * dy_d

            if c == 0:
                prisms.append((sy, sx, w_idx, 0.0, t["hex_wire"], True, False))
            else:
                h = 6.0 + math.pow(c / max_day, 0.60) * 82.0
                if c >= high_threshold:
                    cols = t["hex_peak"]
                    strata = True
                elif c >= 7:
                    cols = t["hex_hi"]
                    strata = h >= 32
                elif c >= 3:
                    cols = t["hex_mid"]
                    strata = False
                else:
                    cols = t["hex_low"]
                    strata = False
                prisms.append((sy, sx, w_idx, h, cols, False, strata))
                if w_idx == best_w and d_idx == best_d:
                    summit_xy = (sx, sy - h)

    prisms.sort(key=lambda item: (item[0], item[1]))
    clips = []
    terrain_svg = []
    clip_idx = 0
    for sy, sx, w_idx, h, cols, wire, strata in prisms:
        el = hex_prism_svg(sx, sy, rx, ry, h, cols, t["hex_stroke"], t["hex_stroke_op"], is_wire=wire, strata=strata)
        if wire:
            terrain_svg.append(el)
        else:
            cid = f"c{clip_idx}"
            clip_idx += 1
            clips.append(hex_socket_clip(cid, sx, sy, rx, ry, h))
            # Smooth cascading left-to-right hydraulic extrusion (18ms per week, 850ms cubic ease-out)
            delay_ms = 80 + w_idx * 18
            terrain_svg.append(
                f'<g clip-path="url(#{cid})">'
                f'<g class="hex-grow" style="--h:{h:.1f}px;animation-delay:{delay_ms}ms">{el}</g>'
                f'</g>'
            )

    callout = ""
    if summit_xy:
        sx, sy_top = summit_xy
        pin_top = sy_top - 22
        elbow_x = sx - 16
        label_x = elbow_x - 7
        callout = (
            f'<g class="summit-callout">'
            f'<circle class="summit-ring" cx="{sx:.1f}" cy="{sy_top:.1f}" r="5.5" fill="none" stroke="{t["accent"]}" stroke-width="1"/>'
            f'<circle cx="{sx:.1f}" cy="{sy_top:.1f}" r="2.2" fill="{t["canvas"]}" stroke="{t["accent"]}" stroke-width="1.4"/>'
            f'<polyline points="{sx:.1f},{sy_top - 2.2:.1f} {sx:.1f},{pin_top:.1f} {elbow_x:.1f},{pin_top:.1f}" fill="none" stroke="{t["accent"]}" stroke-width="1.15"/>'
            f'<text x="{label_x:.1f}" y="{pin_top + 3.5:.1f}" text-anchor="end" font-family="{FONT_MONO}" font-size="9.5" font-weight="600" fill="{t["accent"]}">Peak · {best_c}/day · {stats["peak_week"]}/wk</text>'
            f'</g>'
        )

    anim_style = """
  <style>
    @keyframes hexGrow {
      0% { transform: translateY(var(--h)); }
      100% { transform: translateY(0); }
    }
    @keyframes calloutIn {
      0% { opacity: 0; transform: translateY(6px); }
      100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes summitPulse {
      0%, 100% { opacity: 0.14; transform: scale(0.85); }
      50% { opacity: 0.55; transform: scale(1.32); }
    }
    .hex-grow {
      animation: hexGrow 850ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    .summit-callout {
      animation: calloutIn 480ms cubic-bezier(0.22, 1, 0.36, 1) 1450ms both;
    }
    .summit-ring {
      transform-box: fill-box;
      transform-origin: center;
      animation: summitPulse 3.6s ease-in-out 1900ms infinite;
    }
    @media (prefers-reduced-motion: reduce) {
      .hex-grow, .summit-callout, .summit-ring {
        animation: none !important;
        opacity: 1 !important;
        transform: none !important;
      }
      .summit-ring { opacity: 0.25 !important; }
    }
  </style>
"""

    legend_items = [
        (t["hex_wire"], "0", True),
        (t["hex_low"][0], "1–2", False),
        (t["hex_mid"][0], "3–6", False),
        (t["hex_hi"][0], "7+", False),
        (t["hex_peak"][0], "Peak", False),
    ]
    leg = []
    lx = 16
    for col, txt, is_w in legend_items:
        pts = small_hex_points(lx + 5, 326.5, 4.6)
        if is_w:
            leg.append(f'<polygon points="{pts}" fill="none" stroke="{col}" stroke-width="1.1"/>')
        else:
            leg.append(f'<polygon points="{pts}" fill="{col}"/>')
        leg.append(f'<text x="{lx + 14}" y="330" font-family="{FONT_SANS}" font-size="10.5" fill="{t["ink_dim"]}">{txt}</text>')
        lx += 48 if txt != "Peak" else 56

    # Contributions plaque integrated cleanly right below the legend (y=350..416)
    items = [
        (f"{stats['total_contribs']:,}", "contributions"),
        (f"{stats['merged_prs']:,}", "merged PRs"),
        (f"{stats['active_weeks']} / {stats['total_weeks']}", "active weeks"),
        (f"{stats['owned_repos']}", "repositories"),
    ]
    cols_svg = []
    for i, (val, lbl) in enumerate(items):
        x = 248 + i * 148
        cols_svg.append(f'<line x1="{x - 20}" y1="364" x2="{x - 20}" y2="402" stroke="{t["rule"]}"/>')
        cols_svg.append(f'<text x="{x}" y="383" font-family="{FONT_MONO}" font-size="20" font-weight="700" fill="{t["ink"]}">{val}</text>')
        cols_svg.append(f'<text x="{x}" y="400" font-family="{FONT_SANS}" font-size="11.5" fill="{t["ink_dim"]}">{lbl}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="430" viewBox="0 0 840 430">
  {anim_style}
  <defs>{''.join(clips)}</defs>
  <rect width="840" height="430" fill="{t['canvas']}"/>
  <line x1="16" y1="0.5" x2="824" y2="0.5" stroke="{t['rule']}"/>
  <text x="16" y="38" font-family="{FONT_SANS}" font-size="16" font-weight="600" letter-spacing="-0.2" fill="{t['ink']}">Commit terrain</text>
  <text x="824" y="38" text-anchor="end" font-family="{FONT_SANS}" font-size="12" fill="{t['ink_dim']}">52 completed weeks · updated daily</text>
  {plinth}
  {''.join(terrain_svg)}
  {callout}
  {''.join(leg)}
  <text x="824" y="330" text-anchor="end" font-family="{FONT_SANS}" font-size="10.5" fill="{t['ink_dim']}">52 weeks ago → last week</text>
  <!-- Grounded Contributions Plaque directly beneath the terrain -->
  <rect x="16" y="352" width="808" height="66" rx="10" fill="{t['surface']}"/>
  <text x="38" y="383" font-family="{FONT_MONO}" font-size="16" font-weight="700" fill="{t['ink']}">{stats['start_year']} – {stats['cur_year']}</text>
  <text x="38" y="400" font-family="{FONT_SANS}" font-size="11.5" fill="{t['ink_dim']}">{stats['active_years']} active years on GitHub</text>
  {''.join(cols_svg)}
</svg>
"""
    (ASSETS_DIR / f"terrain-{suffix}.svg").write_text(svg)


def make_section_title(t, suffix, name, title, right_note):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="46" viewBox="0 0 840 46">
  <rect width="840" height="46" fill="{t['canvas']}"/>
  <line x1="16" y1="8.5" x2="824" y2="8.5" stroke="{t['rule']}"/>
  <text x="16" y="36" font-family="{FONT_SANS}" font-size="16" font-weight="600" letter-spacing="-0.2" fill="{t['ink']}">{escape(title)}</text>
  <text x="824" y="36" text-anchor="end" font-family="{FONT_SANS}" font-size="12" fill="{t['ink_dim']}">{escape(right_note)}</text>
</svg>
"""
    (ASSETS_DIR / f"sec-{name}-{suffix}.svg").write_text(svg)


def make_project_card(t, suffix, filename, title, slug, tag, line1, line2, meta):
    # Full-width 840px card (width="100%" in README — ZERO GitHub <themed-picture> side-by-side breakage!)
    slug_x = 38 + len(title) * 11.2 + 12
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="128" viewBox="0 0 840 128">
  <rect width="840" height="128" fill="{t['canvas']}"/>
  <rect x="16" y="5" width="808" height="116" rx="10" fill="{t['surface']}"/>
  <text x="38" y="35" font-family="{FONT_SANS}" font-size="18" font-weight="650" letter-spacing="-0.3" fill="{t['ink']}">{escape(title)}</text>
  <text x="{slug_x:.0f}" y="34.5" font-family="{FONT_MONO}" font-size="11" fill="{t['ink_dim']}">{escape(slug)}</text>
  <text x="802" y="34.5" text-anchor="end" font-family="{FONT_SANS}" font-size="12" font-weight="500" fill="{t['accent']}">{escape(tag)}  ↗</text>
  <text x="38" y="61" font-family="{FONT_SANS}" font-size="13.5" fill="{t['ink_mid']}">{escape(line1)}</text>
  <text x="38" y="80" font-family="{FONT_SANS}" font-size="13.5" fill="{t['ink_mid']}">{escape(line2)}</text>
  <text x="38" y="105" font-family="{FONT_MONO}" font-size="10.8" fill="{t['ink_dim']}">{escape(meta)}</text>
</svg>
"""
    (ASSETS_DIR / f"{filename}-{suffix}.svg").write_text(svg)


def make_stack(t, suffix):
    # Unified Core stack heading + 2x2 matrix in one seamless 840px SVG
    rows = [
        ("Languages", "Python · TypeScript · Kotlin · C/C++ · SQL · C#",
         "Backend & Data", "Frappe/ERPNext · FastAPI · Node.js · PostgreSQL · SQLite · Redis"),
        ("Frontend & Mobile", "Next.js · React · Tailwind CSS · Jetpack Compose · Qt 6",
         "Infrastructure", "Linux · Docker · Kubernetes · Git · GitHub Actions"),
    ]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="162" viewBox="0 0 840 162">
  <rect width="840" height="162" fill="{t['canvas']}"/>
  <line x1="16" y1="8.5" x2="824" y2="8.5" stroke="{t['rule']}"/>
  <text x="16" y="36" font-family="{FONT_SANS}" font-size="16" font-weight="600" letter-spacing="-0.2" fill="{t['ink']}">Core stack</text>

  <text x="16" y="68" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[0][0])}</text>
  <text x="16" y="88" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[0][1])}</text>

  <text x="384" y="68" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[0][2])}</text>
  <text x="384" y="88" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[0][3])}</text>

  <line x1="16" y1="104.5" x2="824" y2="104.5" stroke="{t['rule']}"/>

  <text x="16" y="124" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[1][0])}</text>
  <text x="16" y="144" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[1][1])}</text>

  <text x="384" y="124" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[1][2])}</text>
  <text x="384" y="144" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[1][3])}</text>
</svg>
"""
    (ASSETS_DIR / f"stack-{suffix}.svg").write_text(svg)


def picture_tag(base_name: str, alt: str, width: str = "100%") -> str:
    return (
        f'<picture>'
        f'<source media="(prefers-color-scheme: dark)" srcset="./assets/{base_name}-dark.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="./assets/{base_name}-light.svg">'
        f'<img src="./assets/{base_name}-dark.svg" alt="{escape(alt)}" width="{width}">'
        f'</picture>'
    )


def main():
    stats = fetch_github_stats()

    # Clean old unused sliced files if present
    for old in list(ASSETS_DIR.glob("social-spacer-*.svg")) + list(ASSETS_DIR.glob("stats-*.svg")) + list(ASSETS_DIR.glob("hex-terrain-*.svg")) + list(ASSETS_DIR.glob("sec-stack-*.svg")):
        old.unlink(missing_ok=True)

    icon_email = '<rect x="1" y="3.5" width="16" height="11" rx="2"/><path d="M1.8 4.8L9 10l7.2-5.2"/>'
    icon_tg = '<path d="M16.5 2L1.5 8.2l4.9 1.8 7.8-5.6-5.5 6.6v4.1l2.6-2.6 3.2 2.4L16.5 2z"/>'
    icon_x = '<path d="M2.5 2h3.5l3.6 5.1L14 2h1.7l-5.2 6.1L16.1 16h-3.5l-4-5.6L3.8 16H2.1l5.6-6.6L2.5 2z"/>'

    for suffix, t in THEMES.items():
        make_header(t, suffix)
        make_social_icon(t, suffix, "email", icon_email)
        make_social_icon(t, suffix, "telegram", icon_tg)
        make_social_icon(t, suffix, "x", icon_x, fill_icon=True)
        make_terrain_and_stats(t, suffix, stats)
        make_section_title(t, suffix, "work", "Selected work", "Click any project to open")
        make_project_card(
            t, suffix, "proj-rebuild", "Rebuild", f"{USERNAME}/rebuild-android", f"Android · {stats['rebuild_tag']}",
            "Offline-first Android strength-training app with transactional SQLite snapshots, pure immutable state,",
            "additive schema migrations, and Perfetto-profiled Compose UI (193ms → 40ms tab switch).",
            "Kotlin · Jetpack Compose · SQLite  ·  340+ JVM/Robolectric tests",
        )
        make_project_card(
            t, suffix, "proj-bex", "bex", f"{USERNAME}/bex", "Linux",
            "Daemonless, rootless native Linux performance monitor built with C++20 and Qt 6, rendering live CPU,",
            "memory, disk, network, thermal, and process views with real-time filtering and process classification.",
            "C++20 · Qt 6 · CMake  ·  11 automated Qt test suites",
        )
        make_project_card(
            t, suffix, "proj-routegna", "RouteGna", f"{USERNAME}/multi-fleet-managment", "Web & API",
            "Multi-tenant fleet management, route optimization, and automated payroll SaaS platform with 6-tier RBAC,",
            "Redis caching, scheduled cron payroll jobs, and containerized Node.js and FastAPI services.",
            "TypeScript · React · Node.js · PostgreSQL · Redis · FastAPI · Docker",
        )
        make_stack(t, suffix)

    # Zero side-by-side % hacks that break inside GitHub <themed-picture>!
    # Full-width sections use width="100%", social icon buttons use fixed pixel width="42"!
    readme = f"""<!-- profile:start -->
<div align="left">

{picture_tag("header", "Kidus Mesfin Mekuria — Software engineer building full-stack applications and systems software. Python, TypeScript, Kotlin, C++, Addis Ababa.")}

&nbsp;&nbsp;&nbsp;<a href="mailto:kidusmesfin27@gmail.com">{picture_tag("social-email", "Email: kidusmesfin27@gmail.com", "42")}</a>&nbsp;&nbsp;<a href="https://t.me/crosscodething">{picture_tag("social-telegram", "Telegram: t.me/crosscodething", "42")}</a>&nbsp;&nbsp;<a href="https://x.com/kidus_m27">{picture_tag("social-x", "X: @kidus_m27", "42")}</a>

{picture_tag("terrain", f"Commit terrain: 3D isometric hexagonal prism visualization of 52 completed weeks, peak {stats['max_day']}/day ({stats['peak_week']}/week). {stats['start_year']}–{stats['cur_year']}: {stats['total_contribs']} contributions, {stats['merged_prs']} merged PRs, {stats['active_weeks']} of {stats['total_weeks']} active weeks, {stats['owned_repos']} repositories.")}

{picture_tag("sec-work", "Selected work")}

<a href="https://github.com/{USERNAME}/rebuild-android">{picture_tag("proj-rebuild", f"Rebuild ({USERNAME}/rebuild-android): Offline-first Android strength-training app in Kotlin, Jetpack Compose, and SQLite. 193ms to 40ms tab switch via Perfetto profiling, 340+ JVM/Robolectric tests, {stats['rebuild_tag']}.")}</a>
<a href="https://github.com/{USERNAME}/bex">{picture_tag("proj-bex", f"bex ({USERNAME}/bex): Daemonless, rootless native Linux performance monitor in C++20 and Qt 6 with live CPU, memory, disk, network, thermal, and process views and 11 Qt test suites.")}</a>
<a href="https://github.com/{USERNAME}/multi-fleet-managment">{picture_tag("proj-routegna", f"RouteGna ({USERNAME}/multi-fleet-managment): Multi-tenant fleet, route optimization, and automated payroll platform in TypeScript, React, Node.js, PostgreSQL, Redis, Docker, and FastAPI.")}</a>

{picture_tag("stack", "Core stack: Python, TypeScript, Kotlin, C/C++, SQL, C#, Frappe/ERPNext, FastAPI, Node.js, PostgreSQL, SQLite, Redis, Next.js, React, Tailwind CSS, Jetpack Compose, Qt 6, Linux, Docker, Kubernetes, Git, GitHub Actions.")}

</div>
<!-- profile:end -->
"""
    (ROOT / "README.md").write_text(readme)
    print(f"Generated {len(list(ASSETS_DIR.glob('*.svg')))} SVGs and README.md ({len(readme)} chars).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
