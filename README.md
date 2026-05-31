# FlowCal：本地语音驱动的智能日历与任务管理助手

FlowCal 是一个基于 Streamlit 的本地日历与任务管理工具。用户可以通过中文语音或文本快速创建、查询、修改和管理日程，并在可视化日历中查看安排。

项目默认使用本地 `SenseVoiceSmall` 完成中文语音识别，不上传录音，也不默认调用云端语音服务。识别结果会进入本地语音理解流水线，再根据语义完整度和操作风险决定执行、确认、追问或拒绝。

## 项目亮点

- 默认使用本地 `SenseVoiceSmall` 进行中文语音识别。
- 默认零云端 ASR 费用，不上传录音，不依赖 API Key。
- 自动清理 SenseVoice 输出中的 `<|...|>` 元数据标签。
- 本地语音理解流水线支持上下文词表、候选扩展、语义帧、重排序和风险策略。
- 支持日程创建、日程查询、任务完成、删除和修改。
- 高风险操作和不确定结果会要求用户确认或补充信息。
- Streamlit 界面提供月历、日时间线、弹性任务池和语音回复。
- 语音回复默认只自动播放一次，避免确认阶段重复播放。
- 可选接入 GLM 语义解析器，但默认关闭，不是运行项目的必要依赖。
- 保留显式开启的本地 Whisper fallback，但默认不加载、不下载。

## 功能概览

### 日历与任务管理

FlowCal 支持四类任务：

| 任务类型 | 用途 | 展示方式 |
|---|---|---|
| `fixed_event` | 有明确日期和时间的固定日程，例如面试、会议、课程 | 日历时间块 |
| `deadline_task` | 有截止时间的任务，例如报告、作业、材料提交 | 截止任务卡片 |
| `essential_task` | 指定日期必须完成的生活任务，例如洗衣、买药、取快递 | 每日任务条 |
| `flexible_plan` | 可以灵活安排的待办，例如复习、阅读、练习 | 弹性任务池 |

任务完成后仍可保留在界面中，并以弱化样式展示。页面支持删除、完成、撤销完成、延期以及按任务类型编辑时间、截止时间和任务类型。

### 语音输入

- 浏览器通过 Streamlit `st.audio_input` 采集录音。
- 默认加载本地 `SenseVoiceSmall` 模型进行中文识别。
- SenseVoice 输出中的语言、情绪和音频类型标签会被通用正则清理。
- ASR 转写结果会显示在页面中，用户可以在继续解析前手动修正。
- 没有麦克风时，可以使用文本输入作为回退入口。

标签清理示例：

```text
原始结果：
<|zh|><|NEUTRAL|><|Speech|>明天下午三点开组会

进入语义解析的文本：
明天下午三点开组会
```

### 本地语音理解

本地理解引擎位于 `src/voice_understanding/`，主要能力包括：

- 检查音频时长、采样率和声道等基础质量信息。
- 从现有任务标题、日历词汇和用户配置词汇中构造有限上下文。
- 生成多个可解释的文本候选，而不是直接覆盖原始 ASR 文本。
- 将文本解析为统一语义帧。
- 根据 ASR 置信度、语义完整度、上下文匹配、时间一致性和风险惩罚进行重排序。
- 输出 `execute`、`confirm`、`clarify` 或 `reject` 决策。
- 将本地诊断信息写入 JSONL trace，便于回放和排查。

### 语音回复

`pyttsx3` 在本机生成 WAV 格式语音回复。确认区域和固定回复区域不会同时自动播放同一个音频，避免出现两个声音重叠回答。

### 可选语义解析

项目保留 GLM 语义解析器作为显式开启的可选路径。默认情况下，页面使用本地规则解析器。只有同时配置云端许可开关和对应凭据后，UI 才会尝试使用该可选路径。

音频不会上传到 GLM。启用任何云端能力前，请自行评估费用和隐私风险。

## 当前语音处理流程

```text
浏览器录音
→ 本地 SenseVoiceSmall ASR
→ 清理 <|...|> 元数据标签
→ 文本标准化
→ 本地上下文与候选扩展
→ 本地语义帧解析
→ 候选重排序
→ 风险判断
→ 自动执行 / 用户确认 / 追问 / 拒绝
→ 页面展示与本地语音回复
```

默认配置不会启用双 ASR，也不会加载 Whisper：

```text
VOICE_ASR_ENGINE=sensevoice
VOICE_ENABLE_DUAL_ASR=0
VOICE_ASR_FALLBACK_ENGINE=none
VOICE_WHISPER_ALLOW_DOWNLOAD=0
```

## 环境准备

