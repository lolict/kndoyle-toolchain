const { chromium } = require('playwright');
const fs = require('fs');

const urls = [
  ['xLTLQBOVg0RThL6ZU', 'https://www.doubao.com/thread/xLTLQBOVg0RThL6ZU'],
  ['x3aAWSODUz4AVch6o', 'https://www.doubao.com/thread/x3aAWSODUz4AVch6o'],
  ['xhYWZKoaOgD4gCUTr', 'https://www.doubao.com/thread/xhYWZKoaOgD4gCUTr'],
  ['xe0zpFnuC9K10So2v', 'https://www.doubao.com/thread/xe0zpFnuC9K10So2v'],
  ['x9dIRJEoCe8A9Lcwr', 'https://www.doubao.com/thread/x9dIRJEoCe8A9Lcwr'],
  ['xZ0ntd2EhFtIetSYd', 'https://www.doubao.com/thread/xZ0ntd2EhFtIetSYd'],
  ['xtsat1HY93mx8YjOw', 'https://www.doubao.com/thread/xtsat1HY93mx8YjOw'],
  ['xNJSMR8YBaMh3tJT6', 'https://www.doubao.com/thread/xNJSMR8YBaMh3tJT6'],
];

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-blink-features=AutomationControlled'] });
  for (const [id, url] of urls) {
    const out = `/tmp/opencode/doubao_${id}.txt`;
    const ctx = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
      locale: 'zh-CN'
    });
    const page = await ctx.newPage();
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(25000);
      const title = await page.title();
      const text = await page.evaluate(() => document.body.innerText);
      fs.writeFileSync(out, 'URL: ' + url + '\nTITLE: ' + title + '\n\n' + text, 'utf-8');
      console.log(`OK ${id} | TITLE: ${title} | LEN: ${text.length}`);
    } catch (e) {
      console.log(`FAIL ${id} | ${e.message}`);
    }
    await ctx.close();
    await new Promise(r => setTimeout(r, 5000));
  }
  await browser.close();
  console.log('DONE');
})();
