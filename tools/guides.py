"""Evergreen guide pages (deals/guides/<slug>/index.html), in the homepage style.

Built on every run by home.build(), and listed in the sitemap and on the homepage.
Affiliate links for a guide go in its "links" dict; until a programme approves us the
guide names options neutrally, with no link.
"""
import home

GUIDES = [
    {
        "slug": "used-car-checklist",
        "title": "Buying a Used Car in the UK: The Complete Checklist",
        "short": "Used car buying checklist",
        "desc": "A step-by-step UK checklist for buying a used car: free GOV.UK MOT history checks, vehicle history checks, "
                "what to look at on a viewing, test drive tips, paying safely and what to do after you buy.",
        "updated": "2026-10-08",
        # filled in when an affiliate programme approves us (e.g. carVertical)
        "links": {"history_check": None},
        # roundups to recommend on the guide (day keys under deals/)
        "related": ["2026-10-08-b"],
    },
]


def _history_check_box(link):
    if link:
        cta = (f'<a class="btn" href="{home.e(link)}" rel="sponsored nofollow noopener" target="_blank">'
               'Run a vehicle history check &rsaquo;</a><p class="small">Affiliate link (#ad).</p>')
    else:
        cta = ('<p class="small">Paid checks are available from several UK providers (for example HPI, the AA, RAC and '
               'carVertical). Use one that covers outstanding finance, write-off records and stolen markers.</p>')
    return ('<div class="callout"><h3>&#128269; Do a full vehicle history check</h3><p>The free GOV.UK checks don\'t tell you '
            'about <strong>outstanding finance</strong>, <strong>insurance write-offs</strong>, <strong>stolen markers</strong> '
            'or <strong>number plate changes</strong>. A paid history check does, and costs far less than getting it wrong.</p>'
            f'{cta}</div>')


def _related_box(g):
    """Cards linking to related Amazon roundups (title and pin from each day's data file)."""
    import json
    cards = []
    for k in g.get("related", []):
        f = home.DATA / f"{k}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        url = f"{home.SITE}/{k}/"
        names = ", ".join(p.get("short_name") or p["name"] for p in d["products"][:4])
        cards.append(f'<a class="rel" href="{url}"><img src="{url}pin.jpg" alt="" loading="lazy"><span><strong>{home.e(d["pin_title"])}</strong>'
                     f'<small>{home.e(names)} and more</small><em>See the list &rsaquo;</em></span></a>')
    if not cards:
        return ""
    return ('<div class="related"><h3>&#128663; Kit out your new car</h3><p>Once it&rsquo;s yours, these are the essentials UK drivers '
            'keep in the car, especially through winter.</p>' + "".join(cards) + "</div>")


