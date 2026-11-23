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


def hex_prism_svg(cx, cy_base, rx, ry, h, colors, stroke_col, stroke_op="0.65", is_wire=False, strata=False) -> str:
    def ring(y):
        return [
            (cx + rx, y),
            (cx + rx * 0.5, y + ry),
            (cx - rx * 0.5, y + ry),
            (cx - rx, y),
            (cx - rx * 0.5, y - ry),
            (cx + rx * 0.5, y - ry),
        ]

    if is_wire or h <= 0.5:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in ring(cy_base))
        return f'<polygon points="{pts}" fill="none" stroke="{colors}" stroke-width="0.72" opacity="0.72"/>'

    top_col, fl_col, fc_col, fr_col = colors
    y_top = cy_base - h
    b = ring(cy_base)
    u = ring(y_top)

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
            s = ring(cur_y)
            d = f"M {s[3][0]:.1f},{s[3][1]:.1f} L {s[2][0]:.1f},{s[2][1]:.1f} L {s[1][0]:.1f},{s[1][1]:.1f} L {s[0][0]:.1f},{s[0][1]:.1f}"
            out.append(f'<path d="{d}" fill="none" stroke="{stroke_col}" stroke-width="0.45" opacity="0.20"/>')
            cur_y += step

    return "".join(out)


def make_header(t, suffix):
    emblem = []
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
    for py, px, h, cols, strata in placed:
        emblem.append(hex_prism_svg(px, py, erx, ery, h, cols, t["hex_stroke"], t["hex_stroke_op"], strata=strata))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="148" viewBox="0 0 840 148">
  <rect width="840" height="148" fill="{t['canvas']}"/>
  <text x="16" y="54" font-family="{FONT_SANS}" font-size="34" font-weight="700" letter-spacing="-0.8" fill="{t['ink']}">Kidus Mesfin Mekuria</text>
  <text x="16" y="86" font-family="{FONT_SANS}" font-size="15.5" fill="{t['ink_mid']}">Software engineer building full-stack applications and systems software.</text>
  <text x="16" y="114" font-family="{FONT_SANS}" font-size="13" fill="{t['ink_dim']}">Python  ·  TypeScript  ·  Kotlin  ·  C++  ·  Addis Ababa</text>
  {''.join(emblem)}
</svg>
"""
    (ASSETS_DIR / f"header-{suffix}.svg").write_text(svg)


def make_social_icon_btn(t, suffix, name, icon_svg, slice_w, bx, bw, is_first=False, fill_icon=False):
    ix = bx + (bw - 18) / 2
    iy = 4 + (36 - 18) / 2
    g_attrs = (
        f'fill="{t["ink"]}" stroke="none"'
        if fill_icon
        else f'fill="none" stroke="{t["ink"]}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"'
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{slice_w}" height="54" viewBox="0 0 {slice_w} 54">
  <rect width="{slice_w}" height="54" fill="{t['canvas']}"/>
  <rect x="{bx}" y="4" width="{bw}" height="36" rx="9" fill="{t['surface']}" stroke="{t['rule']}"/>
  <g transform="translate({ix:.1f}, {iy:.1f})" {g_attrs}>
    {icon_svg}
  </g>
  <line x1="{16 if is_first else 0}" y1="53.5" x2="{slice_w}" y2="53.5" stroke="{t['rule']}"/>
</svg>
"""
    (ASSETS_DIR / f"social-{name}-{suffix}.svg").write_text(svg)


def make_social_spacer(t, suffix, slice_w):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{slice_w}" height="54" viewBox="0 0 {slice_w} 54">
  <rect width="{slice_w}" height="54" fill="{t['canvas']}"/>
  <line x1="0" y1="53.5" x2="{slice_w - 16}" y2="53.5" stroke="{t['rule']}"/>
