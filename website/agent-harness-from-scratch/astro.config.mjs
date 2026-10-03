import fs from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

const sidebar = JSON.parse(fs.readFileSync(new URL('./src/generated/sidebar.json', import.meta.url), 'utf8'));
export default defineConfig({
  site: 'https://thelocalnode.dev',
  base: '/agent-harness-from-scratch',
  integrations: [starlight({
    title: 'Agent Harness from Scratch',
    description: 'Build one Python harness across coding, synthetic SRE, and resident automation.',
    favicon: '/favicon.svg',
    sidebar,
    customCss: ['./src/styles/theme.css', './src/styles/course.css'],
    head: [
      { tag: 'script', content: `for(const key of ['localStorage','sessionStorage']){try{window[key].getItem('harness');}catch{const data=new Map();try{Object.defineProperty(window,key,{value:{getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,String(v)),removeItem:k=>data.delete(k),clear:()=>data.clear(),key:i=>[...data.keys()][i]??null,get length(){return data.size;}}});}catch{}}}` },
      { tag: 'script', attrs: { src: '/agent-harness-from-scratch/course-spine.js', defer: true } },
      { tag: 'script', attrs: { src: '/agent-harness-from-scratch/progress.js', defer: true } },
    ],
    tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
  })],
});
