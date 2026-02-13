/**
 * 小冰美化助手 - UXP 插件核心 (最终修复版)
 */
const { core, action } = require("photoshop");
const app = require("photoshop").app;
const constants = require("photoshop").constants;

console.warn("[JS] 插件初始化...");

const WS_URL = "ws://127.0.0.1:8765";

let ws = null;
let reconnectTimer = null;
let isConnected = false;

// 历史快照存储 (docId -> historyState)
const docSnapshots = new Map();

// --- 核心编辑操作 (Internal API, 不直接响应 WS) ---

/**
 * 内部文本更新函数
 */
async function internalUpdateText(layerId, text, parentChain) {
    const operation = async () => {
        // 选中图层
        await action.batchPlay([{
            _obj: "select",
            _target: [{ _ref: "layer", _id: layerId }]
        }], {});
        // 设置文本
        await action.batchPlay([{
            _obj: "set",
            _target: [{ _ref: "textLayer", _id: layerId }],
            to: { _obj: "textLayer", textKey: text }
        }], {});
    };

    if (parentChain && parentChain.length > 0) {
        await executeWithParentChain(parentChain, operation);
    } else {
        await operation();
    }
}

/**
 * 内部换图函数
 */
async function internalReplaceImage(layerId, imagePath, parentChain) {
    const fs = require("uxp").storage.localFileSystem;
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // 辅助：准备文件
    const prepareImage = async (rawPath) => {
        let cleanPath = rawPath.trim().replace(/\\/g, "/");
        if (!cleanPath.startsWith("file:")) {
            if (/^[a-zA-Z]:/.test(cleanPath)) cleanPath = "file:///" + cleanPath;
            else if (cleanPath.startsWith("/")) cleanPath = "file://" + cleanPath;
            else cleanPath = "file:///" + cleanPath;
        }
        try { cleanPath = new URL(cleanPath).href; } catch(e) { cleanPath = encodeURI(cleanPath); }

        const sourceEntry = await fs.getEntryWithUrl(cleanPath);
        const dataFolder = await fs.getDataFolder();
        const safeName = `rep_${Date.now()}.jpg`;
        return await sourceEntry.copyTo(dataFolder, { newName: safeName, overwrite: true });
    };

    const openedDocs = [];
    try {
        const fileEntry = await prepareImage(imagePath);
        await sleep(100);

        // 打开父级链
        for (const pid of parentChain) {
            const preId = app.activeDocument.id;
            await openSmartObjectByBatchPlay(pid);
            if (app.activeDocument.id === preId) throw new Error(`无法打开父级 ID: ${pid}`);
            openedDocs.push(app.activeDocument);
        }

        // 打开目标
        const beforeTargetId = app.activeDocument.id;
        await openSmartObjectByBatchPlay(layerId);
        if (app.activeDocument.id === beforeTargetId) throw new Error("无法打开目标智能对象");
        openedDocs.push(app.activeDocument);

        // 置入
        const token = fs.createSessionToken(fileEntry);
        await action.batchPlay([{
            _obj: "placeEvent",
            ID: 10,
            null: { _path: token, _kind: "local" },
            freeTransformCenterState: { _enum: "quadCenterState", _value: "QCSAverage" },
            offset: { _obj: "offset", horizontal: { _unit: "pixelsUnit", _value: 0 }, vertical: { _unit: "pixelsUnit", _value: 0 } }
        }], {});

        // 隐藏旧层
        const newLayerId = app.activeDocument.activeLayers[0].id;
        const layers = app.activeDocument.layers;
        for (let i = 0; i < layers.length; i++) {
            if (layers[i].id !== newLayerId && layers[i].visible) {
                try {
                    await action.batchPlay([{ _obj: "hide", null: [{ _ref: "layer", _id: layers[i].id }] }], {});
                } catch(e) {}
            }
        }
    } finally {
        for (let i = openedDocs.length - 1; i >= 0; i--) {
            await openedDocs[i].close(constants.SaveOptions.SAVECHANGES);
            await sleep(100);
        }
    }
}

/**
 * 内部滤镜函数
 */
async function internalApplyFilter(layerId, filterType, params, parentChain) {
    const operation = async () => {
        await action.batchPlay([{
            _obj: "select",
            _target: [{ _ref: "layer", _id: layerId }],
            makeVisible: false
        }], {});
        await applyFilter(filterType, params);
    };

    if (parentChain && parentChain.length > 0) {
        await executeWithParentChain(parentChain, operation);
    } else {
        await operation();
    }
}

// --- 辅助函数 ---
function getColorHex(c) { try { if(c&&c.rgb) return c.rgb.hexValue; return "000000"; } catch(e){ return "000000"; } }

async function showDialog(title, message, style='default') {
    const d = document.getElementById("customDialog");
    if(!d) return;
    document.getElementById("dialogTitle").textContent = title;
    document.getElementById("dialogMessage").textContent = message;
    document.getElementById("dialogIcon").className = `dialog-icon ${style}`;
    d.showModal();
    return new Promise(r => {
        const b = document.getElementById("dialogButton");
        const h = () => { d.close(); b.removeEventListener("click", h); r(); };
        b.addEventListener("click", h);
    });
}

// --- 智能对象操作 ---
async function openSmartObjectByBatchPlay(layerId) {
    try {
        await action.batchPlay([{
            _obj: "select",
            _target: [{ _ref: "layer", _id: layerId }]
        }], {});
    } catch (e) { 
        console.warn(`[JS] 选中智能对象失败 [ID: ${layerId}]: ${e.message}`); 
    }

    await action.batchPlay([{
        _obj: "placedLayerEditContents",
        _target: [{ _ref: "layer", _enum: "ordinal", _value: "targetEnum" }]
    }], {});
}

/**
 * 通用的智能对象链处理函数
 * 根据 parent_chain 打开/关闭智能对象，执行操作，然后恢复
 * 
 * @param {Array} parentChain - 父级智能对象链，从外到内，例如 [10, 20]
 * @param {Function} operation - 要在最深层文档中执行的操作函数
 * @returns {Promise} 操作结果
 */
async function executeWithParentChain(parentChain, operation) {
    const startDocId = app.activeDocument.id;
    const openedDocs = [];
    
    try {
        // 依次打开父级链条
        for (const pid of parentChain) {
            await openSmartObjectByBatchPlay(pid);
            
            // 检查是否真的打开了新文档
            if (app.activeDocument.id === startDocId || 
               (openedDocs.length > 0 && app.activeDocument.id === openedDocs[openedDocs.length-1].id)) {
                throw new Error(`无法打开智能对象 [ID: ${pid}]`);
            }
            openedDocs.push(app.activeDocument);
            console.warn(`[JS] 已打开智能对象 [ID: ${pid}]，文档: ${app.activeDocument.name}`);
        }
        
        // 执行操作
        const result = await operation();
        
        return result;
        
    } finally {
        // 倒序关闭并保存所有打开的文档
        for (let i = openedDocs.length - 1; i >= 0; i--) {
            console.warn(`[JS] 保存并关闭智能对象文档: ${openedDocs[i].name}`);
            await openedDocs[i].close(constants.SaveOptions.SAVECHANGES);
        }
    }
}

