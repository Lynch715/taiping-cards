#!/usr/bin/env python3
"""Generate the standalone v0.4.4 handset checklist, without touching game saves."""
from pathlib import Path
import html,json
ROOT=Path(__file__).resolve().parents[1]
SECTIONS=[
 ('mobile','手机触控与桌面图标',[
  ('pinch','游戏中双指捏合、双击空白处，页面不放大；单指上下滚动和章节横向滚动仍正常。'),
  ('input','打开军械库筛选或存档选择，输入控件不触发自动放大；按钮连续点击仍正常。'),
  ('safearea','刘海／底部手势条不挡按钮；320至430px竖屏下没有整页横向溢出。'),
  ('icon','从Safari添加到主屏幕或Android安装后，显示太平军报四字朱印，图标文字未被圆形遮罩裁掉。'),
  ('desktop','从桌面图标重开为独立窗口，应用名称为太平军报；浏览器标签页也有对应小图标。')]),
 ('install','首装下载',[
  ('fresh','使用新的HTTPS测试目录或全新浏览器数据开始；先打开游戏，先不打开本清单。已有军册先导出备份。'),
  ('ready','从首次打开游戏计时，等待“离线包就绪”，记录准备耗时与实际下载量。'),
  ('bytes','本轮首次页面＋SW安装总下载≤10,000,000字节。用远程Network日志合计；未取得字节证据则留空，不凭包大小打勾。'),
  ('initial-detail','初装请求有sprite-64.webp，没有equipment/128/中的20张详情图，也没有人物full.webp的主动预取。'),
  ('standalone','Android用浏览器安装；iPhone用Safari分享→添加到主屏幕。从桌面图标重开，能进入游戏。')]),
 ('offline','离线重开',[
  ('prepare','联网完成一场战斗，记下关卡、军功、银两和装备；等“军册已存”及“离线包就绪”。'),
  ('reopen','开启飞行模式并关闭Wi-Fi；彻底退出已安装应用，再从桌面图标打开，能进入原军册。'),
  ('saved','进度、编队、资源和装备保留；“离线”状态正确，不白屏、不反复要求联网。'),
  ('battle','进入已缓存章节，离线完成一场战斗至结算，再重开核对结果保留。'),
  ('smart','离线点击智能布阵仍得到结果；未解锁章节的素材不应被假装成已缓存。')]),
 ('terrain','战斗四地形',[
  ('land','陆战：太平第1章第1关“金田团营”（tp_1_1），5敌＋5我、地面连续、牌面清楚。'),
  ('siege','攻城：太平第1章第5关“围攻桂林”（tp_1_5），敌方城墙在上，我方壕沟在下。'),
  ('defend','守城：太平第3章第6关“连镇·冯官屯”（tp_3_6），我方墙内马道在下，城外敌营在上。'),
  ('river','水战：太平第1章第6关“蓑衣渡”（tp_1_6），上下战船、中缝江面与水雾。'),
  ('frames','四种地形均检查敌方后排卡框上沿、怒气描边和姓名完整；暂停、变速、跳过可用，无顶栏遮挡。'),
  ('terrain-offline','四种地形在离线状态各开一场，背景与杂兵画像仍可见。未解锁的项目记“未测”，不代勾。')]),
 ('advisor','智能布阵耗时',[
  ('timing','同设备、同关卡连续测3次：从点击“智能布阵”到“已智能布阵”结果出现，分别记录冷启动／后两次秒数。'),
  ('responsive','计算中页面仍能响应滚动；没有无响应或一直卡在“正在比较…”。'),
  ('legal','结果保留君主、只用已有武将／兵装，不消耗军功、银两或招贤令；推荐不等于保证获胜。'),
  ('water-timing','在水战再记录3次，注明武将数与兵装数；反复超过5秒或卡住时附录屏及设备信息，不只填“慢”。')]),
 ('icons','军械库图标',[
  ('inventory','进入军械库，已有兵装使用64px图标，刀／衣／马／书可辨；无空白或别的雪碧单元串入。'),
  ('quality','查看能覆盖到的粗／制／精／珍／绝：同套同部位图案相同，品质边框依次灰褐／绿／蓝／紫／金。'),
  ('reward','正常首通或扫荡获得兵装后，奖励区64px图标与入库后图标一致，点图标能开详情。'),
  ('mobile-width','手机竖屏滚动军械库，图标不挤坏名称与按钮，不出现整页横向滚动；未拥有的套装／品质在备注写未测。')]),
 ('detail','详情大图按需加载',[
  ('first128','联网打开一个此前未看的兵装详情：只新增该图标的equipment/128/{id}.webp请求，图像128×128。'),
  ('cached128','关闭后再次打开同一详情，图像正常；已看过的图可缓存，不应重新下载全部20张。'),
  ('fallback','断网后打开此前未看的另一件兵装：仍显示64雪碧单元的放大回退，无破图／空白，关闭正常。'),
  ('portrait','人物详情full.webp同样是首次打开才请求；离线未缓存大图时显示已有卡面预览。'),
  ('online-again','恢复联网，再打开该详情能显示128图或人物大图，不残留破图；清单记录可导出。')])]