</svg>
"""
    (ASSETS_DIR / f"social-spacer-{suffix}.svg").write_text(svg)


def make_hex_terrain(t, suffix, stats):
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
    ox, oy = 104.0, 128.0
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
    terrain_svg = []
    for sy, sx, w_idx, h, cols, wire, strata in prisms:
        el = hex_prism_svg(sx, sy, rx, ry, h, cols, t["hex_stroke"], t["hex_stroke_op"], is_wire=wire, strata=strata)
        if wire:
            terrain_svg.append(el)
        else:
            delay_ms = 40 + w_idx * 14
            cls = "hex-col hex-peak" if cols == t["hex_peak"] else "hex-col"
            terrain_svg.append(f'<g class="{cls}" style="animation-delay:{delay_ms}ms">{el}</g>')

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
    @keyframes hexRise {
      0% { transform: translateY(10px); }
      100% { transform: translateY(0); }
    }
    @keyframes peakBreathe {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-2.4px); }
    }
    @keyframes summitPulse {
      0%, 100% { opacity: 0.14; transform: scale(0.85); }
      50% { opacity: 0.55; transform: scale(1.3); }
    }
    .hex-col {
      animation: hexRise 580ms cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    .hex-peak {
      animation:
        hexRise 580ms cubic-bezier(0.16, 1, 0.3, 1) both,
        peakBreathe 4.6s ease-in-out 1.4s infinite;
    }
    .summit-ring {
      transform-box: fill-box;
      transform-origin: center;
      animation: summitPulse 3.6s ease-in-out infinite;
    }
    @media (prefers-reduced-motion: reduce) {
      .hex-col, .hex-peak, .summit-ring {
        animation: none !important;
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
        pts = small_hex_points(lx + 5, 316.5, 4.6)
        if is_w:
            leg.append(f'<polygon points="{pts}" fill="none" stroke="{col}" stroke-width="1.1"/>')
        else:
            leg.append(f'<polygon points="{pts}" fill="{col}"/>')
        leg.append(f'<text x="{lx + 14}" y="320" font-family="{FONT_SANS}" font-size="10.5" fill="{t["ink_dim"]}">{txt}</text>')
        lx += 48 if txt != "Peak" else 56

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="334" viewBox="0 0 840 334">
  {anim_style}
  <rect width="840" height="334" fill="{t['canvas']}"/>
  <text x="16" y="34" font-family="{FONT_SANS}" font-size="16" font-weight="600" letter-spacing="-0.2" fill="{t['ink']}">Commit terrain</text>
  <text x="824" y="34" text-anchor="end" font-family="{FONT_SANS}" font-size="12" fill="{t['ink_dim']}">52 completed weeks · updated daily</text>
  {plinth}
  {''.join(terrain_svg)}
  {callout}
  {''.join(leg)}
  <text x="824" y="320" text-anchor="end" font-family="{FONT_SANS}" font-size="10.5" fill="{t['ink_dim']}">52 weeks ago → last week</text>
</svg>
"""
    (ASSETS_DIR / f"hex-terrain-{suffix}.svg").write_text(svg)


