let currentSteps = {};
let currentStep = "";
let openTabs = [];
let activeTab = "";
let unsavedStepData = {};
let lastExecutionResult = {};

function saveCache() {
    localStorage.setItem("workflowEditorCache", JSON.stringify({
        workflow: document.getElementById("workflowSelector").value,
        openTabs,
        unsavedStepData
    }));
}

function loadCache() {
    try {
        const cache = JSON.parse(localStorage.getItem("workflowEditorCache") || "{}");
        if (cache.workflow) document.getElementById("workflowSelector").value = cache.workflow;
        openTabs = cache.openTabs || [];
        unsavedStepData = cache.unsavedStepData || {};
    } catch {
        openTabs = [];
        unsavedStepData = {};
    }
}

function renderSidebarSteps() {
    const ul = document.getElementById("sidebarStepsList");
    ul.innerHTML = "";
    Object.keys(currentSteps).sort().forEach(name => {
        const li = document.createElement("li");
        li.textContent = name;
        li.onclick = () => openStepTab(name);
        if (activeTab === name) li.classList.add("selected");
        ul.appendChild(li);
    });
}

function renderTabs() {
    const tabsDiv = document.getElementById("stepTabs");
    tabsDiv.innerHTML = "";
    openTabs.forEach(tab => {
        const tabDiv = document.createElement("div");
        tabDiv.className = "tab" + (activeTab === tab.name ? " active" : "");
        tabDiv.onclick = () => setActiveTab(tab.name);
        tabDiv.innerHTML = (tab.name === "__new__" ? "+ Novo Step" : tab.name) +
            (tab.dirty ? " *" : "") +
            `<button class="close-btn" onclick="event.stopPropagation();closeTab('${tab.name}')">&times;</button>`;
        tabsDiv.appendChild(tabDiv);
    });
}

function renderTabContents() {
    const contentsDiv = document.getElementById("stepTabContents");
    contentsDiv.innerHTML = "";
    openTabs.forEach(tab => {
        const contentDiv = document.createElement("div");
        contentDiv.className = "tab-content" + (activeTab === tab.name ? "" : " hidden");
        contentDiv.style.display = "none";
        if (tab.name === "__new__") {
            contentDiv.appendChild(renderStepForm("__new__", {}));
        } else {
            const stepData = unsavedStepData[tab.name] || currentSteps[tab.name] || {};
            contentDiv.appendChild(renderStepForm(tab.name, stepData));
        }
        contentsDiv.appendChild(contentDiv);
    });
    // Exibe apenas a última aba (step) como visível
    if (openTabs.length > 0) {
        contentsDiv.lastChild.style.display = "block";
        contentsDiv.lastChild.classList.remove("hidden");
    }
}

function setActiveTab(name) {
    // Move a aba selecionada para o final da lista
    const idx = openTabs.findIndex(t => t.name === name);
    if (idx !== -1) {
        const [tab] = openTabs.splice(idx, 1);
        openTabs.push(tab);
    }
    activeTab = name;
    renderTabs();
    renderTabContents();
    saveCache();
}

function openStepTab(name) {
    if (!openTabs.some(t => t.name === name)) {
        openTabs.push({ name, dirty: false });
    }
    setActiveTab(name);
    renderTabs();
    renderTabContents();
    saveCache();
}

function closeTab(name) {
    openTabs = openTabs.filter(t => t.name !== name);
    if (activeTab === name) {
        activeTab = openTabs.length ? openTabs[openTabs.length - 1].name : "";
    }
    renderTabs();
    renderTabContents();
    saveCache();
}

function markTabDirty(name, dirty) {
    const tab = openTabs.find(t => t.name === name);
    if (tab) tab.dirty = dirty;
    renderTabs();
    saveCache();
}

