"""
测试TSCPrinter类的导入

注意：这个脚本只测试导入，不实际连接打印机
"""

try:
    from tsclib import TSCPrinter, TSCError

    print("成功导入 TSCPrinter 和 TSCError 类")

    # 显示TSCPrinter的一些方法，验证类是否正常
    methods = [method for method in dir(TSCPrinter) if not method.startswith("_")]
    print(f"TSCPrinter类中有 {len(methods)} 个公共方法")
    print("部分方法包括:", ", ".join(methods[:5]))

    print("测试通过!")
except ImportError as e:
    print(f"导入错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")
