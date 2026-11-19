// Proof kit: SVG characters (front, 3/4, back), labels with curved arrows, speech bubbles.
// Rule: filled shapes use cubic/quadratic curves only. hardware Chrome on this machine does not fill SVG arc (A) commands.
const NS = 'http://www.w3.org/2000/svg';
const $ = id => document.getElementById(id);
const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
const ease = x => x<0?0:x>1?1:x*x*(3-2*x);
const lerp = (a,b,k) => a+(b-a)*k;
const clamp01 = x => Math.max(0, Math.min(1, x));
// circle as 4 cubics (no arcs)
const circ = (cx, cy, r) => { const k = .5523*r; return `M${cx-r} ${cy} C${cx-r} ${cy-k} ${cx-k} ${cy-r} ${cx} ${cy-r} C${cx+k} ${cy-r} ${cx+r} ${cy-k} ${cx+r} ${cy} C${cx+r} ${cy+k} ${cx+k} ${cy+r} ${cx} ${cy+r} C${cx-k} ${cy+r} ${cx-r} ${cy+k} ${cx-r} ${cy} Z`; };

const POSES = {
  rest:   {L:[-168,392,-196,280], R:[168,392,196,280]},
  hold:   {L:[-70,300,-180,270],  R:[70,300,180,270]},
  shrug:  {L:[-250,140,-215,270], R:[250,140,215,270]},
  raise:  {L:[-168,392,-196,280], R:[285,40,270,210]},
  wide:   {L:[-310,110,-235,175], R:[310,110,235,175]},
  up:     {L:[-215,-30,-235,170], R:[215,-30,235,170]},
  palm:   {L:[-168,392,-196,280], R:[30,20,215,215]},
  pointL: {L:[-340,170,-250,190], R:[168,392,196,280]},
  pointR: {L:[-168,392,-196,280], R:[340,170,250,190]},
  desk:   {L:[-150,420,-200,300], R:[150,420,200,300]},
  chin:   {L:[-168,392,-196,280], R:[40,110,200,260]},
};
const EXPR = {
  neutral:{eye:16, brow:0,  tilt:0,  mouth:'smile'},
  happy:  {eye:16, brow:6,  tilt:0,  mouth:'smile'},
  excited:{eye:19, brow:14, tilt:0,  mouth:'grin'},
  proud:  {eye:16, brow:10, tilt:0,  mouth:'grin'},
  worried:{eye:16, brow:4,  tilt:14, mouth:'frown'},
  shocked:{eye:25, brow:22, tilt:0,  mouth:'o'},
  deadpan:{eye:7,  brow:-5, tilt:0,  mouth:'flat'},
  smug:   {eye:9,  brow:-2, tilt:-6, mouth:'smile'},
  beam:   {eye:14, brow:4,  tilt:0,  mouth:'teeth'},
  calm:   {eye:9,  brow:2,  tilt:0,  mouth:'smirk'},
};
const BODY = (seated) => `M-112 148 Q-158 250 -150 ${seated?470:462} Q-150 ${seated?470:478} 0 ${seated?470:480} Q150 ${seated?470:478} 150 ${seated?470:462} Q158 250 112 148 Q0 118 -112 148 Z`;