function renderStepForm(name, data) {
    const wrapper = document.createElement("div");
    const subTabs = ["Dados", "Validações", "Result"];
    let activeSubTab = "Dados";
    if (window._activeSubTabs && window._activeSubTabs[name]) {
        activeSubTab = window._activeSubTabs[name];
    }
    if (!window._activeSubTabs) window._activeSubTabs = {};

    // Botões no início
    const btnsDiv = document.createElement("div");
    btnsDiv.className = "step-form-btns";
    if (name !== "__new__") {
        btnsDiv.innerHTML = `
            <button class="btn btn-danger" onclick="deleteStepTab('${name}')">Delete</button>
            <button class="btn" onclick="saveStepTab('${name}')">Salvar</button>
            <button class="btn" onclick="executeStepTab('${name}')">Executar</button>
        `;
    } else {
        btnsDiv.innerHTML = `<button class="btn" onclick="saveStepTab('__new__')">Adicionar Step</button>`;
    }
    wrapper.appendChild(btnsDiv);

    // Resumo de execução logo após os botões
    const result = lastExecutionResult[name];
    const summaryDiv = document.createElement("div");
    summaryDiv.className = "result-summary";
    if (result) {
        summaryDiv.innerHTML = `
            <span>Status: <b>${result.summary.status}</b></span> |
            <span class="exec-timer">Tempo: ${result.summary.timeExecution} ms</span> |
            <span class="success">Sucesso: ${result.summary.successCount}</span> |
            <span class="fail">Falha: ${result.summary.failCount}</span>
        `;
    }
    wrapper.appendChild(summaryDiv);

    // Sub-abas
    const subTabsDiv = document.createElement("div");
    subTabsDiv.className = "sub-tabs";
    subTabs.forEach(sub => {
        const st = document.createElement("div");
        st.className = "sub-tab" + (activeSubTab === sub ? " active" : "");
        st.textContent = sub;
        st.onclick = () => {
            window._activeSubTabs[name] = sub;
            renderTabs();
            renderTabContents();
        };
        subTabsDiv.appendChild(st);
    });
    wrapper.appendChild(subTabsDiv);

    // Sub-tab contents
    const dadosDiv = document.createElement("div");
    dadosDiv.className = "sub-tab-content" + (activeSubTab === "Dados" ? " active" : "");
    dadosDiv.innerHTML = `
        <div class="form-section">
            <label for="stepName_${name}">Step Name</label>
            <input id="stepName_${name}" value="${name === "__new__" ? "" : name}" placeholder="Step Name" />
        </div>
        <div class="form-section">
            <label for="stepDepends_${name}">Depends On</label>
            <select id="stepDepends_${name}">
                <option value="">No dependency</option>
            </select>
        </div>
        <div class="form-section">
            <label for="stepMethod_${name}">Method</label>
            <select id="stepMethod_${name}">
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
                <option value="PATCH">PATCH</option>
            </select>
        </div>
        <div class="form-section">
            <label for="stepUrl_${name}">URL</label>
            <input id="stepUrl_${name}" value="${data.url || ""}" placeholder="URL" />
        </div>
        <div class="form-section">
            <label for="stepHeaders_${name}">Headers</label>
            <textarea id="stepHeaders_${name}" oninput="autoResize(this)" placeholder='{"Authorization": "Bearer {token}"}'>${data.headers ? JSON.stringify(data.headers, null, 2) : ""}</textarea>
        </div>
        <div class="form-section">
            <label for="stepBody_${name}">Body</label>
            <textarea id="stepBody_${name}" oninput="autoResize(this)" placeholder='{"key": "value"}'>${data.body ? JSON.stringify(data.body, null, 2) : ""}</textarea>
        </div>
    `;
    setTimeout(() => {
        document.getElementById(`stepMethod_${name}`).value = data.method || "GET";
        updateDependsOnOptionsForTab(name, data.dependsOn || "");
    }, 0);

    const valDiv = document.createElement("div");
    valDiv.className = "sub-tab-content" + (activeSubTab === "Validações" ? " active" : "");
    valDiv.innerHTML = `<div id="validations_${name}"></div>
        <button class="btn btn-secondary" type="button" onclick="addValidationTab('${name}')">+ Add Validation</button>
    `;
    setTimeout(() => {
        renderValidationsForTab(name, data.validations || []);
    }, 0);

    const resultDiv = document.createElement("div");
    resultDiv.className = "sub-tab-content" + (activeSubTab === "Result" ? " active" : "");
    if (result) {
        // Sub-abas para Result
        const resultSubTabs = ["Body", "Headers", "Validações", "Outros"];
        let activeResultSubTab = "Body";
        if (!window._activeResultSubTabs) window._activeResultSubTabs = {};
        if (window._activeResultSubTabs[name]) activeResultSubTab = window._activeResultSubTabs[name];

        // Renderização das sub-abas
        const resultSubTabsDiv = document.createElement("div");
        resultSubTabsDiv.className = "sub-tabs";
        resultSubTabs.forEach(sub => {
            const st = document.createElement("div");
            st.className = "sub-tab" + (activeResultSubTab === sub ? " active" : "");
            st.textContent = sub;
            st.onclick = () => {
                window._activeResultSubTabs[name] = sub;
                renderTabs();
                renderTabContents();
            };
            resultSubTabsDiv.appendChild(st);
        });
        resultDiv.appendChild(resultSubTabsDiv);

        // Conteúdo das sub-abas
        const resultSubTabContent = document.createElement("div");
        resultSubTabContent.className = "result-sub-tab-content";
        if (activeResultSubTab === "Body") {
            resultSubTabContent.innerHTML = `
                <h4>Body</h4>
                <pre>${JSON.stringify(result.result?.body ?? result.result, null, 2)}</pre>
            `;
        } else if (activeResultSubTab === "Headers") {
            resultSubTabContent.innerHTML = `
                <h4>Headers</h4>
                <pre>${JSON.stringify(result.result?.headers ?? {}, null, 2)}</pre>
            `;
        } else if (activeResultSubTab === "Validações") {
            resultSubTabContent.innerHTML = `
                <h3>Validações</h3>
                <div>
                    <b>Sucesso:</b>
                    <ul class="success-validation">${(result.result?.success_validations || []).map(v => `<li>${v}</li>`).join("")}</ul>
                    <b>Falha:</b>
                    <ul class="failed-validation">${(result.result?.failed_validations || []).map(v => `<li>${v}</li>`).join("")}</ul>
                </div>
            `;
        } else if (activeResultSubTab === "Outros") {
            // Mostra informações extras (exceto body, headers, validations)
            const { body, headers, success_validations, failed_validations, ...others } = result.result || {};
            resultSubTabContent.innerHTML = `
                <h4>Outras informações</h4>
                <pre>${JSON.stringify(others, null, 2)}</pre>
            `;
        }
        resultDiv.appendChild(resultSubTabContent);
    } else {
        resultDiv.innerHTML = `<div class="result-summary">Nenhuma execução realizada ainda.</div>`;
    }

    // Eventos de dirty
    setTimeout(() => {
        ["stepName", "stepMethod", "stepUrl", "stepHeaders", "stepBody", "stepDepends"].forEach(id => {
            const el = document.getElementById(`${id}_${name}`);
            if (el) el.oninput = () => onStepFormChange(name);
        });
        document.getElementById(`validations_${name}`).oninput = () => onStepFormChange(name);
    }, 0);

    wrapper.appendChild(dadosDiv);
    wrapper.appendChild(valDiv);
    wrapper.appendChild(resultDiv);
    return wrapper;
}