// --- 图层序列化 ---
async function serializeLayers(layers, depth=0, openSO=false) {
    if (!layers || depth > 5) return [];
    const res = [];
    const curDocId = app.activeDocument ? app.activeDocument.id : null;

    for (const layer of layers) {
        try {
            let kind = "PIXEL";
            let editable = null;
            let isSO = false;
            let isGroup = false;
            let kName = "UNKNOWN";
            try { if(layer.kind) kName = layer.kind.name || String(layer.kind); } catch(e){}

            // 1. 类型判定 (优先级：智能对象 > 组 > 文本)
            if (kName.toUpperCase().includes("SMART") || layer.smartObject != null) {
                kind = "SMARTOBJECT";
                isSO = true;
            } else if (layer.layers && layer.layers.length > 0) {
                kind = "GROUP";
                isGroup = true;
            } else if (layer.textItem) {
                kind = "TEXT";
                try {
                    editable = {
                        text: layer.textItem.contents,
                        font: layer.textItem.font || "Unknown",
                        size: layer.textItem.size ? layer.textItem.size.value : 0,
                        color: getColorHex(layer.textItem.color)
                    };
                } catch(e){}
            }

            const node = { id: layer.id, name: layer.name, visible: layer.visible, kind: kind, opacity: layer.opacity };
            if (editable) node.editable = editable;

            // 2. 递归
            if (isGroup) {
                node.children = await serializeLayers(layer.layers, depth+1, openSO);
            } else if (isSO && openSO) {
                try {
                    await openSmartObjectByBatchPlay(layer.id);
                    if (app.activeDocument && app.activeDocument.id !== curDocId) {
                        const inner = await serializeLayers(app.activeDocument.layers, depth+1, openSO);
                        if (inner.length > 0) {
                            node.children = inner;
                            node.isSmartObjectContent = true;
                        }
                        await app.activeDocument.close(constants.SaveOptions.DONOTSAVECHANGES);
                    }
                } catch(e) { 
                    node.error = "Open_Failed";
                    // 尝试恢复
                    if (app.activeDocument.id !== curDocId) await app.activeDocument.close(constants.SaveOptions.DONOTSAVECHANGES);
                }
            }
            res.push(node);
        } catch(e) { res.push({id:-1, name:"Error", error:e.message}); }
    }
    return res;
}

// --- WebSocket ---
function updateStatus(s, t) {
    const el = document.getElementById("statusText");
    const ind = document.getElementById("statusIndicator");
    if(el) el.textContent = t;
    if(ind) ind.className = `status-indicator ${s}`;
}

