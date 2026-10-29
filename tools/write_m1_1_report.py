#!/usr/bin/env python3
"""Summarize M1.1 implementation and the saved browser evidence."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'assets/reports/m1_1'
read=lambda p:json.loads((R/p).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
static=read('static_validation.json');gold=json.loads((ROOT/'assets/reports/m1/golden/comparison.json').read_text());font=read('font_coverage.json')
assert static['release_matches_dist'] and static['every_revision_verified']
assert gold['passed']==100 and gold['failed']==0
assert not font['missing_printable']
assert read('npm_audit.json')['metadata']['vulnerabilities']['total']==0
log=(R/'vitest.log').read_text();assert re.search(r'Tests\s+20 passed',log),log
assert 'ServiceWorker' in (R/'chrome_offline_requests.ax.txt').read_text()
assert '离线' in (R/'native_offline_result.ax.txt').read_text()
assert '军势大振' in (R/'native_offline_qing_result.ax.txt').read_text()
assert '6  / 6 捷' in (R/'legacy_m1_save.ax.txt').read_text()
update=read('browser_update_result.json');assert update['meta']==static['version'] and '2 / 6 捷' in update['afterRefreshText']
assets=list((ROOT/'app/public/assets/characters').glob('*/*'))
assert all(sha(p)==sha(ROOT/'assets/characters'/p.parent.name/p.name) for p in assets if p.is_file())
files=[p for p in (ROOT/'app/src').rglob('*') if p.is_file()]+[p for p in (ROOT/'app/scripts').glob('*') if p.is_file()]
manifest={'version':static['version'],'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'data_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'data').glob('*.csv')},'golden':gold,'tests':20,'static':static,'font_missing':font['missing_printable'],'unchanged_art_files':len(assets),'verification':{'installed_desktop_pwa':True,'offline_reload_and_two_campaigns':True,'corrupt_import_preserves_save':True,'valid_import_persists':True,'update_preserves_progress':True,'update_disabled_during_battle':True,'legacy_m1_save_compatible':True,'subdirectory_deployment':True}}
(R/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(R/'golden_comparison.json').write_text(json.dumps(gold,indent=2)+'\n')
text=f'''# M1.1 网页交付验收

按 `docs/06-技术方案.md` v0.2 第 7 节完成；当前交付版本 `{static['version']}`。本次交付为本地可预览、可静态托管的网页版，没有发布到公网。

## 交付结果

|要求|结果|证据|
|---|---|---|
|移除原生工程|通过|app/ios、app/android、Capacitor 配置与补丁脚本已移除；package.json/lock 无 Capacitor 依赖。原工程仅作为历史 ZIP 备份保存在 before/，不进入运行和部署目录。|
|PWA 清单、图标、竖屏、主题|通过|manifest 含相对 id/start_url/scope、standalone、portrait、宣纸色、192/512 与 maskable 图标。|
|离线可玩|通过|Chrome 已安装独立应用，在 DevTools Offline 下重新加载，两条战役线均可出征至结算；缓存提供字体、动态战斗模块、立绘和详情全图。|
|新版本提示|通过|准备完整新包后显示“有新版本，点击刷新”；战斗中按钮禁用；结算后点击才切换版本，进度从 1/6 战至 2/6 后刷新仍为 2/6。|
|军册导出/导入|通过|实测 JSON 下载、坏文件拒绝、导入前摘要、确认后替换、刷新恢复。错误文件没有写入当前军册。|
|静态部署|通过|release/taiping-web 与 app/dist 逐文件一致；所有 {static['precache_files']} 项缓存资源 SHA-256 与构建清单一致；域名根目录和 /taiping/ 子目录均实走对战。|
|竖排战报末列|通过|依全文字数平分列高，末列不再出现一两个字；全文字符保留，标点尽量不置列首。全部 CSV 战报及 1–200 字边界测试通过。|

## 安装与离线验收范围

安装验收是 **macOS Chrome 的真实桌面 PWA 安装**：经过浏览器“安装应用”对话框，出现“已成功安装”，再以独立应用窗口运行，界面显示“已安装”，窗口没有普通地址栏。不是把清单存在当成安装通过，也不是普通书签。

断网通过 Chrome DevTools Network 的 Offline 配置完成，先断网再重新加载。Network 记录显示资源由 ServiceWorker 提供；太平军金田团营自然播放 15 回合至胜利。更新最终版本后，又断网重载，进入清军线、打开曾国藩全图详情、战斗至结算；默认编队两次失利后，用第一章已校准编队正常胜利。没有通过修改军册或强制胜利来伪造结果。验收后已退出 DevTools，确认应用恢复“联网”。

手机部分完成 320×568、390×844 视口检查；本次没有冒充 iPhone / 安卓真机安装验收。320px 横向滚动宽度等于视口，顶部备份入口与底部出征按钮均可用。

## 存档保护

沿用 M1 的 `taiping-m1 / slots` 与 `m1-save-v1`，测试军册继续按 `?qa=标签` 隔离。还实际打开旧 M1 的 QA 军册，清军 6/6 进度与原编队正常读出，不要求迁移或清档。

导出封装包含格式名、版本、导出时间、完整 Save 与 SHA-256。导入先校验 1MB 上限、JSON/版本、合法人物与连续关卡、SHA-256，再展示摘要。只有点击“导入并替换军册”才在一个 IndexedDB 事务中提交当前军册及上一份有效备份；重复保存不会把替换前的备份挤掉。SHA-256 用于发现损坏，不是账号签名或防作弊机制。

实际文件证据保存在 exports/：empty.json 与 one_win.json 是通过游戏导出按钮下载的备份，corrupt.json 是专门修改种子但不更新校验值的测试文件。坏档被拒绝后仍为太平 1/6；有效空档导入回到 0/6，再导入 one_win 恢复 1/6，刷新保持；随后正常对战与更新验收推进至 2/6。

## 缓存与更新

完整离线包 {static['precache_bytes']/1024/1024:.1f}MB，{static['precache_files']} 个资源；包括所有可能延迟加载的战斗模块和第一章可见人物素材，不要求先逐页看过。每个下载资源校验 SHA-256，不完整的离线包不会激活。失败时继续保留上一份可用版本。

新版本默认等待，页面不自动跳转。确认刷新前等待军册事务结束。旧缓存等同一作用域全部打开页面确认新 HTML 后再整理，避免其他旧页的延迟模块突然缺失；清理只针对本游戏缓存，不删除 IndexedDB。

缓存测试覆盖首次安装、等待用户激活、HTTP 失败、不匹配的资源字节、子目录离线导航、未先看过的素材、多开旧页保留缓存。

## 数据与回归

- TypeScript strict、生产构建、20 项 Vitest 全部通过。
- 100 组 Python/TypeScript 金标准，{gold['log_lines']:,} 行日志逐行一致，失败 0；未改战斗引擎或人物技能数值。
- npm audit 已知漏洞 0；新增界面文字已加入本地字体子集，缺失可打印字符 0。
- 原美术 {len(assets)} 个文件逐一哈希一致。
- stages.csv 新增了第二章草案且等级留空。导出器将这些等级保留为 null，运行时只开放 chapter=1，后续草案不会误入第一章；CSV 本身未改动。金标准生成器也明确只取第一章 12 个关卡。

## 部署交付

- 静态目录：`release/taiping-web/`
- 压缩包：`release/taiping-web-0.1.1.zip`（解压后 index.html 位于根层）
- 详细步骤：`app/DEPLOY.md`、`release/DEPLOY.md`
- 本地验收：`cd app && npm run preview`，http://127.0.0.1:5192/ 。开发服务器不注册 SW。
- 线上使用 HTTPS，HTML/SW/清单设为可检查更新；完整上传构建目录。没有后端需求。

ZIP SHA-256：`{static['zip_sha256']}`。本报告、源文件/数据哈希与浏览器记录见 delivery_manifest.json。

## 截图

### 真实安装成功

![Chrome 安装成功](screenshots/pwa_install_success.png)

### 已安装独立窗口

![PWA 独立窗口](screenshots/pwa_installed_window.png)

### 断网重开后试玩并结算

![已安装 PWA 离线胜利](screenshots/pwa_offline_result.png)

### 浏览器真实 Offline 配置和缓存请求

![Offline 与 ServiceWorker 请求](screenshots/offline_cached_requests.png)

### 均匀竖排战报

![战报不留孤列](screenshots/dispatch_balanced.png)

### 坏档拒绝覆盖

![损坏军册被拒绝](screenshots/corrupt_save_rejected.png)

### 新版本提示

![新版本点击刷新](screenshots/update_prompt.png)

实现时核对了 [Chrome 更新生命周期建议](https://developer.chrome.com/docs/workbox/handling-service-worker-updates) 与 [PWA 安装形态说明](https://web.dev/learn/pwa/installation)；最终结果以上述本机实测为准。
'''
(R/'acceptance_report.md').write_text(text)
print(json.dumps({'version':static['version'],'tests':20,'golden':gold,'static_verified':True},ensure_ascii=False))
