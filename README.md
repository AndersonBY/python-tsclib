# Python TSC 打印机控制库 (基于 tsclibnet.dll)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概述

本项目是一个完整的 Python 包 (`tsclib`)，旨在简化通过 USB 连接的 TSC (台半) 标签打印机的控制。包中已经集成了 TSC 官方提供的 `.NET` 动态链接库 `tsclibnet.dll`，并封装了所有必要的依赖，使您可以直接通过简单的 pip 安装即可使用。

**注意:** 此库是针对 `tsclibnet.dll` (.NET 版本) 的封装，其行为可能与旧版的 C/C++ `TSCLIB.DLL` 存在差异。请优先参考本库提供的接口和实际测试结果。

## 主要特性

*   **面向对象:** 封装为 `TSCPrinter` 类，易于使用和管理。
*   **连接管理:** 自动处理 `pythonnet` 初始化和 DLL 加载。
*   **端口控制:** 打开和关闭 USB 打印机端口。
*   **状态查询:** 获取打印机状态码和 DLL 版本信息。
*   **标签设置:** 配置标签尺寸、打印速度、浓度、传感器类型等。
*   **打印缓冲:** 清除打印机缓冲区。
*   **内容打印:**
    *   使用打印机内置字体打印文本。
    *   使用打印机内置引擎打印多种条形码。
    *   调用 Windows 系统安装的 TrueType 字体 (TTF) 打印文本。
*   **原始指令:** 发送 TSPL/TSPL2 原始指令 (包括 UTF-8 编码指令)。
*   **打印执行:** 发送最终的打印命令。
*   **上下文管理:** 支持 `with` 语句，自动管理端口的打开和关闭。
*   **错误处理:** 定义了 `TSCError` 异常类型。

## 环境要求

1.  **Python:** Python 3.10 或更高版本。
2.  **.NET Runtime:** 运行此库的机器上必须安装与 `tsclibnet.dll` 兼容的 .NET Runtime。这通常是 .NET Framework (如 4.x) 或 .NET Core / .NET 5+，具体取决于 `tsclibnet.dll` 的目标框架。请从微软官网下载并安装。
3.  **TSC 打印机:** 一台通过 USB 连接到电脑的 TSC 标签打印机。
4.  **打印机驱动:** 建议安装官方的 TSC 打印机驱动程序，虽然此库尝试直接通过 USB 通信，但驱动可能有助于系统正确识别设备。

## 安装与配置

1.  **安装包:** 使用 pip 安装:
    ```bash
    pip install tsclib
    ```
    
   本包已经包含了所需的 `tsclibnet.dll` 文件和 `pythonnet` 依赖，无需单独安装。

2.  **安装 .NET Runtime:** 确保已安装所需的 .NET 运行时环境。

## 快速开始

以下是一个基本的使用示例，演示如何打印一个包含文本、条码和 Windows 字体的测试标签：

