import asyncio
import random
import os
from server import get_server

async def run_minimal_test():
    # 1. 获取并启动服务器 (测试脚本作为 Server 运行)
    server = get_server()
    try:
        await server.start()
    except Exception as e:
        print(f"!!! 启动失败: {e}。请检查是否已关闭 main.py")
        return

    print("\n>>> [测试] 服务器已启动，等待 UXP 插件连接 (请确保插件已打开)...")
    while not server.is_connected():
        await asyncio.sleep(1)
    
    print(">>> [测试] 插件已连接！开始拉取图层树...")
    
    # 2. 获取图层结构
    layer_tree_future = asyncio.get_event_loop().create_future()
    async def on_layers(tree, err):
        if err: layer_tree_future.set_exception(Exception(err))
        else: layer_tree_future.set_result(tree)
    
    await server.request_layers(callback=on_layers)
    layer_tree = await asyncio.wait_for(layer_tree_future, timeout=10.0)

    # 3. 随机寻找测试目标
    # 提取文本层
    text_layers = server.extract_editable_layers(layer_tree)
    
    # 扁平化所有图层以便随机选择
    all_layers = []
    def flatten(nodes, chain=[]):
        for n in nodes:
            all_layers.append({"id": n["id"], "name": n["name"], "chain": chain, "kind": n.get("kind")})
            if "children" in n:
                new_chain = chain + ([n["id"]] if n.get("kind") == "SMARTOBJECT" else [])
                flatten(n["children"], new_chain)
    flatten(layer_tree)

    # 4. 构建原子任务包
    print("\n>>> [准备] 构建原子化任务包 (副本保护模式)...")
    
    operations = []
    # A. 换文字
    if text_layers:
        t = random.choice(text_layers)
        new_text = f"原子测试_{random.randint(100, 999)}"
        operations.append({
            "type": "update_text_layer",
            "layer_id": t["id"],
            "text": new_text,
            "parent_chain": t["parent_chain"]
        })
        print(f"    * 准备换文字: '{t['name']}' -> '{new_text}'")

    # B. 应用局部滤镜
    so_layers = [l for l in all_layers if l["kind"] == "SMARTOBJECT"]
    target_l = random.choice(so_layers if so_layers else all_layers)
    
    # 随机选一个滤镜测试
    filter_type = random.choice(["emboss", "gaussianBlur"])
    filter_params = {
        "emboss": {"angle": random.randint(-180, 180), "height": 3, "amount": 150},
        "gaussianBlur": {"radius": random.uniform(2.0, 10.0)}
    }[filter_type]

    operations.append({
        "type": "apply_filter",
        "layer_id": target_l["id"],
        "filter_type": filter_type,
        "params": filter_params,
        "parent_chain": target_l["chain"]
    })
    print(f"    * 准备局部滤镜: '{target_l['name']}' 应用 {filter_type} ({filter_params})")

    # 6. 渲染配置
    output_path = os.path.abspath("./test_output").replace("\\", "/")
    if not os.path.exists(output_path): os.makedirs(output_path)
    
    renders = [{
        "file_name": "atomic_test_result",
        "folder": output_path,
        "format": "jpg",
        "filters": [
            {
                "type": "gaussianBlur",
                "params": {"radius": 3.0}
            },
            {
                "type": "emboss",
                "params": {"angle": 135, "height": 2, "amount": 100}
            }
        ]
    }]

    # 7. 原子化发送并执行
    print("\n>>> [执行] 发送原子化任务包 (并等待详细回调)...")
    
    atomic_future = asyncio.get_event_loop().create_future()
    async def on_done(data, err):
        if err: 
            atomic_future.set_exception(Exception(err))
        else: 
            atomic_future.set_result(data)

    await server.execute_strategy_atomic(
        operations=operations,
        renders=renders,
        debug=True, # 开启调试模式，执行完后保留副本供观察
        callback=on_done
    )
    
    result_data = await asyncio.wait_for(atomic_future, timeout=60.0)
    
    print(f"\n>>> [结果] 任务执行状态: {result_data.get('status')}")
    if "rendered_files" in result_data:
        print(">>> [清单] 已生成的文件列表:")
        for file in result_data["rendered_files"]:
            status_icon = "✅" if file["status"] == "ok" else "❌"
            print(f"    {status_icon} {file['name']}: {file.get('path', 'n/a')}")
            if file["status"] != "ok":
                print(f"       错误提示: {file.get('error')}")

    # 8. 验证批量处理 (测试 Group 分组逻辑)
    print("\n>>> [测试] 验证批量处理逻辑 (Group 映射)...")
    
    # 构造一个包含 Group 的测试策略
    test_strategy = {
        "version": "1.1.0",
        "operations": [
            {
                "type": "update_text_layer",
                "target_path": text_layers[0]["target_path"] if text_layers else "主文档 > 未知层",
                "group": 1
            }
        ],
        "renders": [
            {
                "name": "batch_test",
                "filename": "batch_group_test_{index}",
                "output_path": output_path,
                "format": "jpg"
            }
        ]
    }
    
    # 如果有超过一个文本层，测试多个层绑定同一个 group
    if len(text_layers) > 1:
        test_strategy["operations"].append({
            "type": "update_text_layer",
            "target_path": text_layers[1]["target_path"],
            "group": 1
        })
        print(f"    * 已将图层 '{text_layers[0]['name']}' 和 '{text_layers[1]['name']}' 绑定到 Group 1")

    # 准备测试数据 (行数据使用索引字符串作为键)
    test_data = [
        {"1": "第一组数据_组1内容", "output_filename": "group_test_row1"},
        {"1": "第二组数据_组1内容", "output_filename": "group_test_row2"}
    ]
    
    batch_future = asyncio.get_event_loop().create_future()
    async def on_batch_done(results, err):
        if err: batch_future.set_exception(Exception(err))
        else: batch_future.set_result(results)
    
    print(f"    * 开始执行批量处理，共 {len(test_data)} 行...")
    await server.execute_batch_with_data(
        strategy=test_strategy,
        data_table=test_data,
        callback=on_batch_done
    )
    
    batch_results = await asyncio.wait_for(batch_future, timeout=120.0)
    print(f"    * 批量处理完成，结果: {batch_results}")

    print(f"\n>>> [验证] 测试完成！")
    print(f"    1. 由于开启了 debug=True，PS 中应保留了一个名称包含 '_WorkCopy' 的副本。")
    print(f"    2. 请检查该副本中文字是否改变，以及图层 '{target_l['name']}' 是否有滤镜。")
    print(f"    3. 请检查导出文件: {output_path}/atomic_test_result.jpg")
    print(f"    4. 原始模板文档应当没有任何变化且处于激活状态。")
    
    print("\n>>> 脚本将保持运行 2 秒...")
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_minimal_test())