def make_contributions_strip(t, suffix, stats):
    items = [
        (f"{stats['total_contribs']:,}", "contributions"),
        (f"{stats['merged_prs']:,}", "merged PRs"),
        (f"{stats['active_weeks']} / {stats['total_weeks']}", "active weeks"),
        (f"{stats['owned_repos']}", "repositories"),
    ]
    cols_svg = []
    for i, (val, lbl) in enumerate(items):
        x = 248 + i * 148
        cols_svg.append(f'<line x1="{x - 20}" y1="20" x2="{x - 20}" y2="58" stroke="{t["rule"]}"/>')
        cols_svg.append(f'<text x="{x}" y="39" font-family="{FONT_MONO}" font-size="20" font-weight="700" fill="{t["ink"]}">{val}</text>')
        cols_svg.append(f'<text x="{x}" y="56" font-family="{FONT_SANS}" font-size="11.5" fill="{t["ink_dim"]}">{lbl}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="86" viewBox="0 0 840 86">
  <rect width="840" height="86" fill="{t['canvas']}"/>
  <rect x="16" y="8" width="808" height="66" rx="10" fill="{t['surface']}"/>
  <text x="38" y="39" font-family="{FONT_MONO}" font-size="16" font-weight="700" fill="{t['ink']}">{stats['start_year']} – {stats['cur_year']}</text>
  <text x="38" y="56" font-family="{FONT_SANS}" font-size="11.5" fill="{t['ink_dim']}">{stats['active_years']} active years on GitHub</text>
  {''.join(cols_svg)}
</svg>
"""
    (ASSETS_DIR / f"stats-{suffix}.svg").write_text(svg)


def make_section_title(t, suffix, name, title, right_note):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="46" viewBox="0 0 840 46">
  <rect width="840" height="46" fill="{t['canvas']}"/>
  <line x1="16" y1="8.5" x2="824" y2="8.5" stroke="{t['rule']}"/>
  <text x="16" y="36" font-family="{FONT_SANS}" font-size="16" font-weight="600" letter-spacing="-0.2" fill="{t['ink']}">{escape(title)}</text>
  <text x="824" y="36" text-anchor="end" font-family="{FONT_SANS}" font-size="12" fill="{t['ink_dim']}">{escape(right_note)}</text>
</svg>
"""
    (ASSETS_DIR / f"sec-{name}-{suffix}.svg").write_text(svg)


def make_hero_project(t, suffix, stats):
    tag = stats["rebuild_tag"]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="134" viewBox="0 0 840 134">
  <rect width="840" height="134" fill="{t['canvas']}"/>
  <rect x="16" y="6" width="808" height="120" rx="10" fill="{t['surface']}"/>
  <text x="38" y="37" font-family="{FONT_SANS}" font-size="18.5" font-weight="650" letter-spacing="-0.3" fill="{t['ink']}">Rebuild</text>
  <text x="115" y="36.5" font-family="{FONT_MONO}" font-size="11" fill="{t['ink_dim']}">{USERNAME}/rebuild-android</text>
  <text x="802" y="36.5" text-anchor="end" font-family="{FONT_SANS}" font-size="12" font-weight="500" fill="{t['accent']}">Android · {escape(tag)}  ↗</text>
  <text x="38" y="63" font-family="{FONT_SANS}" font-size="13.5" fill="{t['ink_mid']}">Offline-first Android strength-training logbook with transactional SQLite snapshots, pure immutable state,</text>
  <text x="38" y="82" font-family="{FONT_SANS}" font-size="13.5" fill="{t['ink_mid']}">additive schema migrations, and Perfetto-profiled Compose UI (193ms → 40ms tab switch).</text>
  <text x="38" y="109" font-family="{FONT_MONO}" font-size="10.8" fill="{t['ink_dim']}">Kotlin · Jetpack Compose · SQLite  ·  340+ JVM/Robolectric tests</text>
</svg>
"""
    (ASSETS_DIR / f"proj-rebuild-{suffix}.svg").write_text(svg)


def make_half_project(t, suffix, filename, title, tag, lines, meta, side="left"):
    px = 16 if side == "left" else 6
    pw = 398
    body = "".join(
        f'<text x="{px + 22}" y="{63 + i * 19}" font-family="{FONT_SANS}" font-size="13.2" fill="{t["ink_mid"]}">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="148" viewBox="0 0 420 148">
  <rect width="420" height="148" fill="{t['canvas']}"/>
  <rect x="{px}" y="6" width="{pw}" height="134" rx="10" fill="{t['surface']}"/>
  <text x="{px + 22}" y="37" font-family="{FONT_SANS}" font-size="18" font-weight="650" letter-spacing="-0.3" fill="{t['ink']}">{escape(title)}</text>
  <text x="{px + pw - 22}" y="36.5" text-anchor="end" font-family="{FONT_SANS}" font-size="12" font-weight="500" fill="{t['accent']}">{escape(tag)}  ↗</text>
  {body}
  <text x="{px + 22}" y="123" font-family="{FONT_MONO}" font-size="10.5" fill="{t['ink_dim']}">{escape(meta)}</text>
</svg>
"""
    (ASSETS_DIR / f"{filename}-{suffix}.svg").write_text(svg)


def make_stack(t, suffix):
    rows = [
        ("Languages", "Python · TypeScript · Kotlin · C/C++ · SQL · C#",
         "Backend & Data", "Frappe/ERPNext · FastAPI · Node.js · PostgreSQL · SQLite · Redis"),
        ("Frontend & Mobile", "Next.js · React · Tailwind CSS · Jetpack Compose · Qt 6",
         "Infrastructure", "Linux · Docker · Kubernetes · Git · GitHub Actions"),
    ]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="114" viewBox="0 0 840 114">
  <rect width="840" height="114" fill="{t['canvas']}"/>
  <text x="16" y="22" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[0][0])}</text>
  <text x="16" y="42" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[0][1])}</text>

  <text x="384" y="22" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[0][2])}</text>
  <text x="384" y="42" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[0][3])}</text>

  <line x1="16" y1="58.5" x2="824" y2="58.5" stroke="{t['rule']}"/>

  <text x="16" y="78" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[1][0])}</text>
  <text x="16" y="98" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[1][1])}</text>

  <text x="384" y="78" font-family="{FONT_SANS}" font-size="11.5" font-weight="600" fill="{t['ink_dim']}">{escape(rows[1][2])}</text>
  <text x="384" y="98" font-family="{FONT_SANS}" font-size="13.2" fill="{t['ink']}">{escape(rows[1][3])}</text>
