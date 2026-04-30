const fs = require('fs');
const path = require('path');

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    file = path.join(dir, file);
    const stat = fs.statSync(file);
    if (stat && stat.isDirectory()) {
      results = results.concat(walk(file));
    } else if (file.endsWith('.vue')) {
      results.push(file);
    }
  });
  return results;
}

const files = walk('./src');
files.forEach(f => {
  let content = fs.readFileSync(f, 'utf8');
  content = content.replace(/\btext-zinc-100\b/g, 'text-zinc-900 dark:text-zinc-100');
  content = content.replace(/\btext-zinc-200\b/g, 'text-zinc-800 dark:text-zinc-200');
  content = content.replace(/\btext-zinc-300\b/g, 'text-zinc-700 dark:text-zinc-300');
  content = content.replace(/\btext-zinc-400\b/g, 'text-zinc-500 dark:text-zinc-400');
  
  content = content.replace(/\bbg-zinc-950\b/g, 'bg-zinc-50 dark:bg-zinc-950');
  content = content.replace(/\bbg-zinc-950\/50\b/g, 'bg-zinc-50/50 dark:bg-zinc-950/50');
  
  content = content.replace(/\bbg-zinc-900\b/g, 'bg-white dark:bg-zinc-900');
  content = content.replace(/\bbg-zinc-900\/50\b/g, 'bg-white/50 dark:bg-zinc-900/50');
  content = content.replace(/\bbg-zinc-900\/80\b/g, 'bg-white/80 dark:bg-zinc-900/80');
  
  content = content.replace(/\bbg-zinc-800\b/g, 'bg-zinc-100 dark:bg-zinc-800');
  content = content.replace(/\bbg-zinc-800\/40\b/g, 'bg-zinc-50 dark:bg-zinc-800/40');
  content = content.replace(/\bbg-zinc-800\/50\b/g, 'bg-zinc-100/50 dark:bg-zinc-800/50');
  content = content.replace(/\bbg-zinc-800\/60\b/g, 'bg-zinc-100/60 dark:bg-zinc-800/60');
  content = content.replace(/\bbg-zinc-800\/70\b/g, 'bg-zinc-100/70 dark:bg-zinc-800/70');
  content = content.replace(/\bbg-zinc-800\/80\b/g, 'bg-zinc-100/80 dark:bg-zinc-800/80');
  
  content = content.replace(/\bbg-zinc-700\b/g, 'bg-zinc-200 dark:bg-zinc-700');
  
  content = content.replace(/\bborder-zinc-800\b/g, 'border-zinc-200 dark:border-zinc-800');
  content = content.replace(/\bborder-zinc-800\/50\b/g, 'border-zinc-200/50 dark:border-zinc-800/50');
  content = content.replace(/\bborder-zinc-700\b/g, 'border-zinc-300 dark:border-zinc-700');
  content = content.replace(/\bborder-zinc-700\/50\b/g, 'border-zinc-300/50 dark:border-zinc-700/50');
  content = content.replace(/\bborder-zinc-700\/60\b/g, 'border-zinc-300/60 dark:border-zinc-700/60');
  fs.writeFileSync(f, content);
});