function onStepFormChange(name) {
    if (name === "__new__") return;
    unsavedStepData[name] = readStepFormTab(name);
    markTabDirty(name, true);
    saveCache();
}

function readStepFormTab(name) {
    const depends = (document.getElementById(`stepDepends_${name}`)?.value || "").trim();
    let headers = {};
    let body = {};
    try { headers = JSON.parse(document.getElementById(`stepHeaders_${name}`).value.trim() || "{}"); } catch { }
    try { body = JSON.parse(document.getElementById(`stepBody_${name}`).value.trim() || "{}"); } catch { }
    return {
        name: document.getElementById(`stepName_${name}`).value.trim(),
        method: document.getElementById(`stepMethod_${name}`).value.trim(),
        url: document.getElementById(`stepUrl_${name}`).value.trim(),
        headers,
        body,
        dependsOn: depends || "",
        validations: getValidationsTab(name)
    };
}

function updateDependsOnOptionsForTab(tabName, selected) {
    const select = document.getElementById(`stepDepends_${tabName}`);
    if (!select) return;
    select.innerHTML = '<option value="">No dependency</option>';
    Object.keys(currentSteps).forEach(name => {
        if (name !== tabName) {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            if (name === selected) opt.selected = true;
            select.appendChild(opt);
        }
    });
}