function makeChar(parent, o){
  const id = o.id + (o.tag||''), g = el('g', {id}, parent);
  const HEAD = o.head || circ(0,0,165);   // a character may have its own head outline (default: the round head)
  const legs = o.seated ? '' : `
    <path class="legL" fill="none" stroke-width="8"/><path class="legR" fill="none" stroke-width="8"/>
    <ellipse class="shoeL" rx="30" ry="13" fill="#1f1a17" stroke-width="5"/><ellipse class="shoeR" rx="30" ry="13" fill="#1f1a17" stroke-width="5"/>`;
  g.innerHTML = `
  <clipPath id="${id}-bc"><path d="${BODY(o.seated)}"/></clipPath>
  <clipPath id="${id}-hc"><path d="${HEAD}"/></clipPath>
  <g class="rig">
    ${legs}
    <g class="body">
      <path d="${BODY(o.seated)}" fill="${o.suit}" stroke-width="7"/>
      <g clip-path="url(#${id}-bc)" stroke="none">
        <path class="bodyShade" d="M60 110 Q150 230 160 490 L200 490 L200 110 Z" fill="${o.suitShade}"/>
        <path d="M-120 200 Q-130 300 -128 470" fill="none" stroke="#fff" stroke-width="12" opacity=".1"/>
      </g>
      <g class="torso">${o.torso}</g>
      <g class="torsoBack" style="display:none"><path d="M0 150 L0 470" fill="none" stroke-width="4" opacity=".5"/><path d="M-70 150 Q0 132 70 150" fill="none" stroke-width="5"/></g>
    </g>
    <g class="head">
      <g class="hairBack">${o.hairBack||''}</g>
      <path d="${HEAD}" fill="${o.skin}" stroke="none"/>
      <g clip-path="url(#${id}-hc)" stroke="none"><path class="headShade" d="${HEAD}" fill="${o.skinShade}"/></g>
      <path d="${HEAD}" fill="none" stroke-width="7"/>
      <g class="face">
        <g class="hairFront">${o.hair}</g>
        <path class="browL" d="${(o.brows||[])[0]||'M-72 -46 Q-50 -58 -26 -50'}" fill="none" stroke-width="${o.browW||7}"/>
        <path class="browR" d="${(o.brows||[])[1]||'M26 -50 Q50 -58 72 -46'}" fill="none" stroke-width="${o.browW||7}"/>
        <g fill="#2d2622" stroke="none">
          <ellipse class="eyeL" cx="-48" cy="-6" rx="11" ry="16"/><ellipse class="eyeR" cx="48" cy="-6" rx="11" ry="16"/>
          <circle class="glL" cx="-44" cy="-12" r="3.5" fill="#fff"/><circle class="glR" cx="52" cy="-12" r="3.5" fill="#fff"/>
        </g>
        ${o.glasses ? `<g fill="none" stroke-width="5"><path d="${circ(-48,-6,36)}" fill="#fff" fill-opacity=".12"/><path d="${circ(48,-6,36)}" fill="#fff" fill-opacity=".12"/><path d="M-12 -8 Q0 -16 12 -8 M-84 -10 L-150 -24 M84 -10 L150 -24"/></g>` : ''}
        ${o.extraFace||''}
        <path class="nose" d="M-6 22 Q0 30 8 24" fill="none" stroke-width="4.5" opacity=".75"/>
        <path class="mouthLine" fill="none" stroke-width="6"/>
        <path class="mouthOpen" fill="#5b2420" stroke-width="5.5"/>
        <path class="tongue" fill="#c45a50" stroke="none"/>
      </g>
      <g class="rear" style="display:none">${o.hairRear||''}</g>
    </g>
    <path class="armL" fill="none" stroke-width="8"/><path class="armR" fill="none" stroke-width="8"/>
    <g class="prop"></g>
  </g>`;
  const q = c => g.querySelector('.'+c);
  const P = {};
  for (const c of ['rig','body','head','face','rear','torso','torsoBack','hairBack','hairFront','headShade','bodyShade','armL','armR','legL','legR','shoeL','shoeR','browL','browR','eyeL','eyeR','glL','glR','mouthLine','mouthOpen','tongue','prop']) P[c] = q(c);
  if (o.prop) P.prop.innerHTML = o.prop;
  return { g, o, P, set(st){ setChar(this, st); } };
}
function blend(a, b, k){ const r = {}; for (const s of ['L','R']) r[s] = a[s].map((v,i)=>lerp(v, b[s][i], k)); return r; }