推荐使用 Python 3.11 和独立 Conda 环境。

```powershell
conda create -n flow_calendar python=3.11
conda activate flow_calendar
pip install -r requirements.txt
```

本地 SenseVoice 运行时需要额外安装：

```powershell
pip install torch torchaudio funasr modelscope
```

`requirements.txt` 保留项目基础依赖。SenseVoice 相关依赖单独安装，便于不需要语音模型的开发环境继续运行文本和单元测试。

## 本地 SenseVoice 模型配置

推荐提前下载 `iic/SenseVoiceSmall`，并通过环境变量指定本地模型目录。不要将模型权重提交到 Git。

Windows PowerShell：

```powershell
$env:VOICE_ASR_ENGINE="sensevoice"
$env:VOICE_SENSEVOICE_MODEL_PATH="<LOCAL_SENSEVOICE_MODEL_PATH>"
$env:VOICE_SENSEVOICE_ALLOW_DOWNLOAD="0"
$env:VOICE_ENABLE_DUAL_ASR="0"
$env:VOICE_ASR_FALLBACK_ENGINE="none"
$env:VOICE_WHISPER_ALLOW_DOWNLOAD="0"
```

ModelScope 的常见本地缓存位置可以写为：

```text
%USERPROFILE%\.cache\modelscope\hub\models\iic\SenseVoiceSmall
```

默认不会自动下载 SenseVoice 或 Whisper 权重。`ffmpeg` 未安装时，SenseVoice 仍可通过 `torchaudio` 读取部分音频格式；如果遇到格式兼容问题，建议额外安装 `ffmpeg`。

### 可选 Whisper fallback

Whisper `large-v3-turbo` 仅作为显式开启的本地 fallback 保留。建议优先准备本地模型目录：

```powershell
$env:VOICE_ENABLE_DUAL_ASR="1"
$env:VOICE_ASR_FALLBACK_ENGINE="whisper"
$env:VOICE_WHISPER_MODEL_PATH="<LOCAL_WHISPER_MODEL_PATH>"
$env:VOICE_WHISPER_ALLOW_DOWNLOAD="0"
```

只有显式将 `VOICE_WHISPER_ALLOW_DOWNLOAD` 设为 `1` 时，才允许 `faster-whisper` 下载配置的模型。

## 启动项目

在仓库根目录运行：

```powershell
python -m streamlit run app.py --server.port 8501
```

打开终端输出的本地地址，并允许浏览器使用麦克风。

仓库中的 `.streamlit/config.toml` 已关闭 Streamlit file watcher。原因是 FunASR 会加载 `transformers`，Streamlit 默认 watcher 可能扫描无关的可选视觉模块并输出 `torchvision` 缺失噪声。关闭 watcher 后，修改 Python 文件需要手动重启 Streamlit。

## 配置说明

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `VOICE_ASR_ENGINE` | `sensevoice` | 默认本地 ASR 引擎 |
| `VOICE_ASR_MODEL` | `iic/SenseVoiceSmall` | SenseVoice 模型名 |
| `VOICE_SENSEVOICE_MODEL_PATH` | 当前用户的 ModelScope 缓存目录 | 本地 SenseVoice 模型路径 |
| `VOICE_SENSEVOICE_ALLOW_DOWNLOAD` | `0` | 是否允许自动下载 SenseVoice |
| `VOICE_ENABLE_DUAL_ASR` | `0` | 是否开启双 ASR 比较 |
| `VOICE_ASR_FALLBACK_ENGINE` | `none` | fallback ASR 引擎 |
| `VOICE_WHISPER_MODEL` | `large-v3-turbo` | 可选 Whisper 模型名 |
| `VOICE_WHISPER_MODEL_PATH` | 空 | 本地 Whisper 模型路径 |
| `VOICE_WHISPER_ALLOW_DOWNLOAD` | `0` | 是否允许自动下载 Whisper |
| `VOICE_ASR_LANGUAGE` | `zh` | Whisper fallback 的识别语言 |
| `VOICE_ALLOW_CLOUD` | `0` | 是否允许 UI 使用可选云端语义解析 |
| `VOICE_ENABLE_TRACE` | `1` | 是否写入本地语音理解 trace |
| `VOICE_TRACE_DIR` | `outputs/voice_traces` | 本地 trace 目录 |
| `VOICE_SAVE_RAW_AUDIO` | `0` | 是否保存原始音频，默认关闭 |
| `VOICE_ENABLE_ASR_DIAGNOSTICS` | `1` | 是否打印本地 ASR 诊断日志 |

完整配置和语音理解设计见 [本地语音理解引擎文档](docs/local_voice_understanding_engine.md)。