function renderValidationsForTab(tabName, validations) {
    const container = document.getElementById(`validations_${tabName}`);
    if (!container) return;
    container.innerHTML = "";
    (validations || []).forEach(v => addValidationFromDataTab(tabName, v));
}

function getValidationsTab(tabName) {
    const validations = [];
    document.querySelectorAll(`#validations_${tabName} .validation`).forEach(el => {
        const target = el.querySelector(".val-target").value.trim();
        const operator = el.querySelector(".val-operator").value.trim();
        const value = el.querySelector(".val-value").value.trim();
        const v = { target, operator };
        if (operator !== "notEmpty") v.value = isNaN(value) ? value : Number(value);
        validations.push(v);
    });
    return validations;
}

function addValidationTab(tabName) {
    addValidationFromDataTab(tabName, { target: "", operator: "equals", value: "" });
    onStepFormChange(tabName);
}

function addValidationFromDataTab(tabName, { target, operator, value }) {
    const div = document.createElement("div");
    div.className = "validation";
    div.innerHTML = `
        <input placeholder="Target (e.g. body.valor)" class="val-target" value="${target || ""}">
        <select class="val-operator">
          <option value="equals">equals</option>
          <option value="notEquals">notEquals</option>
          <option value="contains">contains</option>
          <option value="notEmpty">notEmpty</option>
          <option value="greaterThan">greaterThan</option>
          <option value="lessThan">lessThan</option>
          <option value="minLength">minLength</option>
          <option value="maxLength">maxLength</option>
          <option value="isType">isType</option>
          <option value="matchesRegex">matchesRegex</option>
        </select>
        <input placeholder="Value (if needed)" class="val-value" value="${value ?? ""}">
        <button type="button" onclick="this.parentElement.remove();onStepFormChange('${tabName}')">✖</button>
    `;
    div.querySelector(".val-operator").value = operator;
    document.getElementById(`validations_${tabName}`).appendChild(div);
}

async function saveStepTab(name) {
    const workflowName = document.getElementById("workflowSelector").value;
    if (name === "__new__") {
        const data = readStepFormTab("__new__");
        await fetch(`/workflow/${workflowName}/steps`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        await loadWorkflow(workflowName);
        openTabs = openTabs.filter(t => t.name !== "__new__");
        openStepTab(data.name);
    } else {
        const data = readStepFormTab(name);
        await fetch(`/workflow/${workflowName}/steps/${name}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        delete unsavedStepData[name];
        markTabDirty(name, false);
        await loadWorkflow(workflowName);
    }
    saveCache();
}

async function deleteStepTab(name) {
    if (!confirm("Delete step?")) return;
    const workflowName = document.getElementById("workflowSelector").value;
    await fetch(`/workflow/${workflowName}/steps/${name}`, { method: "DELETE" });
    await loadWorkflow(workflowName);
    closeTab(name);
    delete unsavedStepData[name];
    saveCache();
}

async function executeStepTab(name) {
    const workflowName = document.getElementById("workflowSelector").value;
    const env = document.getElementById("envSelector").value;
    const useProxy = document.getElementById("useProxyCheckbox").checked;
    const data = readStepFormTab(name);

    // Adiciona/atualiza o contador de tempo na tela
    let timerDiv = document.getElementById("execTimer_" + name);
    if (!timerDiv) {
        timerDiv = document.createElement("div");
        timerDiv.id = "execTimer_" + name;
        timerDiv.className = "exec-timer";
        // Insere logo após os botões do formulário
        const form = document.querySelector(`#stepTabContents .tab-content:not(.hidden) .step-form-btns`);
        if (form) form.parentNode.insertBefore(timerDiv, form.nextSibling);
    }
    timerDiv.textContent = "Executando... 0 ms";
    timerDiv.style.display = "block";

    let start = Date.now();
    let interval = setInterval(() => {
        timerDiv.textContent = `Executando... ${Date.now() - start} ms`;
    }, 50);

    const res = await fetch(`/workflow/${workflowName}/steps/${name}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ env, useProxy, ...data })
    });
    const elapsed = Date.now() - start;
    clearInterval(interval);

    const result = await res.json();
    lastExecutionResult[name] = {
        result,
        summary: {
            status: result.status || res.status,
            successCount: (result.success_validations || []).length,
            failCount: (result.failed_validations || []).length,
            timeExecution: elapsed || 0
        }
    };
    renderTabs();
    renderTabContents();
}


function isValidWorkflowName(name) {
    // Apenas letras, números, hífen e underline
    return /^[a-zA-Z0-9_-]+$/.test(name);
}


async function createNewWorkflow() {
    const workflowName = prompt("Enter new workflow name:")?.trim();
    if (!workflowName) return;
    if (!isValidWorkflowName(workflowName)) {
        alert("Workflow name must not contain spaces or special characters. Use only letters, numbers, hyphens, or underscores.");
        return;
    }
    if (workflowName) {
        await fetch(`/workflow/${workflowName}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ workflowName, global: {} })
        });
        await loadWorkflows();
        document.getElementById("workflowSelector").value = workflowName;
        document.querySelectorAll('textarea').forEach(t => autoResize(t));
        loadWorkflow(workflowName);
    }
}

