"use strict";

const memoryContent = {
  working: {
    tab: "tab-working",
    code: "WORKING SUMMARY",
    name: "工作摘要",
    purpose: "保存当前任务的增量步骤摘要，支持压缩与 Token 控制，让下一位 Agent 知道任务如何走到这里。",
    effect: "研究简报 → 初稿 → 审校报告的关键决策进入当前任务上下文。",
    fields: [
      ["来源", "任务步骤"],
      ["范围", "当前任务"],
      ["生命周期", "任务进行中"],
      ["操作", "增量摘要 / 压缩"]
    ]
  },
  session: {
    tab: "tab-session",
    code: "CONVERSATION MESSAGES",
    name: "会话消息",
    purpose: "保存本轮会话消息与语义上下文，通过动态窗口和语义回捞补足当前对话。",
    effect: "提纲确认与本轮修改要求进入写作 Agent 上下文，不扩散到其他任务。",
    fields: [
      ["来源", "本轮会话"],
      ["范围", "当前会话"],
      ["生命周期", "会话期间"],
      ["操作", "动态窗口 / 语义回捞"]
    ]
  },
  longterm: {
    tab: "tab-longterm",
    code: "LONG-TERM PREFERENCES",
    name: "长期偏好",
    purpose: "保存 hard、pattern、feedback 三类偏好，并保留来源、置信度、出现次数、状态与替代链。",
    effect: "“禁用模板化句式”作为已确认反馈生效；价值取向差异仍按用户和范围处理。",
    fields: [
      ["来源", "用户反馈"],
      ["范围", "指定用户 / 场景"],
      ["置信度", "持续验证"],
      ["生命周期", "可修正 / 可替代"]
    ]
  },
  entity: {
    tab: "tab-entity",
    code: "ENTITY RELATION NETWORK",
    name: "实体关系网络",
    purpose: "存储实体与关系，支持实体抽取和关联检索，让人物、事件与主题关系可被后续任务复用。",
    effect: "审校可关联检索人物、事件与主题上下文，同时保留信源边界。",
    fields: [
      ["来源", "实体抽取"],
      ["范围", "关联主题"],
      ["关系", "实体 / 关系"],
      ["操作", "关联检索"]
    ]
  }
};

const agentSequence = [
  {
    key: "research",
    running: "检索与核验中",
    complete: "研究完成",
    artifact: "研究简报 v1 · 已生成",
    event: "研究 Agent 生成研究简报 v1，完成信源与信息缺口检查"
  },
  {
    key: "writer",
    running: "读取简报与记忆",
    complete: "初稿完成",
    artifact: "初稿 v1 · 已生成",
    event: "写作 Agent 读取研究简报与 Memory，生成初稿 v1"
  },
  {
    key: "review",
    running: "事实与结构审校",
    complete: "需要人工裁决",
    artifact: "审校报告 v1 · 已生成",
    event: "审校 Agent 发现个人视角缺失，生成 Decision Packet"
  }
];

const runButton = document.querySelector("#run-flow");
const resetButton = document.querySelector("#reset-demo");
const runAnotherButton = document.querySelector("#run-another");
const saveTakeoverButton = document.querySelector("#save-takeover");
const eventLog = document.querySelector("#event-log");
const consoleStatus = document.querySelector("#console-status");
const decisionPacket = document.querySelector("#decision-packet");
const packetStatus = document.querySelector("#packet-status");
const packetLockMessage = document.querySelector(".packet-lock-message");
const decisionResult = document.querySelector("#decision-result");
const takeoverEditor = document.querySelector("#takeover-editor");
const currentOwner = document.querySelector("#current-owner");
const taskState = document.querySelector("#task-state");
const resultTitle = document.querySelector("#result-title");
const resultDetail = document.querySelector("#result-detail");
const humanDraft = document.querySelector("#human-draft");
const decisionButtons = Array.from(document.querySelectorAll("[data-decision]"));
const timers = [];
let flowReady = false;
let eventTick = 0;

function makeTime() {
  eventTick += 1;
  return "00:0" + eventTick;
}

function addEvent(message) {
  const item = document.createElement("li");
  const time = document.createElement("time");
  const text = document.createElement("span");
  time.textContent = makeTime();
  text.textContent = message;
  item.append(time, text);
  eventLog.append(item);
}

function getAgent(key) {
  return document.querySelector('[data-agent="' + key + '"]');
}

function setAgent(agentData, phase) {
  const card = getAgent(agentData.key);
  const state = card.querySelector("[data-state-label]");
  const artifact = card.querySelector("[data-artifact]");
  card.classList.remove("is-running", "is-complete", "is-returned");

  if (phase === "running") {
    card.classList.add("is-running");
    state.textContent = agentData.running;
    consoleStatus.textContent = "RUNNING";
    return;
  }

  card.classList.add("is-complete");
  state.textContent = agentData.complete;
  artifact.textContent = agentData.artifact;
  addEvent(agentData.event);
}

function clearTimers() {
  while (timers.length > 0) {
    window.clearTimeout(timers.pop());
  }
}

function setDecisionButtons(disabled) {
  decisionButtons.forEach(function (button) {
    button.disabled = disabled;
  });
}