function setChar(c, st){
  const P = c.P, o = c.o;
  c.g.style.display = st.hide ? 'none' : '';
  if (st.hide) return;
  const back = st.view === 'back';
  c.g.setAttribute('transform', `translate(${st.x} ${st.y}) scale(${st.s} ${st.s})`);
  const t = st.t, br = Math.sin(t*2.4 + (o.phase||0))*.007;
  const w = st.walk || 0, ph = (st.walkPh||0);
  const bob = w ? -Math.abs(Math.sin(ph))*14 : 0;
  P.rig.setAttribute('transform', `translate(0 ${bob})`);
  P.body.setAttribute('transform', `translate(0 470) scale(1 ${1+br}) translate(0 -470)`);
  if (P.legL) {
    const sw = w ? Math.sin(ph)*48 : 0, fy = 640 - bob;
    P.legL.setAttribute('d', `M-46 462 L${-50+sw} ${fy}`); P.legR.setAttribute('d', `M46 462 L${50-sw} ${fy}`);
    P.shoeL.setAttribute('cx', -62+sw); P.shoeL.setAttribute('cy', fy+4); P.shoeR.setAttribute('cx', 62-sw); P.shoeR.setAttribute('cy', fy+4);
  }
  // 3/4 turn: the face slides toward where the character looks, the shade moves to the far side
  const f = back ? 0 : (st.face||0);
  P.face.style.display = back ? 'none' : '';
  P.rear.style.display = back ? '' : 'none';
  P.hairBack.style.display = back ? 'none' : '';
  P.torso.style.display = back ? 'none' : '';
  P.torsoBack.style.display = back ? '' : 'none';
  P.face.setAttribute('transform', `translate(${f*40} 0) scale(${1 - Math.abs(f)*.1} 1)`);
  // cel shade: head minus a lit circle shifted toward the light (evenodd, clipped to the head)
  const lx = (st.light||-1) * 36;
  P.headShade.setAttribute('d', (o.head || circ(0,0,165)) + ' ' + circ(lx, -22, 170));
  P.headShade.setAttribute('fill-rule', 'evenodd');
  P.bodyShade.setAttribute('transform', (st.light||-1) > 0 ? 'scale(-1 1)' : '');
  // pose
  const pose = blend(POSES[st.poseFrom||st.pose], POSES[st.pose], st.poseK==null?1:ease(st.poseK));
  const swingA = w ? Math.sin(ph)*30 : 0;
  P.armL.setAttribute('d', `M-112 168 Q${pose.L[2]} ${pose.L[3]} ${pose.L[0]-swingA} ${pose.L[1]+br*200}`);
  P.armR.setAttribute('d', `M112 168 Q${pose.R[2]} ${pose.R[3]} ${pose.R[0]+swingA} ${pose.R[1]+br*200}`);
  if (o.propAt) { const h = o.propAt === 'R' ? pose.R : pose.L; P.prop.setAttribute('transform', `translate(${h[0]} ${h[1]})`); P.prop.style.display = st.prop===false?'none':''; }
  // head motion
  const E = EXPR[st.expr||'neutral'];
  const tilt = Math.sin(t*1.7 + (o.phase||0))*2 + (st.tilt||0);
  P.head.setAttribute('transform', `translate(0 ${Math.sin(t*2.4)*2}) rotate(${tilt} 0 120)`);
  if (back) return;
  const blink = st.blink || ((t + (o.phase||0)*0.7) % 3.4 < .12);
  const ey = blink ? 2 : E.eye, look = st.look||0;
  for (const [e,x] of [[P.eyeL,-48],[P.eyeR,48]]) { e.setAttribute('ry', ey); e.setAttribute('rx', E.eye>20 ? 9 : 11); e.setAttribute('cx', x+look); }
  P.glL.setAttribute('cx', -44+look); P.glR.setAttribute('cx', 52+look);
  P.glL.style.display = P.glR.style.display = blink || E.eye<10 ? 'none' : '';
  P.browL.setAttribute('transform', `translate(0 ${-E.brow}) rotate(${-E.tilt} -50 -52)`);
  P.browR.setAttribute('transform', `translate(0 ${-E.brow}) rotate(${E.tilt} 50 -52)`);
  const a = st.talk || 0;
  if (a > .06) {
    const h = 10 + a*34, wd = 24 + a*6;
    P.mouthLine.setAttribute('d', '');
    P.mouthOpen.setAttribute('d', `M${-wd} 50 Q0 46 ${wd} 50 Q${wd-4} ${50+h} 0 ${52+h} Q${-wd+4} ${50+h} ${-wd} 50 Z`);
    P.tongue.setAttribute('d', h>22 ? `M-13 ${44+h} Q0 ${36+h} 13 ${44+h} Q8 ${50+h} 0 ${50+h} Q-8 ${50+h} -13 ${44+h} Z` : '');
  } else {
    P.tongue.setAttribute('d', '');
    const m = E.mouth;
    const set = (line, open, tg) => { P.mouthLine.setAttribute('d', line||''); P.mouthOpen.setAttribute('d', open||''); P.tongue.setAttribute('d', tg||''); };
    if (m==='smile') set('M-34 52 Q0 78 34 52');
    else if (m==='frown') set('M-28 68 Q0 50 28 68');
    else if (m==='flat') set('M-24 62 L24 62');
    else if (m==='grin') set('', 'M-46 46 Q0 54 46 46 Q36 98 0 100 Q-36 98 -46 46 Z', 'M-20 86 Q0 74 20 86 Q10 96 0 96 Q-10 96 -20 86 Z');
    else if (m==='o') set('', 'M-17 62 Q-17 40 0 40 Q17 40 17 62 Q17 86 0 86 Q-17 86 -17 62 Z');
    else if (m==='smirk') set('M-34 58 Q0 70 36 52');
    else if (m==='teeth') set('', 'M-62 40 Q0 58 62 40 Q46 100 0 104 Q-46 100 -62 40 Z', 'M-52 48 Q0 62 52 48 L44 70 Q0 80 -44 70 Z');
    P.tongue.setAttribute('fill', m === 'teeth' && !(a > .06) ? '#f6f2e6' : '#c45a50');
  }
}