async function loadWorkflow(name) {
    const res = await fetch(`/workflow/${name}`);
    const data = await res.json();
    document.getElementById("workflowName").value = data.workflowName;
    document.getElementById("globalInput").value = JSON.stringify(data.global, null, 2);
    document.getElementById("useProxyCheckbox").checked = !!data.useProxy;
    currentSteps = data.steps || {};
    renderSidebarSteps();
    renderTabs();
    renderTabContents();
    saveCache();
}

async function updateWorkflow() {
    const workflowName = document.getElementById("workflowSelector").value.trim();
    await fetch(`/workflow/${workflowName}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            workflowName: document.getElementById("workflowName").value.trim(),
            global: JSON.parse(document.getElementById("globalInput").value.trim()),
            useProxy: document.getElementById("useProxyCheckbox").checked
        })
    });
    document.querySelectorAll('textarea').forEach(t => autoResize(t));
    await loadWorkflow(workflowName);
}

function loadSelectedWorkflow() {
    const selectedWorkflow = document.getElementById("workflowSelector").value;
    if (selectedWorkflow) {
        loadWorkflow(selectedWorkflow);
    }
}

async function loadEnvironments() {
    const res = await fetch("/environments");
    const envs = await res.json();
    const envSelector = document.getElementById("envSelector");
    envSelector.innerHTML = "";
    envs.forEach(env => {
        const opt = document.createElement("option");
        opt.value = env.name;
        opt.textContent = env.name;
        envSelector.appendChild(opt);
    });
}

async function loadWorkflows() {
    const res = await fetch("/workflows");
    const workflows = await res.json();
    const selector = document.getElementById("workflowSelector");
    selector.innerHTML = '<option value="">-- Select Workflow --</option>';
    workflows.forEach(name => {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        selector.appendChild(option);
    });
}

function showGlobalConfig() {
    const globalConfigPanel = document.getElementById("globalConfigPanel");
    const stepFormPanel = document.getElementById("stepFormPanel");
    const toggleGlobalConfigButton = document.getElementById("showGlobalConfig");

    const isHidden = globalConfigPanel.style.display === "none";
    globalConfigPanel.style.display = isHidden ? "block" : "none";
    stepFormPanel.style.display = isHidden ? "none" : "block";
    toggleGlobalConfigButton.textContent = isHidden ? "👣" : "⚙️";

    document.querySelectorAll('textarea').forEach(t => autoResize(t));
}
function autoResize(textarea) {
    textarea.style.height = 'auto'; // Reseta a altura
    textarea.style.height = textarea.scrollHeight + 'px'; // Ajusta para o conteúdo
}

loadEnvironments();
loadWorkflows().then(() => {
    loadCache();
    if (document.getElementById("workflowSelector").value) {
        loadWorkflow(document.getElementById("workflowSelector").value);
    }
    renderTabs();
    renderTabContents();
});