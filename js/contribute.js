import { isSafeImageSrc } from './utils.js';
import { isSeedRecipe } from './data.js';

// Switch branch to 'main' once the site is published from main.
export const GITHUB_REPO = { owner: 'VlodkoH', name: 'CookBook', branch: 'develop' };
const RECIPES_DIR = 'data/recipes';
// Longer URLs risk HTTP 414 from GitHub; the JSON is then pasted from the clipboard instead.
const MAX_URL_LENGTH = 8000;
const TECH_FIELDS = ['mode', 'temperature', 'pressure', 'valve'];

const isSet = (v) => v !== null && v !== undefined && v !== '';

function dropEmpty(obj, optionalKeys) {
  for (const key of optionalKeys) if (!isSet(obj[key])) delete obj[key];
  return obj;
}

/** Converts a normalized user recipe into a data/recipes/<id>.json object. */
export function toBookRecipe(r) {
  return {
    id: r.id,
    title: r.title,
    category: r.category,
    description: r.description,
    servings: r.servings,
    prepMinutes: r.prepMinutes,
    cookMinutes: r.cookMinutes,
    difficulty: r.difficulty,
    tags: r.tags,
    ingredients: r.ingredients.map((i) => dropEmpty({
      name: i.name, amount: i.amount, amountMax: i.amountMax, unit: i.unit, note: i.note
    }, ['amountMax'])),
    steps: r.steps.map((s) => dropEmpty({
      stage: s.stage,
      text: s.text,
      mode: s.mode,
      temperature: s.temperature,
      pressure: s.pressure,
      minutes: s.minutes,
      minutesMax: s.minutesMax,
      valve: s.valve,
      note: s.note,
      // Device parameters stay unconfirmed until the reviewer checks them against the manual.
      verified: TECH_FIELDS.some((k) => isSet(s[k])) ? false : s.verified
    }, ['stage', 'minutesMax', 'valve', 'note'])),
    tips: r.tips,
    image: isSafeImageSrc(r.image) && !/^https:/i.test(r.image) ? r.image : null
  };
}

/** Returns the JSON text and a GitHub "create file" URL for the recipe. */
export function prepareContribution(recipe) {
  const json = JSON.stringify(toBookRecipe(recipe), null, 2) + '\n';
  const { owner, name, branch } = GITHUB_REPO;
  const filename = `${recipe.id}.json`;
  const isEdit = isSeedRecipe(recipe.id);
  const base = `https://github.com/${owner}/${name}/${isEdit ? 'edit' : 'new'}/${encodeURIComponent(branch)}/${RECIPES_DIR}`;
  if (isEdit) return { json, filename, prefilled: false, isEdit, url: `${base}/${filename}` };
  const prefilledUrl = `${base}?${new URLSearchParams({ filename, value: json })}`;
  const prefilled = prefilledUrl.length <= MAX_URL_LENGTH;
  return {
    json,
    filename,
    prefilled,
    isEdit,
    url: prefilled ? prefilledUrl : `${base}?${new URLSearchParams({ filename })}`
  };
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