function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    
    try {
        ws = new WebSocket(WS_URL);
        ws.onopen = () => {
            isConnected = true;
            updateStatus("connected", "已连接");
        };
        ws.onclose = () => {
            isConnected = false;
            updateStatus("disconnected", "重连中...");
            reconnectTimer = setTimeout(() => connect(), 1200);
        };
        ws.onerror = (e) => console.warn("[JS] WS Error");

        ws.onmessage = async (evt) => {
            try {
                const msg = JSON.parse(evt.data);
                
                // 1.5 原子化执行策略包 (副本机制保护)
                if (msg.type === "execute_atomic") {
                    await core.executeAsModal(async () => {
                        console.warn(`[JS] 收到原子化执行请求，操作数: ${msg.operations?.length}, 渲染数: ${msg.renders?.length}`);
                        
                        // 进度通知辅助函数
                        const sendProgress = (step, current, total, details) => {
                            ws.send(JSON.stringify({
                                id: msg.id,
                                type: "atomic_progress",
                                step: step,
                                current: current,
                                total: total,
                                message: details
                            }));
                        };

                        let workCopy = null;
                        const renderedFiles = [];
                        try {
                            // A0. 自动切换焦点文档 (工作流支持)
                            if (msg.target_document) {
                                console.warn(`[JS] 正在寻找目标文档: ${msg.target_document}`);
                                const targetDoc = app.documents.find(d => d.name === msg.target_document || d.id === msg.target_document);
                                if (targetDoc) {
                                    app.activeDocument = targetDoc;
                                    console.warn(`[JS] 已激活目标文档: ${targetDoc.name}`);
                                } else {
                                    throw new Error(`未找到目标文档: ${msg.target_document}`);
                                }
                            }

                            // A. 创建主工作副本
                            sendProgress("init", 0, 1, "正在创建工作副本...");
                            workCopy = await app.activeDocument.duplicate(`${app.activeDocument.name}_WorkCopy`);
                            
                            // B. 执行编辑操作
                            const ops = msg.operations || [];
                            for (let i = 0; i < ops.length; i++) {
                                const op = ops[i];
                                sendProgress("operation", i + 1, ops.length, `正在执行: ${op.type}...`);
                                try {
                                    if (op.type === "update_text_layer") {
                                        await internalUpdateText(op.layer_id, op.text, op.parent_chain);
                                    } else if (op.type === "replace_image") {
                                        await internalReplaceImage(op.layer_id, op.image_path, op.parent_chain);
                                    } else if (op.type === "apply_filter") {
                                        await internalApplyFilter(op.layer_id, op.filter_type, op.params, op.parent_chain);
                                    }
                                } catch (e) {
                                    console.error(`[JS] 操作失败: ${e.message}`);
                                }
                            }

                            // C. 循环执行渲染
                            const renders = msg.renders || [];
                            for (let i = 0; i < renders.length; i++) {
                                const render = renders[i];
                                sendProgress("render", i + 1, renders.length, `正在渲染: ${render.file_name}...`);
                                let renderCopy = null;
                                try {
                                    app.activeDocument = workCopy;
                                    renderCopy = await workCopy.duplicate(`${render.file_name}_Render`);
                                    
                                    if (render.root_ids && render.root_ids.length > 0) {
                                        await setRootVisibility(renderCopy, render.root_ids);
                                    }

                                    if (render.tiling && render.width > 0 && render.height > 0) {
                                        await applySimpleTiling(renderCopy, render.width, render.height, render.resolution || 300);
                                    }

                                    if (render.filters && render.filters.length > 0) {
                                        if (renderCopy.layers.length > 1) {
                                            await action.batchPlay([
                                                { _obj: "selectAllLayers", _target: [{ _ref: "layer", _enum: "ordinal", _value: "targetEnum" }] },
                                                { _obj: "mergeVisible" }
                                            ], {});
                                        }
                                        app.activeDocument = renderCopy;
                                        for (const f of render.filters) {
                                            await applyFilter(f.type, f.params || {});
                                        }
                                    }

                                    const savedPath = await saveExportFile(renderCopy, render.folder, render.file_name, render.format);
                                    renderedFiles.push({
                                        name: render.file_name,
                                        path: savedPath || `${render.folder}/${render.file_name}.${render.format}`,
                                        status: "ok"
                                    });

                                } catch (e) {
                                    console.error(`[JS] 渲染失败: ${e.message}`);
                                    renderedFiles.push({ name: render.file_name, status: "error", error: e.message });
                                } finally {
                                    if (renderCopy) {
                                        try { await renderCopy.close(constants.SaveOptions.DONOTSAVECHANGES); } catch(e){}
                                    }
                                }
                            }

                            ws.send(JSON.stringify({ 
                                id: msg.id, 
                                type: "execute_atomic_response",
                                status: "success", 
                                rendered_files: renderedFiles 
                            }));

                        } catch (err) {
                            ws.send(JSON.stringify({ 
                                id: msg.id, 
                                type: "execute_atomic_response",
                                status: "error", 
                                error: err.message 
                            }));
                        } finally {
                            if (workCopy && !msg.debug) {
                                try { await workCopy.close(constants.SaveOptions.DONOTSAVECHANGES); } catch(e){}
                            }
                        }
                    }, { "commandName": "原子化策略执行" });
                }
// 17. 优化 PS 环境设置 (解决空间不足、停放失败等问题)
else if (msg.type === "fix_environment") {
    core.executeAsModal(async () => {
        try {
            await action.batchPlay([
                // 1. 关闭“以选项卡方式打开文档”
                {
                    _obj: "set",
                    _target: [{ _ref: "property", _property: "workspacePreferences" }],
                    to: {
                        _obj: "workspacePreferences",
                        openDocumentsAsTabs: false,
                        incrementalNaming: true
                    }
                },
                // 2. 优化性能：禁用一些可能干扰自动化的 UI 动画
                {
                    _obj: "set",
                    _target: [{ _ref: "property", _property: "interfacePrefs" }],
                    to: {
                        _obj: "interfacePrefs",
                        useWindowZoomAnchor: true
                    }
                }
            ], {});
            ws.send(JSON.stringify({ id: msg.id, status: "success", message: "PS 环境已优化：已关闭标签页模式" }));
        } catch (e) {
            ws.send(JSON.stringify({ id: msg.id, status: "error", error: e.message }));
        }
    }, { "commandName": "优化环境" });
}
// 1. 弹窗
else if (msg.type === "show_dialog") {
                    await showDialog(msg.title, msg.message, msg.style);
                }
                // 2. 获取图层（统一获取所有结构，包含智能对象内部）
                else if (msg.type === "get_layers") {
                    await core.executeAsModal(async () => {
                        console.warn(`[JS] 获取图层结构（统一获取所有结构，包含智能对象内部）`);
                        const tree = await serializeLayers(app.activeDocument.layers, 0, true);
                        console.warn(`[JS] 图层结构获取完成，根节点数量: ${tree.length}`);
                        ws.send(JSON.stringify({ id: msg.id, type: "layers_response", status: "success", data: tree }));
                    }, {"commandName": "获取图层"});
                }
                // 3. 更新单个文本图层（支持多层嵌套）
                else if (msg.type === "update_text_layer") {
                    await core.executeAsModal(async () => {
                        const parentChain = msg.parent_chain || [];
                        console.warn(`[JS] 更新文本图层 [ID: ${msg.layer_id}]，文本: "${msg.text}"，位置: ${parentChain.length > 0 ? `智能对象链 ${JSON.stringify(parentChain)}` : "主文档"}`);
                        
                        try {
                            if (parentChain.length > 0) {
                                // 在智能对象内部执行
                                await executeWithParentChain(parentChain, async () => {
                                    await action.batchPlay([{_obj:"select",_target:[{_ref:"layer",_id:msg.layer_id}]}],{});
                                    await action.batchPlay([{_obj:"set",_target:[{_ref:"textLayer",_id:msg.layer_id}],to:{_obj:"textLayer",textKey:msg.text}}],{});
                                });
                            } else {
                                // 在主文档执行
                                await action.batchPlay([{_obj:"set",_target:[{_ref:"textLayer",_id:msg.layer_id}],to:{_obj:"textLayer",textKey:msg.text}}],{});
                            }
                            ws.send(JSON.stringify({id:msg.id, type:"update_response", results:[{id:msg.layer_id, status:"ok"}]}));
                        } catch(e) {
                            console.warn(`[JS] 更新文本图层失败: ${e.message}`);
                            ws.send(JSON.stringify({id:msg.id, type:"update_response", results:[{id:msg.layer_id, status:"error", error:e.message}]}));
                        }
                    }, {"commandName": "更新文本图层"});
                }
                // 4. 批量更新文本图层（支持混合主文档和智能对象内部）
                else if (msg.type === "update_text_layers") {
                    await core.executeAsModal(async () => {
                        console.warn(`[JS] 批量更新文本图层，数量: ${msg.updates.length}`);
                        const res = [];
                        
                        // 按 parent_chain 分组
                        const groups = {};
                        for (const item of msg.updates) {
                            const chainKey = JSON.stringify(item.parent_chain || []);
                            if (!groups[chainKey]) groups[chainKey] = [];
                            groups[chainKey].push(item);
                        }
                        
                        // 按组执行
                        for (const [chainKey, updates] of Object.entries(groups)) {
                            const parentChain = JSON.parse(chainKey);
                            const location = parentChain.length > 0 ? `智能对象链 ${chainKey}` : "主文档";
                            console.warn(`[JS] 处理组: ${location}，数量: ${updates.length}`);
                            
                            try {
                                if (parentChain.length > 0) {
                                    // 在智能对象内部执行
                                    await executeWithParentChain(parentChain, async () => {
                                        for (const item of updates) {
                                            try {
                                                await action.batchPlay([{_obj:"select",_target:[{_ref:"layer",_id:item.layer_id}]}],{});
                                                await action.batchPlay([{_obj:"set",_target:[{_ref:"textLayer",_id:item.layer_id}],to:{_obj:"textLayer",textKey:item.text}}],{});
                                                res.push({id:item.layer_id, status:"ok"});
                                            } catch(e) {
                                                console.warn(`[JS] 更新图层失败 [ID: ${item.layer_id}]: ${e.message}`);
                                                res.push({id:item.layer_id, status:"error", error:e.message});
                                            }
                                        }
                                    });
                                } else {
                                    // 在主文档执行
                                    for (const item of updates) {
                                        try {
                                            await action.batchPlay([{_obj:"set",_target:[{_ref:"textLayer",_id:item.layer_id}],to:{_obj:"textLayer",textKey:item.text}}],{});
                                            res.push({id:item.layer_id, status:"ok"});
                                        } catch(e) {
                                            console.warn(`[JS] 更新图层失败 [ID: ${item.layer_id}]: ${e.message}`);
                                            res.push({id:item.layer_id, status:"error", error:e.message});
                                        }
                                    }
                                }
                            } catch(e) {
                                console.warn(`[JS] 处理组失败 ${location}: ${e.message}`);
                                for (const item of updates) {
                                    res.push({id:item.layer_id, status:"error", error:e.message});
                                }
                            }
                        }
                        
                        ws.send(JSON.stringify({id:msg.id, type:"update_response", results:res}));
                    }, {"commandName": "批量更新文本图层"});
                }
                // 5. 原生 BatchPlay（支持多层嵌套）
                else if (msg.type === "batchPlay") {
                    await core.executeAsModal(async () => {
                        const parentChain = msg.parent_chain || [];
                        const location = parentChain.length > 0 ? `智能对象链 ${JSON.stringify(parentChain)}` : "主文档";
                        console.warn(`[JS] 执行 BatchPlay，描述符数量: ${msg.descriptors.length}，位置: ${location}`);
                        
                        try {
                            if (parentChain.length > 0) {
                                // 在智能对象内部执行
                                await executeWithParentChain(parentChain, async () => {
                                    await action.batchPlay(msg.descriptors, msg.options||{});
                                });
                            } else {
                                // 在主文档执行
                                await action.batchPlay(msg.descriptors, msg.options||{});
                            }
                            ws.send(JSON.stringify({id:msg.id, status:"success"}));
                        } catch(e) {
                            console.warn(`[JS] BatchPlay 执行失败: ${e.message}`);
                            ws.send(JSON.stringify({id:msg.id, status:"error", error:e.message}));
                        }
                    }, {"commandName": "BatchPlay"});
                }
// 6. 替换图片 (Mockup 专用版：进入内部置入)
else if (msg.type === "replace_image") {
    const fs = require("uxp").storage.localFileSystem;
    const parentChain = msg.parent_chain || [];
    
    console.warn(`[JS] 收到换图请求 [ReqID: ${msg.id}, LayerID: ${msg.layer_id}]`);

    // 辅助：睡眠
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // 辅助：准备文件
    const prepareImage = async (rawPath) => {
        try {
            let cleanPath = rawPath.trim().replace(/\\/g, "/");
            if (!cleanPath.startsWith("file:")) {
                if (/^[a-zA-Z]:/.test(cleanPath)) cleanPath = "file:///" + cleanPath;
                else if (cleanPath.startsWith("/")) cleanPath = "file://" + cleanPath;
                else cleanPath = "file:///" + cleanPath;
            }
            try { cleanPath = new URL(cleanPath).href; } catch(e) { cleanPath = encodeURI(cleanPath); }

            const sourceEntry = await fs.getEntryWithUrl(cleanPath);
            const dataFolder = await fs.getDataFolder();
            const safeName = `rep_${Date.now()}.jpg`;
            return await sourceEntry.copyTo(dataFolder, { newName: safeName, overwrite: true });
        } catch (e) {
            throw new Error(`图片准备失败: ${e.message}`);
        }
    };

    await core.executeAsModal(async () => {
        const openedDocs = []; // 记录所有打开的文档，最后统一关

        try {
            // A. 准备文件
            const fileEntry = await prepareImage(msg.path);
            await sleep(200);

            // B. 打开父级链 (如果有)
            if (parentChain.length > 0) {
                for (const pid of parentChain) {
                    const preId = app.activeDocument.id;
                    await openSmartObjectByBatchPlay(pid);
                    if (app.activeDocument.id === preId) throw new Error(`无法打开父级 ID: ${pid}`);
                    openedDocs.push(app.activeDocument);
                    await sleep(200);
                }
            }

            // C. 【关键步骤】打开目标智能对象本身！
            // 我们不替换它，而是进入它内部
            console.warn(`[JS] 正在打开目标智能对象 [ID: ${msg.layer_id}]...`);
            const beforeTargetId = app.activeDocument.id;
            
            await openSmartObjectByBatchPlay(msg.layer_id);
            
            // 检查是否成功进入了目标内部
            if (app.activeDocument.id === beforeTargetId) {
                throw new Error("无法打开目标智能对象，请确认它是智能对象而非普通像素层");
            }
            // 将目标文档也加入栈，稍后保存关闭
            openedDocs.push(app.activeDocument);
            await sleep(300);

            // --- 此时我们已经在 Mockup 的内部文档里了 ---

            // D. 执行 "置入" (Place Embedded)
            console.warn("[JS] 在内部执行置入...");
            const token = fs.createSessionToken(fileEntry);
            
            await action.batchPlay([{
                _obj: "placeEvent",
                ID: 10, 
                null: { _path: token, _kind: "local" },
                freeTransformCenterState: { _enum: "quadCenterState", _value: "QCSAverage" },
                offset: { _obj: "offset", horizontal: { _unit: "pixelsUnit", _value: 0 }, vertical: { _unit: "pixelsUnit", _value: 0 } }
            }], {});
            
            await sleep(200);

            // E. 隐藏内部的其他图层 (只保留刚置入的这张)
            // 刚置入的图层默认是选中的
            const newLayerId = app.activeDocument.activeLayers[0].id;
            console.warn(`[JS] 新图层 ID: ${newLayerId}, 正在隐藏旧图层...`);

            // 获取当前文档所有图层
            const layers = app.activeDocument.layers;
            for (let i = 0; i < layers.length; i++) {
                // 如果不是刚置入的新图，就隐藏
                if (layers[i].id !== newLayerId && layers[i].visible) {
                    try {
                        // 使用 BatchPlay 隐藏，避免 DOM 遍历的性能问题
                        await action.batchPlay([{
                            _obj: "hide",
                            null: [{ _ref: "layer", _id: layers[i].id }]
                        }], {});
                    } catch(e) {}
                }
            }

            ws.send(JSON.stringify({ id: msg.id, status: "success" }));

        } catch (err) {
            console.warn(`[JS] 替换失败: ${err.message}`);
            ws.send(JSON.stringify({ id: msg.id, status: "error", error: err.message }));
        } finally {
            // F. 倒序关闭所有文档 (Target -> Parent -> GrandParent)
            // 关键：全部保存！
            console.warn(`[JS] 正在保存并关闭 ${openedDocs.length} 个文档...`);
            for (let i = openedDocs.length - 1; i >= 0; i--) {
                try {
                    console.warn(`[JS] 保存关闭: ${openedDocs[i].name}`);
                    await openedDocs[i].close(require("photoshop").constants.SaveOptions.SAVECHANGES);
                    await sleep(300); // 必须给保存留足时间，否则PS会崩
                } catch(e) {
                    console.warn(`[JS] 关闭文档失败: ${e.message}`);
                }
            }
        }
    }, {"commandName": "Mockup替换"});
}
// 7. 渲染输出 (单文档极简版)
else if (msg.type === "render_output") {
    console.warn(`[JS] 渲染请求 [ID:${msg.id}]`);
    
    await core.executeAsModal(async () => {
        // 定义临时文档变量
        let dupDoc = null;   // 筛选图层用的临时副本
        let finalDoc = null; // 最终保存用的文档 (可能是副本，也可能是平铺出的新文档)
        
        try {
            // 1. 复制原文档 (保护原稿)
            // 这一步确保我们不修改用户的源文件
            console.warn("[JS] 复制文档...");
            dupDoc = await app.activeDocument.duplicate(`${msg.file_name}_temp`);
            
            // 默认情况下，我们要保存的就是这个副本
            finalDoc = dupDoc;
            
            // 2. 筛选图层
            if (msg.root_ids && msg.root_ids.length > 0) {
                await setRootVisibility(dupDoc, msg.root_ids);
            }

            // 3. 如果需要平铺
            // 如果需要平铺
            if (msg.tiling && msg.width > 0 && msg.height > 0) {
                // 获取前端传来的分辨率，如果没有传则默认为 300
                // 假设前端字段叫 msg.resolution
                const targetRes = msg.resolution ? parseInt(msg.resolution) : 300;
                
                console.warn(`[JS] 执行新建文档平铺 (PPI: ${targetRes})...`);
                
                // 传入第4个参数
                finalDoc = await applySimpleTiling(dupDoc, msg.width, msg.height, targetRes);
            }

            // 4. 如果需要应用滤镜（在最终叠加好可见层后应用）
            if (msg.filters && msg.filters.length > 0) {
                console.warn(`[JS] 应用 ${msg.filters.length} 个全局滤镜...`);
                try {
                    // 确保操作的是 finalDoc
                    app.activeDocument = finalDoc;
                    
                    // 如果还没有合并图层（平铺时已经合并了），先合并所有可见图层
                    const layerCount = finalDoc.layers.length;
                    if (layerCount > 1) {
                        console.warn(`[JS] 检测到 ${layerCount} 个图层，先合并再应用滤镜...`);
                        await action.batchPlay([
                            { _obj: "selectAllLayers", _target: [{ _ref: "layer", _enum: "ordinal", _value: "targetEnum" }] },
                            { _obj: "mergeVisible" }
                        ], {});
                    }
                    
                    // 选中当前图层（强制选中最顶层，确保滤镜有操作对象）
                    await action.batchPlay([{
                        _obj: "select",
                        _target: [{ _ref: "layer", _enum: "ordinal", _value: "targetEnum" }]
                    }], {});
                    
                    // 再次确认我们就在 finalDoc 中
                    if (app.activeDocument.id !== finalDoc.id) {
                        await finalDoc.activate();
                    }
                    
                    // 按顺序应用所有滤镜
                    for (const filter of msg.filters) {
                        console.warn(`[JS] 应用滤镜: ${filter.type}`);
                        // 确保每一层滤镜都应用在当前激活图层上
                        await applyFilter(filter.type, filter.params || {});
                    }
                    
                    console.warn("[JS] 全局滤镜应用完成");
                } catch (e) {
                    console.warn(`[JS] 应用全局滤镜失败: ${e.message}`);
                }
            }

            // 5. 保存 (总是保存 finalDoc)
            console.warn("[JS] 保存...");
            await saveExportFile(finalDoc, msg.folder, msg.file_name, msg.format);
            
            ws.send(JSON.stringify({ id: msg.id, status: "success" }));

        } catch (err) {
            console.warn(`[JS] 渲染失败: ${err.message}`);
            ws.send(JSON.stringify({ id: msg.id, status: "error", error: err.message }));
        } finally {
            // 5. 任务结束，清理垃圾
            const SaveOptions = require("photoshop").constants.SaveOptions;

            // 情况A：如果开启了平铺，finalDoc 是那个新建的平铺文档，需要单独关闭
            //if (finalDoc && finalDoc !== dupDoc) {
            //    try {
            //        console.warn("[JS] 关闭平铺文档");
            //        await finalDoc.close(SaveOptions.DONOTSAVECHANGES);
            //    } catch(e) {}
            //}

            // 情况B：dupDoc 是复制出来的筛选图层用的副本，必须关闭
            if (dupDoc) {
                try {
                    console.warn("[JS] 关闭临时副本");
                    await dupDoc.close(SaveOptions.DONOTSAVECHANGES);
                } catch(e) {}
            }
            
            // 原文档 (app.activeDocument) 在此过程中全程未被引用关闭，非常安全
        }
    }, {"commandName": "渲染输出"});
}
// 8. 读取编辑策略
else if (msg.type === "read_strategy") {
    console.warn(`[JS] ===== 读取编辑策略请求 [ID:${msg.id}] =====`);

    await core.executeAsModal(async () => {
        try {
            console.warn(`[JS] 开始读取XMP元数据...`);

            // 读取XMP元数据
            const xmpResult = await action.batchPlay([
                {
                    "_obj": "get",
                    "_target": [
                        {
                            "_property": "XMPMetadataAsUTF8"
                        },
                        {
                            "_ref": "document",
                            "_enum": "ordinal",
                            "_value": "targetEnum"
                        }
                    ]
                }
            ], {});

            console.warn(`[JS] XMP读取结果:`, xmpResult);

            let strategy = null;

            if (xmpResult && xmpResult[0] && xmpResult[0].XMPMetadataAsUTF8) {
                const xmpData = xmpResult[0].XMPMetadataAsUTF8;
                console.warn(`[JS] 找到XMP数据，长度: ${xmpData.length}`);

                // 从XMP中提取编辑策略
                const strategyStart = '<photoshop:edit_strategy>';
                const strategyEnd = '</photoshop:edit_strategy>';

                const startIdx = xmpData.indexOf(strategyStart);
                const endIdx = xmpData.indexOf(strategyEnd, startIdx);

                console.warn(`[JS] 查找策略标签 - 开始位置: ${startIdx}, 结束位置: ${endIdx}`);

                if (startIdx !== -1 && endIdx !== -1) {
                    const strategyJson = xmpData.substring(startIdx + strategyStart.length, endIdx);
                    console.warn(`[JS] 提取的策略JSON长度: ${strategyJson.length}`);

                    // 反转义XML实体
                    const cleanJson = strategyJson
                        // 基本实体
                        .replace(/&gt;/g, '>')
                        .replace(/&lt;/g, '<')
                        .replace(/&amp;/g, '&')
                        .replace(/&quot;/g, '"')
                        .replace(/&apos;/g, "'")
                        // 数字实体（特别是换行）
                        .replace(/&#x0A;|&#xA;|&#10;/gi, '\n')
                        .replace(/&#x0D;|&#xD;|&#13;/gi, '\r')
                        .trim();

                    console.warn(`[JS] 清理后的JSON(前200字符):`, cleanJson.substring(0, 200) + '...');

                    // 为了更健壮：只截取第一个 "{" 到 最后一个 "}" 之间的内容再解析
                    let jsonToParse = cleanJson;
                    const firstBrace = cleanJson.indexOf("{");
                    const lastBrace = cleanJson.lastIndexOf("}");
                    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
                        jsonToParse = cleanJson.substring(firstBrace, lastBrace + 1);
                    }

                    console.warn(`[JS] 实际用于解析的JSON(前200字符):`, jsonToParse.substring(0, 200) + '...');

                    try {
                        strategy = JSON.parse(jsonToParse);
                        console.warn(`[JS] ✅ 读取策略成功，版本: ${strategy.version}, 操作数: ${strategy.operations?.length || 0}`);
                    } catch (parseErr) {
                        console.warn(`[JS] ❌ 策略JSON解析失败: ${parseErr.message}`);
                        ws.send(JSON.stringify({
                            id: msg.id,
                            type: "read_strategy_response",
                            error: `JSON解析失败: ${parseErr.message}`
                        }));
                        return;
                    }
                } else {
                    console.warn(`[JS] 未找到编辑策略标签`);
                }
            } else {
                console.warn(`[JS] 未找到XMP元数据`);
            }

            console.warn(`[JS] 返回策略: ${strategy ? '找到' : '未找到'}`);
            ws.send(JSON.stringify({
                id: msg.id,
                type: "read_strategy_response",
                strategy: strategy
            }));
            console.warn(`[JS] ===== 读取策略响应已发送 =====`);
        } catch (err) {
            console.warn(`[JS] ❌ 读取策略失败: ${err.message}`);
            console.warn(`[JS] 错误详情:`, err);
            ws.send(JSON.stringify({
                id: msg.id,
                type: "read_strategy_response",
                error: err.message
            }));
        }
    }, {"commandName": "读取编辑策略"});
}
// 9. 写入编辑策略
else if (msg.type === "write_strategy") {
    console.warn(`[JS] ===== 写入编辑策略请求 [ID:${msg.id}] =====`);
    console.warn(`[JS] 策略数据:`, msg.strategy);

    await core.executeAsModal(async () => {
        try {
            console.warn(`[JS] 开始读取现有XMP数据...`);

            // 首先读取现有的XMP数据
            const xmpResult = await action.batchPlay([
                {
                    "_obj": "get",
                    "_target": [
                        {
                            "_property": "XMPMetadataAsUTF8"
                        },
                        {
                            "_ref": "document",
                            "_enum": "ordinal",
                            "_value": "targetEnum"
                        }
                    ]
                }
            ], {});

            console.warn(`[JS] 现有XMP读取结果:`, xmpResult);

            let newXmp = "";

            if (msg.strategy) {
                // 有策略数据，构建包含策略的XMP
                console.warn(`[JS] 构建包含策略的XMP...`);
                const strategyJson = JSON.stringify(msg.strategy, null, 2);
                console.warn(`[JS] 策略JSON长度: ${strategyJson.length}`);

                // XMP模板
                const xmpTemplate = `<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.1-c000 79.9e4d4e6, 2022/06/30-20:37:39">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
         <photoshop:edit_strategy>{strategy_json}</photoshop:edit_strategy>
      </rdf:Description>
   </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>`;

                // 转义策略JSON中的特殊字符
                const escapedJson = strategyJson
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');

                newXmp = xmpTemplate.replace('{strategy_json}', escapedJson);
                console.warn(`[JS] 新XMP长度: ${newXmp.length}`);
                console.warn(`[JS] 写入策略，版本: ${msg.strategy.version}`);
            } else {
                // 没有策略数据，创建空的XMP（删除策略）
                console.warn(`[JS] 构建空XMP（删除策略）...`);
                newXmp = `<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.1-c000 79.9e4d4e6, 2022/06/30-20:37:39">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
         <photoshop:edit_strategy></photoshop:edit_strategy>
      </rdf:Description>
   </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>`;
                console.warn("[JS] 删除策略");
            }

            console.warn(`[JS] 开始写入XMP数据...`);

            // 写入XMP数据
            const writeResult = await action.batchPlay([
                {
                    "_obj": "set",
                    "_target": [
                        {
                            "_property": "XMPMetadataAsUTF8"
                        },
                        {
                            "_ref": "document",
                            "_enum": "ordinal",
                            "_value": "targetEnum"
                        }
                    ],
                    "to": {
                        "_obj": "document",
                        "XMPMetadataAsUTF8": newXmp
                    }
                }
            ], {});

            console.warn(`[JS] XMP写入结果:`, writeResult);
            console.warn("[JS] 编辑策略已设置，刷新文档状态...");

            // 尝试保存文档以应用更改
            let saveSuccessful = false;
            let saveErrorMessage = "";
            try {
                console.warn(`[JS] 检查文档保存状态...`);

                // 检查文档是否已保存过
                const docInfo = await action.batchPlay([
                    {
                        "_obj": "get",
                        "_target": [
                            {
                                "_property": "fileReference"
                            },
                            {
                                "_ref": "document",
                                "_enum": "ordinal",
                                "_value": "targetEnum"
                            }
                        ]
                    }
                ], {});

                console.warn(`[JS] 文档信息:`, docInfo);
                const hasFilePath = docInfo && docInfo[0] && docInfo[0].fileReference;

                if (hasFilePath) {
                    console.warn(`[JS] 文档已保存，开始执行保存...`);
                    // 执行保存
                    const saveResult = await action.batchPlay([
                        {
                            "_obj": "save",
                            "_target": [
                                {
                                    "_ref": "document",
                                    "_enum": "ordinal",
                                    "_value": "targetEnum"
                                }
                            ]
                        }
                    ], {});
                    console.warn(`[JS] 保存结果:`, saveResult);
                    console.warn("[JS] 文档保存成功，策略写入完成");
                    saveSuccessful = true;
                } else {
                    console.warn("[JS] 新建文档，跳过保存步骤（策略数据已设置）");
                }
            } catch (saveErr) {
                saveErrorMessage = saveErr.message || String(saveErr);
                console.warn(`[JS] 文档保存失败: ${saveErrorMessage}`);
                console.warn("[JS] 策略数据已设置，请手动保存文档以应用更改");
            }

            // 如果保存失败，给用户指导
            if (!saveSuccessful) {
                console.warn("[JS] 注意：策略数据已写入，请在Photoshop中手动保存文档 (Ctrl+S)");
            }

            // 根据保存结果给 Python 返回状态
            if (saveSuccessful) {
                console.warn(`[JS] ===== 写入策略成功 =====`);
                ws.send(JSON.stringify({
                    id: msg.id,
                    type: "write_strategy_response",
                    status: "success"
                }));
            } else {
                console.warn(`[JS] ===== 写入策略成功，但保存失败 =====`);
                ws.send(JSON.stringify({
                    id: msg.id,
                    type: "write_strategy_response",
                    status: "error",
                    error: saveErrorMessage || "策略已写入，但文档保存失败，请检查文件是否只读或被占用"
                }));
            }
        } catch (err) {
            console.warn(`[JS] ❌ 写入策略失败: ${err.message}`);
            console.warn(`[JS] 错误详情:`, err);
            ws.send(JSON.stringify({
                id: msg.id,
                type: "write_strategy_response",
                status: "error",
                error: err.message
            }));
        }
    }, {"commandName": "写入编辑策略"});
}
// 10. 应用通用滤镜
else if (msg.type === "apply_filter") {
    await core.executeAsModal(async () => {
        const parentChain = msg.parent_chain || [];
        const layerId = msg.layer_id;
        const filterType = msg.filter_type;
        const params = msg.params || {};

        console.warn(`[JS] 应用滤镜 [${filterType}] 到图层 [ID: ${layerId}]`);

        const operation = async () => {
            // 1. 选中指定图层 (加强版选中：确保 ID 正确且激活)
            await action.batchPlay([{
                _obj: "select",
                _target: [{ _ref: "layer", _id: layerId }],
                makeVisible: false
            }], {});

            // 2. 执行滤镜
            await applyFilter(filterType, params);
            
            // 3. 强制刷新图层状态 (防止 UI 不更新)
            await action.batchPlay([{ _obj: "select", _target: [{ _ref: "layer", _enum: "ordinal", _value: "targetEnum" }] }], {});
        };

        try {
            if (parentChain.length > 0) {
                await executeWithParentChain(parentChain, operation);
            } else {
                await operation();
            }
            ws.send(JSON.stringify({ id: msg.id, status: "success" }));
        } catch (e) {
            console.error(`[JS] 滤镜应用失败: ${e.message}`);
            ws.send(JSON.stringify({ id: msg.id, status: "error", error: e.message }));
        }
    }, { "commandName": "应用滤镜" });
}
// 11. 创建历史快照
else if (msg.type === "create_snapshot") {
    const doc = app.activeDocument;
    if (doc) {
        docSnapshots.set(doc.id, doc.activeHistoryState);
        console.warn(`[JS] 已为文档 [ID: ${doc.id}] 创建历史快照`);
        ws.send(JSON.stringify({ id: msg.id, status: "success" }));
    }
}
// 12. 恢复历史快照
else if (msg.type === "restore_snapshot") {
    const doc = app.activeDocument;
    if (doc && docSnapshots.has(doc.id)) {
        await core.executeAsModal(async () => {
            doc.activeHistoryState = docSnapshots.get(doc.id);
            docSnapshots.delete(doc.id);
            console.warn(`[JS] 已恢复文档 [ID: ${doc.id}] 的历史快照`);
            ws.send(JSON.stringify({ id: msg.id, status: "success" }));
        }, { "commandName": "恢复历史快照" });
    } else {
        ws.send(JSON.stringify({ id: msg.id, status: "error", error: "未找到快照" }));
    }
}
// 13. 获取所有打开的文档列表
else if (msg.type === "get_open_docs") {
    const docs = app.documents.map(d => ({
        id: d.id,
        name: d.name,
        path: d.path || "unsaved",
        active: d.id === app.activeDocument.id
    }));
    ws.send(JSON.stringify({ id: msg.id, type: "get_open_docs_response", status: "success", data: docs }));
}
// 14. 打开指定路径的文档
else if (msg.type === "open_doc") {
    const fs = require("uxp").storage.localFileSystem;
    let cleanPath = msg.path.trim().replace(/\\/g, "/");
    if (!cleanPath.startsWith("file:")) {
        if (/^[a-zA-Z]:/.test(cleanPath)) cleanPath = "file:///" + cleanPath;
        else if (cleanPath.startsWith("/")) cleanPath = "file://" + cleanPath;
        else cleanPath = "file:///" + cleanPath;
    }
    
    core.executeAsModal(async () => {
        try {
            const fileEntry = await fs.getEntryWithUrl(cleanPath);
            const newDoc = await app.open(fileEntry);
            ws.send(JSON.stringify({ id: msg.id, status: "success", doc_id: newDoc.id, name: newDoc.name }));
        } catch (e) {
            ws.send(JSON.stringify({ id: msg.id, status: "error", error: e.message }));
        }
    }, { "commandName": "打开文档" });
}
// 15. 关闭指定文档
else if (msg.type === "close_doc") {
    const targetId = msg.doc_id;
    const saveChanges = msg.save ? constants.SaveOptions.SAVECHANGES : constants.SaveOptions.DONOTSAVECHANGES;
    
    core.executeAsModal(async () => {
        try {
            const doc = app.documents.find(d => d.id === targetId || d.name === msg.name);
            if (doc) {
                await doc.close(saveChanges);
                ws.send(JSON.stringify({ id: msg.id, status: "success" }));
            } else {
                ws.send(JSON.stringify({ id: msg.id, status: "error", error: "未找到目标文档" }));
            }
        } catch (e) {
            ws.send(JSON.stringify({ id: msg.id, status: "error", error: e.message }));
        }
    }, { "commandName": "关闭文档" });
}
// 16. 激活指定文档 (修复版：加入 Modal 作用域)
else if (msg.type === "activate_doc") {
    core.executeAsModal(async () => {
        try {
            const doc = app.documents.find(d => d.id === msg.doc_id || d.name === msg.name);
            if (doc) {
                app.activeDocument = doc;
                ws.send(JSON.stringify({ id: msg.id, status: "success" }));
            } else {
                ws.send(JSON.stringify({ id: msg.id, status: "error", error: "未找到目标文档" }));
            }
        } catch (e) {
            ws.send(JSON.stringify({ id: msg.id, status: "error", error: e.message }));
        }
    }, { "commandName": "切换文档" });
}

            } catch(e) { console.warn("[JS] Msg Error:", e); }
        };
    } catch(e) {
        isConnected = false;
        updateStatus("disconnected", "重连中...");
        reconnectTimer = setTimeout(() => connect(), 1200);
    }
}
// --- 渲染专用辅助函数 ---