```python
import logging
from tsclib import TSCPrinter, SensorType, BarcodeReadable, Rotation, TSCError

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- TSC 打印机模块测试 ---
logging.info("--- 开始 TSC 打印机模块测试 ---")

try:
    # 使用 'with' 语句确保端口在使用后自动关闭
    with TSCPrinter() as printer:
        logging.info("打印机端口已打开 (通过上下文管理器)")

        # 检查打印机状态 (可选但推荐)
        status = printer.get_status()
        print(f"打印机状态: {status}")
        if status != "00": # '00' 通常表示准备就绪
            logging.warning(f"打印机未准备就绪 (状态码: {status})，请检查打印机。")
            # 根据需要，可以决定是否继续或抛出错误

        # 1. 设置标签参数 (示例: 70mm 宽, 40mm 高)
        #    请根据你的实际标签和打印机调整这些值
        printer.setup_label(
            width_mm="70",
            height_mm="40",
            speed="4.0",      # 打印速度 (查阅 TSPL 手册)
            density="10",     # 打印浓度 (0-15)
            sensor_type=SensorType.GAP, # 传感器类型 (GAP 或 BLACK_MARK)
            gap_mm="3",       # 标签间隙/黑标高度 (mm)
            offset_mm="0"     # 偏移量 (通常为 0)
        )

        # 2. 清除打印机缓冲区 (重要！)
        printer.clear_buffer()

        # 3. 向缓冲区添加打印内容
        # 打印内部字体文本
        printer.print_text_internal_font(
            x="50", y="50", font_type="3", rotation=Rotation.DEG_0,
            x_mul="1", y_mul="1", text="Internal Font Test"
        )

        # 打印条形码 (Code 128)
        printer.print_barcode(
            x="50", y="100", barcode_type="128", height="70",
            readable=BarcodeReadable.YES, rotation=Rotation.DEG_0,
            narrow_bar_mul="2", wide_bar_mul="1", code="TSC-PYTHON-123"
        )

        # 打印 Windows 字体文本 (确保系统安装了 Arial 字体)
        printer.print_text_windows_font(
            x=50, y=250, font_height=48, rotation=0,
            font_style=0, font_underline=0, font_face_name="Arial",
            text="Windows Arial Test"
        )

        # 发送原始 TSPL 命令 (例如，画一个框)
        printer.send_command('BOX 50,350,600,450,3') # x1,y1,x2,y2,线宽

        # 发送 UTF-8 编码的命令 (如果打印机支持)
        # 可能需要先发送 "CODEPAGE UTF-8" 命令
        # printer.send_command("CODEPAGE UTF-8")
        printer.send_command_utf8('TEXT 50,500,"KAIU.TTF",0,12,12,"测试中文 Text"')

        # 4. 执行打印命令
        printer.print_label(quantity="1", copies="1") # 打印 1 张

        logging.info("打印任务已发送至打印机。")

    logging.info("打印机端口已关闭 (通过上下文管理器)")

except FileNotFoundError as e:
    logging.error(f"初始化失败: {e}")
    print(f"错误: 无法找到所需的DLL文件。")
except ConnectionError as e:
    logging.error(f"连接错误: {e}")
    print(f"错误: 无法连接到打印机或通信失败。请检查打印机连接和电源。")
except TSCError as e:
    logging.error(f"TSC 打印机错误: {e}")
    print(f"打印机错误: {e}。请检查打印机状态 (纸张、碳带等) 和发送的命令。")
except Exception as e:
    logging.error(f"发生意外错误: {e}", exc_info=True)
    print(f"发生意外错误: {e}")

logging.info("--- TSC 打印机模块测试结束 ---")
```

## API 说明

### `TSCPrinter` 类

#### `__init__(self, dll_path: str | Path | None = None)`
初始化打印机接口。
*   `dll_path`: 可选参数，指定 `tsclibnet.dll` 的路径。如果为 `None`，则使用包中内置的 DLL 文件。一般情况下无需指定此参数。

#### `open_port(self, port_name: str = "") -> object`
打开与打印机的通信端口。
*   `port_name`: 端口名称。对于 USB 连接，通常传入空字符串 `""` 即可让库自动查找。也可以尝试使用驱动名或 `"USB"`。

#### `close_port(self) -> object`
关闭通信端口。

#### `setup_label(self, width_mm: str, height_mm: str, speed: str, density: str, sensor_type: str, gap_mm: str, offset_mm: str) -> object`
设置标签的基本参数。**注意：** 尽管是尺寸、速度等数值，但根据观察和文档，这些参数通常以 **字符串** 形式传递。
*   `width_mm`: 标签宽度 (毫米)。
*   `height_mm`: 标签高度 (毫米)。
*   `speed`: 打印速度 (例如 `"4.0"`)。具体可用值请参考 TSPL 手册。
*   `density`: 打印浓度 (例如 `"10"`)。范围通常是 "0" 到 "15"。
*   `sensor_type`: 传感器类型 (`SensorType.GAP` 或 `SensorType.BLACK_MARK`)。
*   `gap_mm`: 标签间隙或黑标的高度 (毫米)。
*   `offset_mm`: 垂直偏移量 (毫米，通常为 `"0"`)。

