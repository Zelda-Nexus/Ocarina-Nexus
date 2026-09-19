"""Régénère site/assets/img/hyrule/hyrule-map.svg — le fond de carte visuel
uniquement. Les repères et leurs données (résumé, scène noclip) viennent de
gold.map_location via scripts/export_site_locations.py, pas de ce script :
ne relancer ceci que pour redessiner le dessin lui-meme.

Les contours de régions ne sont pas dessinés à la main : on part d'un polygone
de contrôle grossier (la géographie réelle d'Ocarina of Time), puis on applique
un déplacement fractal de point milieu pour obtenir des côtes irrégulières,
et enfin un lissage Catmull-Rom -> Bézier. Le même seed redonne la même carte.
"""

import math
import random

W, H = 1000, 640


# --------------------------------------------------------------------------
# géométrie
# --------------------------------------------------------------------------
def displace(points, iters=4, amp=26.0, rnd=None):
    """Déplacement de point milieu, perpendiculairement à chaque arête."""
    pts = list(points)
    for _ in range(iters):
        out = []
        n = len(pts)
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            out.append((ax, ay))
            mx, my = (ax + bx) / 2, (ay + by) / 2
            dx, dy = bx - ax, by - ay
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            d = rnd.uniform(-amp, amp) * min(1.0, ln / 55.0)
            out.append((mx + nx * d, my + ny * d))
        pts = out
        amp *= 0.6
    return pts