FIELDS=[('device','手机型号'),('os','系统及版本'),('browser','浏览器及版本'),('network','网络／Wi-Fi／蜂窝'),('date','实测日期'),('url','游戏部署地址'),('download','首装实测字节数'),('installSeconds','到离线包就绪（秒）'),('landTimes','陆战布阵3次（秒）'),('waterTimes','水战布阵3次（秒）'),('roster','武将数／兵装数'),('evidence','录像／Network记录编号')]

def main():
 out=ROOT/'app/public';out.mkdir(parents=True,exist_ok=True)
 md=['# v0.4.4 手机实测清单','','适用：v0.4.2经济＋已验收A/B/C批美术。真机项目未代测、未代勾。','',
 '先完成首装计量，再打开本清单。清单本身也在静态包内；后续章节增量、已打开的详情、重复测试流量不并入首装。首次安装门槛为十进制10MB。', '',
 '已有军册先导出。全新首装最好用独立HTTPS测试目录；`?qa=`只隔离军册，不清除SW／HTTP缓存，不能单凭加qa参数称为冷安装。手机上的127.0.0.1不是电脑；请部署后使用HTTPS地址。', '',
 '网页清单支持勾选、记录及导出JSON，单独存于本浏览器，和军册分开。换浏览器／清站点数据前导出；本Markdown可打印手填。','']
 for _,name in FIELDS:md.append(f'- {name}：________________')
 md+=['','说明：布阵按真实点击到结果计时；桌面0.4–1.1秒不作为手机承诺。反复超过5秒先记异常及录屏，测试用例的5秒超时不是产品SLA。','',
 '四地形使用已解锁进度；未解锁／未拥有的内容记录“未测”，不当成通过。覆盖到的具体关卡、图标、品质写入各节备注。','']
 cards=[]
 for sid,title,items in SECTIONS:
  md+=['## '+title,'']
  checks=[]
  for ident,text in items:
   md.append('- [ ] '+text)
   checks.append(f'<label class="check"><input type="checkbox" id="{sid}-{ident}" data-record><span>{html.escape(text)}</span></label>')
  md+=['','结果／未测范围／异常及截图编号：________________','']
  cards.append(f'<section><h2>{title}</h2>'+''.join(checks)+f'<label class="notes">结果／未测范围／异常及截图编号<textarea id="notes-{sid}" data-record rows="3"></textarea></label></section>')
 md+=['## 首装计量口径','','用远程浏览器Network的传输量，覆盖从首次页面到离线包就绪的初装请求；保留日志和实际字节数。手机流量统计可作旁证，不能等同精确逐请求合计。整份静态zip约数十MB，包含后期章节与详情，不能拿zip大小代替首装下载。','',
 '开启真离线请用飞行模式并确认Wi-Fi关闭，不能只看缓存命中或模拟offline事件。首次根本没缓存的站点无法离线启动。','',
 '完成后导出清单记录，并附Network日志或录屏。不得把桌面模拟截图标作手机真机通过。','']
 source='\n'.join(md);(out/'mobile-checklist-v0.4.4.md').write_text(source)
 fields=''.join(f'<label>{html.escape(name)}<input id="field-{key}" data-record autocomplete="off" type="text"></label>' for key,name in FIELDS)
 page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v0.4.4 手机实测清单</title><style>