/**
 * 设置根节点可见性
 * 只显示 rootIds 中的图层，隐藏其他顶层图层
 */
async function setRootVisibility(doc, rootIds) {
    if (!rootIds || rootIds.length === 0) return; // 空列表代表全显，不做处理
    
    const layers = doc.layers;
    for (let i = 0; i < layers.length; i++) {
        const layer = layers[i];
        // 如果图层ID在白名单里，设为可见；否则隐藏
        // 注意：UXP DOM 修改 visible 属性是异步的，但在这里我们不需要 await 每一条
        // 建议使用 BatchPlay 批量处理，或者简单循环 (少量根节点循环没问题)
        try {
            const shouldShow = rootIds.includes(layer.id);
            if (layer.visible !== shouldShow) {
                layer.visible = shouldShow;
            }
        } catch (e) {
            console.warn(`[JS] 设置图层可见性失败 ID:${layer.id}`, e);
        }
    }
}
/**
 * 执行平铺逻辑 (核弹版：新文档 + 物理填充)
 * 既然图案是对的，我们就直接在一个新文档里用“油漆桶”把它填满。
 */
/**
 * 新建文档平铺法 (ContentLayer + Rasterize 强力版)
 * @param {Document} doc 源文档
 * @param {Number} targetWidth 目标宽度 (像素)
 * @param {Number} targetHeight 目标高度 (像素)
 * @param {Number} targetResolution [可选] 目标分辨率 (PPI), 默认 300
 */
