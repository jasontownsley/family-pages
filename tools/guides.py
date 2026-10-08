"""Evergreen guide pages (deals/guides/<slug>/index.html), in the homepage style.

Built on every run by home.build(), and listed in the sitemap and on the homepage.
Affiliate links for a guide go in its "links" dict; until a programme approves us the
guide names options neutrally, with no link.
"""
import home

GUIDES = [
    {
        "slug": "christmas-gift-guide",
        "title": "Christmas Gift Ideas UK 2026: For Her, Him, Kids & Stocking Fillers",
        "short": "Christmas gift guide 2026",
        "desc": "Our hand-picked Christmas gift ideas for 2026: gifts for her, for him, for kids, for the home, stocking fillers "
                "under \u00a315 and show-stopper hampers, from UK shops including Cadbury, Yankee Candle, Bare Kind and Amazon.",
        "updated": "2026-10-08",
        "links": {},
        "related": [],
        "og": {"pill": "CHRISTMAS 2026", "lines": ["Christmas", "Gift Ideas"], "sub": "Hand-picked for 2026",
               "items": ["Gifts for her", "Gifts for him", "Gifts for kids", "For the home & host",
                         "Stocking fillers under \u00a315", "Show-stopper hampers"]},
    },
    {
        "slug": "used-car-checklist",
        "title": "Buying a Used Car in the UK: The Complete Checklist",
        "short": "Used car buying checklist",
        "desc": "A step-by-step UK checklist for buying a used car: free GOV.UK MOT history checks, vehicle history checks, "
                "what to look at on a viewing, test drive tips, paying safely and what to do after you buy.",
        "updated": "2026-10-08",
        # filled in when an affiliate programme approves us (e.g. carVertical)
        # history_check: carVertical AFFILIATE link once approved (then the button is marked #ad);
        # history_check_site: plain link used until then
        "links": {"history_check": None, "history_check_site": "https://www.carvertical.com/gb"},
        # roundups to recommend on the guide (day keys under deals/)
        "related": ["2026-10-08-b"],
        "og": {"pill": "FREE UK GUIDE", "lines": ["Buying a", "Used Car?"], "sub": "The complete checklist",
               "items": ["Budget & research", "Free GOV.UK MOT history check", "Vehicle history check", "V5C & VIN checks",
                         "Look the car over", "Test drive", "Pay safely", "Tax & insure before driving"]},
    },
    {
        "slug": "travel-esim",
        "title": "Travel eSIMs Explained: Cheaper Mobile Data Abroad",
        "short": "Travel eSIMs explained",
        "desc": "How a travel eSIM works, why it can cost far less than roaming, and how to set one up in minutes before you fly. "
                "No contract, keep your UK number, top up in an app.",
        "updated": "2026-10-08",
        # affiliate links go in saily / breeze once approved on Awin (then marked #ad); *_site are plain links until then
        "links": {"saily": None, "saily_site": "https://saily.com/",
                  "breeze": None, "breeze_site": "https://www.breezesim.com/"},
        "related": [],
        "og": {"pill": "TRAVEL GUIDE", "lines": ["Travel", "eSIMs"], "sub": "Cheaper data abroad",
               "items": ["No contract", "Keep your UK number", "Set up before you fly", "Data in 190+ countries",
                         "Top up in the app", "No surprise roaming bills"]},
    },
]


