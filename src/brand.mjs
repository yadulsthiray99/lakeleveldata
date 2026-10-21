// Brand: logo mark, homepage illustration, colours. Inline SVG only (no requests).
export const NAME = ['LakeLevel', 'Data'];
export const COLORS = { bg: '#0b3954', hi: '#38bdf8', accent: '#0369a1' };
export const TAGLINE = ['Lake levels today', 'Official gauge readings for 100 U.S. lakes'];
const F = 'font-family="system-ui,Segoe UI,Arial,sans-serif"';
const n1 = (x) => x.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const mark = (size = 34) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="${size}" height="${size}" aria-hidden="true">
<rect width="40" height="40" rx="9" fill="#0369a1"/>
<path d="M0 24Q5 20.5 10 24T20 24T30 24T40 24V31Q40 40 31 40H9Q0 40 0 31Z" fill="#38bdf8"/>
<rect x="25" y="5" width="7" height="30" rx="2" fill="#fff"/>
<path d="M25 10h4M25 15h3M25 20h4M25 25h3M25 30h4" stroke="#0b3954" stroke-width="1.6"/>
<path d="M14 15l6 5-6 5z" fill="#fde68a"/></svg>`;

// Cross-section of a reservoir: today's level against full pool, scaled between full pool and dead pool.
export const hero = ({ name = 'Lake Mead', now = 1037.2, full = 1229, dead = 895 } = {}) => {
  const yF = 66, yB = 196, frac = Math.max(0.05, Math.min(0.9, (full - now) / (full - dead)));
  const yW = Math.round(yF + frac * (yB - yF));
  const below = full - now;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 232" role="img" aria-label="${name} cross-section: ${n1(now)} feet today, ${n1(below)} feet below full pool of ${n1(full)} feet">
<defs><linearGradient id="lw" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#0369a1"/></linearGradient></defs>
<rect width="360" height="232" rx="14" fill="#eef6fb"/>
<rect x="0" y="${yW}" width="360" height="${232 - yW}" fill="url(#lw)"/>
<path d="M0 46L34 54Q104 206 178 208Q258 206 324 62L360 52V232H0Z" fill="#d9c49b"/>
<path d="M0 46L34 54Q104 206 178 208Q258 206 324 62L360 52" fill="none" stroke="#b9a274" stroke-width="3"/>
<path d="M0 232V214Q90 222 180 216T360 212V232Z" fill="#c4ad80"/>
<line x1="20" y1="${yF}" x2="340" y2="${yF}" stroke="#0b3954" stroke-width="2" stroke-dasharray="7 5"/>
<text x="24" y="${yF - 8}" ${F} font-size="13" font-weight="700" fill="#0b3954">Full pool ${n1(full)} ft</text>
<line x1="282" y1="${yF + 4}" x2="282" y2="${yW - 4}" stroke="#b45309" stroke-width="2.5"/>
<path d="M276 ${yW - 11}L282 ${yW - 2}L288 ${yW - 11}" fill="none" stroke="#b45309" stroke-width="2.5" stroke-linejoin="round"/>
<text x="292" y="${Math.round((yF + yW) / 2) + 5}" ${F} font-size="13" font-weight="700" fill="#b45309">−${n1(below)} ft</text>
<rect x="104" y="${yW - 14}" width="150" height="28" rx="14" fill="#fff"/>
<text x="179" y="${yW + 5}" text-anchor="middle" ${F} font-size="13.5" font-weight="800" fill="#0b3954">Today ${n1(now)} ft</text>
<text x="179" y="${Math.min(226, yW + 40)}" text-anchor="middle" ${F} font-size="12" fill="#e0f2fe">${name}</text></svg>`;
};
