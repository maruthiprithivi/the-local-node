// @ts-check
import fs from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { pluginLineNumbers } from '@expressive-code/plugin-line-numbers';

// Written by scripts/sync.mjs from the kit folder.
const sidebar = JSON.parse(fs.readFileSync(new URL('./src/generated/sidebar.json', import.meta.url), 'utf8'));

const FONTS = 'https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap';
// IBM Plex Mono from Google Fonts has no box-drawing or arrow glyphs; these fallbacks do, at the same width.
const MONO = '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, "DejaVu Sans Mono", "Liberation Mono", "Noto Sans Mono", monospace';

// A link to #file-... points at a collapsed file block: open it on load, on in-page hash changes, and when
// the same link is clicked again after the block was closed.
const OPEN_TARGETED_FILE = `(()=>{const open=(h)=>{let id;try{id=decodeURIComponent(h.slice(1));}catch{return;}const t=id&&document.getElementById(id);if(t&&t.tagName==='DETAILS'){t.open=true;t.scrollIntoView();}};addEventListener('hashchange',()=>open(location.hash));addEventListener('click',(e)=>{const a=e.target.closest&&e.target.closest('a[href*="#"]');if(a&&a.hash&&a.pathname===location.pathname&&a.hash===location.hash)open(a.hash);});document.readyState==='loading'?addEventListener('DOMContentLoaded',()=>open(location.hash)):open(location.hash);})();`;

// With site data blocked (browser setting, some private modes, sandboxed frames), reading localStorage or
// sessionStorage throws, and Starlight's theme and sidebar scripts stop with an error. This runs first in
// <head> and puts storage that lasts for the page view in their place, so every page still works.
const STORAGE_FALLBACK = `(()=>{for(const k of['localStorage','sessionStorage']){try{window[k].getItem('fek');continue;}catch(e){}const m=new Map(),s={getItem:(x)=>(m.has(String(x))?m.get(String(x)):null),setItem:(x,v)=>{m.set(String(x),String(v));},removeItem:(x)=>{m.delete(String(x));},clear:()=>{m.clear();},key:(i)=>[...m.keys()][i]??null,get length(){return m.size;}};try{Object.defineProperty(window,k,{value:s,configurable:true});}catch(e){}}})();`;

export default defineConfig({
  site: 'https://thelocalnode.dev',
  base: '/ai-field-engineer',
  integrations: [
    starlight({
      title: 'AI Engineering Field Kit',
      description: 'Hands-on lessons in building, measuring and explaining AI systems for new AI engineers and field engineers.',
      favicon: '/favicon.svg',
      sidebar,
      // course.css styles the guided course (scripts/course-pages.mjs) on top of the site theme
      customCss: ['./src/styles/theme.css', './src/styles/course.css'],
      head: [
        { tag: 'script', content: STORAGE_FALLBACK },
        { tag: 'link', attrs: { rel: 'preconnect', href: 'https://fonts.googleapis.com' } },
        { tag: 'link', attrs: { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' } },
        { tag: 'link', attrs: { rel: 'stylesheet', href: FONTS } },
        { tag: 'script', content: OPEN_TARGETED_FILE },
        // The course client: progress on this device, Continue, ticks, drill, video chapters. The spine
        // (window.KIT_SPINE, written by scripts/sync.mjs) must run first; deferred scripts run in order.
        { tag: 'script', attrs: { src: '/ai-field-engineer/kit-spine.js', defer: true } },
        { tag: 'script', attrs: { src: '/ai-field-engineer/kit.js', defer: true } },
      ],
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
      expressiveCode: {
        themes: ['github-dark-default', 'github-light-default'],
        plugins: [pluginLineNumbers()],
        defaultProps: { showLineNumbers: false },
        tabWidth: 0, // keep tabs: a copied Makefile needs its tab-indented recipes
        styleOverrides: {
          borderRadius: '10px',
          codeFontFamily: MONO,
          codeFontSize: '0.84rem',
          uiFontFamily: '"IBM Plex Sans", system-ui, sans-serif',
        },
      },
    }),
  ],
});