def _history_check_box(links):
    aff, site = links.get("history_check"), links.get("history_check_site")
    if aff or site:
        rel = "sponsored nofollow noopener" if aff else "noopener"
        note = ("Affiliate link (#ad): we may earn a small commission, at no extra cost to you." if aff else
                "Other providers such as HPI, the AA and the RAC offer checks too. Whichever you use, make sure it covers "
                "outstanding finance, write-offs and stolen markers.")
        cta = (f'<p>We recommend <strong>carVertical</strong>: enter the registration and you get a report covering '
               f'outstanding finance, write-off records, stolen markers, mileage history and more.</p>'
               f'<a class="btn" href="{home.e(aff or site)}" rel="{rel}" target="_blank">Check a car with carVertical &rsaquo;</a>'
               f'<p class="small">{note}</p>')
    else:
        cta = ('<p class="small">Paid checks are available from several UK providers (for example HPI, the AA, RAC and '
               'carVertical). Use one that covers outstanding finance, write-off records and stolen markers.</p>')
    return ('<div class="callout"><h3>&#128269; Do a full vehicle history check</h3><p>The free GOV.UK checks don&rsquo;t tell you '
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

        _history_check_box(g["links"]),

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


# ---------------------------------------------------------------- eSIM phone checker
# Conservative list of UK models known to support eSIM (phone must also be unlocked).
# Anything not listed gets the *#06# EID test rather than a guess. "no" = known not to support eSIM.
ESIM_DEVICES = {
    "Apple iPhone": {
        "yes": ["iPhone 17 Pro Max", "iPhone 17 Pro", "iPhone Air", "iPhone 17", "iPhone 16e", "iPhone 16 Pro Max", "iPhone 16 Pro",
                "iPhone 16 Plus", "iPhone 16", "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15 Plus", "iPhone 15",
                "iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14 Plus", "iPhone 14", "iPhone SE (3rd gen, 2022)",
                "iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13", "iPhone 13 mini", "iPhone 12 Pro Max", "iPhone 12 Pro",
                "iPhone 12", "iPhone 12 mini", "iPhone SE (2nd gen, 2020)", "iPhone 11 Pro Max", "iPhone 11 Pro", "iPhone 11",
                "iPhone XS Max", "iPhone XS", "iPhone XR"],
        "no": ["iPhone X", "iPhone 8 Plus", "iPhone 8", "iPhone 7 or older", "iPhone SE (1st gen, 2016)"],
    },
    "Google Pixel": {
        "yes": ["Pixel 10 Pro Fold", "Pixel 10 Pro XL", "Pixel 10 Pro", "Pixel 10", "Pixel 9a", "Pixel 9 Pro Fold", "Pixel 9 Pro XL",
                "Pixel 9 Pro", "Pixel 9", "Pixel 8a", "Pixel 8 Pro", "Pixel 8", "Pixel Fold", "Pixel 7a", "Pixel 7 Pro", "Pixel 7",
                "Pixel 6a", "Pixel 6 Pro", "Pixel 6", "Pixel 5a", "Pixel 5", "Pixel 4a 5G", "Pixel 4a", "Pixel 4 XL", "Pixel 4",
                "Pixel 3a XL", "Pixel 3a", "Pixel 3 XL", "Pixel 3"],
        "no": ["Pixel 2 or older"],
    },
    "Samsung Galaxy": {
        "yes": ["Galaxy S25 Ultra", "Galaxy S25 Edge", "Galaxy S25+", "Galaxy S25", "Galaxy S24 Ultra", "Galaxy S24+", "Galaxy S24",
                "Galaxy S23 Ultra", "Galaxy S23+", "Galaxy S23", "Galaxy S22 Ultra", "Galaxy S22+", "Galaxy S22",
                "Galaxy S21 Ultra", "Galaxy S21+", "Galaxy S21", "Galaxy S20 Ultra", "Galaxy S20+", "Galaxy S20",
                "Galaxy Z Fold7", "Galaxy Z Fold6", "Galaxy Z Fold5", "Galaxy Z Fold4", "Galaxy Z Fold3", "Galaxy Z Fold2",
                "Galaxy Z Flip7", "Galaxy Z Flip6", "Galaxy Z Flip5", "Galaxy Z Flip4", "Galaxy Z Flip3", "Galaxy Z Flip",
                "Galaxy Note20 Ultra", "Galaxy Note20"],
        "no": [],
    },
}
# Android model codes (navigator.userAgentData) -> model name, for auto-detect
SAMSUNG_CODES = {
    "SM-S938": "Galaxy S25 Ultra", "SM-S937": "Galaxy S25 Edge", "SM-S936": "Galaxy S25+", "SM-S931": "Galaxy S25",
    "SM-S928": "Galaxy S24 Ultra", "SM-S926": "Galaxy S24+", "SM-S921": "Galaxy S24",
    "SM-S918": "Galaxy S23 Ultra", "SM-S916": "Galaxy S23+", "SM-S911": "Galaxy S23",
    "SM-S908": "Galaxy S22 Ultra", "SM-S906": "Galaxy S22+", "SM-S901": "Galaxy S22",
    "SM-G998": "Galaxy S21 Ultra", "SM-G996": "Galaxy S21+", "SM-G991": "Galaxy S21",
    "SM-G988": "Galaxy S20 Ultra", "SM-G986": "Galaxy S20+", "SM-G985": "Galaxy S20+", "SM-G981": "Galaxy S20", "SM-G980": "Galaxy S20",
    "SM-F966": "Galaxy Z Fold7", "SM-F956": "Galaxy Z Fold6", "SM-F946": "Galaxy Z Fold5", "SM-F936": "Galaxy Z Fold4",
    "SM-F926": "Galaxy Z Fold3", "SM-F916": "Galaxy Z Fold2", "SM-F766": "Galaxy Z Flip7", "SM-F741": "Galaxy Z Flip6",
    "SM-F731": "Galaxy Z Flip5", "SM-F721": "Galaxy Z Flip4", "SM-F711": "Galaxy Z Flip3", "SM-F707": "Galaxy Z Flip", "SM-F700": "Galaxy Z Flip",
    "SM-N986": "Galaxy Note20 Ultra", "SM-N985": "Galaxy Note20 Ultra", "SM-N981": "Galaxy Note20", "SM-N980": "Galaxy Note20",
}


def esim_checker():
    import json
    data = json.dumps({"devices": ESIM_DEVICES, "samsung": SAMSUNG_CODES})
    return ("""<section class="checker" id="checker"><h2>&#128241; Is my phone eSIM compatible?</h2>
<p>Pick your phone below for an instant answer.</p><p class="detect" id="esimDetect" hidden></p>
<div class="selects"><label>Brand<select id="esimBrand"><option value="">Choose brand&hellip;</option></select></label>
<label>Model<select id="esimModel" disabled><option value="">Choose model&hellip;</option></select></label></div>
<div class="result" id="esimResult" hidden></div>
<p class="small">Based on UK models. Your phone also needs to be <strong>unlocked</strong> (not tied to one network). Some phones
sold outside the UK, for example in mainland China or Hong Kong, may not support eSIM.</p></section>
<script>(function(){var D=""" + data + """,b=document.getElementById('esimBrand'),m=document.getElementById('esimModel'),
r=document.getElementById('esimResult'),det=document.getElementById('esimDetect');
var test='<p><strong>Quick test:</strong> open your phone&rsquo;s dialler and type <strong>*#06#</strong>. If you see an <strong>EID</strong> number, your phone supports eSIM.</p>';
Object.keys(D.devices).concat(['Other brand']).forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=k;b.appendChild(o)});
function fill(){m.innerHTML='<option value="">Choose model&hellip;</option>';var d=D.devices[b.value];r.hidden=true;
if(b.value==='Other brand'){m.disabled=true;show('maybe');return}
if(!d){m.disabled=true;return}m.disabled=false;
d.yes.concat(d.no).concat(['My model isn\\u2019t listed']).forEach(function(x){var o=document.createElement('option');o.value=x;o.textContent=x;m.appendChild(o)})}
function show(kind,name){r.hidden=false;r.className='result '+kind;
if(kind==='yes'){r.innerHTML='<h3>&#9989; Yes &ndash; the '+name+' supports eSIM</h3><p>As long as it&rsquo;s unlocked, you can use a travel eSIM on this phone.</p><a class="btn" href="#picks">See travel eSIM plans &rsaquo;</a>'}
else if(kind==='no'){r.innerHTML='<h3>&#10060; Sorry &ndash; the '+name+' doesn&rsquo;t support eSIM</h3><p>You&rsquo;d need a physical travel SIM, or a newer phone. Check your network&rsquo;s roaming add-ons before you go.</p>'}
else{r.innerHTML='<h3>&#129300; Not sure? It&rsquo;s easy to check</h3>'+test+'<a class="btn" href="#picks">See travel eSIM plans &rsaquo;</a>'}}
b.addEventListener('change',fill);
m.addEventListener('change',function(){var d=D.devices[b.value],v=m.value;if(!v){r.hidden=true;return}
show(d.yes.indexOf(v)>=0?'yes':(d.no.indexOf(v)>=0?'no':'maybe'),v)});
function pick(brand,model){b.value=brand;fill();if(model){m.value=model;m.dispatchEvent(new Event('change'))}}
var ua=navigator.userAgent||'';
if(/iPhone/.test(ua)){pick('Apple iPhone');det.hidden=false;det.textContent='You seem to be on an iPhone \\u2013 choose your model below.'}
else if(navigator.userAgentData&&navigator.userAgentData.getHighEntropyValues){
navigator.userAgentData.getHighEntropyValues(['model']).then(function(v){var mo=(v.model||'').trim();if(!mo)return;
var px=mo.match(/^Pixel.*/);if(px&&D.devices['Google Pixel'].yes.indexOf(mo)>=0){pick('Google Pixel',mo);det.hidden=false;det.textContent='We think you\\u2019re on a Google '+mo+'.';return}
var c=mo.slice(0,7).toUpperCase();if(D.samsung[c]){pick('Samsung Galaxy',D.samsung[c]);det.hidden=false;det.textContent='We think you\\u2019re on a Samsung '+D.samsung[c]+'.'}}).catch(function(){})}
})();</script>""")


def _provider_card(name, link, site, tagline, points):
    href, rel = (link, "sponsored nofollow noopener") if link else (site, "noopener")
    lis = "".join(f"<li>{p}</li>" for p in points)
    note = '<p class="small">Affiliate link (#ad).</p>' if link else ""
    return (f'<div class="prov"><h3>{name}</h3><p class="tag2">{tagline}</p><ul>{lis}</ul>'
            f'<a class="btn" href="{home.e(href)}" rel="{rel}" target="_blank">See {name} plans &rsaquo;</a>{note}</div>')


def esim_body(g):
    L = g["links"]

    def tick(items):
        return '<ul class="check">' + "".join(
            f'<li><label><input type="checkbox"> <span>{i}</span></label></li>' for i in items) + "</ul>"

    return "".join([
        '<div class="intro"><p>Coming home from holiday to a big phone bill is a feeling most of us know. A travel eSIM is a simple '
        'way to avoid it: you buy a data plan for where you are going, install it on your phone in a few minutes, and use local-rate '
        'data while you are away, with your normal UK number still working.</p></div>',

        '<section class="step"><div class="sn">?</div><div><h2>What is an eSIM?</h2>'
        '<p>An eSIM is a digital SIM built into your phone. Instead of a plastic card, you download a mobile plan by scanning a QR code '
        'or tapping a button in an app. Most phones can hold several eSIMs alongside your normal SIM, so you can add a travel data plan '
        '<strong>without removing your UK SIM or changing your number</strong>.</p>'
        '<p>Travel eSIMs are usually <strong>data-only</strong>. You use the data for maps, browsing, WhatsApp, FaceTime and other apps, '
        'while your UK number can stay switched on in the background for texts such as bank security codes.</p></div></section>',

        esim_checker(),

        '<section class="step"><div class="sn">&pound;</div><div><h2>Why it saves money</h2>'
        '<p>Since Brexit, UK networks are free to charge for roaming in Europe again, and most do. Many charge a daily fee, typically '
        '<strong>around &pound;2 to &pound;3 a day</strong> in Europe, and outside Europe (the USA, Turkey, Dubai, Asia and so on) roaming '
        'can cost a lot more. Prices depend on your network and when you joined, so check your own network\u2019s roaming page.</p>'
        '<div class="compare"><div><span class="lbl">Roaming, 14 days in Spain</span><strong>&pound;28 &ndash; &pound;42</strong>'
        '<small>at a typical &pound;2&ndash;&pound;3 a day</small></div><div class="vs">vs</div>'
        '<div class="win"><span class="lbl">Travel eSIM for Europe</span><strong>around &pound;10 &ndash; &pound;15</strong>'
        '<small>for a typical 10GB, 30-day plan</small></div></div>'
        '<p class="small">Illustrative example only. Roaming charges and eSIM prices change, so check current prices before you buy. '
        'Families can save even more, as a roaming charge applies to every phone.</p></div></section>',

        '<section class="step"><div class="sn">&#10003;</div><div><h2>The benefits at a glance</h2><ul class="ben">'
        '<li><strong>No contract</strong>: pay once for the data you need, with no subscription and no credit check.</li>'
        '<li><strong>Keep your UK number</strong>: your normal SIM stays in the phone for calls and texts.</li>'
        '<li><strong>Set up before you fly</strong>: no hunting for a local SIM shop at the airport.</li>'
        '<li><strong>Connected as you land</strong>: maps, taxi apps and messages work straight away.</li>'
        '<li><strong>No bill shock</strong>: you can only use what you have paid for, and you can top up in the app.</li>'
        '<li><strong>Works in lots of countries</strong>: single-country and regional plans (for example all of Europe) are available.</li>'
        '</ul></div></section>',

        '<section class="step"><div class="sn">4</div><div><h2>How to set one up (about 5 minutes)</h2>'
        '<ol class="howto">'
        '<li><strong>Check your phone supports eSIM and is unlocked.</strong> Most iPhones from 2018 onwards and most recent Android '
        'phones do. Use <a href="#checker">our checker above</a>, or dial <strong>*#06#</strong>: if you see an <strong>EID</strong> number, your phone supports eSIM.</li>'
        '<li><strong>Choose a plan</strong> for your destination: how much data and for how many days.</li>'
        '<li><strong>Install it at home on Wi-Fi</strong> before you travel, by scanning the QR code or tapping install in the app. '
        'It will not start using data until you switch to it abroad.</li>'
        '<li><strong>When you land</strong>, set the travel eSIM as your mobile data line and turn on data roaming <em>for the eSIM</em>. '
        'Turn data roaming <strong>off</strong> on your UK SIM so you are not charged for data on it.</li>'
        '</ol></div></section>',

        '<h2 class="ph2" id="picks">Our picks</h2><div class="provs">',
        _provider_card("Saily", L.get("saily"), L.get("saily_site"), "From the team behind NordVPN", [
            "Plans for 200+ destinations, according to Saily",
            "Everything runs in the Saily app: buy, install and top up",
            "Switch between country plans without installing a new eSIM",
            "Optional extras including ad and tracker blocking, and a virtual location feature",
            "24/7 support in the app",
        ]),
        _provider_card("Breeze", L.get("breeze"), L.get("breeze_site"), "Simple, no-contract travel data", [
            "Data plans for 190+ countries, including regional plans such as Europe",
            "No contract, with instant activation by QR code",
            "Usage alerts, and you are never charged beyond the plan you bought",
            "Save 10% when you buy 2 or more plans, handy for families",
            "Top up or add another plan when you need more",
        ]),
        '</div>',

        '<section class="step"><div class="sn">&#9992;</div><div><h2>Before you fly: eSIM checklist</h2>',
        tick([
            "Phone is <strong>unlocked</strong> and supports eSIM (dial *#06# and look for an EID)",
            "Plan bought for the right country or region, with enough data for the trip",
            "eSIM <strong>installed at home on Wi-Fi</strong>, and labelled something like \u201cTravel\u201d",
            "Know how to switch your mobile data line to the eSIM when you land",
            "Data roaming on your UK SIM set to <strong>off</strong> (calls and texts can stay on)",
            "WhatsApp or FaceTime set up for calls home over data",
            "Offline maps downloaded as a backup",
        ]),
        '</div></section>',

        '<section class="step"><div class="sn">FAQ</div><div><h2>Quick answers</h2>'
        '<p><strong>Will I still get texts to my UK number?</strong> Usually yes, if your UK SIM stays switched on. Receiving texts abroad '
        'is often free, but check your network\u2019s roaming terms.</p>'
        '<p><strong>Can I make normal phone calls on a travel eSIM?</strong> Most travel eSIMs are data-only, so use WhatsApp, FaceTime '
        'or similar apps for calls.</p>'
        '<p><strong>Can I use it again on my next trip?</strong> Often yes: many apps let you top up or buy a new plan for the same eSIM.</p>'
        '<p><strong>Does it work for the whole family?</strong> Each phone needs its own plan, and some providers give a discount for '
        'buying several.</p></div></section>',

        '<p class="small">This guide is general information, not financial advice. Features, coverage and prices are as stated by each '
        f'provider and can change, so check before you buy. Last updated {home.pretty(g["updated"])} {g["updated"][:4]}.</p>',
    ])


# ---------------------------------------------------------------- Christmas gift guide (article with in-text links)
AMAZON_TAG = "dailydeal07d1-21"
KIND_EMOJI = {"Cosy": "&#128715;&#65039;", "Drinks": "&#129347;", "Winter": "&#129507;", "Games": "&#127922;",
              "Decor": "&#10024;", "Bath & body": "&#129506;"}


def _item_url(it):
    return f"https://www.amazon.co.uk/dp/{it['asin']}?tag={AMAZON_TAG}" if it["src"] == "amazon" else it["url"]


def _a(it, text=None):
    return (f'<a href="{home.e(_item_url(it))}" rel="sponsored nofollow noopener" target="_blank">'
            f'{home.e(text or it["name"])}</a>')


def _band(it):
    if it["src"] != "awin":
        return ""
    p = it["price"]
    return next(b for lim, b in ((10, "Under &pound;10"), (15, "Under &pound;15"), (20, "Under &pound;20"), (30, "Under &pound;30"),
                                 (50, "Under &pound;50"), (10**9, "&pound;50+")) if p < lim)


def _card(it):
    if it["src"] == "awin":
        pic = f'<img src="img/{home.e(it["key"])}.jpg" alt="{home.e(it["name"])}" loading="lazy">'
    else:
        pic = f'<span class="emo">{KIND_EMOJI.get(it.get("kind"), "&#127873;")}</span>'
    band = _band(it)
    return (f'<article class="pcard"><a class="ph{"" if it["src"] == "awin" else " noimg"}" href="{home.e(_item_url(it))}" '
            f'rel="sponsored nofollow noopener" target="_blank">{pic}{f"<span class=tag>{band}</span>" if band else ""}</a>'
            f'<div class="pb"><span class="brand">{home.e(it.get("kind") or it["shop"])}</span><h3>{home.e(it["name"])}</h3>'
            f'<p class="kind">From {home.e(it["shop"])}</p>{home.price_html(it["key"][3:]) if it["src"] == "awin" else ""}'
            f'<p class="why">{home.e(it["why"])}</p>'
            f'<a class="btn" href="{home.e(_item_url(it))}" rel="sponsored nofollow noopener" target="_blank">'
            f'See it at {home.e(it["shop"])} &rsaquo;</a></div></article>')


def xmas_body(g):
    import json
    d = json.loads((home.DATA / "guide-christmas.json").read_text(encoding="utf-8"))
    secs = d["sections"]
    find = {it["key"]: it for s in secs for it in s["items"]}
    top = [("Best for her", "B0FF4LX6V5"), ("Best for him", "aw-53984693911937"), ("Best for kids", "aw-36225688688"),
           ("Best for the home", "aw-38031934423195"), ("Best show-stopper", "aw-27900252065")]
    out = ['<div class="intro"><p>Christmas shopping doesn&rsquo;t need to mean hours of scrolling. We&rsquo;ve picked the gifts '
           'we&rsquo;d genuinely be happy to give this year, from cosy treats like a '
           f'{_a(find["B0FF4LX6V5"], "heated throw")} to a classic {_a(find["aw-44777982177"], "tub of Cadbury Roses")} for the '
           'stocking. Everything comes from well-known UK shops, and every Amazon pick has hundreds or thousands of good reviews.</p>'
           '<p class="small">Prices and stock change quickly in the run-up to Christmas, so check the latest price and the last '
           'order dates for Christmas delivery on each shop&rsquo;s site.</p></div>']
    pr = home.prices()
    out.append(home.offers_strip(pr, [], []))
    out.append('<div class="toppicks"><h2>&#11088; Our top picks</h2><ol>' + "".join(
        f'<li><strong>{lab}:</strong> {_a(find[k])}</li>' for lab, k in top) + "</ol></div>")
    out.append('<nav class="jump">' + "".join(f'<a href="#{s["id"]}">{s["title"]}</a>' for s in secs) +
               '<a href="#quick">Quick picks table</a></nav>')
    for s in secs:
        links = [_a(it) for it in s["items"][:2]]
        intro = s["intro"].format(*links)
        out.append(f'<section class="gsec" id="{s["id"]}"><h2>{s["emoji"]} {s["title"]}</h2><p class="lead">{intro}</p>'
                   '<div class="grid">' + "".join(_card(it) for it in s["items"]) + "</div></section>")
    rows = "".join(f'<tr><td>{s["title"].replace("Gifts for ", "").replace(" (and the host)", "").capitalize()}</td>'
                   f'<td>{_a(s["items"][0])}</td><td>{_band(s["items"][0]) or "See price"}</td>'
                   f'<td>{home.e(s["items"][0]["shop"])}</td></tr>' for s in secs)
    out.append('<section class="gsec" id="quick"><h2>&#9989; Quick picks at a glance</h2><div class="tablewrap"><table class="qt">'
               '<thead><tr><th>Who for</th><th>Our pick</th><th>Budget</th><th>Shop</th></tr></thead>'
               f'<tbody>{rows}</tbody></table></div></section>')
    out.append('<div class="related"><h3>&#127876; More Christmas ideas</h3><p>New picks are added every day.</p>'
               f'<p><a href="{home.SITE}/c/christmas/">Browse all Christmas finds &rsaquo;</a> &middot; '
               f'<a href="{home.SITE}/c/candles/">Christmas candles &rsaquo;</a> &middot; '
               f'<a href="{home.SITE}/c/gifts/">Gift roundups &rsaquo;</a></p></div>')
    out.append(f'<p class="small">Links on this page are affiliate links (#ad): we may earn a small commission if you buy, at no '
               f'extra cost to you. As an Amazon Associate I earn from qualifying purchases. Last updated '
               f'{home.pretty(d["updated"])} {d["updated"][:4]}.</p>')
    return "".join(out)


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
.step p{margin:0 0 10px}.sn{font-size:15px}
.compare{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center;margin:12px 0}
.compare>div{border:1px solid var(--border);border-radius:14px;padding:14px;text-align:center}
.compare .win{border:2px solid var(--blue);background:color-mix(in srgb,var(--blue) 8%,transparent)}
.compare .lbl{display:block;font-size:13px;color:var(--dim)}.compare strong{display:block;font-family:Georgia,serif;font-size:26px;margin:4px 0}
.compare small{color:var(--dim)}.compare .vs{border:0;font-weight:700;color:var(--dim)}
.ben{margin:0;padding-left:20px}.ben li{margin:6px 0}.howto{margin:0;padding-left:22px}.howto li{margin:8px 0}
.ph2{font-family:Georgia,serif;font-size:28px;margin:26px 0 4px;scroll-margin-top:16px}
.checker{background:linear-gradient(135deg,var(--deep),var(--blue));color:#fff;border-radius:20px;padding:22px;margin:16px 0;scroll-margin-top:16px}
.checker h2{font-family:Georgia,serif;font-size:26px;margin:0 0 4px}.checker>p{margin:0 0 12px;color:var(--soft)}
.checker .detect{background:rgba(255,255,255,.14);border-radius:10px;padding:8px 12px;color:#fff}
.selects{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0 12px}
.selects label{display:flex;flex-direction:column;gap:6px;font-weight:600;font-size:14px}
.selects select{font:500 16px Poppins,system-ui,sans-serif;padding:12px;border-radius:12px;border:0;background:#fff;color:#14213D}
.selects select:disabled{opacity:.6}
.result{background:#fff;color:#14213D;border-radius:14px;padding:16px;margin:0 0 12px}.result h3{margin:0 0 6px;font-size:19px}
.result p{margin:0 0 10px}.result.yes{border-left:6px solid #1E9E5A}.result.no{border-left:6px solid var(--red)}.result.maybe{border-left:6px solid #F5A623}
.checker .small{color:var(--soft)}
@media (max-width:560px){.selects{grid-template-columns:1fr}}
.provs{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin:12px 0}
.prov{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:18px;display:flex;flex-direction:column}
.prov h3{font-family:Georgia,serif;font-size:26px;margin:0}.prov .tag2{color:var(--blue);font-weight:600;margin:2px 0 8px}
.prov ul{margin:0 0 14px;padding-left:20px;flex:1}.prov li{margin:5px 0}
.toppicks{background:linear-gradient(135deg,var(--deep),var(--blue));color:#fff;border-radius:18px;padding:20px 22px;margin:16px 0}
.toppicks h2{font-family:Georgia,serif;font-size:24px;margin:0 0 8px}.toppicks ol{margin:0;padding-left:22px}.toppicks li{margin:6px 0}
.toppicks a{color:#fff;text-decoration:underline;text-decoration-color:var(--gold, #F5D27A);text-underline-offset:3px;font-weight:600}
.jump{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.jump a{text-decoration:none;background:var(--surface);border:1px solid var(--border);padding:7px 13px;border-radius:99px;font-size:14px;font-weight:500}
.gsec{padding:22px 0 6px;scroll-margin-top:12px}.gsec h2{font-family:Georgia,serif;font-size:clamp(24px,4vw,30px);margin:0 0 6px}
.lead{font-size:17px;margin:0 0 16px}.lead a,.intro a,.qt a{color:var(--blue);font-weight:600}
.pcard .why{color:var(--dim);font-size:15px;margin:0 0 14px;flex:1}
.ph.noimg{background:linear-gradient(135deg,#FFF6E5,#E8F1FF)}.emo{font-size:72px;line-height:1}
.tablewrap{overflow-x:auto}.qt{width:100%;border-collapse:collapse;background:var(--surface);border-radius:14px;overflow:hidden}
.qt th,.qt td{padding:12px 14px;text-align:left;border-bottom:1px solid var(--border);font-size:15px}.qt th{background:var(--blue);color:#fff;font-weight:600}
@media (max-width:560px){.compare{grid-template-columns:1fr}.compare .vs{display:none}}
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

BODIES = {"used-car-checklist": used_car_body, "travel-esim": esim_body, "christmas-gift-guide": xmas_body}


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
    og = g["og"]
    from PIL import Image, ImageDraw, ImageFont
    F = "C:/Windows/Fonts/"
    f = lambda n, s: ImageFont.truetype(F + n, s)
    W, H, M = 1000, 1500, 64
    grad = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), "#0678FF"), Image.new("RGB", (W, H), "#0A3FA8"), grad)
    dr = ImageDraw.Draw(img)
    pf = f("segoeuib.ttf", 30)
    dr.rounded_rectangle([M, 60, M + dr.textlength(og["pill"], font=pf) + 44, 114], radius=27, fill="#D0021B")
    dr.text((M + 22, 87), og["pill"], font=pf, fill="white", anchor="lm")
    y = 160
    for ln in og["lines"]:
        dr.text((M, y), ln, font=f("georgiab.ttf", 104), fill="white"); y += 116
    dr.text((M, y + 10), og["sub"], font=f("seguisb.ttf", 46), fill="#CFE3FF")
    dr.line([M, y + 84, M + 140, y + 84], fill="#F5D27A", width=5)
    top = y + 130
    dr.rounded_rectangle([M, top, W - M, H - 190], radius=32, fill="white")
    steps = og["items"]
    step = (H - 190 - top - 40) / len(steps)
    for i, s in enumerate(steps, 1):
        cy = int(top + 20 + step * (i - 0.5))
        dr.ellipse([M + 34, cy - 24, M + 82, cy + 24], fill="#D0021B")
        dr.text((M + 58, cy), "\u2713", font=f("seguisym.ttf", 30), fill="white", anchor="mm")
        dr.text((M + 104, cy), s, font=f("segoeuib.ttf", 38), fill="#14213D", anchor="lm")
    dr.rectangle([0, H - 130, W, H], fill="#0052CC")
    dr.text((M, H - 65), "DAILY DEALS UK", font=f("ariblk.ttf", 42), fill="white", anchor="lm")
    dr.text((W - M, H - 65), "Tap to read the guide \u203A", font=f("seguisb.ttf", 30), fill="#CFE3FF", anchor="rm")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90, optimize=True)
