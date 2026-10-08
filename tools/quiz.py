"""Christmas gift finder quiz: 3 tap-to-answer questions -> the best 3 gifts.

Products come from the Christmas gift guide (deals/data/guide-christmas.json) with live prices from
prices.json for shop products. Amazon items carry an approximate budget band ("band") for filtering
only; their price is never shown (Amazon's rules).
"""
import json

import home

# who each guide section suits (stocking fillers and show-stoppers suit anyone)
SECTION_FOR = {"her": ["her"], "him": ["him"], "kids": ["kids"], "home": ["home", "her"],
               "stocking": ["her", "him", "kids", "anyone"], "big": ["her", "him", "home", "anyone"]}
# extra recipients for products that suit more than one person
EXTRA_FOR = {"aw-38031934423195": ["her"], "B0FF4LX6V5": ["home"], "aw-45805584779": ["her"], "B0BMGSHQ12": ["anyone"],
             "B005I5M2F8": ["kids"], "B0DBLX2HS7": ["him", "her"], "aw-44777982177": ["home"], "aw-41956185965": ["anyone"],
             "aw-31066460759": ["anyone"], "B0GTLVMNV1": ["her"]}
VIBE = {"Bath & body": "pamper", "Grooming": "pamper", "Cosy": "cosy", "Candles": "cosy", "Socks": "cosy", "Winter": "cosy",
        "Decor": "cosy", "Food & drink": "treats", "Chocolate": "treats", "Hampers": "treats", "Advent": "treats",
        "Drinks": "treats", "Games": "fun", "Activity": "fun"}
# approximate price for Amazon items (used to filter by budget only, never displayed)
AMAZON_APPROX = {"B0FF4LX6V5": 30, "B004EDWMBO": 22, "B0BVX2VC5H": 20, "B08JLXWHFT": 7, "B0BMGSHQ12": 15,
                 "B0GTLVMNV1": 10, "B005I5M2F8": 6, "B0DBLX2HS7": 12}


def data():
    g = home.DATA / "guide-christmas.json"
    if not g.exists():
        return []
    pr = home.prices()
    items = []
    for s in json.loads(g.read_text(encoding="utf-8"))["sections"]:
        for it in s["items"]:
            key = it["key"]
            if it["src"] == "awin":
                v = pr.get(key[3:], {})
                if v and not v.get("in_stock", True):
                    continue
                price = v.get("price") or it.get("price")
                url = it["url"]
                img = f"{home.SITE}/guides/christmas-gift-guide/img/{key}.jpg"
                ph = home.price_html(key[3:], pr)
            else:
                price = AMAZON_APPROX.get(key, 25)
                url = f"https://www.amazon.co.uk/dp/{key}?tag=dailydeal07d1-21"
                img = ""
                ph = ""
            items.append({"k": key, "n": it["name"], "s": it["shop"], "w": it["why"], "u": url, "i": img, "ph": ph,
                          "p": price, "f": sorted(set(SECTION_FOR.get(s["id"], []) + EXTRA_FOR.get(key, []))),
                          "v": VIBE.get(it.get("kind"), "cosy"), "sv": (pr.get(key[3:], {}) or {}).get("save", 0)})
    return items