</svg>
"""
    (ASSETS_DIR / f"stack-{suffix}.svg").write_text(svg)


def picture_tag(base_name: str, alt: str, width: str = "100%") -> str:
    return (
        f'<picture>'
        f'<source media="(prefers-color-scheme: dark)" srcset="./assets/{base_name}-dark.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="./assets/{base_name}-light.svg">'
        f'<img src="./assets/{base_name}-dark.svg" alt="{escape(alt)}" width="{width}" align="top">'
        f'</picture>'
    )


def main():
    stats = fetch_github_stats()

    icon_email = '<rect x="1" y="3.5" width="16" height="11" rx="2"/><path d="M1.8 4.8L9 10l7.2-5.2"/>'
    icon_tg = '<path d="M16.5 2L1.5 8.2l4.9 1.8 7.8-5.6-5.5 6.6v4.1l2.6-2.6 3.2 2.4L16.5 2z"/>'
    icon_x = '<path d="M2.5 2h3.5l3.6 5.1L14 2h1.7l-5.2 6.1L16.1 16h-3.5l-4-5.6L3.8 16H2.1l5.6-6.6L2.5 2z"/>'

    for suffix, t in THEMES.items():
        make_header(t, suffix)
        make_social_icon_btn(t, suffix, "email", icon_email, 64, 16, 42, is_first=True)
        make_social_icon_btn(t, suffix, "telegram", icon_tg, 50, 4, 42)
        make_social_icon_btn(t, suffix, "x", icon_x, 50, 4, 42, fill_icon=True)
        make_social_spacer(t, suffix, 676)
        make_hex_terrain(t, suffix, stats)
        make_contributions_strip(t, suffix, stats)
        make_section_title(t, suffix, "work", "Selected work", "Click any project to open")
        make_hero_project(t, suffix, stats)
        make_half_project(
            t, suffix, "proj-bex", "bex", "Linux",
            [
                "Daemonless, rootless native Linux",
                "performance monitor with live CPU, memory,",
                "disk, network, thermal, and process views.",
            ],
            "C++20 · Qt 6 · CMake  ·  11 Qt test suites",
            side="left",
        )
        make_half_project(
            t, suffix, "proj-routegna", "RouteGna", "Web & API",
            [
                "Multi-tenant fleet, route optimization, and",
                "automated payroll platform with 6-tier RBAC,",
                "Redis caching, and containerized services.",
            ],
            "TypeScript · React · Node.js · PostgreSQL · FastAPI",
            side="right",
        )
        make_section_title(t, suffix, "stack", "Core stack", "")
        make_stack(t, suffix)

    readme = f"""<!-- profile:start -->
<div align="center">
{picture_tag("header", "Kidus Mesfin Mekuria — Software engineer building full-stack applications and systems software. Python, TypeScript, Kotlin, C++, Addis Ababa.")}
<a href="mailto:kidusmesfin27@gmail.com">{picture_tag("social-email", "Email: kidusmesfin27@gmail.com", "7.61%")}</a><a href="https://t.me/crosscodething">{picture_tag("social-telegram", "Telegram: t.me/crosscodething", "5.95%")}</a><a href="https://x.com/kidus_m27">{picture_tag("social-x", "X: @kidus_m27", "5.95%")}</a>{picture_tag("social-spacer", "", "80.47%")}
{picture_tag("hex-terrain", f"Commit terrain: 3D isometric hexagonal prism visualization of 52 completed weeks, peak {stats['max_day']}/day ({stats['peak_week']}/week), updated daily via GitHub Actions.")}
{picture_tag("stats", f"{stats['start_year']}–{stats['cur_year']} on GitHub: {stats['total_contribs']} contributions, {stats['merged_prs']} merged PRs, {stats['active_weeks']} of {stats['total_weeks']} active weeks, {stats['owned_repos']} repositories.")}
{picture_tag("sec-work", "Selected work")}
<a href="https://github.com/{USERNAME}/rebuild-android">{picture_tag("proj-rebuild", f"Rebuild ({USERNAME}/rebuild-android): Offline-first Android strength-training logbook in Kotlin, Jetpack Compose, and SQLite. 193ms to 40ms tab switch via Perfetto profiling, 340+ JVM/Robolectric tests, {stats['rebuild_tag']}.")}</a>
<a href="https://github.com/{USERNAME}/bex">{picture_tag("proj-bex", f"bex ({USERNAME}/bex): Daemonless, rootless native Linux performance monitor in C++20 and Qt 6 with live CPU, memory, disk, network, thermal, and process views and 11 Qt test suites.", "50%")}</a><a href="https://github.com/{USERNAME}/multi-fleet-managment">{picture_tag("proj-routegna", f"RouteGna ({USERNAME}/multi-fleet-managment): Multi-tenant fleet, route optimization, and automated payroll platform in TypeScript, React, Node.js, PostgreSQL, Redis, Docker, and FastAPI.", "50%")}</a>
{picture_tag("sec-stack", "Core stack")}
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
