import asyncio
import os
from server import get_server

async def run_workflow_test():
    server = get_server()
    try:
        await server.start()
    except Exception as e:
        print(f"启动服务器失败: {e}")
        return

    print("\n>>> [Workflow] 等待插件连接...")
    while not server.is_connected():
        await asyncio.sleep(1)
    
    print(">>> [Workflow] 插件已连接！正在构建工作流任务...")

    # 模拟两个 PSD 任务
    # 注意：这些路径应该是您本地存在的真实 PSD 路径，这里仅做示意
    # 如果要运行，请修改为真实的绝对路径
    # psd_files = [
    #     "C:/Templates/Design_A.psd",
    #     "C:/Templates/Design_B.psd"
    # ]
    
    # 获取当前打开的文档作为测试
    doc_future = asyncio.get_event_loop().create_future()
    async def on_docs(docs, err):
        if err: doc_future.set_exception(Exception(err))
        else: doc_future.set_result(docs)
    
    await server.list_open_documents(callback=on_docs)
    open_docs = await asyncio.wait_for(doc_future, timeout=10.0)

    if not open_docs:
        print(">>> [Workflow] 请先在 PS 中打开至少一个 PSD 文档用于测试")
        await server.stop()
        return

    print(f">>> [Workflow] 发现 {len(open_docs)} 个已打开文档，将模拟工作流轮转...")

    # 构建任务包
    tasks = []
    for doc in open_docs:
        if doc["path"] == "unsaved": continue # 跳过未保存的新建文档
        
        # 为每个文档构建一个简单的策略任务
        tasks.append({
            "psd_path": doc["path"],
            "strategy": {
                "version": "1.1.0",
                "operations": [], # 这里可以留空，仅测试轮转渲染
                "renders": [
                    {
                        "filename": f"wf_test_{doc['id']}",
                        "output_path": os.path.abspath("./test_output").replace("\\", "/"),
                        "format": "jpg"
                    }
                ]
            },
            "data_table": [{"index": 1}] # 执行一次渲染
        })

    if not tasks:
        print(">>> [Workflow] 任务清单为空（可能所有文档都未保存，没有物理路径）")
    else:
        print(f">>> [Workflow] 开始执行工作流，共 {len(tasks)} 个文档...")
        
        async def progress(idx, total, status, msg):
            print(f"    [进度] {idx}/{total} | {status} | {msg}")

        results = await server.execute_workflow(tasks, progress_callback=progress)
        
        print("\n>>> [Workflow] 执行结果汇总:")
        for r in results:
            icon = "✅" if r["status"] == "ok" else "❌"
            print(f"    {icon} {r['psd']}: {r['status']}")

    print("\n>>> 任务结束，正在关闭服务器...")
    await asyncio.sleep(2)
    await server.stop()

if __name__ == "__main__":
    asyncio.run(run_workflow_test())