def html():
    items = data()
    if not items:
        return ""
    return """<section class="quiz" id="gift-finder"><div class="qhead"><span class="pill">Gift finder</span>
<h2>&#127873; Find the perfect gift in 3 taps</h2><p>Answer three quick questions and we&rsquo;ll pick our best matches.</p></div>
<div class="qbody" id="qBody"></div></section>
<script>(function(){var I=""" + json.dumps(items) + """;
var Q=[{k:'f',t:'Who are you buying for?',o:[['her','For her'],['him','For him'],['kids','For kids'],['home','For the home or host'],['anyone','Anyone / not sure']]},
{k:'b',t:'What\\u2019s your budget?',o:[[10,'Under \\u00a310'],[20,'Under \\u00a320'],[30,'Under \\u00a330'],[1000,'Treat them (\\u00a330+)']]},
{k:'v',t:'What are they into?',o:[['cosy','Cosy nights in'],['treats','Food & sweet treats'],['pamper','Pampering'],['fun','Fun & games'],['any','Surprise me']]}];
var A={},step=0,box=document.getElementById('qBody');
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
function render(){if(step<Q.length){var q=Q[step];box.innerHTML='<div class="qprog">Question '+(step+1)+' of '+Q.length+'</div><h3>'+q.t+'</h3><div class="qopts">'+
q.o.map(function(o,i){return '<button type="button" data-i="'+i+'">'+o[1]+'</button>'}).join('')+'</div>'+(step?'<button type="button" class="qback">&lsaquo; Back</button>':'');
[].forEach.call(box.querySelectorAll('.qopts button'),function(b){b.onclick=function(){A[q.k]=q.o[+b.dataset.i][0];step++;render()}});
var bk=box.querySelector('.qback');if(bk)bk.onclick=function(){step--;render()};return}
var hi=A.b===1000?1e9:A.b,lo=A.b===1000?30:0;
function score(x){var s=0;if(x.f.indexOf(A.f)>=0)s+=4;else if(A.f==='anyone'||x.f.indexOf('anyone')>=0)s+=2;
if(x.p<=hi&&x.p>=lo)s+=3;else if(x.p<=hi)s+=1;if(A.v==='any'||x.v===A.v)s+=2;if(x.sv>=5)s+=0.5;return s}
function rank(f){return I.filter(f).map(function(x){return [score(x),x]}).sort(function(a,b){return b[0]-a[0]}).map(function(a){return a[1]})}var r=rank(function(x){return x.p<=hi&&x.p>=lo});if(r.length<3)r=r.concat(rank(function(x){return x.p<=hi&&r.indexOf(x)<0}));r=r.slice(0,3);
if(!r.length)r=I.slice().sort(function(a,b){return a.p-b.p}).slice(0,3);
box.innerHTML='<h3>Our picks for you</h3><div class="qres">'+r.map(function(x){var am=x.s==='Amazon';
return '<a class="qcard" href="'+x.u+'" rel="sponsored nofollow noopener" target="_blank">'+(x.i?'<span class="qimg"><img src="'+x.i+'" alt=""></span>':'<span class="qimg qemo">&#127873;</span>')+
'<span class="qb"><strong>'+esc(x.n)+'</strong><small>From '+esc(x.s)+'</small>'+x.ph+'<span class="qw">'+esc(x.w)+'</span><span class="btn">See it at '+esc(x.s)+' &rsaquo;</span></span></a>'}).join('')+
'</div><div class="qfoot"><button type="button" class="qagain">&#8635; Start again</button> <a href="'+""" + json.dumps(home.SITE + "/guides/christmas-gift-guide/") + """+'">See the full Christmas gift guide &rsaquo;</a></div><p class="small">Affiliate links (#ad).</p>';
box.querySelector('.qagain').onclick=function(){A={};step=0;render()}}
render()})();</script>"""


CSS = """
.quiz{background:linear-gradient(135deg,#0A3FA8,#0678FF);color:#fff;border-radius:22px;padding:24px;margin:28px 0;scroll-margin-top:12px}
.qhead h2{font-family:Georgia,serif;font-size:clamp(24px,4vw,32px);margin:8px 0 4px}.qhead p{color:#CFE3FF;margin:0 0 16px}
.qbody{background:#fff;color:#14213D;border-radius:16px;padding:20px}.qbody h3{font-family:Georgia,serif;font-size:22px;margin:4px 0 14px}
.qprog{font-size:13px;color:#5B6178;font-weight:600}
.qopts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(170px,100%),1fr));gap:10px}
.qopts button,.qback,.qagain{font:600 16px Poppins,system-ui,sans-serif;border-radius:12px;padding:14px;cursor:pointer}
.qopts button{background:#F3F6FC;color:#14213D;border:2px solid #DCE4F2;text-align:left}.qopts button:hover{border-color:#0678FF;background:#E8F1FF}
.qback,.qagain{background:none;border:0;color:#0678FF;padding:12px 0 0;font-size:14px}
.qres{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr));gap:14px}
.qcard{display:flex;flex-direction:column;text-decoration:none;color:#14213D;border:1px solid #DCE4F2;border-radius:14px;overflow:hidden}
.qimg{background:#fff;aspect-ratio:4/3;display:grid;place-items:center;padding:10px}.qimg img{max-width:100%;max-height:100%;object-fit:contain}
.qemo{font-size:60px;background:linear-gradient(135deg,#FFF6E5,#E8F1FF)}
.qb{display:flex;flex-direction:column;gap:4px;padding:12px 14px 14px;flex:1}.qb strong{font-size:16px;line-height:1.3}.qb small{color:#5B6178}
.qw{color:#5B6178;font-size:14px;flex:1}.qb .btn{align-self:flex-start;margin-top:8px}
.qcard .price strong{font-size:18px}.qcard .pchk{margin:0}
.qfoot{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-top:12px}.qfoot a{color:#0678FF;font-weight:600}
.quiz .small{color:#5B6178;margin:8px 0 0}
@media (max-width:560px){.quiz{padding:18px 14px}.qbody{padding:14px}}
"""
