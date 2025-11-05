# How to wire the site to `poems.json`

1) Put this HTML somewhere in your `index.html` where poems should appear:

```html
<section id="poetry">
  <h2>Poetry</h2>
  <div id="poems-container"></div>
</section>

<script>
  function nl2br(str) { return (str || '').replace(/\n/g, '<br>'); }
  function togglePoem(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = (el.style.display === 'block') ? 'none' : 'block';
  }
  fetch('poems.json', { cache: 'no-store' })
    .then(r => r.json())
    .then(poems => {
      const container = document.getElementById('poems-container');
      let idx = 0;
      const catOrder = ["Стихи / Poems","Переводы / Translations","Шутки в сторону / Not serious"];
      catOrder.forEach(cat => {
        const section = document.createElement('div');
        const h = document.createElement('h3');
        h.textContent = cat;
        section.appendChild(h);
        poems.filter(p => p.category === cat).forEach(p => {
          idx += 1;
          const id = `poem-${idx}`;
          const title = document.createElement('h4');
          title.className = 'poem-title';
          title.textContent = p.title + (p.year ? ` (${p.year})` : '');
          title.onclick = () => togglePoem(id);
          const content = document.createElement('div');
          content.className = 'poem-content';
          content.id = id;
          content.style.display = 'none';
          content.innerHTML = `<div>${nl2br(p.body)}</div>`;
          section.appendChild(title);
          section.appendChild(content);
        });
        container.appendChild(section);
      });
    });
</script>
```

2) Commit the new files:
- `scripts/sync_poems.py`
- `.github/workflows/sync-poems.yml`

3) In your GitHub repository settings → **Secrets and variables → Actions → New repository secret**:
   - Name: `DOC_PUBLISHED_URL`
   - Value: paste the **Publish to the web** URL of your Google Doc (not the edit link).

4) In Google Docs: **File → Share → Publish to web** → copy the public link.
   (The regular “anyone with the link can view” edit URL won’t work in GitHub Actions without credentials.)

5) Trigger the workflow via **Actions → Sync poems from Google Doc → Run workflow**,
   or wait for the daily schedule.