/**
 * 智能平铺函数 (最终稳定版)
 * 策略：原地操作 + 隐式图案引用 + 像素填充
 */
async function applySimpleTiling(doc, targetWidth, targetHeight, targetResolution = 300) {
    const { action, core } = require("photoshop");
    const app = require("photoshop").app;
    
    // 同步执行助手
    const batchPlaySync = (cmds) => action.batchPlay(cmds, { synchronousExecution: true });

    // 确保操作的是当前文档
    await app.activeDocument;

    await core.executeAsModal(async () => {
        // 1. 准备素材
        // 合并所有可见图层
        await batchPlaySync([
            { _obj: "selectAllLayers", _target: [{ _ref: "layer", _enum: "ordinal", _value: "targetEnum" }] },
            { _obj: "mergeVisible" }
        ]);

        // 强制不透明度 100% (防止半透明素材导致效果不佳)
        try {
            await batchPlaySync([{
                _obj: "set",
                _target: [{ _ref: "layer", _enum: "ordinal", _value: "targetEnum" }],
                to: { _obj: "layer", opacity: { _unit: "percentUnit", _value: 100 } }
            }]);
        } catch(e) {}

        // 解锁背景 (防止裁切或变大画布时出错)
        try {
            await batchPlaySync([{ 
                _obj: "set", 
                _target: [{ _ref: "layer", _property: "background" }], 
                to: { _obj: "layer", name: "SourceLayer" } 
            }]);
        } catch (e) {}

        // 裁切透明区域 (Trim)
        try {
            await batchPlaySync([{ _obj: "trim", basedOn: { _enum: "trimBasedOn", _value: "transparency" }, top: true, bottom: true, left: true, right: true }]);
        } catch (e) {}

        // 2. 定义图案 (Define Pattern)
        await batchPlaySync([{ _obj: "selectAll" }]); // 全选
        
        await batchPlaySync([{
            _obj: "make",
            _target: [{ _ref: "pattern" }],
            name: "TempTilePattern", // 名字不重要，只是占位
            using: { _ref: "property", _property: "selection" }
        }]);

        await batchPlaySync([{ _obj: "set", _target: [{ _ref: "channel", _property: "selection" }], to: { _enum: "ordinal", _value: "none" } }]);

        // 3. 调整画布 (Canvas Size)
        await batchPlaySync([{
            _obj: "canvasSize",
            width: { _unit: "pixelsUnit", _value: targetWidth },
            height: { _unit: "pixelsUnit", _value: targetHeight },
            horizontal: { _enum: "horizontalLocation", _value: "center" },
            vertical: { _enum: "verticalLocation", _value: "center" }
        }]);

        // 4. 执行填充
        // 新建一个空白层
        await batchPlaySync([{ _obj: "make", _target: [{ _ref: "layer" }] }]);
        // 全选
        await batchPlaySync([{ _obj: "selectAll" }]);
        
        // 填充 (不指定 pattern 参数，默认使用刚定义的那个)
        await batchPlaySync([{
            _obj: "fill",
            using: { _enum: "fillContents", _value: "pattern" },
            opacity: { _unit: "percentUnit", _value: 100 },
            mode: { _enum: "blendMode", _value: "normal" }
        }]);

        await batchPlaySync([{ _obj: "set", _target: [{ _ref: "channel", _property: "selection" }], to: { _enum: "ordinal", _value: "none" } }]);

        // 5. 清理底层原图
        try {
            await batchPlaySync([{ _obj: "delete", _target: [{ _ref: "layer", _enum: "ordinal", _value: "backwardEnum" }] }]);
        } catch(e) {}

        // (可选) 如果您需要白底而不是透明底，请取消下面这行的注释
        // await batchPlaySync([{ _obj: "flattenImage" }]);

    }, { "commandName": "平铺处理" });

    return doc;
}
/**
 * 通用滤镜分发函数
 * @param {string} type - 滤镜类型
 * @param {object} params - 滤镜参数
 */
