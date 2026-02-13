"""
小冰美化助手 - 服务器核心 (Server.py)
版本：3.0 (统一接口 + 顺序执行)

功能：
1. WebSocket 服务：管理与 PS 插件的连接
2. 图层提取：统一获取所有结构（包含智能对象内部）
3. 统一接口：所有操作支持 parent_chain，支持任意层级嵌套
4. 顺序执行：支持操作队列的顺序执行
"""

import asyncio
import json
import re
import websockets
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime
import time
import inspect


def _get_timestamp() -> str:            
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(message: str):
    timestamp = _get_timestamp()
    print(f"[{timestamp}] [server] {message}")


class PSServer:
    """
    Photoshop 通信服务器
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.server: Optional[websockets.Serve] = None
        self.is_running = False
        self.callbacks: dict[int, Callable] = {}
        # 所有请求的默认超时时间（秒），用于防止无限等待前端响应
        self.default_timeout: float = 10.0
    
    async def start(self):
        """启动服务器（仅使用固定端口；若被占用则直接报错）"""
        if self.is_running:
            _log("警告: 服务器已经在运行")
            return
        
        start_port = int(self.port)
        _log(f"启动服务器 ws://{self.host}:{start_port}")
        
        async def handler(websocket):
            await self._handle_client(websocket)
        
        try:
            self.server = await websockets.serve(handler, self.host, start_port)
        except OSError as e:
            _log(f"错误: 端口 {start_port} 被占用或无权限，无法启动服务")
            _log(f"详细信息: {e}")
            raise

        self.is_running = True
        _log(f"服务器已启动 ws://{self.host}:{self.port}，等待插件连接")
    
    async def stop(self):
        """停止服务器"""
        if not self.is_running: return
        
        _log("正在停止服务器")
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # 清理所有待处理的回调
        if self.callbacks:
            _log(f"清理 {len(self.callbacks)} 个待处理的回调")
            self.callbacks.clear()
        
        self.is_running = False
        _log("服务器已停止")
    
    def is_connected(self) -> bool:
        return self.websocket is not None
    
    async def _handle_client(self, websocket):
        """处理客户端连接与消息分发"""
        _log("Photoshop 插件已连接")
        self.websocket = websocket
        
        try:
            async for message in websocket:
                # 记录收到的原始消息
                _log(f"收到消息: {message}")
                
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    _log(f"JSON 解析失败: {e}, 原始消息: {message}")
                    continue

                msg_type = data.get("type")
                msg_id = data.get("id")
                
                _log(f"解析消息 - 类型: {msg_type}, ID: {msg_id}")
                
                # --- 1. 图层数据响应 ---
                if msg_type == "layers_response":
                    _log(f"收到图层数据响应 [ID: {msg_id}]")
                    status = data.get("status")
                    if status == "success":
                        raw_tree = data.get("data", [])
                        _log(f"图层树获取成功，根节点数: {len(raw_tree)}")
                        await self._execute_callback(msg_id, raw_tree, None)
                    else:
                        error_msg = data.get("error", "Unknown Error")
                        _log(f"图层获取失败: {error_msg}")
                        await self._execute_callback(msg_id, None, error_msg)
                
                # --- 2. 更新响应 (文本/图片) ---
                elif msg_type == "update_response":
                    results = data.get("results", [])
                    success_cnt = sum(1 for r in results if r.get('status') == 'ok')
                    error_cnt = sum(1 for r in results if r.get('status') == 'error')
                    _log(f"更新响应 [ID: {msg_id}] - 成功: {success_cnt}, 失败: {error_cnt}, 总计: {len(results)}")
                    # 显示详细结果（不做长度限制）
                    for result in results:
                        status = result.get('status', 'unknown')
                        layer_id = result.get('id', 'unknown')
                        if status == 'ok':
                            _log(f"  图层 [ID: {layer_id}] 更新成功")
                        else:
                            error_info = result.get('msg', result.get('error', '未知错误'))
                            _log(f"  图层 [ID: {layer_id}] 更新失败: {error_info}")
                    await self._execute_callback(msg_id, results)
                
                # --- 3. BatchPlay 响应 ---
                elif msg_type == "batchPlay_response":
                    success = (data.get("status") == "success")
                    error_info = data.get("error")
                    _log(f"BatchPlay 响应 [ID: {msg_id}] - 状态: {'成功' if success else '失败'}")
                    if error_info:
                        _log(f"错误信息: {error_info}")
                    await self._execute_callback(msg_id, success, error_info)
                 # --- 4. 读取策略响应 ---
                elif msg_type == "read_strategy_response":
                    strategy = data.get("strategy")
                    error_info = data.get("error")
                    if error_info:
                        _log(f"读取策略失败 [ID: {msg_id}]: {error_info}")
                        await self._execute_callback(msg_id, None, error_info)
                    else:
                        if strategy:
                            _log(f"读取策略成功 [ID: {msg_id}] - 版本: {strategy.get('version', '未知')}")
                            await self._execute_callback(msg_id, strategy, None)
                        else:
                            _log(f"读取策略成功 [ID: {msg_id}] - 未找到策略")
                            await self._execute_callback(msg_id, None, None)

                # --- 5. 写入策略响应 ---
                elif msg_type == "write_strategy_response":
                    success = (data.get("status") == "success")
                    error_info = data.get("error")
                    if success:
                        _log(f"写入策略成功 [ID: {msg_id}]")
                        await self._execute_callback(msg_id, True, None)
                    else:
                        error_msg = error_info or "未知错误"
                        _log(f"写入策略失败 [ID: {msg_id}]: {error_msg}")
                        await self._execute_callback(msg_id, False, error_msg)
                
                # --- 6. 渲染输出响应 ---
                elif msg_type == "render_output_response":
                    success = (data.get("status") == "success")
                    error_info = data.get("error")
                    output_path = data.get("output_path")
                    if success:
                        _log(f"渲染输出成功 [ID: {msg_id}]")
                        if output_path:
                            _log(f"  输出文件: {output_path}")
                        await self._execute_callback(msg_id, output_path, None)
                    else:
                        error_msg = error_info or "未知错误"
                        _log(f"渲染输出失败 [ID: {msg_id}]: {error_msg}")
                        await self._execute_callback(msg_id, None, error_msg)
                
                # --- 7. 原子化进度通知 ---
                elif msg_type == "atomic_progress":
                    step = data.get("step")
                    current = data.get("current")
                    total = data.get("total")
                    message = data.get("message")
                    _log(f"原子任务进度 [ID: {msg_id}] - [{step}] {current}/{total}: {message}")
                
                # --- 8. 原子化最终结果响应 ---
                elif msg_type == "execute_atomic_response":
                    success = (data.get("status") == "success")
                    _log(f"原子化任务完成 [ID: {msg_id}] - 状态: {'成功' if success else '失败'}")
                    await self._execute_callback(msg_id, data, data.get("error"))

                # --- 9. 多文档列表响应 ---
                elif msg_type == "get_open_docs_response":
                    docs = data.get("data", [])
                    _log(f"获取文档列表成功 [ID: {msg_id}] - 数量: {len(docs)}")
                    await self._execute_callback(msg_id, docs, None)

                # --- 10. 通用状态响应 ---
                elif msg_id and "status" in data:
                    success = (data.get("status") == "success")
                    error_info = data.get("error")
                    await self._execute_callback(msg_id, success, error_info)
                
                else:
                    _log(f"收到其他消息类型: {msg_type}, 完整数据: {json.dumps(data, ensure_ascii=False)}")
                                                                           
        except websockets.exceptions.ConnectionClosed:
            _log("连接断开")
        finally:
            self.websocket = None
            _log("等待下次连接")

    async def _execute_callback(self, req_id, *args):
        """安全执行回调函数"""
        if req_id in self.callbacks:
            callback = self.callbacks.pop(req_id)
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
            except Exception as e:
                _log(f"回调执行异常 [ID: {req_id}]: {e}")

    # ============================================
    # 基础功能方法 (Low-level API)
    # ============================================
    
    async def send_dialog(self, title: str, message: str, style: str = "default"):
        """发送弹窗"""
        if not self.websocket: return
        await self.websocket.send(json.dumps({
            "type": "show_dialog", "title": title, "message": message, "style": style
        }, ensure_ascii=False))
    
    async def request_layers(self, callback=None) -> int:
        """
        获取图层结构（统一获取所有结构，包含智能对象内部）
        """
        return await self._send_payload({
            "type": "get_layers",
            "include_smart_object_contents": True  # 统一获取所有结构
        }, callback)

    async def update_text_layer(self, layer_id: int, text: str, parent_chain: list = [], callback=None) -> int:
        """
        修改单个文本图层（支持任意层级嵌套）
        
        参数:
            layer_id: 目标文本图层ID
            text: 新的文本内容
            parent_chain: 父级智能对象链，从外到内，例如 [10, 20] 表示目标在智能对象20内，而20又在智能对象10内
        """
        return await self._send_payload({
            "type": "update_text_layer",
            "layer_id": layer_id,
            "text": text,
            "parent_chain": parent_chain
        }, callback)

    async def update_text_layers(self, updates: list, callback=None) -> int:
        """
        批量修改文本图层（支持混合主文档和智能对象内部）
        
        参数:
            updates: 更新列表，每个项包含 {"layer_id": int, "text": str, "parent_chain": list}
        """
        return await self._send_payload({
            "type": "update_text_layers",
            "updates": updates
        }, callback)
    
    async def batch_play(self, descriptors: list, parent_chain: list = [], callback=None) -> int:
        """
        执行原生 BatchPlay（支持在智能对象内部执行）
        
        参数:
            descriptors: BatchPlay 描述符列表
            parent_chain: 父级智能对象链，从外到内，空列表表示在主文档执行
        """
        return await self._send_payload({
            "type": "batchPlay",
            "descriptors": descriptors,
            "parent_chain": parent_chain
        }, callback)

    async def _send_payload(self, payload: dict, callback=None) -> int:

        if not self.websocket:
            _log("错误: 未连接，无法发送消息")
            if callback: 
                # 简单处理未连接回调
                try:
                    if asyncio.iscoroutinefunction(callback): await callback(None, "Not Connected")
                    else: callback(None, "Not Connected")
                except Exception as e:
                    _log(f"回调执行异常: {e}")
            return 0
        
        req_id = int(time.time() * 1000)
        if callback: 
            self.callbacks[req_id] = callback
            _log(f"已注册回调函数 [ID: {req_id}]")
        
        payload["id"] = req_id
        payload_str = json.dumps(payload, ensure_ascii=False)
        
        # 记录发送的消息
        msg_type = payload.get("type", "unknown")
        _log(f"发送消息 [ID: {req_id}, 类型: {msg_type}]")

        # 为该请求启动一个超时检测任务，避免永远等待前端响应
        if callback and self.default_timeout and self.default_timeout > 0:
            async def _timeout_watch(req_id=req_id, cb=callback, msg_type=msg_type):
                try:
                    await asyncio.sleep(self.default_timeout)
                    if req_id in self.callbacks:
                        # 超时仍未收到前端响应，触发超时回调
                        self.callbacks.pop(req_id, None)
                        _log(f"请求超时 [ID: {req_id}, 类型: {msg_type}]，默认超时: {self.default_timeout}s")
                        try:
                            sig = inspect.signature(cb)
                            param_count = len(sig.parameters)
                            # 0 个参数：仅调用，不传错误信息
                            if param_count == 0:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb()
                                else:
                                    cb()
                            # 1 个参数：传递错误字符串
                            elif param_count == 1:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb("Timeout")
                                else:
                                    cb("Timeout")
                            # >=2 个参数：按照 (result, error) 约定，传递 (None, "Timeout")
                            else:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb(None, "Timeout")
                                else:
                                    cb(None, "Timeout")
                        except Exception as e:
                            _log(f"超时回调执行异常 [ID: {req_id}]: {e}")
                except Exception as e:
                    _log(f"超时监控任务异常 [ID: {req_id}]: {e}")

            asyncio.create_task(_timeout_watch())
        
        # 根据消息类型显示详细信息（不做长度限制）
        if msg_type == "get_layers":
            _log(f"  获取图层结构（统一获取所有结构，包含智能对象内部）")
        elif msg_type == "update_text_layer":
            layer_id = payload.get("layer_id")
            text = payload.get("text", "")
            parent_chain = payload.get("parent_chain", [])
            location = "主文档" if not parent_chain else f"智能对象链 {parent_chain}"
            _log(f"  更新文本图层 [ID: {layer_id}] -> '{text}' (位置: {location})")
        elif msg_type == "update_text_layers":
            updates = payload.get("updates", [])
            _log(f"  批量更新文本图层，数量: {len(updates)}")
            for update in updates:
                layer_id = update.get("layer_id")
                text = update.get("text", "")
                parent_chain = update.get("parent_chain", [])
                location = "主文档" if not parent_chain else f"智能对象链 {parent_chain}"
                _log(f"    图层 [ID: {layer_id}] -> '{text}' (位置: {location})")
        elif msg_type == "batchPlay":
            descriptors = payload.get("descriptors", [])
            parent_chain = payload.get("parent_chain", [])
            location = "主文档" if not parent_chain else f"智能对象链 {parent_chain}"
            _log(f"  执行 BatchPlay，描述符数量: {len(descriptors)} (位置: {location})")
        elif msg_type == "replace_image":
            layer_id = payload.get("layer_id")
            path = payload.get("path", "")
            parent_chain = payload.get("parent_chain", [])
            location = "主文档" if not parent_chain else f"智能对象链 {parent_chain}"
            _log(f"  替换图层图片 [ID: {layer_id}] -> '{path}' (位置: {location})")
        elif msg_type == "show_dialog":
            title = payload.get("title", "")
            message = payload.get("message", "")
            style = payload.get("style", "default")
            _log(f"  显示对话框: [{style}] {title} - {message}")
        else:
            # 对于其他类型，显示完整 payload（不做长度限制）
            _log(f"  完整消息: {payload_str}")
        
        await self.websocket.send(payload_str)
        _log(f"消息已发送 [ID: {req_id}]")
        return req_id

    async def replace_layer_image(self, layer_id: int, image_path: str, parent_chain: list = [], callback=None) -> int:
        """
        替换图层图片
        
        参数:
            layer_id: 目标图层 ID
            image_path: 图片路径
            parent_chain: 父级智能对象链，从外到内，例如 [10, 20] 表示目标在智能对象20内，而20又在智能对象10内
        """
        clean_path = image_path.replace("\\", "/")
        return await self._send_payload({
            "type": "replace_image",
            "layer_id": layer_id,
            "path": clean_path,
            "parent_chain": parent_chain
        }, callback)

    async def render_output(self, 
                            output_folder: str, 
                            file_name: str, 
                            format: str = "jpg", 
                            root_ids: list = None,
                            tiling: bool = False,
                            output_width: int = 0,
                            output_height: int = 0,
                            filters: list = None,
                            callback=None) -> int:
        """
        渲染输出图像
        
        参数:
            output_folder: 输出文件夹路径 (如 "D:/Output")
            file_name: 文件名 (不含后缀, 如 "design_v1")
            format: 格式 ("jpg", "jpeg", "png", "gif", "psd")
            root_ids: 需要渲染的根节点ID列表 (None 或 [] 表示渲染全部)
            tiling: 是否平铺
            output_width: 输出画布宽度 (仅当 tiling=True 时生效)
            output_height: 输出画布高度 (仅当 tiling=True 时生效)
            filters: 滤镜配置列表，例如 [{"type": "emboss", "params": {...}}]
        """
        if not self.websocket:  
            _log("错误: 未连接，无法发送渲染请求")
            if callback: 
                try:
                    if asyncio.iscoroutinefunction(callback): 
                        await callback(None, "Not Connected")
                    else: 
                        callback(None, "Not Connected")
                except Exception as e:
                    _log(f"回调执行异常: {e}")
            return 0
        
        # 路径标准化
        clean_folder = output_folder.replace("\\", "/")
        format = format.lower().replace("jpeg", "jpg")
        
        req_id = int(time.time() * 1000)
        if callback: self.callbacks[req_id] = callback
        
        # 处理root_ids：None或空列表表示渲染全部，非空列表表示只渲染指定的图层
        if root_ids is None:
            root_ids_to_send = []  # 空列表表示渲染全部
        else:
            root_ids_to_send = root_ids  # 非空列表表示只渲染指定的图层
        
        # 处理滤镜：统一转换为列表格式
        filters_to_send = filters if isinstance(filters, list) else []
        
        payload = {
            "id": req_id,
            "type": "render_output",
            "folder": clean_folder,
            "file_name": file_name,
            "format": format,
            "root_ids": root_ids_to_send,
            "tiling": tiling,
            "width": output_width,
            "height": output_height,
            "filters": filters_to_send
        }
        
        await self.websocket.send(json.dumps(payload, ensure_ascii=False))
        _log(f"发送渲染指令 [ID:{req_id}] -> {file_name}.{format}, root_ids: {root_ids_to_send}, filters: {len(filters_to_send)}")
        return req_id

    # ============================================
    # 高级工具方法 (High-level API)
    # ============================================

    def extract_editable_layers(self, layer_tree: list) -> list:
        """
        [工具] 递归提取所有可编辑文本层
        只提取 kind == "TEXT" 且包含 editable 字段的图层
        
        返回列表项示例:
        {
            "id": 44, 
            "name": "标题", 
            "info": {...}, 
            "parent_so_id": 9  # 最后一个智能对象ID（兼容旧代码），None代表在主文档
            "parent_chain": [10, 9]  # 完整的父级智能对象链（从外到内）
        }
        """
        text_layers = []

        # parents 参数现在是一个列表，记录路径 [id1, id2]
        def _traverse(nodes, parents=[]):
            for node in nodes:
                # 记录当前完整路径
                current_chain = list(parents) # 复制列表
                
                # 1. 只提取文本层（TEXT 类型且包含 editable 字段）
                # 注意：不提取 SMARTOBJECT，智能对象本身不是文本层
                if node.get("kind") == "TEXT" and "editable" in node:
                    item = {
                        "id": node["id"],
                        "name": node["name"],
                        "info": node.get("editable"),
                        "parent_so_id": current_chain[-1] if current_chain else None,  # 最后一个ID作为parent_so_id（兼容旧代码）
                        "parent_chain": current_chain  # 完整的父级链
                    }
                    text_layers.append(item)
                
                # 2. 如果是智能对象，把自己的 ID 加入路径，往下传（但不提取智能对象本身）
                if node.get("kind") == "SMARTOBJECT":
                    new_parents = current_chain + [node["id"]]
                    if "children" in node:
                        _traverse(node["children"], new_parents)
                
                # 3. 普通组，路径不变，继续往下传
                elif node.get("kind") == "GROUP" and "children" in node:
                    _traverse(node["children"], current_chain)

        _traverse(layer_tree)
        return text_layers

    def _apply_regex_processing(self, text: str, regex_steps: list) -> str:
        """应用多步正则预处理 (期望文本是单行的)"""
        if not regex_steps:
            return text
            
        # 强制单行处理，确保符合预期
        processed_text = text.replace('\n', ' ').replace('\r', '')
        
        for step in regex_steps:
            find_pattern = step.get("find")
            replace_str = step.get("replace", "")
            if find_pattern:
                try:
                    # 将 JS 风格的 $1, $2 转换为 Python 风格的 \1, \2
                    py_replace = re.sub(r'\$(\d+)', r'\\\1', replace_str)
                    processed_text = re.sub(find_pattern, py_replace, processed_text)
                except Exception as e:
                    _log(f"正则处理失败 [{step.get('name', '未命名')}]: {e}")
                    
        return processed_text

    async def execute_operations_sequentially(self, operations: List[Dict[str, Any]]):
        """
        顺序执行操作队列
        
        参数:
            operations: 操作列表，每个操作包含:
                - "type": 操作类型 ("update_text_layer", "replace_image", "batch_play" 等)
                - "layer_id": 图层ID（如适用）
                - "parent_chain": 父级智能对象链（如适用）
                - 其他操作特定参数
        """
        # 定义操作优先级
        priority_map = {
            "update_text_layer": 10,
            "replace_image": 20,
            "apply_filter": 30,
            "batch_play": 40
        }
        
        # 按优先级排序
        sorted_ops = sorted(operations, key=lambda x: priority_map.get(x.get("type", ""), 99))
        
        _log("=" * 60)
        _log(f"开始顺序执行操作队列，共 {len(sorted_ops)} 个操作")
        
        if not sorted_ops:
            _log("操作队列为空")
            return
        
        for idx, op in enumerate(sorted_ops, 1):
            op_type = op.get("type")
            _log(f"[{idx}/{len(sorted_ops)}] 执行操作: {op_type}")
            
            try:
                if op_type == "update_text_layer":
                    text = op.get("text", "")
                    # 如果有正则步骤，进行预处理
                    if "regex_steps" in op:
                        text = self._apply_regex_processing(text, op["regex_steps"])
                        
                    await self.update_text_layer(
                        layer_id=op["layer_id"],
                        text=text,
                        parent_chain=op.get("parent_chain", [])
                    )
                elif op_type == "replace_image":
                    await self.replace_layer_image(
                        layer_id=op["layer_id"],
                        image_path=op["image_path"],
                        parent_chain=op.get("parent_chain", [])
                    )
                elif op_type == "batch_play":
                    await self.batch_play(
                        descriptors=op["descriptors"],
                        parent_chain=op.get("parent_chain", [])
                    )
                elif op_type == "apply_filter":
                    await self._apply_filter(
                        layer_id=op["layer_id"],
                        filter_type=op.get("filter_type"),
                        params=op.get("params", {}),
                        parent_chain=op.get("parent_chain", [])
                    )
                else:
                    _log(f"  未知操作类型: {op_type}")
                    continue
                
                _log(f"  操作 [{idx}] 已提交")
                
            except Exception as e:
                _log(f"  操作 [{idx}] 执行失败: {e}")
        
        _log("=" * 60)
        _log("所有操作已提交完成")

    async def _apply_filter(self, layer_id: int, filter_type: str, params: dict = {}, parent_chain: list = [], callback=None) -> int:
        """
        应用滤镜到指定图层
        """
        return await self._send_payload({
            "type": "apply_filter",
            "layer_id": layer_id,
            "filter_type": filter_type,
            "params": params,
            "parent_chain": parent_chain
        }, callback)

    async def create_snapshot(self, callback=None) -> int:
        """创建当前文档的历史快照"""
        return await self._send_payload({"type": "create_snapshot"}, callback)

    async def restore_snapshot(self, callback=None) -> int:
        """回滚到之前创建的历史快照"""
        return await self._send_payload({"type": "restore_snapshot"}, callback)

    # --- 多文档管理 (Workflow Support) ---
    
    async def list_open_documents(self, callback=None) -> int:
        """获取当前 PS 中所有打开的文档列表"""
        return await self._send_payload({"type": "get_open_docs"}, callback)

    async def open_psd(self, file_path: str, callback=None) -> int:
        """打开指定路径的 PSD 文件"""
        return await self._send_payload({"type": "open_doc", "path": file_path}, callback)

    async def close_psd(self, doc_id: int = None, name: str = None, save: bool = False, callback=None) -> int:
        """关闭指定文档"""
        return await self._send_payload({
            "type": "close_doc", 
            "doc_id": doc_id, 
            "name": name, 
            "save": save
        }, callback)

    async def activate_psd(self, doc_id: int = None, name: str = None, callback=None) -> int:
        """激活/切换到指定文档"""
        return await self._send_payload({
            "type": "activate_doc", 
            "doc_id": doc_id, 
            "name": name
        }, callback)

    async def fix_ps_environment(self, callback=None) -> int:
        """优化 PS 环境设置（关闭标签页模式，解决空间不足报错）"""
        return await self._send_payload({"type": "fix_environment"}, callback)

    async def execute_strategy_atomic(self, operations: list, renders: list, debug: bool = False, target_document: str = None, callback=None) -> int:
        """
        原子化执行完整策略包
        
        参数:
            operations: 编辑操作列表
            renders: 渲染配置列表
            debug: 是否处于调试模式（调试模式下不关闭中间副本）
            target_document: 目标文档名称或ID（可选，用于工作流自动切换）
        """
        return await self._send_payload({
            "type": "execute_atomic",
            "operations": operations,
            "renders": renders,
            "debug": debug,
            "target_document": target_document
        }, callback)

    # ============================================
    # 策略自动化相关 (Strategy Automation)
    # ============================================

    def get_strategy_data_requirements(self, strategy: dict) -> dict:
        """
        获取策略的数据需求，按 group 索引归类
        
        参数:
            strategy: 策略字典（从 read_strategy 获取）
        
        返回:
            {
                "groups": {
                    "1": {"type": "text", "targets": ["主文档 > A", ...]},
                    "2": {"type": "image", "targets": ["主文档 > B", ...]}
                },
                "output_configs": [{"name": "...", "filename_template": "...", "format": "..."}]
            }
        """
        requirements = {
            "groups": {},
            "output_configs": []
        }
        
        if not strategy:
            return requirements

        # 1. 解析 operations
        for op in strategy.get("operations", []):
            op_type = op.get("type")
            group = op.get("group")
            target_path = op.get("target_path")
            
            if group is None or not target_path:
                continue
            
            group_key = str(group)
            if group_key not in requirements["groups"]:
                requirements["groups"][group_key] = {
                    "type": "text" if op_type == "update_text_layer" else "image",
                    "targets": []
                }
            
            requirements["groups"][group_key]["targets"].append(target_path)
        
        # 2. 解析 renders
        for render in strategy.get("renders", []):
            requirements["output_configs"].append({
                "name": render.get("name"),
                "filename_template": render.get("filename", "export_{index}"),
                "output_path": render.get("output_path", ""),
                "format": render.get("format", "jpg")
            })
            
        return requirements

    async def execute_batch_with_data(self, strategy: dict, data_table: List[Dict[str, Any]], callback=None, progress_callback=None) -> int:
        """
        使用预处理好的数据执行批量处理任务
        
        参数:
            strategy: 完整策略字典
            data_table: UI解析好的数据列表，每项是一个包含字段映射的字典
            callback: 任务完成后的回调 (results, error)
            progress_callback: 进度回调 (current, total, status, message)
        """
        if not self.websocket:
            _log("错误: 未连接，无法执行批量处理")
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(None, "Not Connected")
                    else:
                        callback(None, "Not Connected")
                except Exception as e:
                    _log(f"回调执行异常: {e}")
            return 0

        # 1. 获取最新图层结构以解析路径
        _log("正在获取图层结构以解析策略路径...")
        
        # 使用 Future 来同步等待异步回调
        loop = asyncio.get_event_loop()
        layer_tree_future = loop.create_future()
        
        async def on_layers(tree, err):
            if err: layer_tree_future.set_exception(Exception(err))
            else: layer_tree_future.set_result(tree)
            
        await self.request_layers(callback=on_layers)
        try:
            layer_tree = await asyncio.wait_for(layer_tree_future, timeout=10.0)
        except Exception as e:
            _log(f"获取图层结构失败: {e}")
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(None, f"Layer tree error: {e}")
                    else:
                        callback(None, f"Layer tree error: {e}")
                except Exception as cb_err:
                    _log(f"回调执行异常: {cb_err}")
            return 0

        # 2. 预解析所有 target_path 为 layer_id + parent_chain
        _log("正在解析图层路径并校验操作类型...")
        op_templates = []
        for op in strategy.get("operations", []):
            target_path = op.get("target_path")
            if not target_path: continue
            
            layer_id, parent_chain, kind = self._resolve_layer_path(layer_tree, target_path)
            
            if layer_id is None:
                _log(f"警告: 无法找到图层路径: {target_path}，该操作将被忽略")
                continue

            # --- 安全性校验 ---
            if op.get("type") == "apply_filter" and kind != "SMARTOBJECT":
                _log(f"拦截操作: 局部滤镜仅支持智能对象。图层 '{target_path}' 类型为 {kind}，已跳过。")
                continue
            
            op_template = op.copy()
            op_template["layer_id"] = layer_id
            op_template["parent_chain"] = parent_chain
            op_templates.append(op_template)

        # 3. 循环执行每一行数据
        total = len(data_table)
        _log(f"开始执行批量队列，共 {total} 组数据")
        
        # 报告开始
        if progress_callback:
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(0, total, "started", "开始批量处理")
                else:
                    progress_callback(0, total, "started", "开始批量处理")
            except Exception as e:
                _log(f"进度回调异常: {e}")
        
        results = []
        for idx, row in enumerate(data_table, 1):
            _log(f"--- 处理第 {idx}/{total} 组数据 ---")
            
            # 报告当前进度
            if progress_callback:
                try:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(idx, total, "processing", f"处理第 {idx}/{total} 行")
                    else:
                        progress_callback(idx, total, "processing", f"处理第 {idx}/{total} 行")
                except Exception as e:
                    _log(f"进度回调异常: {e}")
            
            try:
                # 3.1 构建当前行的操作列表
                current_ops = []
                for template in op_templates:
                    op = template.copy()
                    group = op.get("group")
                    group_key = str(group) if group is not None else None
                    
                    if op["type"] == "update_text_layer":
                        text = op.get("text", "")
                        if group_key and group_key in row:
                            text = str(row[group_key])
                        
                        # 应用多步正则预处理
                        op["text"] = self._apply_regex_processing(text, op.get("regex_steps", []))
                    elif op["type"] == "replace_image" and group_key and group_key in row:
                        # 统一路径为正斜杠
                        op["image_path"] = str(row[group_key]).replace("\\", "/")
                    
                    current_ops.append(op)
                
                # 3.2 准备渲染配置
                current_renders = []
                for render_config in strategy.get("renders", []):
                    # 文件名处理
                    filename = row.get("output_filename")
                    if not filename:
                        filename = render_config.get("filename", "export_{index}").replace("{index}", str(idx))
                    
                    # 确定 root_ids
                    root_layers_paths = render_config.get("root_layers", [])
                    root_ids = []
                    for path in root_layers_paths:
                        rid, _, _ = self._resolve_layer_path(layer_tree, path)
                        if rid: root_ids.append(rid)
                    
                    # 统一路径为正斜杠
                    output_folder = render_config.get("output_path", ".").replace("\\", "/")
                    
                    current_renders.append({
                        "folder": output_folder,
                        "file_name": filename,
                        "format": render_config.get("format", "jpg"),
                        "root_ids": root_ids,
                        "tiling": render_config.get("tiling", {}).get("enabled", False),
                        "width": render_config.get("tiling", {}).get("width", 0),
                        "height": render_config.get("tiling", {}).get("height", 0),
                        "resolution": render_config.get("tiling", {}).get("ppi", 300),
                        "filters": render_config.get("filters", [])
                    })

                # 3.3 原子化发送任务包
                # 使用 Future 等待当前行的原子任务完成
                loop = asyncio.get_event_loop()
                atomic_future = loop.create_future()
                async def on_atomic_done(success, err):
                    if err: atomic_future.set_exception(Exception(err))
                    else: atomic_future.set_result(success)

                await self.execute_strategy_atomic(
                    operations=current_ops,
                    renders=current_renders,
                    debug=False, # 批量处理默认不开启调试
                    callback=on_atomic_done
                )
                
                await asyncio.wait_for(atomic_future, timeout=120.0) # 每行原子任务包给 120s
                results.append({"index": idx, "status": "ok"})
                
                # 报告成功
                if progress_callback:
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(idx, total, "success", f"第 {idx} 行处理成功")
                        else:
                            progress_callback(idx, total, "success", f"第 {idx} 行处理成功")
                    except Exception as e:
                        _log(f"进度回调异常: {e}")
                        
            except Exception as e:
                _log(f"第 {idx} 组数据处理失败: {e}")
                results.append({"index": idx, "status": "error", "error": str(e)})
                
                # 报告错误
                if progress_callback:
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(idx, total, "error", f"第 {idx} 行处理失败: {str(e)}")
                        else:
                            progress_callback(idx, total, "error", f"第 {idx} 行处理失败: {str(e)}")
                    except Exception as e:
                        _log(f"进度回调异常: {e}")

        success_count = sum(1 for r in results if r['status']=='ok')
        _log(f"批量处理完成，成功: {success_count}/{total}")
        
        # 报告完成
        if progress_callback:
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(total, total, "completed", f"全部完成: {success_count}/{total} 成功")
                else:
                    progress_callback(total, total, "completed", f"全部完成: {success_count}/{total} 成功")
            except Exception as e:
                _log(f"进度回调异常: {e}")
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(results, None)
                else:
                    callback(results, None)
            except Exception as e:
                _log(f"回调执行异常: {e}")
        
        return 0

    async def execute_workflow(self, tasks: list, progress_callback=None) -> list:
        """
        执行多文档工作流
        
        参数:
            tasks: 任务列表，每一项包含:
                - "psd_path": PSD文件路径
                - "strategy": 策略字典
                - "data_table": 数据表
        """
        _log(f"开始执行工作流，共 {len(tasks)} 个 PSD 任务")
        results = []
        loop = asyncio.get_event_loop()

        for idx, task in enumerate(tasks, 1):
            psd_path = task["psd_path"]
            psd_name = psd_path.replace("\\", "/").split("/")[-1]
            _log(f"--- [Workflow {idx}/{len(tasks)}] 处理文件: {psd_name} ---")
            
            try:
                # 1. 打开文件
                open_future = loop.create_future()
                async def on_open(res, err):
                    if err: open_future.set_exception(Exception(err))
                    else: open_future.set_result(res)
                
                await self.open_psd(psd_path, callback=on_open)
                await asyncio.wait_for(open_future, timeout=30.0)
                
                # 2. 执行批量任务 (借用现有的 execute_batch_with_data)
                batch_future = loop.create_future()
                async def on_batch_done(res, err):
                    if err: batch_future.set_exception(Exception(err))
                    else: batch_future.set_result(res)

                # 进度中继
                async def sub_progress(curr, total, status, msg):
                    if progress_callback:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(idx, len(tasks), f"PSD {idx} 进度: {curr}/{total}", msg)
                        else:
                            progress_callback(idx, len(tasks), f"PSD {idx} 进度: {curr}/{total}", msg)

                await self.execute_batch_with_data(
                    strategy=task["strategy"],
                    data_table=task["data_table"],
                    callback=on_batch_done,
                    progress_callback=sub_progress
                )
                
                batch_results = await asyncio.wait_for(batch_future, timeout=600.0) # 每个文件给 10 分钟
                
                # 3. 关闭文件 (不保存修改，因为原子化操作已经保护了原稿)
                await self.close_psd(name=psd_name, save=False)
                
                results.append({"psd": psd_name, "status": "ok", "details": batch_results})
                _log(f"文件 {psd_name} 处理完成")
                
            except Exception as e:
                _log(f"处理文件 {psd_name} 失败: {e}")
                results.append({"psd": psd_name, "status": "error", "error": str(e)})
                # 尝试关闭出错的文件
                try: await self.close_psd(name=psd_name, save=False)
                except: pass

        _log(f"工作流执行完毕")
        return results

    def _resolve_layer_path(self, layer_tree: list, target_path: str) -> tuple:
        """
        将图层路径解析为 ID 和父级链
        路径示例: "主文档 > 智能对象A > 标题层"
        返回: (layer_id, parent_chain, kind)
        """
        parts = [p.strip() for p in target_path.split(">")]
        if not parts or parts[0] != "主文档":
            return None, [], None
        
        remaining_path = parts[1:]
        if not remaining_path:
            return None, [], None

        def _find_recursive(nodes, path_parts, current_chain):
            if not path_parts:
                return None, current_chain, None
            
            target_name = path_parts[0]
            is_last = (len(path_parts) == 1)
            
            for node in nodes:
                # 精确匹配名称（不区分大小写）
                node_name = node.get("name", "")
                if node_name.lower() == target_name.lower():
                    if is_last:
                        return node.get("id"), current_chain, node.get("kind")
                    
                    # 如果不是最后一级，必须是组或智能对象
                    if node.get("kind") == "SMARTOBJECT":
                        return _find_recursive(node.get("children", []), path_parts[1:], current_chain + [node.get("id")])
                    elif node.get("kind") == "GROUP":
                        return _find_recursive(node.get("children", []), path_parts[1:], current_chain)
            
            return None, current_chain, None

        return _find_recursive(layer_tree, remaining_path, [])

    async def read_strategy(self, callback=None) -> int:
        """
        读取当前文档的编辑策略（UXP 端会从 XMP 中解析）

        callback 参数:
            strategy: dict | None  - 解析到的策略对象；如果未找到则为 None
            error: str | None      - 错误信息（如果有）
        """
        return await self._send_payload({
            "type": "read_strategy"
        }, callback)

    async def write_strategy(self, strategy: dict | None, callback=None) -> int:
        """
        写入/清空当前文档的编辑策略（UXP 端会序列化到 XMP 中）

        参数:
            strategy: dict | None
                - 传入 dict: 写入该策略
                - 传入 None: 清空已有策略

        callback 参数:
            success: bool        - 是否写入成功
            error: str | None    - 错误信息（如果有）
        """
        return await self._send_payload({
            "type": "write_strategy",
            "strategy": strategy
        }, callback)



# ============================================
# 全局实例
# ============================================
_server_instance: Optional[PSServer] = None

def get_server() -> PSServer:
    global _server_instance
    if _server_instance is None:
        _server_instance = PSServer()
    return _server_instance


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    async def main():
        server = get_server()
        await server.start()
        
        print("等待插件连接...")
        while not server.is_connected():
            await asyncio.sleep(1)
        
        # 这里仅演示保持运行
        await asyncio.Future()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