*{box-sizing:border-box}body{margin:0;background:#ede3cc;color:#28231b;font-family:Songti SC,STSong,serif;line-height:1.8}main{max-width:860px;margin:auto;padding:22px 16px 70px}h1{font-size:27px;margin:6px 0}h2{font-size:20px;border-bottom:3px double #a4906d;padding-bottom:8px}p{font-size:14px}.note{border-left:4px solid #245249;padding:12px;background:#e1d6bb}.fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}.fields label,.notes{display:block;font-size:13px}input[type=text],textarea{display:block;background:#faf3e4;border:1px solid #a99877;border-radius:0;min-height:42px;width:100%;font:16px/1.6 serif;padding:6px}textarea{resize:vertical}section{border:1px solid #aa9876;background:#f5eddc;padding:14px 16px;margin-top:18px}.check{display:flex;gap:12px;padding:12px 0;align-items:flex-start;border-bottom:1px solid #ddd0b4;font-size:15px;min-height:48px}.check input{flex:none;width:22px;height:22px;margin:3px 0 0;accent-color:#245249}.notes{margin-top:16px}nav{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}button,a.action{border:1px solid #245249;background:#245249;color:#fff;font:14px/1.5 serif;padding:10px 14px;min-height:44px;text-decoration:none}a{color:#245249}#save-status,#progress{font-size:13px}#progress{font-weight:bold}details{margin-top:20px}summary{cursor:pointer;min-height:44px}footer{font-size:12px;margin-top:20px}@media(max-width:500px){.fields{grid-template-columns:1fr}main{padding:18px 12px 50px}section{padding:12px}}@media print{body{background:white}main{padding:0;max-width:none}nav,details,footer{display:none}section{break-inside:avoid;background:white}input[type=text],textarea{background:white}h1{font-size:23px}.check{font-size:12px;padding:6px 0}}
</style></head><body><main><h1>v0.4.4 手机实测清单</h1><p>v0.4.2经济＋A/B/C批美术 · 真机结果由你逐项填写</p><p class="note">先完成首装计量，再打开清单。每项初始未勾选；勾选仅保存在本浏览器，与游戏军册分开。请导出记录留档。</p><p>冷安装请用独立HTTPS测试目录或全新浏览器数据。qa参数只隔离军册，不会清SW缓存；已有军册先导出。手机127.0.0.1不指向电脑，使用部署后的HTTPS游戏地址。</p><div class="fields">'''+fields+'''</div><nav><button id="export" type="button">导出实测记录</button><button id="print" type="button">打印／存为PDF</button><a class="action" href="mobile-checklist-v0.4.4.md" download>下载空白Markdown</a><a href="./">返回游戏</a></nav><p id="progress" role="status"></p><p id="save-status" aria-live="polite">本清单不读写游戏军册。</p>'''+''.join(cards)+'''<details><summary>计量与判定说明</summary><p>首装为首次页面至“离线包就绪”，门槛10,000,000字节；用远程Network传输量合计并留日志。整份zip、已解锁后续章节、详情按需下载、再次测试流量分别记载，不并入初装。手机流量统计可作旁证。</p><p>真离线使用飞行模式并关闭Wi-Fi。未解锁或未拥有内容注明未测；不改正常军册来假造通过。桌面布阵耗时不代表手机承诺；3次点击至结果分别记录，反复超过5秒或卡住时记异常及录屏，5秒不是产品SLA。</p><p>完成后导出JSON，并附Network日志、录像和实际设备信息。浏览器模拟与自动测试不得标成手机真机通过。</p></details><footer>查看包版本／文件清单：<a href="pwa-build.json">pwa-build.json</a>。网页清单支持离线填写；换浏览器或清站点数据前导出。</footer></main><script>
(()=>{'use strict';const qa=new URLSearchParams(location.search).get('qa');const key='taiping-mobile-acceptance-v044'+(qa?'-qa-'+qa.replace(/[^a-zA-Z0-9_-]/g,''):'');const fields=[...document.querySelectorAll('[data-record]')];let state={};try{state=JSON.parse(localStorage.getItem(key)||'{}')||{};}catch{}for(const el of fields){if(el.type==='checkbox')el.checked=state[el.id]===true;else if(typeof state[el.id]==='string')el.value=state[el.id];}function read(){return Object.fromEntries(fields.map(el=>[el.id,el.type==='checkbox'?el.checked:el.value]));}function progress(){const all=fields.filter(el=>el.type==='checkbox');document.querySelector('#progress').textContent='已勾选 '+all.filter(el=>el.checked).length+' / '+all.length+' 项（未勾选不代表通过）';}function persist(){state=read();try{localStorage.setItem(key,JSON.stringify(state));document.querySelector('#save-status').textContent='清单已保存在本浏览器；请另导出留档。';}catch{document.querySelector('#save-status').textContent='当前浏览器不能保存清单，请立即导出记录。';}progress();}for(const el of fields)el.addEventListener('input',persist);document.querySelector('#export').addEventListener('click',()=>{const data={format:'taiping-mobile-acceptance',version:1,release:'0.4.4',exportedAt:new Date().toISOString(),entries:read()};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='taiping-v0.4.4-手机实测记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);});document.querySelector('#print').addEventListener('click',()=>print());progress();})();
</script></body></html>'''
 (out/'mobile-checklist-v0.4.4.html').write_text(page)
 (ROOT/'docs/手机实测清单-v0.4.4.md').write_text(source)
 print(json.dumps({'items':sum(len(x[2]) for x in SECTIONS),'html_bytes':len(page.encode()),'markdown_bytes':len(source.encode())}))
if __name__=='__main__':main()
