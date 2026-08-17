# -*- coding: utf-8 -*-
"""诊断：手机视口下聊天页横向溢出元素"""
from playwright.sync_api import sync_playwright

URL = "http://106.54.59.177:7595/"
VIEWPORT = {"width": 390, "height": 844}

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport=VIEWPORT)
    page.goto(URL, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)

    metrics = page.evaluate("""() => {
      const vw = window.innerWidth;
      const sw = document.documentElement.scrollWidth;
      const sh = document.documentElement.scrollHeight;
      // 收集溢出视口的元素
      const overflow = [];
      document.querySelectorAll('*').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.right > vw + 1 || r.left < -1) {
          overflow.push({
            tag: el.tagName,
            cls: (el.className && el.className.toString ? el.className.toString().slice(0, 80) : ''),
            left: Math.round(r.left),
            right: Math.round(r.right),
            w: Math.round(r.width),
          });
        }
      });
      // 找出可横向滚动容器
      const scrollX = [];
      document.querySelectorAll('*').forEach(el => {
        if (el.scrollWidth > el.clientWidth + 2) {
          scrollX.push({
            tag: el.tagName,
            cls: (el.className && el.className.toString ? el.className.toString().slice(0, 80) : ''),
            clientW: el.clientWidth,
            scrollW: el.scrollWidth,
          });
        }
      });
      return { vw, sw, sh, overflowCount: overflow.length, overflow: overflow.slice(0, 20),
               scrollXCount: scrollX.length, scrollX: scrollX.slice(0, 15) };
    }""")

    import json
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    b.close()
