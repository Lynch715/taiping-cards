# 太平天国 · 军报

手机竖屏优先的离线卡牌游戏，两条战役线、各八章，共96关。

- 游戏：https://lynch715.github.io/taiping-cards/
- 手机实测清单：https://lynch715.github.io/taiping-cards/mobile-checklist-v0.4.4.html
- 当前版本：v0.4.4。经济保持v0.4.2，整合已验收A/B/C美术，并补手机触控与安装图标。

## 开发与构建

Node.js 22+、npm、Python 3；静态构建无后端。

```sh
cd app
npm ci
npm test -- --maxWorkers=1
npm run build
npm run dev
```

生产构建位于app/dist；可部署到域名根目录或子目录。发布分支codex/pages只包含静态运行文件；默认分支保留源代码、数据、网页派生图和回归所需的冻结fixtures。原始美术母版、历史大批报告和个人军册不放入公开仓库。

## 手机与离线

等待“离线包就绪”再断网；手机使用Safari“添加到主屏幕”或Android浏览器“安装应用”。桌面图标为太平军报四字朱印。游戏限制捏合与空白双击缩放，保留滚动、章节切换和表单交互。

64px兵装使用一张WebP雪碧图预缓存，128px详情按需下载；离线或加载失败回退64px。人物大图也按需加载。后续章节按解锁增量缓存。首装构建门槛为十进制10MB。

军册只保存在当前浏览器及站点。由本地地址迁往Pages时，先在原地址“军册备份”导出，再在新地址导入。不要把个人军册提交到仓库。

## 资源与说明

字体为Noto Serif SC子集，OFL授权随fonts目录附带。兵种与装备的图源及重建范围见docs/reference/npc_sources.md。