def used_car_body(g):
    def step(n, title, items):
        lis = "".join(f'<li><label><input type="checkbox"> <span>{i}</span></label></li>' for i in items)
        return (f'<section class="step" id="step{n}"><div class="sn">{n}</div><div><h2>{title}</h2>'
                f'<ul class="check">{lis}</ul></div></section>')

    return "".join([
        '<div class="intro"><p>Buying second-hand can save thousands, but a car with hidden finance, a past write-off or a '
        'wound-back mileage can cost you dearly. Work through this checklist before you hand over any money. Tick items off '
        'as you go: your ticks are saved on this device, and the page prints neatly to take with you.</p>'
        '<div class="tools"><button onclick="window.print()">&#128424; Print checklist</button>'
        '<button onclick="clearTicks()">Clear ticks</button></div></div>',

        step(1, "Before you go: budget and research", [
            "Set a total budget that includes <strong>insurance, road tax (VED), fuel and a servicing fund</strong>, not just the price",
            "Get insurance quotes for the exact make, model and engine before you commit: they vary a lot",
            "Look up the model's common faults and recalls, and what a fair price is for its age and mileage",
            "Decide whether you'll buy from a <strong>dealer</strong> (more legal protection) or a <strong>private seller</strong> (often cheaper, fewer rights)",
        ]),

        step(2, "Free checks on GOV.UK (do these first)", [
            'Check the <strong>MOT history</strong> using the registration: <a href="https://www.gov.uk/check-mot-history" rel="noopener" target="_blank">gov.uk/check-mot-history</a>. Look at past failures, advisories and the mileage recorded at each test',
            "Make sure the mileage rises steadily from test to test: a drop or a long gap is a red flag",
            'Check the tax and MOT status and the vehicle details (colour, engine size, first registered): <a href="https://www.gov.uk/check-vehicle-tax" rel="noopener" target="_blank">gov.uk/check-vehicle-tax</a>',
            "Make sure the details match the advert. A different colour or engine size can mean a cloned car",
        ]),

        _history_check_box(g["links"].get("history_check")),

        step(3, "Paperwork and identity checks at the viewing", [
            "View the car <strong>at the seller's home address</strong>, in daylight, not in a car park or lay-by",
            "Ask for the <strong>V5C logbook</strong>: the name and address should match the seller and where you're viewing",
            "Check the <strong>VIN</strong> (vehicle identification number) on the V5C matches the car: usually at the bottom of the windscreen, on the door pillar and under the bonnet",
            "Hold the V5C up to the light and check it has a DVLA watermark. Never buy without a V5C",
            "Go through the <strong>service history</strong>, receipts and old MOT certificates: they should match the mileage",
            "Check there are <strong>two keys</strong>, plus the locking wheel nut key if fitted",
        ]),

        step(4, "Looking over the car", [
            "Start the engine <strong>from cold</strong> (put your hand on the bonnet first): listen for rattles and watch for smoke",
            "Check every <strong>warning light</strong> comes on with the ignition and then goes out",
            "Look for uneven panel gaps, mismatched paint or overspray: signs of accident repairs",
            "Check the <strong>tyres</strong>: at least 1.6mm of tread (the legal minimum) across the central three-quarters, with no cracks, and even wear (uneven wear can mean alignment problems)",
            "Look under the oil filler cap: a creamy, mayonnaise-like residue can point to head gasket trouble",
            "Check for damp carpets, musty smells or condensation, which can mean leaks",
            "Test the electrics: windows, mirrors, lights, wipers, air conditioning, heated screens and the infotainment",
        ]),

        step(5, "The test drive", [
            "Make sure you're <strong>insured</strong> to drive it: many policies only give third-party cover on other cars, or none",
            "Drive on a mix of roads, including a faster road, for at least 15-20 minutes",
            "Brakes should feel firm and stop straight, with no pulling, grinding or juddering",
            "Gears should change smoothly. On a manual, a clutch that bites very high can mean it needs replacing soon",
            "The car should track straight with no knocks over bumps, and the steering wheel should be centred",
            "Afterwards, look under the car for any fresh drips",
        ]),

        step(6, "Negotiating and paying safely", [
            "Use anything you've found (advisories, worn tyres, a service due) to <strong>negotiate</strong> the price",
            "Avoid carrying large amounts of cash. A bank transfer gives you a record. Be wary of anyone who wants an unusual payment method",
            "Get a <strong>written receipt</strong> with the date, price, registration, VIN, and both names and addresses",
            "<strong>Dealer:</strong> under the Consumer Rights Act 2015 the car must be of satisfactory quality, fit for purpose and as described, and you have a short-term right to reject within 30 days",
            "<strong>Private sale:</strong> the car must be as described and the seller must have the right to sell it, but you have far fewer rights, so the checks above matter even more",
        ]),

        step(7, "After you buy", [
            "<strong>Tax the car before you drive it</strong>: road tax doesn't transfer to a new keeper",
            "Make sure your <strong>insurance</strong> is in place before you drive away",
            "The seller should tell DVLA about the change of keeper, and give you the new keeper slip (V5C/2) to keep until your new V5C arrives",
            "Book a service if one is due, and note the date of the next MOT",
        ]),

        _related_box(g),

        '<div class="callout soft"><h3>&#128664; Red flags: walk away if&hellip;</h3><ul>'
        "<li>There's no V5C, or the seller's details don't match it</li>"
        "<li>The VIN doesn't match the paperwork, or looks tampered with</li>"
        "<li>The MOT history shows the mileage going down</li>"
        "<li>The seller won't let you view at their home or rushes you</li>"
        "<li>The history check shows outstanding finance, a write-off or a stolen marker</li></ul></div>",

        '<p class="small">This guide is general information to help you buy with care, not legal or financial advice. '
        f'Last updated {home.pretty(g["updated"])} {g["updated"][:4]}.</p>',
    ])


GUIDE_CSS = """
.gwrap{max-width:820px;margin:0 auto;padding-top:22px}
.intro p{font-size:17px}.tools{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 10px}
.tools button{font:600 14px Poppins,system-ui,sans-serif;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:9px 14px;cursor:pointer}
.step{display:grid;grid-template-columns:44px 1fr;gap:14px;background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:18px;margin:16px 0}
.sn{width:40px;height:40px;border-radius:50%;background:var(--red);color:#fff;font-family:'Archivo Black',sans-serif;display:grid;place-items:center}
.step h2{font-family:Georgia,serif;font-size:22px;margin:4px 0 8px}
.check{list-style:none;margin:0;padding:0}.check li{padding:7px 0;border-top:1px solid var(--border)}.check li:first-child{border-top:0}
.check label{display:flex;gap:10px;align-items:flex-start;cursor:pointer}.check input{width:18px;height:18px;margin-top:4px;accent-color:var(--blue);flex:none}
.check input:checked+span{color:var(--dim);text-decoration:line-through}
.check a{color:var(--blue)}
.callout{background:linear-gradient(135deg,var(--deep),var(--blue));color:#fff;border-radius:18px;padding:20px;margin:16px 0}
.callout h3{font-family:Georgia,serif;font-size:21px;margin:0 0 6px}.callout .btn{background:#fff;color:var(--deep);margin-top:6px}
.callout .small{color:var(--soft)}.callout.soft{background:var(--surface);color:var(--text);border:2px solid var(--red)}
.small{font-size:13px;color:var(--dim)}
.related{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:18px;margin:16px 0}
.related h3{font-family:Georgia,serif;font-size:21px;margin:0 0 4px}.related>p{margin:0 0 12px;color:var(--dim)}
.rel{display:grid;grid-template-columns:96px 1fr;gap:14px;align-items:center;text-decoration:none;border-top:1px solid var(--border);padding-top:12px}
.rel img{width:96px;aspect-ratio:2/3;object-fit:cover;border-radius:10px}.rel strong{display:block;font-size:17px}
.rel small{display:block;color:var(--dim);margin:2px 0 6px}.rel em{font-style:normal;color:var(--blue);font-weight:600}
@media print{.related{display:none}}
@media print{header.top,.chips,.disc,.tools,.follow,footer,.callout .btn{display:none!important}body{background:#fff;color:#000}
.step,.callout{break-inside:avoid;border:1px solid #999;box-shadow:none}.callout{background:#fff;color:#000}.callout .small{color:#333}}
"""