function resetDemo() {
  clearTimers();
  flowReady = false;
  eventTick = 0;
  runButton.disabled = false;
  consoleStatus.textContent = "IDLE";
  eventLog.innerHTML = "<li><time>00:00</time><span>等待运行机制演示</span></li>";

  agentSequence.forEach(function (agentData, index) {
    const card = getAgent(agentData.key);
    card.classList.remove("is-running", "is-complete", "is-returned");
    card.querySelector("[data-state-label]").textContent = index === 0 ? "等待任务" : "等待上游";
    card.querySelector("[data-artifact]").textContent =
      index === 0 ? "研究简报 · 待生成" : index === 1 ? "初稿 · 等待研究" : "审校报告 · 等待初稿";
  });

  decisionPacket.classList.add("is-locked");
  decisionPacket.classList.remove("is-ready");
  packetStatus.textContent = "等待审校";
  packetLockMessage.hidden = false;
  setDecisionButtons(true);
  decisionResult.hidden = true;
  takeoverEditor.hidden = true;
  currentOwner.textContent = "ORCHESTRATOR";
  taskState.textContent = "等待协作流";
  humanDraft.value = "当前稿件已保留信源依据，仍需由作者补充个人视角与具体判断。";
}

function runFlow() {
  resetDemo();
  runButton.disabled = true;
  taskState.textContent = "Agent 协作中";
  eventLog.innerHTML = "";
  addEvent("Orchestrator 创建任务并获取执行 Lease");

  agentSequence.forEach(function (agentData, index) {
    const startTimer = window.setTimeout(function () {
      setAgent(agentData, "running");
    }, 250 + index * 850);
    timers.push(startTimer);

    const completeTimer = window.setTimeout(function () {
      setAgent(agentData, "complete");
      if (index === agentSequence.length - 1) {
        flowReady = true;
        consoleStatus.textContent = "HUMAN GATE";
        packetStatus.textContent = "等待人工决策";
        decisionPacket.classList.remove("is-locked");
        decisionPacket.classList.add("is-ready");
        packetLockMessage.hidden = true;
        setDecisionButtons(false);
        currentOwner.textContent = "HUMAN REVIEWER";
        taskState.textContent = "等待人工 Decision";
      }
    }, 780 + index * 850);
    timers.push(completeTimer);
  });
}

function recordDecision(type) {
  if (!flowReady) {
    return;
  }

  setDecisionButtons(true);
  decisionPacket.classList.remove("is-ready");
  takeoverEditor.hidden = true;
  decisionResult.hidden = false;

  if (type === "approve") {
    packetStatus.textContent = "已批准";
    currentOwner.textContent = "PUBLISH QUEUE";
    taskState.textContent = "待发布";
    resultTitle.textContent = "已批准，进入待发布";
    resultDetail.textContent = "当前版本被接受，Decision 与批准后的目标状态已记录。";
    addEvent("人工批准当前版本，任务进入待发布");
  }

  if (type === "return") {
    const writer = getAgent("writer");
    writer.classList.remove("is-complete");
    writer.classList.add("is-returned");
    writer.querySelector("[data-state-label]").textContent = "收到退回";
    writer.querySelector("[data-artifact]").textContent = "修订稿 v2 · 待生成";
    packetStatus.textContent = "已退回";
    currentOwner.textContent = "WRITING AGENT";
    taskState.textContent = "退回写作";
    resultTitle.textContent = "已退回写作 Agent";
    resultDetail.textContent = "退回原因与版本差异被保留，写作 Agent 将在同一任务中生成修订稿。";
    addEvent("人工退回写作 Agent，并保留退回原因与版本差异");
  }

  if (type === "takeover") {
    packetStatus.textContent = "人工接管";
    currentOwner.textContent = "MOSEY / HUMAN";
    taskState.textContent = "Agent 已暂停";
    resultTitle.textContent = "责任已转交给人";
    resultDetail.textContent = "Agent 停止继续执行，当前稿件已开放为本地人工版本。";
    takeoverEditor.hidden = false;
    addEvent("用户接管当前任务，Agent 执行暂停");
    humanDraft.focus();
  }
}

function saveHumanVersion() {
  const draft = humanDraft.value.trim();
  if (!draft) {
    humanDraft.focus();
    return;
  }
  packetStatus.textContent = "人工版本已保存";
  taskState.textContent = "人工修订完成";
  resultTitle.textContent = "人工版本已保存在本页";
  resultDetail.textContent = "这是本地演示状态，不会上传或写入线上系统。";
  addEvent("人工版本保存完成，等待后续确认");
  takeoverEditor.hidden = true;
}

function renderMemory(key) {
  const content = memoryContent[key];
  if (!content) {
    return;
  }

  document.querySelectorAll(".memory-tab").forEach(function (tab) {
    const isActive = tab.dataset.memory === key;
    tab.classList.toggle("is-active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
  });

  const panel = document.querySelector("#memory-panel");
  panel.setAttribute("aria-labelledby", content.tab);
  document.querySelector("#memory-code").textContent = content.code;
  document.querySelector("#memory-name").textContent = content.name;
  document.querySelector("#memory-purpose").textContent = content.purpose;
  document.querySelector("#memory-effect").textContent = content.effect;

  const fields = document.querySelector("#memory-fields");
  fields.innerHTML = "";
  content.fields.forEach(function (field) {
    const wrapper = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = field[0];
    detail.textContent = field[1];
    wrapper.append(term, detail);
    fields.append(wrapper);
  });
}

document.querySelectorAll(".memory-tab").forEach(function (tab) {
  tab.addEventListener("click", function () {
    renderMemory(tab.dataset.memory);
  });
});

decisionButtons.forEach(function (button) {
  button.addEventListener("click", function () {
    recordDecision(button.dataset.decision);
  });
});

runButton.addEventListener("click", runFlow);
resetButton.addEventListener("click", resetDemo);
runAnotherButton.addEventListener("click", function () {
  resetDemo();
  document.querySelector("#workflow").scrollIntoView({ behavior: "smooth", block: "start" });
});
saveTakeoverButton.addEventListener("click", saveHumanVersion);

resetDemo();
