const byId = id => document.getElementById(id);
const endpoint = new URL("api", location.href);
let words = [];
let effects = {};
let canEditEffects = false;
let canEditWords = false;
let canPrank = false;
let mode = "suggest";
let busy = false;
const styles = {normal: "普通弹幕", gold: "金色弹幕", urgent: "醒目提醒",
  comic: "漫画爆炸字", sticker: "歪章贴纸", signal: "方向路牌", prank: "单挑大字"};
const positions = {scroll: "从右往左", top: "顶部正中", bottom: "底部悬浮",
  right: "右侧弹入", left: "左侧弹入", auto: "跟随语音方向"};

function effectEditor(word) {
  const [style, delay, glyph, position = "scroll"] = Object.hasOwn(effects, word)
    ? effects[word] : ["normal", 0, "区"];
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = [styles[style], style === "prank" ? "屏幕中央" : positions[position],
    delay ? delay + " 秒冷却" : ""].filter(Boolean).join(" · ");
  const form = document.createElement("form");
  const select = document.createElement("select");
  for (const [value, name] of Object.entries(styles)) {
    if (value === "prank" && !canPrank) continue;
    select.add(new Option(name, value, value === style, value === style));
  }
  const placement = document.createElement("select");
  for (const [value, name] of Object.entries(positions)) {
    placement.add(new Option(name, value, value === position, value === position));
  }
  placement.disabled = style === "prank";
  select.onchange = () => { placement.disabled = select.value === "prank"; };
  const seconds = document.createElement("input");
  seconds.type = "number";
  seconds.min = "0";
  seconds.max = "120";
  seconds.value = delay;
  seconds.required = true;
  const character = document.createElement("input");
  character.maxLength = 2;
  character.value = glyph;
  const fields = [["弹幕特效", select], ["出场位置", placement], ["冷却秒数", seconds], ["整蛊大字", character]];
  for (const [title, field] of fields) {
    const label = document.createElement("label");
    label.append(title, field);
    form.append(label);
  }
  const save = document.createElement("button");
  save.textContent = mode === "suggest" ? "提交特效建议" : "保存特效";
  form.append(save);
  form.onsubmit = event => {
    event.preventDefault();
    request({action: "effect", word, style: select.value,
      cooldown: Number(seconds.value), glyph: character.value || "区", position: placement.value});
  };
  details.append(summary, form);
  return details;
}
function render() {
  const needle = byId("search").value.toLocaleLowerCase();
  const list = byId("words");
  list.replaceChildren();
  for (const word of words.filter(word => word.toLocaleLowerCase().includes(needle))) {
    const row = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = word;
    const remove = document.createElement("button");
    remove.textContent = mode === "suggest" ? "建议删除" : "删除";
    remove.setAttribute("aria-label", remove.textContent + " " + word);
    remove.onclick = () => request({action: "delete", word});
    const heading = document.createElement("div");
    heading.className = "word-heading";
    heading.append(name);
    if (canEditWords) heading.append(remove);
    row.append(heading);
    if (canEditEffects) row.append(effectEditor(word));
    list.append(row);
  }
}
async function request(change) {
  if (busy) return false;
  busy = true;
  try {
    const reply = await fetch(endpoint, change ? {
      method: "POST", headers: {"Content-Type": "application/json", "X-Word-Edit": "1"},
      body: JSON.stringify(change)
    } : {});
    if (reply.status === 404) throw Error("编辑链接已撤销或已失效");
    const data = await reply.json();
    if (!reply.ok) throw Error(data.error);
    words = data.words;
    effects = data.effects;
    mode = data.share_mode;
    canEditWords = data.share_words;
    canEditEffects = data.share_effects;
    canPrank = mode === "suggest" || data.friend_pranks;
    byId("add").hidden = !canEditWords;
    byId("add-button").textContent = mode === "suggest" ? "提交建议" : "添加";
    byId("permissions").textContent = mode === "suggest"
      ? "建议链接 · 由词库主人通过后生效。"
      : "限时共编 · 改动即时生效 · " + new Date(data.share_expires * 1000).toLocaleString() + " 到期";
    render();
    byId("status").textContent = (change ? (mode === "suggest" ? "建议已提交 · " : "已保存 · ") : "")
      + words.length + " 个关键词";
    return true;
  } catch (error) {
    byId("status").textContent = error.message;
    return false;
  } finally {
    busy = false;
  }
}
byId("search").oninput = render;
byId("add").onsubmit = async event => {
  event.preventDefault();
  if (await request({action: "add", word: byId("word").value})) byId("word").value = "";
};
request();