async function applyFilter(type, params) {
    if (type === "emboss") {
        // 使用更严谨的参数提取，防止 0 被判定为 false
        const angle = typeof params.angle !== 'undefined' ? params.angle : 135;
        const height = typeof params.height !== 'undefined' ? params.height : 2;
        const amount = typeof params.amount !== 'undefined' ? params.amount : 100;
        
        return await applyEmbossEffect(angle, height, amount);
    } else if (type === "gaussianBlur") {
        const radius = typeof params.radius !== 'undefined' ? params.radius : 1.0;
        return await applyGaussianBlurEffect(radius);
    } else {
        console.warn(`[JS] 未知的滤镜类型: ${type}`);
        return null;
    }
}

/**
 * 对当前选中图层应用高斯模糊滤镜
 * @param {number} radius - 半径 (0.1 到 1000 像素)
 */
async function applyGaussianBlurEffect(radius = 1.0) {
    const { action } = require("photoshop");
    
    const descriptor = {
        _obj: "gaussianBlur",
        radius: {
            _unit: "pixelsUnit",
            _value: radius
        }
    };

    return await action.batchPlay([descriptor], {});
}
/**
 * 对当前选中图层应用浮雕滤镜
 * @param {number} angle - 角度 (-180 到 180)
 * @param {number} height - 高度 (1 到 100)
 * @param {number} amount - 数量 (1% 到 500%)
 */
