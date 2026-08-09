# ericdocmic.top 主站

这是 `ericdocmic.top` 根域的独立静态主站页面「eric的开发日记」。

- 根域：`https://ericdocmic.top`
- 首页：`index.html`
- 404 页面：`404.html`

根域不做自动跳转，也不展示 GitHub、作品集或项目入口。`404.html` 可在 1Panel / OpenResty 中配置为网站的 404 错误页。

推荐在网站的 OpenResty 配置中加入：

```nginx
error_page 404 /404.html;

location = /404.html {
  internal;
}
```

## 打包

```bash
npm run export:1panel
```

产物会输出到 `release/ericdocmic-main-1panel-*.tar.gz`，压缩包包含 `index.html` 和 `404.html`，可直接上传到 1Panel 网站根目录。