// ---------- screen text ----------
function caption(UI, t, t0, x, y, big, small){
  const p = clamp01((t-t0)/.35); if (p<=0) return;
  const sc = p<1 ? (p<.7 ? p/.7*1.12 : 1.12-(p-.7)/.3*.12) : 1;
  const g = el('g', {transform:`translate(${x} ${y}) scale(${sc}) rotate(-4)`}, UI);
  el('text', {x:0, y:0, 'font-family':'Hand', 'font-size':92, 'text-anchor':'middle', fill:'#fff', stroke:'#16120f', 'stroke-width':14, 'paint-order':'stroke'}, g).textContent = big;
  if (small) el('text', {x:8, y:54, 'font-family':'Hand', 'font-size':40, 'text-anchor':'middle', fill:'#fff', stroke:'#16120f', 'stroke-width':9, 'paint-order':'stroke'}, g).textContent = small;
  // keep the caption inside the frame
  const R = document.getElementById('root').getBoundingClientRect(), u = R.width / 1920, gb = g.getBoundingClientRect(); const b = {left: (gb.left - R.left) / u, right: (gb.right - R.left) / u}; let dx = 0;
  if (b.left < 40) dx = 40 - b.left; else if (b.right > 1880) dx = 1880 - b.right;
  if (dx) g.setAttribute('transform', `translate(${x + dx} ${y}) scale(${sc}) rotate(-4)`);
}
// floating italic label with a curved arrow that draws on (reference: "Kang Wei, her husband ->")
function labelArrow(UI, t, t0, text, sub, x, y, tx, ty, bend){
  const p = clamp01((t-t0)/.3); if (p<=0) return;
  const g = el('g', {}, UI);
  const tt = el('text', {x, y, 'font-family':'Hand', 'font-size':64, 'text-anchor':'middle', fill:'#fff', stroke:'#16120f', 'stroke-width':12, 'paint-order':'stroke', transform:`rotate(-4 ${x} ${y})`, opacity:p}, g); tt.textContent = text;
  if (sub) { const s = el('text', {x:x+6, y:y+46, 'font-family':'Hand', 'font-size':36, 'text-anchor':'middle', fill:'#fff', stroke:'#16120f', 'stroke-width':8, 'paint-order':'stroke', transform:`rotate(-4 ${x} ${y})`, opacity:p}, g); s.textContent = sub; }
  const a = clamp01((t-t0-.15)/.4);
  const sx = x + (tx > x ? 60 : -60), sy = y + (sub ? 70 : 24);
  const mx = (sx+tx)/2 + (bend||60), my = (sy+ty)/2 - (bend||60)*.5;
  const d = `M${sx} ${sy} Q${mx} ${my} ${tx} ${ty}`;
  for (const [col, wd] of [['#16120f', 12], ['#fff', 5]]) {
    const pa = el('path', {d, fill:'none', stroke:col, 'stroke-width':wd, 'stroke-linecap':'round'}, g);
    const L = pa.getTotalLength(); pa.setAttribute('stroke-dasharray', L); pa.setAttribute('stroke-dashoffset', L*(1-a));
  }
  if (a >= 1) {
    const ang = Math.atan2(ty - my, tx - mx);
    const h = (s) => [tx - 26*Math.cos(ang + s), ty - 26*Math.sin(ang + s)];
    const [h1, h2] = [h(.5), h(-.5)];
    for (const [col, wd] of [['#16120f', 12], ['#fff', 5]]) el('path', {d:`M${h1[0]} ${h1[1]} L${tx} ${ty} L${h2[0]} ${h2[1]}`, fill:'none', stroke:col, 'stroke-width':wd, 'stroke-linecap':'round', 'stroke-linejoin':'round'}, g);
  }
}
// speech bubble: the script's words, revealed at the pace the voice says them
function bubble(UI, t, line, tip, side, dy){
  const {t0, text, words} = line;
  if (t < t0 - .05) return;
  const lt = t - t0, sw = text.split(' ');
  const said = words.filter(w => w[0] <= lt + .02).length;
  const shown = sw.slice(0, Math.max(1, Math.round(sw.length * said / words.length))).join(' ');
  const g = el('g', {}, UI);
  const tx = el('text', {'font-family':'Hand', 'font-size':50, fill:'#1e1a17'}, g); tx.textContent = text;
  const w = tx.getComputedTextLength() + 64, h = 92;
  let bx = side==='L' ? tip[0] - w + 40 : tip[0] - 40, by = tip[1] - h - 70 + (dy||0);
  bx = Math.max(40, Math.min(1856 - w, bx)); by = Math.max(36, by);
  const pop = clamp01((t - t0 + .05)/.15), sc = .7 + .3*pop;
  g.setAttribute('transform', `translate(${tip[0]} ${tip[1]}) scale(${sc}) translate(${-tip[0]} ${-tip[1]})`);
  const tailX = Math.max(bx+60, Math.min(bx+w-60, tip[0] + (side==='L' ? -40 : 40)));
  el('path', {d:`M${tailX-22} ${by+h-4} L${tip[0]} ${tip[1]-14} L${tailX+22} ${by+h-4} Z`, fill:'#fff', stroke:'#16120f', 'stroke-width':6}, g);
  el('rect', {x:bx, y:by, width:w, height:h, rx:30, fill:'#fff', stroke:'#16120f', 'stroke-width':6}, g);
  el('path', {d:`M${tailX-18} ${by+h-2} L${tailX+18} ${by+h-2}`, stroke:'#fff', 'stroke-width':8}, g);
  g.appendChild(tx); tx.setAttribute('x', bx+32); tx.setAttribute('y', by+62); tx.textContent = shown;
}