async function applyEmbossEffect(angle = 135, height = 2, amount = 100) {
    const { action } = require("photoshop");
    
    const descriptor = {
        _obj: "emboss",
        angle: {
            _unit: "angleUnit",
            _value: angle
        },
        height: height,
        amount: amount
    };

    return await action.batchPlay([descriptor], {});
}
/**
 * 保存文件核心逻辑
 */
async function saveExportFile(doc, folderPath, fileName, format) {
    const fs = require("uxp").storage.localFileSystem;
    const action = require("photoshop").action;
    
    // 统一转为小写处理
    const lowerFormat = format.toLowerCase();
    
    // 0. 白名单校验：先检查格式是否支持，不支持直接报错返回
    // 支持的格式：psd, jpg, png, webp, bmp, gif
    const supportedFormats = ["psd", "jpg", "jpeg", "png", "webp", "bmp", "gif"];
    if (!supportedFormats.includes(lowerFormat)) {
        throw new Error(`不支持的导出格式: .${format} (仅支持: psd, jpg, png, webp, bmp, gif)`);
    }

    // 1. 获取/创建输出目录
    let folderEntry;
    try {
        let cleanPath = folderPath.trim().replace(/\\/g, "/");
        if (!cleanPath.startsWith("file:")) cleanPath = "file:///" + cleanPath;
        try { cleanPath = new URL(cleanPath).href; } catch(e) { cleanPath = encodeURI(cleanPath); }
        folderEntry = await fs.getEntryWithUrl(cleanPath);
    } catch (e) {
        throw new Error(`输出目录不存在或无法访问: ${folderPath}`);
    }

    const fullFileName = `${fileName}.${lowerFormat}`;
    
    // 3. 准备 BatchPlay 保存 (JPG, PNG, WEBP, BMP, GIF, PSD)
    // 创建空文件并获取 Token
    const fileEntry = await folderEntry.createFile(fullFileName, { overwrite: true });
    const token = fs.createSessionToken(fileEntry);

    let exportCmd = {};
    const commonIn = { _path: token, _kind: "local" };

    if (lowerFormat === "jpg" || lowerFormat === "jpeg") {
        exportCmd = {
            _obj: "save",
            as: {
                _obj: "JPEG",
                extendedQuality: 10, // 0-12
                matte: { _enum: "matteColor", _value: "none" }
            },
            in: commonIn,
            copy: true
        };
    } else if (lowerFormat === "png") {
        exportCmd = {
            _obj: "save",
            as: {
                _obj: "PNGFormat",
                method: { _enum: "PNGMethod", _value: "quick" }, // 快速压缩
                PNGInterlaceType: { _enum: "PNGInterlaceType", _value: "PNGInterlaceNone" }
            },
            in: commonIn,
            copy: true
        };
    } else if (lowerFormat === "webp") {
        // WebP 适配 (Photoshop 23.2+ 原生支持)
        exportCmd = {
            _obj: "save",
            as: {
                _obj: "WebPFormat",
                // 压缩方式: compressionLossy (有损) / compressionLossless (无损)
                compression: { _enum: "WebPCompression", _value: "compressionLossy" },
                quality: 75, // 0-100
                includeXMP: false,
                includeEXIF: false,
                includeIPTC: false
            },
            in: commonIn,
            copy: true
        };
    } else if (lowerFormat === "bmp") {
        // BMP 适配 (兼容性好)
        exportCmd = {
            _obj: "save",
            as: {
                _obj: "BMPFormat",
                platform: { _enum: "BMPPlatform", _value: "Windows" }, // Windows 格式
                bitDepth: { _enum: "BMPBitDepth", _value: "thirtyTwo" }, // 32位 (带透明通道支持)
                alphaChannels: true
            },
            in: commonIn,
            copy: true
        };
    } else if (lowerFormat === "gif") {
        // GIF 适配 (注意：GIF渲染通常涉及颜色降维，此配置为标准导出)
        exportCmd = {
            _obj: "save",
            as: {
                _obj: "GIFFormat",
                colors: 256,
                dither: { _enum: "dither", _value: "diffusion" },
                ditherAmount: 75,
                transparency: true,
                matte: { _enum: "matteColor", _value: "none" }
            },
            in: commonIn,
            copy: true
        };
    } else if (lowerFormat === "psd") {
        // PSD 适配 (保留图层和最大兼容性)
        exportCmd = {
            _obj: "save",
            as: {
                _obj: "photoshop35Format",
                maximizeCompatibility: true
            },
            in: commonIn,
            copy: true
        };
    }

    // 执行保存
    // 注意：如果是 WebP 但 PS版本过低不支持，这里可能会报错，外层 try-catch 会捕获
    await action.batchPlay([exportCmd], {});
    
    return `${folderPath}/${fullFileName}`;
}
document.addEventListener("DOMContentLoaded", () => {
    updateStatus("disconnected", "连接中...");
    connect();
});