## 测试方式

运行完整测试：

```powershell
python -m pytest -q
```

运行文本侧 smoke test：

```powershell
python scripts/voice_pipeline_smoke_test.py
```

验证真实语音样本清单但不加载模型：

```powershell
python scripts/voice_samples_regression.py
```

显式执行本地真实语音回归：

```powershell
python scripts/voice_samples_regression.py --run-local-asr
```

当前已验证结果：

```text
277 passed
```

## 项目结构

```text
app.py                              # Streamlit 页面、交互流程和语音回复
src/
  asr_adapter.py                    # SenseVoice、FunASR、Whisper 和 Mock ASR 适配器
  voice_config.py                   # 本地语音环境变量配置
  voice_pipeline.py                 # 兼容旧接口的语音流水线入口
  voice_understanding/              # 候选、语义帧、重排序、风险策略和 trace
  command_parser.py                 # 本地规则语义解析器
  glm_semantic_parser.py            # 可选 GLM 语义解析器
  task_store.py                     # 本地 JSON 任务存储
  calendar_view.py                  # 月历和日时间线视图
tests/                              # 单元测试与本地零云端测试
scripts/                            # smoke test 与语音样本回归脚本
docs/                               # 详细设计文档
.streamlit/config.toml              # 关闭 Streamlit watcher
```

## 隐私与费用说明

- 默认语音识别在本机运行，不上传录音。
- 默认不调用 OpenAI、Google、Azure、智谱等云端 ASR 服务。
- 默认不调用云端语义解析器。
- 默认不加载或下载 Whisper `large-v3-turbo`。
- 原始音频默认不保存，`VOICE_SAVE_RAW_AUDIO=0`。
- 本地 trace 默认开启，写入 `outputs/voice_traces/YYYYMMDD.jsonl`。
- trace 和 `[flowcal-asr]` 诊断日志可能包含识别文本。处理真实私人日程时，请妥善保护本地输出目录，必要时关闭 trace 和诊断日志。
- `outputs/`、音频文件、模型权重、密钥和本地配置不应提交到 Git。
- 显式开启云端能力、模型下载或 Whisper fallback 前，请自行确认费用、磁盘空间和隐私影响。

## 常见问题

### 为什么切到分支后默认使用 SenseVoice？

`src/voice_config.py` 将 `VOICE_ASR_ENGINE` 的默认值设为 `sensevoice`。启动后会优先加载本地 `SenseVoiceSmall` 目录，不会默认下载模型。

### 为什么没有安装 ffmpeg 也能识别？

SenseVoice 可以通过 `torchaudio` 读取部分音频格式。安装 `ffmpeg` 可以扩展格式兼容性，但不是当前本地识别的硬性前提。

### 为什么关闭 Streamlit watcher？

FunASR 会加载 `transformers`。Streamlit watcher 扫描第三方模块时，可能误触发无关视觉模块的可选依赖检查并输出 `torchvision` 缺失 traceback。该噪声与语音识别无关，因此项目关闭 watcher。修改代码后请手动重启服务。

### 为什么不默认启用 Whisper fallback？

Whisper `large-v3-turbo` 模型较大。默认关闭可以避免首次录音时突然下载权重，也能减少磁盘占用和等待时间。

### 为什么 SenseVoice 原始输出中有 `<|zh|><|NEUTRAL|>`？

这些是 SenseVoice 返回的语言、情绪或音频类型元数据。适配器会使用通用正则清理 `<|...|>` 标签，并保留原始结果用于本地诊断。

### 为什么有些操作需要确认？

删除、修改、语音标记完成以及存在候选扩展或低置信度的操作具有误操作风险。系统会要求确认或追问，避免静默写入错误日程。

### 如果语音识别仍然不准，应该如何排查？

1. 确认 `VOICE_SENSEVOICE_MODEL_PATH` 指向已准备好的本地模型目录。
2. 检查终端中的 `[flowcal-asr]` 日志，关注 `raw_text`、`cleaned_text`、音频时长和质量信息。
3. 在安静环境中重新录音，并尽量说完整的日期、时间和任务标题。
4. 将可公开的本地样本加入 `examples/voice_samples/manifest.json`，运行回归脚本。
5. 如需双模型比较，再显式开启本地 Whisper fallback。

## 后续改进方向

- 持续积累脱敏后的真实语音回归样本。
- 扩展更多中文时间表达和口语省略场景。
- 增加可维护的用户词表与反馈学习机制。
- 完善可选本地 Whisper fallback 的离线准备流程。
- 增强噪声、静音和异常音频的质量检测。
