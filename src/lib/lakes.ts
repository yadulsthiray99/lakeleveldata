import data from '../data/lakes.json';

export type Lake = (typeof data.lakes)[number];
export const LAKES = data.lakes as Lake[];
export const BUILT = data.built;

export const STATES = Object.values(
  LAKES.reduce((acc: Record<string, { slug: string; name: string; code: string; lakes: Lake[]; demand: number }>, l) => {
    (acc[l.state_slug] ??= { slug: l.state_slug, name: l.state_name, code: l.state, lakes: [], demand: 0 }).lakes.push(l);
    acc[l.state_slug].demand += l.demand;
    return acc;
  }, {}),
).sort((a, b) => b.demand - a.demand);

export const ft = (v: number | null | undefined, d = 2) =>
  v == null ? '–' : v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
export const sgn = (v: number | null | undefined, d = 2) =>
  v == null ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : '±'}${ft(Math.abs(v), d)} ft`;
export const cls = (v: number | null | undefined) => (v == null || Math.abs(v) < 0.005 ? '' : v > 0 ? 'up' : 'down');

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
export const dLong = (iso: string) => { const [y, m, d] = iso.slice(0, 10).split('-').map(Number); return `${MONTH[m - 1]} ${d}, ${y}`; };
export const dShort = (iso: string) => { const [y, m, d] = iso.slice(0, 10).split('-').map(Number); return `${MON[m - 1]} ${d}, ${y}`; };
export const dNoYear = (iso: string) => { const [, m, d] = iso.slice(0, 10).split('-').map(Number); return `${MON[m - 1]} ${d}`; };

// "October 20, 2026 at 2:00 AM" in the gauge's own time zone (the ISO string carries its offset)
export const when = (l: Lake) => {
  if (l.daily_only || l.time.length <= 10) return `the reading for ${dLong(l.last_day)}`;
  const h = Number(l.time.slice(11, 13)), m = l.time.slice(14, 16);
  return `${dLong(l.time)} at ${((h + 11) % 12) + 1}:${m} ${h < 12 ? 'AM' : 'PM'}`;
};

const rate = (v: number) => (Math.abs(v) < 0.1 ? 'almost unchanged' : Math.abs(v) < 0.5 ? 'slowly' : Math.abs(v) < 2 ? 'steadily' : 'quickly');

export function trendSentence(l: Lake) {
  if (l.ch7 == null) return '';
  if (Math.abs(l.ch7) < 0.1) return `The level has held steady over the past week (${sgn(l.ch7)} in 7 days${l.ch30 != null ? `, ${sgn(l.ch30)} in 30 days` : ''}).`;
  const dir = l.ch7 > 0 ? 'rising' : 'falling';
  return `${l.name} is ${dir} ${rate(l.ch7)}: ${l.ch7 > 0 ? 'up' : 'down'} ${ft(Math.abs(l.ch7))} ft in the past 7 days${l.ch30 != null ? ` and ${l.ch30 >= 0 ? 'up' : 'down'} ${ft(Math.abs(l.ch30))} ft over 30 days` : ''}.`;
}

export function fullSentence(l: Lake) {
  const bits: string[] = [];
  if (l.pf != null) bits.push(`The lake is ${ft(l.pf, 1)}% full`);
  if (l.vs_full != null) {
    const v = l.vs_full;
    bits.push(Math.abs(v) < 0.05 ? `right at full pool (${ft(l.full)} ft)` : v < 0 ? `${ft(-v)} ft below full pool (${ft(l.full)} ft)` : `${ft(v)} ft above full pool (${ft(l.full)} ft), so flood storage is in use`);
  }
  if (l.vs_guide != null) {
    const g = l.vs_guide;
    bits.push(Math.abs(g) < 0.05 ? `exactly on the Corps' guide curve for today (${ft(l.guide)} ft)` : `${ft(Math.abs(g))} ft ${g < 0 ? 'below' : 'above'} the Corps' guide curve target for today (${ft(l.guide)} ft)`);
  }
  if (!bits.length) return '';
  const s = bits.join(', ');
  return (l.pf != null ? s : `It is ${s}`) + '.';
}

export function yearSentence(l: Lake) {
  if (l.ch365 == null) return '';
  const v = l.ch365;
  if (Math.abs(v) < 0.1) return `That is about the same as a year ago.`;
  return `Compared with the same date last year, the lake is ${ft(Math.abs(v))} ft ${v > 0 ? 'higher' : 'lower'}${l.pf != null && l.pf_1y != null ? ` (${ft(l.pf_1y, 1)}% full then, ${ft(l.pf, 1)}% now)` : ''}.`;
}

export const levelAnswer = (l: Lake) =>
  `${l.name} is at ${ft(l.now)} ft above sea level (${when(l)}). ${fullSentence(l)} ${trendSentence(l)}`.replace(/\s+/g, ' ').trim();

export const neighbors = (l: Lake, n = 8) => LAKES.filter((x) => x.state_slug === l.state_slug && x.slug !== l.slug).slice(0, n);
export const lakeUrl = (l: Lake) => `/${l.state_slug}/${l.slug}/`;