TICK_JS = """<script>
(function(){var k='ddk-'+location.pathname,boxes=[].slice.call(document.querySelectorAll('.check input'));
var s=[];try{s=JSON.parse(localStorage.getItem(k)||'[]')}catch(e){}
boxes.forEach(function(b,i){b.checked=!!s[i];b.addEventListener('change',function(){
try{localStorage.setItem(k,JSON.stringify(boxes.map(function(x){return x.checked})))}catch(e){}})});
window.clearTicks=function(){boxes.forEach(function(b){b.checked=false});try{localStorage.removeItem(k)}catch(e){}}})();
</script>"""

BODIES = {"used-car-checklist": used_car_body}


def build():
    for g in GUIDES:
        url = f"{home.SITE}/guides/{g['slug']}/"
        hero = (f'<div class="hero small"><div class="meta"><span class="pill">Guide</span></div><h1>{home.e(g["title"])}</h1>'
                f'<p>{home.e(g["desc"])}</p></div>')
        page = (home.head(f"{g['title']} | Daily Deals UK", g["desc"], url, f"{home.SITE}/guides/{g['slug']}/og.jpg")
                .replace("</style>", home.DAY_CSS + GUIDE_CSS + "</style>")
                + home.topbar(hero) + home.chips("") + '<div class="gwrap">' + BODIES[g["slug"]](g) + "</div>"
                + home.footer().replace("</body>", TICK_JS + "</body>"))
        out = home.DEALS / "guides" / g["slug"] / "index.html"
        if not (out.parent / "og.jpg").exists():
            make_og(g, out.parent / "og.jpg")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
    return GUIDES


def make_og(g, out):
    """1000x1500 pin image for a guide (blue style), made once."""
    from PIL import Image, ImageDraw, ImageFont
    F = "C:/Windows/Fonts/"
    f = lambda n, s: ImageFont.truetype(F + n, s)
    W, H, M = 1000, 1500, 64
    grad = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), "#0678FF"), Image.new("RGB", (W, H), "#0A3FA8"), grad)
    dr = ImageDraw.Draw(img)
    pf = f("segoeuib.ttf", 30)
    dr.rounded_rectangle([M, 60, M + dr.textlength("FREE UK GUIDE", font=pf) + 44, 114], radius=27, fill="#D0021B")
    dr.text((M + 22, 87), "FREE UK GUIDE", font=pf, fill="white", anchor="lm")
    y = 160
    for ln in ("Buying a", "Used Car?"):
        dr.text((M, y), ln, font=f("georgiab.ttf", 104), fill="white"); y += 116
    dr.text((M, y + 10), "The complete checklist", font=f("seguisb.ttf", 46), fill="#CFE3FF")
    dr.line([M, y + 84, M + 140, y + 84], fill="#F5D27A", width=5)
    top = y + 130
    dr.rounded_rectangle([M, top, W - M, H - 190], radius=32, fill="white")
    steps = ["Budget & research", "Free GOV.UK MOT history check", "Vehicle history check", "V5C & VIN checks",
             "Look the car over", "Test drive", "Pay safely", "Tax & insure before driving"]
    step = (H - 190 - top - 40) / len(steps)
    for i, s in enumerate(steps, 1):
        cy = int(top + 20 + step * (i - 0.5))
        dr.ellipse([M + 34, cy - 24, M + 82, cy + 24], fill="#D0021B")
        dr.text((M + 58, cy), "\u2713", font=f("seguisym.ttf", 30), fill="white", anchor="mm")
        dr.text((M + 104, cy), s, font=f("segoeuib.ttf", 38), fill="#14213D", anchor="lm")
    dr.rectangle([0, H - 130, W, H], fill="#0052CC")
    dr.text((M, H - 65), "DAILY DEALS UK", font=f("ariblk.ttf", 42), fill="white", anchor="lm")
    dr.text((W - M, H - 65), "Tap for the full list \u203A", font=f("seguisb.ttf", 30), fill="#CFE3FF", anchor="rm")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90, optimize=True)
