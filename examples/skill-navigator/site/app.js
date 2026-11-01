'use strict';
const $ = id => document.getElementById(id);
const statusLabels = {bindable:'可绑定',not_indexed:'未被索引',ambiguous:'入口歧义',stale:'内容已变化',disabled:'宿主未启用',invalid_source:'源未接纳'};
const sourceLabels = {local:'本机技能',plugin:'插件技能',system:'系统技能',project:'项目技能',external:'根目录之外'};
let dataset = null, visible = [], limit = 24, lastTrigger = null;

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function reset() {
  $('filters').reset(); limit = 24; render();
}
function render() {
  if (!dataset) return;
  const query = $('search').value.trim().toLocaleLowerCase();
  const source = $('source-filter').value, state = $('state-filter').value;
  visible = dataset.skills.filter(s => (source === 'all' || source === s.source_kind) &&
    (state === 'all' || state === s.binding_status) &&
    (!query || [s.id,s.name,s.description,s.source_label].join(' ').toLocaleLowerCase().includes(query)));
  $('result-count').textContent = `找到 ${visible.length} / ${dataset.skills.length} 项技能`;
  $('empty').hidden = visible.length !== 0;
  $('load-more').hidden = visible.length <= limit;
  $('page-info').textContent = visible.length ? `已显示 ${Math.min(limit,visible.length)} / ${visible.length}` : '';
  const fragment = document.createDocumentFragment();
  for (const s of visible.slice(0,limit)) {
    const li = node('li'), button = node('button',undefined,'skill-open');
    button.type = 'button'; button.setAttribute('aria-label',`查看 ${s.name} 详情`);
    const info = node('span'), meta = node('span',undefined,'skill-status');
    info.append(node('span',s.name,'skill-name'),node('span',s.description || '此入口未提供描述。','skill-description'),node('span',s.source_label,'skill-source'));
    meta.append(node('span',statusLabels[s.binding_status],`badge ${s.binding_status}`),node('span',s.host_enabled?'宿主已启用':'宿主未启用'),node('span','依赖未知'));
    button.append(info,meta); button.addEventListener('click',() => showDetail(s,button));
    li.append(button);fragment.append(li);
  }
  $('results').replaceChildren(fragment);
}
function showDetail(skill, trigger) {
  lastTrigger = trigger; $('detail-title').textContent = skill.name;
  $('detail-description').textContent = skill.description || '此入口未提供描述。';
  $('entrypoint').value = skill.entrypoint; $('copy-status').textContent = '';
  const explicit = skill.explicit_only === null ? '索引未提供' : skill.explicit_only ? '需要用户明确点名' : '按适用条件选择';
  const fields = [['技能 ID',skill.id],['来源',skill.source_label],['宿主状态',skill.host_enabled?'已启用':'未启用'],['Vibe 绑定',statusLabels[skill.binding_status]],['依赖验证','未知 · 需按具体任务验证'],['调用条件',explicit]];
  if (skill.binding_reasons.length) fields.push(['诊断原因',skill.binding_reasons.join('；')]);
  const fragment = document.createDocumentFragment();
  for (const [key,value] of fields) fragment.append(node('dt',key),node('dd',value));
  $('detail-meta').replaceChildren(fragment); $('skill-detail').showModal();
}
function validate(data) {
  if (!data || data.schema_version !== 'skill_navigator_v1' || data.data_origin !== 'live_codex_app_server' || !Array.isArray(data.skills) || !data.summary || !Array.isArray(data.diagnostics)) throw new Error('清单格式不受支持，请重新运行导出工具。');
  const keys = new Set();
  for (const s of data.skills) {
    if (!s || typeof s.key!=='string' || keys.has(s.key) || !['id','name','description','entrypoint','source_label'].every(k=>typeof s[k]==='string') || typeof s.host_enabled!=='boolean' || !Object.hasOwn(statusLabels,s.binding_status) || !Object.hasOwn(sourceLabels,s.source_kind) || s.dependency_status!=='unknown' || !Array.isArray(s.binding_reasons)) throw new Error('清单包含无效或重复的技能记录。');
    keys.add(s.key);
  }
  if (data.summary.total !== data.skills.length || data.summary.host_enabled !== data.skills.filter(s=>s.host_enabled).length || data.summary.vibe_bindable !== data.skills.filter(s=>s.binding_status==='bindable').length || data.summary.dependency_unknown !== data.skills.length) throw new Error('清单统计与实际记录不一致。');
  return data;
}
async function load() {
  dataset = null; $('results').replaceChildren();$('results').setAttribute('aria-busy','true');
  $('load-error').hidden = true; $('empty').hidden = true; $('load-more').hidden = true;
  $('result-count').textContent = '正在载入…'; $('page-info').textContent = '';
  for (const id of ['enabled-stat','bindable-stat','other-stat','dependency-stat']) $(id).textContent='—';
  for (const id of ['search','source-filter','state-filter','reset-filters']) $(id).disabled = true;
  try {
    const response = await fetch('../source-data/enabled-skills.json',{cache:'no-store'});
    if (!response.ok) throw new Error(`数据文件读取失败（HTTP ${response.status}）。`);
    dataset = validate(await response.json());
    const summary = dataset.summary;
    $('enabled-stat').textContent=summary.host_enabled; $('bindable-stat').textContent=summary.vibe_bindable;
    $('other-stat').textContent=summary.total-summary.vibe_bindable; $('dependency-stat').textContent=summary.dependency_unknown;
    const date = new Date(dataset.generated_at); $('snapshot').textContent=`原生注册表快照 · ${Number.isNaN(date.valueOf())?dataset.generated_at:date.toLocaleString('zh-CN',{hour12:false})} · ${summary.enabled_plugins_count} 个启用插件`;
    for (const [id,field,labels] of [['source-filter','source_kind',sourceLabels],['state-filter','binding_status',statusLabels]]) {
      const select=$(id);select.replaceChildren(new Option(id==='source-filter'?'全部来源':'全部状态','all'));
      for (const key of Object.keys(labels)) {const count=dataset.skills.filter(s=>s[field]===key).length;if(count) select.add(new Option(`${labels[key]} · ${count}`,key));}
    }
    $('diagnostic-count').textContent=`· ${dataset.diagnostics.length} 条`;
    $('diagnostic-list').replaceChildren(...dataset.diagnostics.map(d=>{const li=node('li',d.reason||d.group||'未分类诊断');if(d.message)li.append(node('p',d.message));if(d.path)li.append(node('code',d.path));return li;}));
    for (const id of ['search','source-filter','state-filter','reset-filters']) $(id).disabled = false;
    $('filters').reset();limit=24;render();
  } catch (error) {
    dataset = null; $('load-error').hidden=false;$('error-message').textContent=error.message;
    $('result-count').textContent='清单不可用';$('snapshot').textContent='未加载有效快照';
    $('diagnostic-count').textContent='';$('diagnostic-list').replaceChildren();
  } finally {$('results').setAttribute('aria-busy','false');}
}
$('filters').addEventListener('submit',event=>event.preventDefault());
for (const id of ['search','source-filter','state-filter']) $(id).addEventListener(id==='search'?'input':'change',()=>{limit=24;render();});
$('reset-filters').addEventListener('click',reset);$('clear-empty').addEventListener('click',()=>{reset();$('search').focus();});
$('retry').addEventListener('click',load);$('load-more').addEventListener('click',()=>{limit+=24;render();});
$('close-detail').addEventListener('click',()=>$('skill-detail').close());
$('skill-detail').addEventListener('close',()=>{if(lastTrigger?.isConnected)lastTrigger.focus();});
$('copy-entry').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('entrypoint').value);$('copy-status').textContent='入口已复制';}catch{$('entrypoint').focus();$('entrypoint').select();$('copy-status').textContent='请按系统复制快捷键复制已选入口';}});
document.addEventListener('keydown',event=>{if(event.key==='/'&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!$('skill-detail').open&&!['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName)) {event.preventDefault();$('search').focus();}});
load();