#### `clear_buffer(self) -> object`
清除打印机内部的指令缓冲区。**强烈建议** 在每次打印新标签前调用此方法。

#### `print_label(self, quantity: str = "1", copies: str = "1") -> object`
执行打印命令，打印缓冲区中的内容。
*   `quantity`: 打印的标签 **组数** (set)。
*   `copies`: 每组标签打印的 **份数** (copy)。

#### `print_text_internal_font(self, x: str, y: str, font_type: str, rotation: str, x_mul: str, y_mul: str, text: str) -> object`
使用打印机内置字体打印文本。
*   `x`, `y`: 起始坐标 (单位: dots)。
*   `font_type`: 内置字体编号 (字符串，例如 `"1"`, `"2"`, ... `"TST24.BF2"` 等)。请参考 TSPL 手册。
*   `rotation`: 旋转角度 (`Rotation.DEG_0`, `Rotation.DEG_90` 等)。
*   `x_mul`, `y_mul`: 水平和垂直放大倍数 (字符串, "1" 到 "8")。
*   `text`: 要打印的文本内容。

#### `print_barcode(self, x: str, y: str, barcode_type: str, height: str, readable: str, rotation: str, narrow_bar_mul: str, wide_bar_mul: str, code: str) -> object`
打印条形码。
*   `x`, `y`: 起始坐标 (dots)。
*   `barcode_type`: 条码类型 (字符串，例如 `"128"`, `"39"`, `"EAN13"` 等)。请参考 TSPL 手册。
*   `height`: 条码高度 (dots)。
*   `readable`: 是否打印可读字符 (`BarcodeReadable.YES` 或 `BarcodeReadable.NO`)。
*   `rotation`: 旋转角度 (`Rotation.DEG_0` 等)。
*   `narrow_bar_mul`, `wide_bar_mul`: 窄条/宽条比例因子或宽度 (字符串)。请参考 TSPL 手册。
*   `code`: 条码数据。

#### `print_text_windows_font(self, x: int, y: int, font_height: int, rotation: int, font_style: int, font_underline: int, font_face_name: str, text: str) -> object`
使用 Windows TTF 字体打印文本。**注意：** 此方法的坐标、高度、角度等参数使用 **整数** 类型。
*   `x`, `y`: 起始坐标 (dots)。
*   `font_height`: 字体高度 (dots)。
*   `rotation`: 旋转角度 (整数: 0, 90, 180, 270)。
*   `font_style`: 字体样式 (整数: 0=常规, 1=斜体, 2=粗体, 3=粗斜体)。
*   `font_underline`: 是否加下划线 (整数: 0=无, 1=有)。
*   `font_face_name`: Windows 中安装的字体名称 (例如 `"Arial"`, `"微软雅黑"`)。
*   `text`: 要打印的文本内容 (支持 Unicode)。

#### `send_command(self, command: str) -> object`
发送原始的 TSPL/TSPL2 指令字符串。使用打印机当前的代码页。
*   `command`: TSPL 指令字符串 (例如 `'GAP 3 mm, 0 mm'`)。

#### `send_command_utf8(self, command: str) -> object`
以 UTF-8 编码发送原始 TSPL/TSPL2 指令字符串。适用于包含非 ASCII 字符的指令。
*   `command`: TSPL 指令字符串。

#### `get_status(self, delay_ms: int = 100) -> str`
获取打印机状态码。
*   `delay_ms`: 等待状态返回的延迟时间 (毫秒)。
*   返回值: 状态码字符串 (例如 `"00"` 表示正常)。含义请参考 TSPL 手册 `<ESC>!?` 指令。