def catmull(points, tension=0.6):
    """Polygone fermé -> chemin SVG lissé."""
    n = len(points)
    d = [f"M{points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6 * tension, p1[1] + (p2[1] - p0[1]) / 6 * tension)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6 * tension, p2[1] - (p3[1] - p1[1]) / 6 * tension)
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    d.append("Z")
    return "".join(d)


def region(points, seed, iters=4, amp=26.0):
    rnd = random.Random(seed)
    pts = displace(points, iters, amp, rnd)
    return catmull(pts), pts


def inside(pt, poly):
    x, y = pt
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            c = not c
        j = i
    return c


def scatter(poly, n, seed, margin=16, min_dist=26):
    """Points pseudo-aléatoires à l'intérieur d'un polygone, espacés."""
    rnd = random.Random(seed)
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    out = []
    tries = 0
    while len(out) < n and tries < n * 400:
        tries += 1
        p = (rnd.uniform(x0, x1), rnd.uniform(y0, y1))
        if not inside(p, poly):
            continue
        if any(inside((p[0] + dx, p[1] + dy), poly) is False
               for dx, dy in ((-margin, 0), (margin, 0), (0, -margin), (0, margin))):
            continue
        if any(math.hypot(p[0] - q[0], p[1] - q[1]) < min_dist for q in out):
            continue
        out.append(p)
    return out


def ticks(poly, length=9, step=3, color="#7d6a4a", width=1.1, inward=True):
    """Petits traits perpendiculaires le long d'un contour : falaises gravées."""
    segs = []
    n = len(poly)
    for i in range(0, n, step):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = (dy / ln, -dx / ln) if inward else (-dy / ln, dx / ln)
        segs.append(f"M{ax:.1f} {ay:.1f}l{nx * length:.1f} {ny * length:.1f}")
    return (f'<path d="{"".join(segs)}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" opacity=".55"/>')


# --------------------------------------------------------------------------
# géographie d'Hyrule (polygones de contrôle)
# --------------------------------------------------------------------------
LAND = [(52, 320), (38, 206), (92, 122), (188, 78), (300, 66), (392, 40), (500, 52),
        (606, 32), (712, 54), (812, 40), (896, 82), (944, 150), (930, 214),
        (976, 262), (936, 336), (978, 420), (940, 500), (872, 564), (786, 592),
        (700, 618), (600, 592), (500, 620), (404, 600), (300, 596), (206, 546),
        (128, 490), (96, 404)]

DESERT = [(30, 258), (26, 176), (70, 120), (150, 100), (206, 132), (238, 106),
          (288, 158), (270, 212), (314, 252), (276, 302), (292, 354), (224, 386),
          (150, 372), (116, 392), (62, 348), (46, 296)]

MOUNT = [(618, 232), (628, 156), (676, 96), (740, 52), (800, 68), (848, 24),
         (908, 48), (944, 102), (988, 152), (956, 204), (980, 244), (908, 264),
         (846, 240), (776, 270), (716, 246), (662, 264)]

FOREST = [(664, 470), (674, 392), (706, 330), (768, 294), (820, 314), (872, 278),
          (936, 306), (962, 366), (992, 420), (958, 470), (988, 522), (928, 574),
          (862, 590), (800, 566), (742, 594), (690, 538)]

FIELD = [(298, 340), (312, 250), (352, 186), (420, 146), (500, 126), (566, 146),
         (596, 196), (650, 206), (688, 258), (662, 302), (702, 352), (672, 412),
         (606, 448), (556, 432), (512, 480), (436, 488), (368, 450), (320, 404)]

LAKE = [(330, 520), (352, 456), (408, 422), (468, 438), (520, 410), (588, 438),
        (626, 482), (670, 514), (632, 560), (648, 608), (566, 626), (494, 600),
        (420, 624), (360, 578)]

MEADOW = [(898, 336), (938, 330), (962, 362), (948, 392), (908, 392), (888, 364)]
KOKIRI = [(762, 438), (796, 422), (832, 440), (832, 476), (798, 492), (766, 474)]
CRATER = [(816, 70), (856, 50), (896, 66), (892, 96), (850, 106), (816, 96)]


def build():
    land_d, land_p = region(LAND, 3, iters=4, amp=16)
    des_d, des_p = region(DESERT, 11, iters=4, amp=46)
    mnt_d, mnt_p = region(MOUNT, 23, iters=4, amp=50)
    for_d, for_p = region(FOREST, 31, iters=4, amp=46)
    fld_d, fld_p = region(FIELD, 47, iters=4, amp=42)
    lak_d, lak_p = region(LAKE, 59, iters=4, amp=36)
    mea_d, _ = region(MEADOW, 71, iters=3, amp=8)
    kok_d, _ = region(KOKIRI, 83, iters=3, amp=8)
    cra_d, _ = region(CRATER, 97, iters=3, amp=7)

    trees = scatter(for_p, 74, 101, margin=12, min_dist=24)
    trees = [t for t in trees
             if not inside(t, [(p[0], p[1]) for p in region(MEADOW, 71, 3, 8)[1]])
             and not inside(t, [(p[0], p[1]) for p in region(KOKIRI, 83, 3, 8)[1]])]
    dunes = scatter(des_p, 17, 113, margin=16, min_dist=46)
    peaks = scatter(mnt_p, 16, 127, margin=18, min_dist=46)
    peaks = [p for p in peaks if not inside(p, region(CRATER, 97, 3, 7)[1])]
    grass = scatter(fld_p, 26, 139, margin=20, min_dist=48)

    def use(href, x, y, w, h):
        return f'<use href="#{href}" x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w}" height="{h}"/>'

    tree_g = "".join(use("tree", x, y, 18, 20) for x, y in trees)
    dune_g = "".join(use("dune", x, y, 44, 11) for x, y in dunes)
    peak_g = "".join(use("peak", x, y, 78 if i % 3 else 58, 47 if i % 3 else 35)
                     for i, (x, y) in enumerate(peaks))
    grass_g = "".join(
        f'<path d="M{x:.0f} {y:.0f}l-4 -7M{x:.0f} {y:.0f}l0 -9M{x:.0f} {y:.0f}l4 -7" '
        f'fill="none" stroke="#7c8b4d" stroke-width="1.4" stroke-linecap="round"/>'
        for x, y in grass)

    cliffs = (ticks(des_p, 8, 4, "#9a7f4c", 1.2)
              + ticks(mnt_p, 9, 4, "#7d6a4a", 1.3)
              + ticks(fld_p, 7, 5, "#6e7b41", 1.1)
              + ticks(for_p, 7, 5, "#3f5a2c", 1.1))

    return dict(land=land_d, desert=des_d, mount=mnt_d, forest=for_d, field=fld_d,
                lake=lak_d, meadow=mea_d, kokiri=kok_d, crater=cra_d,
                trees=tree_g, dunes=dune_g, peaks=peak_g, grass=grass_g, cliffs=cliffs)


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 640" role="img"
     aria-label="Carte dessinée du royaume d'Hyrule : désert Gerudo à l'ouest, plaine centrale, mont du Péril au nord-est, bois perdus à l'est, lac Hylia au sud.">
<title>Hyrule — carte du royaume</title>
<defs>
  <linearGradient id="vellum" x1="0" y1="0" x2=".85" y2="1">
    <stop offset="0" stop-color="#f2e7cd"/><stop offset=".5" stop-color="#e7d9b7"/>
    <stop offset="1" stop-color="#d4c095"/>
  </linearGradient>
  <linearGradient id="plain" x1="0" y1="0" x2=".4" y2="1">
    <stop offset="0" stop-color="#a9bd75"/><stop offset="1" stop-color="#93a962"/>
  </linearGradient>
  <linearGradient id="wood" x1=".2" y1="0" x2=".8" y2="1">
    <stop offset="0" stop-color="#6b8a4a"/><stop offset="1" stop-color="#4d6a37"/>
  </linearGradient>
  <linearGradient id="rock" x1=".1" y1="0" x2=".9" y2="1">
    <stop offset="0" stop-color="#c0ad8d"/><stop offset="1" stop-color="#9b8768"/>
  </linearGradient>
  <linearGradient id="sands" x1="0" y1="0" x2=".6" y2="1">
    <stop offset="0" stop-color="#e8d4a1"/><stop offset="1" stop-color="#cfb madeup"/>
  </linearGradient>
  <radialGradient id="deep" cx=".4" cy=".35" r=".8">
    <stop offset="0" stop-color="#8ab6c4"/><stop offset="1" stop-color="#4f8095"/>
  </radialGradient>
  <radialGradient id="vignette" cx=".5" cy=".45" r=".76">
    <stop offset=".5" stop-color="#000" stop-opacity="0"/>
    <stop offset="1" stop-color="#4a3819" stop-opacity=".42"/>
  </radialGradient>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="4" seed="9"/>
    <feColorMatrix type="saturate" values="0"/>
    <feComponentTransfer><feFuncA type="linear" slope=".2"/></feComponentTransfer>
  </filter>
  <filter id="inkedge" x="-6%" y="-6%" width="112%" height="112%">
    <feGaussianBlur stdDeviation="3.5" result="b"/>
    <feComposite in="SourceGraphic" in2="b" operator="over"/>
  </filter>
  <symbol id="tree" viewBox="0 0 20 22">
    <path d="M10 22v-7" stroke="#3d3018" stroke-width="1.7" fill="none" stroke-linecap="round"/>
    <path d="M10 1.5c3.3 0 5.8 2.1 5.8 4.8 0 .9.4 1.4 1.1 2 1.1 1 1.3 2.5.6 3.7-.9 1.3-2.5 1.7-3.8 1.1-.9-.4-1.6-.1-2.1.5-1 1-2.5 1-3.5 0-.5-.6-1.2-.9-2.1-.5-1.3.6-2.9.2-3.8-1.1-.7-1.2-.5-2.7.6-3.7.7-.6 1.1-1.1 1.1-2C3.9 3.6 6.7 1.5 10 1.5z"/>
  </symbol>
  <symbol id="peak" viewBox="0 0 40 24">
    <path d="M1 23 13.5 2.5l8.5 11.5 5-6.5L39 23z"/>
    <path d="M13.5 2.5 8 12h11z" fill="#f0e7ce" fill-opacity=".5"/>
  </symbol>
  <symbol id="dune" viewBox="0 0 40 10">
    <path d="M1 8c6-7 13-7 19 0M20 8c6-7 13-7 19 0" fill="none" stroke="#b0954f"
          stroke-width="1.6" stroke-linecap="round"/>
  </symbol>
</defs>

<rect width="1000" height="640" fill="url(#vellum)"/>
<g opacity=".35">
  <path d="M0 0h1000v640H0z" fill="none"/>
  <g stroke="#b6a276" stroke-width=".6" opacity=".5">
    {graticule}
  </g>
</g>

<!== masse continentale ==>
<path d="{land}" fill="#ded0ab" stroke="#8c7748" stroke-width="3"/>
<path d="{land}" fill="none" stroke="#8c7748" stroke-width="1" opacity=".45"
      transform="translate(6 7)"/>

<!== régions ==>
<path d="{desert}" fill="#e2cd97" stroke="#a98f57" stroke-width="2"/>
<path d="{mount}" fill="url(#rock)" stroke="#7d6a4a" stroke-width="2.2"/>
<path d="{forest}" fill="url(#wood)" stroke="#3f5a2c" stroke-width="2.2"/>
<path d="{field}" fill="url(#plain)" stroke="#6e7b41" stroke-width="2.4"/>
<path d="{lake}" fill="url(#deep)" stroke="#4a7688" stroke-width="2.4"/>
<path d="{meadow}" fill="#a9bd75" stroke="#6e7b41" stroke-width="1.6"/>
<path d="{kokiri}" fill="#a9bd75" stroke="#6e7b41" stroke-width="1.6"/>
{cliffs}

<!== gorge de la vallee Gerudo ==>
<path d="M258 286c26 2 52 10 74 24 16 10 28 22 36 36l-20 12c-8-14-20-26-34-34-18-10-38-16-58-18z"
      fill="#c9ad72" stroke="#8d7343" stroke-width="1.8"/>
<path d="M254 320c22 4 44 14 62 30 12 10 22 22 28 34l-22 6c-6-12-14-22-24-30-16-12-34-20-52-24z"
      fill="#c9ad72" stroke="#8d7343" stroke-width="1.8"/>
<g stroke="#7a6034" stroke-width="1.1" opacity=".6" fill="none">
  <path d="M270 300l6 10M292 306l5 10M314 316l5 11M334 330l4 11"/>
  <path d="M272 332l-5 10M296 340l-5 10M318 352l-5 10M338 368l-5 10"/>
</g>
<g stroke="#5c4a28" stroke-width="2">
  <path d="M296 302 310 338" stroke-width="2.6"/>
  <path d="M292 308 306 344"/>
  <path d="M291 312l16-4M295 322l16-4M299 332l16-4"/>
</g>
<!== relief ==>
<g fill="#8f7c5e" opacity=".92">{peaks}</g>
<path d="{crater}" fill="#8f6a48" stroke="#6d4f36" stroke-width="2"/>
<ellipse cx="856" cy="78" rx="26" ry="11" fill="#c2643c"/>
<path d="M840 58c5-12 12-18 9-29M868 56c4-10 10-15 8-25" fill="none" stroke="#efe8d3"
      stroke-width="3" stroke-linecap="round" opacity=".5"/>
<g opacity=".8">{dunes}</g>
<g fill="#4b6531">{trees}</g>
<g opacity=".55">{grass}</g>

<!== eaux courantes ==>
<g fill="none" stroke="#6fa0b2" stroke-linecap="round">
  <path d="M948 152c-20 28-50 46-82 60-34 16-66 25-98 32-28 6-54 9-80 9" stroke-width="8"/>
  <path d="M468 468c3 12 8 22 16 30" stroke-width="7"/>
  <path d="M272 352c-32 22-54 58-58 100-3 30 6 57 23 76" stroke-width="6" opacity=".9"/>
  <path d="M240 534c38 10 78 10 116 4" stroke-width="6" opacity=".9"/>
</g>
<g fill="none" stroke="#b9dbe4" stroke-width="2" stroke-linecap="round" opacity=".6">
  <path d="M948 152c-20 28-50 46-82 60-34 16-66 25-98 32-28 6-54 9-80 9"/>
</g>

<!== routes ==>
<g fill="none" stroke="#9d7f4d" stroke-width="4" stroke-linecap="round"
   stroke-dasharray="2 10" opacity=".85">
  <path d="M494 336 478 212"/>
  <path d="M556 302c44-24 94-58 136-88"/>
  <path d="M596 396c52 20 108 40 164 52"/>
  <path d="M470 404c6 24 3 44-2 62"/>
  <path d="M366 358c-30-8-64-12-98-14"/>
  <path d="M494 336 452 362"/>
</g>

<!== ponts ==>
<g stroke="#8d7343" stroke-width="2" fill="#dcc79a">
  <path d="M316 336l26 14-6 10-26-14z"/>
  <path d="M462 462h18v12h-18z"/>
</g>

<!== repères dépendant de l'époque ==>
<g class="era-layer era-child">
  <g transform="translate(470 176)">
    <path d="M-28 15h56v-21l-9-7v-13l-10 7-9-11-9 11-10-7v13l-9 7z" fill="#f0e6ca"
          stroke="#5c5138" stroke-width="2.2"/>
    <path d="M-10 15v-14h20v14" fill="#c8b68c" stroke="#5c5138" stroke-width="1.4"/>
    <path d="M0-46v-13" stroke="#5c5138" stroke-width="2"/><circle cy="-61" r="4" fill="#c9a227"/>
  </g>
  <g transform="translate(512 216)">
    <path d="M-15 12h30l-4-20-11-9-11 9z" fill="#f0e6ca" stroke="#5c5138" stroke-width="2"/>
    <path d="M0-23v-9" stroke="#5c5138" stroke-width="2"/>
  </g>
</g>
<g class="era-layer era-adult">
  <path d="{mount}" fill="#5a3f2e" opacity=".18"/>
  <path d="{field}" fill="#4a3a2c" opacity=".14"/>
  <g transform="translate(470 176)">
    <path d="M-26 16h52l-9-32 7-13-16-5-8-20-8 20-16 5 7 13z" fill="#3a2f3f"
          stroke="#18121f" stroke-width="2.2"/>
    <path d="M0-54v-14" stroke="#8d2f2f" stroke-width="3"/>
    <path d="M-40 16c14-10 26-14 40-14s26 4 40 14" fill="none" stroke="#18121f"
          stroke-width="1.6" opacity=".7"/>
  </g>
  <g transform="translate(512 216)">
    <path d="M-15 12h30l-4-20-11-9-11 9z" fill="#ddd0b0" stroke="#5c5138"
          stroke-width="2" stroke-dasharray="5 4"/>
  </g>
</g>

<!== toponymes gravés ==>
<g font-family="Cinzel,Spectral,Georgia,serif" fill="#473a22" text-anchor="middle">
  <text x="492" y="306" font-size="20" letter-spacing="6" opacity=".62">PLAINE D'HYRULE</text>
  <text x="150" y="250" font-size="13" letter-spacing="4" opacity=".6">DÉSERT HANTÉ</text>
  <text x="826" y="196" font-size="13" letter-spacing="4" opacity=".62" fill="#3d3221">MONT DU PÉRIL</text>
  <text x="862" y="512" font-size="13" letter-spacing="4" opacity=".7" fill="#e6efd6">BOIS PERDUS</text>
  <text x="492" y="556" font-size="13" letter-spacing="4" opacity=".8" fill="#e2f0f4">LAC HYLIA</text>
  <text x="248" y="410" font-size="10" letter-spacing="3" opacity=".6">VALLÉE GERUDO</text>
</g>

<!== rose des vents ==>
<g transform="translate(126 506)" opacity=".62">
  <circle r="44" fill="none" stroke="#6b5a38" stroke-width="1.3"/>
  <circle r="34" fill="none" stroke="#6b5a38" stroke-width=".7" stroke-dasharray="2 7"/>
  <path d="M0-42 9-7 0 0-9-7z" fill="#473a22"/>
  <path d="M0 42 9 7 0 0-9 7z" fill="#473a22" opacity=".4"/>
  <path d="M42 0 7 9 0 0 7-9z" fill="#473a22" opacity=".4"/>
  <path d="M-42 0-7 9 0 0-7-9z" fill="#473a22" opacity=".4"/>
  <text y="-49" text-anchor="middle" font-family="Cinzel,Georgia,serif" font-size="12"
        fill="#473a22">N</text>
</g>

<!== cartouche ==>
<g transform="translate(168 598)" opacity=".9">
  <path d="M-126-23h252l11 23-11 23h-252l-11-23z" fill="#eadfc0" stroke="#6b5a38" stroke-width="1.6"/>
  <path d="M-118-15h236M-118 15h236" stroke="#6b5a38" stroke-width=".6" opacity=".5"/>
  <text text-anchor="middle" y="8" font-family="'Cinzel Decorative',Cinzel,Georgia,serif"
        font-size="25" letter-spacing="11" fill="#473a22">HYRULE</text>
</g>

<rect width="1000" height="640" filter="url(#grain)" opacity=".22" pointer-events="none"/>
<rect width="1000" height="640" fill="url(#vignette)" pointer-events="none"/>
<rect x="10" y="10" width="980" height="620" fill="none" stroke="#6b5a38" stroke-width="2.2" opacity=".65"/>
<rect x="18" y="18" width="964" height="604" fill="none" stroke="#6b5a38" stroke-width=".8" opacity=".45"/>
</svg>
"""


def main():
    parts = build()
    grat = []
    for x in range(100, 1000, 100):
        grat.append(f'<path d="M{x} 20V620"/>')
    for y in range(80, 640, 100):
        grat.append(f'<path d="M20 {y}H980"/>')
    svg = SVG.format(graticule="".join(grat), **parts)
    svg = svg.replace("#cfb madeup", "#cbb075")
    svg = svg.replace("<!==", "<!--").replace("==>", "-->")
    out = "site/assets/img/hyrule/hyrule-map.svg"
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{out}: {len(svg)} octets")


if __name__ == "__main__":
    main()