#### `get_about_info(self) -> str`
获取 `tsclibnet.dll` 的关于信息 (通常是版本号)。

### 上下文管理器 (`with` 语句)

`TSCPrinter` 类支持 Python 的 `with` 语句，这是推荐的使用方式。它会在进入 `with` 代码块时自动调用 `open_port()`，并在退出代码块时（无论是否发生异常）自动调用 `close_port()`。

```python
with TSCPrinter() as printer:
    # 在这里执行打印操作
    printer.setup_label(...)
    printer.clear_buffer()
    # ... 添加打印内容 ...
    printer.print_label()
# 离开 with 代码块后，printer.close_port() 会被自动调用
```

### 参数传递

请注意，许多接受多个参数的 `.NET` 方法（如 `setup`, `barcode`, `printerfont`, `windowsfont`）在此 Python 封装中是通过传递一个 `types.SimpleNamespace` 对象来实现的。这与旧版 C DLL 直接接受多个独立参数的方式不同。本库已将此细节封装在相应的方法中。

### 坐标单位

TSPL/TSPL2 命令中的坐标和尺寸单位通常是 **点 (dots)**。实际物理尺寸取决于打印机的分辨率 (DPI - Dots Per Inch)。
*   200 DPI: 1 毫米 ≈ 8 dots
*   300 DPI: 1 毫米 ≈ 12 dots

## 错误处理

*   **初始化错误:** 如果 DLL 未找到、.NET 环境有问题或 `pythonnet` 加载失败，`__init__` 方法会抛出 `FileNotFoundError`, `ImportError`, `RuntimeError` 或 `TSCError`。
*   **通信错误:** 在 `open_port`, `close_port` 或发送指令期间，如果无法与打印机通信（例如，USB 未连接，电源关闭），可能会抛出 `ConnectionError` 或底层的 `.NET` 异常（通常被包装在 `TSCError` 中）。
*   **打印机错误:** 如果发送的指令无效，或者打印机处于错误状态（缺纸、缺碳带、卡纸、打印头开启等），`get_status()` 会返回相应的状态码，而执行打印相关操作可能会失败并抛出 `TSCError`。建议在打印前检查 `get_status()` 的返回值。
*   **其他异常:** 可能还会遇到标准的 Python 异常，如 `AttributeError` (如果尝试调用不存在的方法) 等。

建议使用 `try...except` 块来捕获这些潜在的异常，并根据错误类型进行处理，例如记录日志或向用户显示友好的错误信息。

## 注意事项

*   **DLL 依赖性:** 此库强依赖于特定版本的 `tsclibnet.dll`。如果更换了 DLL 文件（尤其是不同版本或来自不同来源的），API 行为可能发生变化，需要重新测试甚至修改代码。
*   **.NET 互操作性:** `pythonnet` 在后台处理了复杂的 .NET 互操作。大多数情况下是透明的，但理解其基本工作方式有助于排查问题。DLL 的方法大多返回 `Task<System.Object>`，本库通过 `.Result` 阻塞等待其完成。
*   **官方文档差异:** TSC 官方提供的旧版 `TSCLIB.DLL` 文档（通常是 PDF 格式）描述的是 C/C++ 接口，其函数签名、参数类型甚至函数名称可能与 `tsclibnet.dll` 中的 `.NET` 接口不完全匹配。**请以本库的代码、注释和逆向工程得到的 API 列表为准。**
*   **参数类型:** 再次强调，TSPL 命令中的许多数值参数（坐标、尺寸、速度等）在此封装中通常需要以 **字符串** 形式传递给对应的方法，`windowsfont` 是一个例外，它使用整数。

## 贡献

欢迎提交问题报告 (Issues) 或提出改进建议 (Pull Requests)。请提供清晰的问题描述、复现步骤和相关的环境信息。

## 许可 (License)

本项目采用 [MIT License](LICENSE) 授权。