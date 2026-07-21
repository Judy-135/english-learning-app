# 英语朗读学习助手 · 产品规划与开发规范文档（Product Spec）

> 本文档面向**后续接手开发与完善的 AI / 工程师**，目标是让任何一位新接手者无需口头沟通即可：
> 1. 准确理解本产品是什么、为谁服务；
> 2. 复刻/还原全部现有功能与 UI；
> 3. 在既有架构上安全地新增、修改、优化功能。
>
> 文档与代码严格对应 `english-learning-app/` 目录的当前实现（截至 2026-07-21）。凡与代码冲突，以代码为准；改动后请同步更新本文件「版本/状态」时间戳。

---

## 0. 一句话定位

**一个零后端的单文件网页应用**：用户粘贴英文文本 → 自动分句、逐词/短语高亮跟读、点击任意单词即查释义并收藏生词本、句子级翻译。面向英语学习者，主打「朗读 + 即点即查」的轻量学习闭环。

- 核心价值：*听（TTS 跟读）+ 读（高亮）+ 查（点词即译）+ 记（生词本）* 一站式。
- 形态：纯静态网页（`index.html` 单文件内联 CSS/JS），可本地打开、可托管 GitHub Pages、可用配套 Python 代理部署到 Render 公网。
- 依赖原则：**前端零第三方库**；后端代理仅用 Python 标准库（无 pip 依赖）。

---

## 1. 目标用户与场景

| 维度 | 说明 |
|---|---|
| 主要用户 | 英语学习者（含备考/日常/职场），偏好「朗读跟读 + 即时查词」 |
| 使用设备 | 桌面浏览器 + 移动端浏览器（iOS Safari / Android Chrome 均已适配） |
| 典型场景 | ① 跟读新闻/演讲稿练发音 ② 阅读长文时点词查义 ③ 攒生词本复习 ④ 回看历史文本 |
| 网络要求 | 查词/翻译需联网；朗读使用浏览器内置 TTS，离线可用（无音则降级提示） |
| 账户体系 | **无**。所有个人数据存浏览器 `localStorage`，不跨设备同步 |

---

## 2. 功能清单（Functional Spec）

所有功能均在 `index.html` 的单个 IIFE `(function(){...})()` 内实现。以下按模块列出**可见行为**与**代码锚点**（行号对应提交 `fc67b1d` 的 index.html）。

### 2.1 文本输入与生成
| 功能 | 行为 | 代码锚点 |
|---|---|---|
| 粘贴文本 | 文本框 `textarea#sourceText`，`rows=7`，`spellcheck=false` | L332, L214 |
| 生成学习视图 | 点击「生成学习视图」→ 分句、渲染、翻译、入历史 | `generateView()` L1159 |
| 填入示例 | 一键填入内置 ESG 主题样例 | `exampleBtn` L1175, `EXAMPLE` L1154 |
| 收起/展开输入 | 顶栏「收起输入」按钮，隐藏 `#inputPanel` | L1177 |
| 输入提示 | `inputHint` 显示状态（如「已生成 N 个句子」），4s 后自动消失 | `setHint()` L1149 |

### 2.2 分句与渲染
- **分句规则** `splitSentences()` L535：先 `\s+` 归一空白，再用正则 `/[^.!?]+[.!?]+["')\]»”’]*|\S[^.!?]*$/` 按句号/问号/感叹号切句；兜底返回整段。
- **分词** `tokenize()` L543：正则 `/\b[\w']+\b/g` 提取单词并记录 `start/end` 偏移，用于后续逐词高亮定位。
- **短语标注** `markPhrases()` L553：用内置 `PHRASES` 词库（约 230 条常用搭配，L415）+ 最长匹配，给相邻单词打 `phrase` 标记。
- **渲染** `renderSentences()` L608：每句一个 `.sentence-block`，内含 `.sentence-original`（带可点单词 span）与 `.sentence-translation`（默认「翻译加载中…」）。

### 2.3 朗读（Web Speech API）
| 功能 | 行为 | 代码锚点 |
|---|---|---|
| 播放 | 从当前句（或第 0 句）开始逐句朗读 | `startPlayback()` L729 / `speakSentence(i)` L700 |
| 暂停/继续 | `speechSynthesis.pause()/resume()`，按钮文案在「播放/继续」间切换 | `pausePlayback()` L740, `updateTransportUI()` L793 |
| 停止 | `cancel()` 并清空高亮、进度归零 | `stopPlayback()` L747 |
| 语速 | 滑块 `0.5x–2.0x`（步进 0.1），实时标签；变更后重读当前句 | `rateSlider` L1887, `reSpeakCurrent()` L761 |
| **逐句重复** | 控制栏「重复」下拉选 ×1/×2/×3/×5：每句朗读达到设定遍数后再进下一句，重复间留 `REPEAT_GAP_MS=350ms` 停顿；进度标签显示「(第2/3遍)」 | `repeatCount`/`currentRepeat` 状态变量；`speakSentence` 的 `onend` 重播逻辑 |
| 发音人选择 | 下拉 `#voiceSelect` 列出英文嗓音；选择持久化到 localStorage | `loadVoices()` L650, `pickVoiceByIndex()` L690 |
| 单句/单词朗读 | 点单词卡片「朗读单词」、生词本「朗读」，均用 `speakWord()` L995 | L955, L1086 |
| 逐词高亮 | `onboundary` 事件按 `charIndex` 给当前词加 `.speaking`（**见 §6 限制**） | `highlightWord()` L776 |

**移动端发音修复（重要）**：不再缓存会过期的 `SpeechSynthesisVoice` 对象，改为**存嗓音名字字符串**（`selectedVoiceName` + localStorage `elapp_voice`），每次朗读前 `getResolvedVoice()` L643 按名字重新解析。并加 `ensureVoicesLoaded()` L677 轮询兜底（移动端 `getVoices()` 首调常空），朗读前 `cancel()` 清队列（iOS 首句不响问题）。

### 2.4 翻译
- **优先级**：`usesDeepl()` L896 为真（本地存了 DeepL key 或服务器有 key）→ 走 DeepL；否则 MyMemory。
- **DeepL 调用** `translateViaDeepl()` L858：
  - 若检测到同源代理 `deeplProxyBase`（见 §4），POST 到 `/__deepl/translate`（绕 CORS）；
  - 否则直连 `https://api-free.deepl.com/v2/translate`（需自带 key，浏览器直连会被 CORS 拦）。
- **MyMemory 兜底** `translateViaMyMemory()` L847：直连 `api.mymemory.translated.net`，`langpair=en|zh-CN`；若返回 `MYMEMORY WARNING`（超额）则抛错。
- **失败回退**：`doTranslate()` L897 捕获 DeepL 错误后自动回退 MyMemory；若代理 401，提示「token 可能有误」。
- **批量翻译** `translateAll()` L925：生成视图后对所有句子并发翻译并填入译文区。
- **翻译源标签**：控件栏 `transSourceLabel` 实时显示「MyMemory / DeepL（代理）/ DeepL（服务器密钥）/ DeepL（直连/CORS受限）」。

### 2.5 点词即查（单词卡片）
- 点击阅读区任意单词（`click`/`Enter`/`Space`）→ `showWordCard()` L981：
  - 先显示「查询中…」，定位卡片到锚点词下方（边界自动翻转，`positionCard()` L967）；
  - `lookupWord()` L808：先查 `dictionaryapi.dev`（音标/词性/英文释义），再查翻译（中文），二者皆失败则用内置 `FALLBACK_DICT`（约 60 个高频词，L473）；
  - `renderWordCard()` L933 渲染：单词 + 音标 + 词性标签 + 中文 + 英文释义 + 「朗读单词」「加入生词本」按钮。
- 关闭：卡片外点击 / `Esc` / 滚动页面（`scroll` 监听 L1318 自动关）。

### 2.6 生词本（Vocabulary）
- 数据：`localStorage` key `elapp_vocab`（数组，最新在前），`addToVocab()` L1011。
- 字段：`{ word, phonetic, pos[], zh, enDef, addedAt }`。
- 操作：加入（去重）、移除、导出 JSON（`exportVocab()` L1027）、朗读。
- 顶栏「生词本」按钮带数量徽标 `vocabBadge`，点开右侧抽屉式面板（`side-panel`）。

### 2.7 历史记录（History）
- 数据：`localStorage` key `elapp_history`，最多保留 30 条（`addHistory()` L1036），去重。
- 操作：载入（回填文本框并重生成）、删除、清空。
- 顶栏「历史记录」徽标 `historyBadge`，同一右侧面板切 tab。

### 2.8 设置（翻译密钥）
- 弹窗 `settingsModal`（L300）含两项输入：`deeplKey`（DeepL 密钥）、`proxyToken`（代理访问 Token）。
- 操作：保存并测试、清除密钥、查询 DeepL 额度（`checkDeeplUsage()` L1243，调用 `/__deepl/usage`）。
- 持久化：key 存 `elapp_deepl_key`，token 存 `elapp_proxy_token`。
- 智能提示：若服务器已配 `DEEPL_API_KEY`（`serverHasDeeplKey`），DeepL 密钥输入框显示「可选」，引导用户只填代理 Token。

### 2.9 图片 OCR 文字识别
- **入口**：输入面板「📷 上传图片」按钮（`#uploadBtn` 标签 → `#imageInput` 文件选择）。
- **引擎**：`Tesseract.js v5`（CDN `https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js`），**按需动态注入** `<script>`，首次使用自动下载 `eng` 训练数据（约 10MB，IndexedDB 缓存）。
- **流程** `handleImageOCR()`：加载引擎 → `Tesseract.recognize(file, "eng", {logger})` → 报告百分比进度到 `inputHint` → `reconstructOcrText()` 重建文本 → 填入 `#sourceText` 并自动 `generateView()`。
- **准确性要点**：
  - 仅英文（`eng`），面向印刷体英文最佳。
  - `reconstructOcrText()` 从 `data.blocks → paragraphs → lines → words` 抽取，按行 `bbox.y0` 排序，**依行间距 > 行高×1.3 判定为段落分隔**，从而保留换行与段落结构（解决「段落切换不准」）。
  - 识别结果**自动回填到可编辑文本框并立即生成视图**，用户可随手修正 OCR 误差（这是应对「单词识别不准」的实用兜底）；完成提示含置信度百分比。
- 依赖：联网、CDN 可达；离线时给出明确失败提示。

---

## 3. UI / UX 设计规约（Design Spec）

> 复制 UI 时请严格遵循以下 token 与结构，保持视觉一致性。所有样式在 `<style>`（L7–182）。

### 3.1 设计语言
- 风格：现代、干净、轻量，卡片化 + 柔和阴影，主次分明。
- 主题：浅色为主，靛蓝（`#4f46e5`）作主色（accent）。
- 字体栈：`"Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif`。
- 圆角 `--radius: 14px`；阴影两级 `--shadow` / `--shadow-sm`。
- 无障碍：所有交互元素 `tabIndex`/`aria-label`，支持键盘（`Enter`/`Space` 触发点词，`Esc` 关闭弹层）；尊重 `prefers-reduced-motion`（L179 全局去动画）。

### 3.2 颜色变量（CSS 自定义属性，L8–25）
| 变量 | 值 | 用途 |
|---|---|---|
| `--bg` | `#f6f7fb` | 页面背景 |
| `--surface` | `#ffffff` | 卡片/面板背景 |
| `--surface-2` | `#f0f2f8` | 输入框/次级背景 |
| `--border` | `#e3e6ef` | 描边 |
| `--text` | `#1f2430` | 主文字 |
| `--text-muted` | `#6b7280` | 次要文字 |
| `--accent` | `#4f46e5` | 主色（按钮/高亮/选中） |
| `--accent-soft` | `#eef2ff` | 主色浅底（标签/激活态） |
| `--phrase-bg` | `#fff3cd` | 短语底色 |
| `--phrase-border` | `#f0d27a` | 短语下划线 |
| `--speaking-bg` | `#ffe08a` | 正在朗读单词底色 |
| `--playing-bg` | `#eef2ff` | 正在朗读句子底色 |
| `--danger` | `#dc2626` | 错误/危险操作 |

### 3.3 页面结构（自上而下）
```
┌─ Header (.app-header, 不吸顶)
│   ├─ 品牌：图标 + 「英语朗读学习助手」+ 副标题「粘贴英文 · 自然朗读 · 短语高亮 · 即点即查」
│   └─ 右侧操作：生词本(徽标) / 历史记录(徽标) / ⚙设置 / 收起输入
├─ Main (.app-main, max-width 1080px)
│   ├─ 输入面板 (.input-panel)：textarea + [生成学习视图][填入示例][📷上传图片] + hint
│   ├─ 控制栏 (.controls, ★position:sticky;top:0★ 仅此栏吸顶)
│   │   ├─ 传输：[播放][暂停][停止]
│   │   ├─ 语速：[滑块 0.5–2.0][1.0x 标签]
│   │   ├─ 重复：[下拉 ×1/×2/×3/×5]（每句重复播放遍数）
│   │   └─ 右侧：[进度 x/y][隐藏翻译][翻译源标签][发音 ▼]
│   └─ 阅读区 (.reading-area)
│       ├─ 空状态 (.empty-state)
│       └─ 句子列表 (.sentences) → 每句 .sentence-block(.playing)
│           ├─ .sentence-original（单词 span：.word / .word.phrase / .word.speaking）
│           └─ .sentence-translation
├─ 单词卡片 (.word-card, fixed 定位, 跟随锚点词)
├─ 右侧抽屉 (.side-panel + .overlay)：生词本 / 历史记录 两个 tab
└─ 设置弹窗 (.modal)：DeepL 密钥 + 代理 Token
```

### 3.4 关键组件视觉
- **单词**：默认可点（`cursor:pointer`），hover 变主色浅底；`.phrase` 黄底+下划线；`.speaking` 橙底。
- **句子块**：`.playing` 时浅蓝底 + 左侧主色竖条；朗读时 `scrollIntoView` 居中。
- **控制栏吸顶**：仅 `.controls` 吸顶（`position:sticky;top:0;z-index:15`），Header 与生词本/历史面板**不吸顶**（用户明确需求）。
- **右侧抽屉**：宽 380px（移动端 `92vw`），从右滑入（`transform:translateX`，`.open` 切换），`100dvh` 全高。
- **设置弹窗**：居中卡片，背景遮罩 `rgba(17,20,30,.45)`，淡入+上移。

### 3.5 响应式（@media max-width:720px, L171）
- 控制栏 `gap` 收紧；`.right-controls` 占满整行 `justify-content:space-between`。
- 语速滑块缩至 110px；发音下拉字号 16px（便于手指点击）。
- 正文 `font-size` 由 18px → 16.5px；阅读区内边距收紧。

---

## 4. 技术架构（Architecture）

```
┌─────────────────────────── 浏览器 (index.html) ───────────────────────────┐
│  Vanilla JS (无框架)                                                        │
│  • 文本处理（分句/分词/短语标注）                                           │
│  • Web Speech API（朗读 + 逐词高亮）                                        │
│  • 翻译：dictionaryapi.dev + (DeepL | MyMemory)                            │
│  • 持久化：localStorage（生词本/历史/密钥/发音）                            │
│  • 自动探测同源代理：GET /__deepl/health                                    │
└───────────────┬───────────────────────────────┬──────────────────────────┘
                │ 同源（无 CORS）                 │ 直连（CORS 受限）
                ▼                                ▼
        ┌──────────────┐              api-free.deepl.com (仅当浏览器直连且自带 key)
        │ deepl_proxy  │  ← 可选，公网部署时必需
        │ (Python 标准库)│
        └──────┬───────┘
               ▼
        api-free.deepl.com / api.deepl.com
```

### 4.1 前端技术栈
- **零框架**：纯 HTML + CSS + 原生 JS（ES5+ 兼容写法，IIFE 封装作用域）。
- **TTS**：`window.speechSynthesis` + `SpeechSynthesisUtterance`。
- **OCR（按需）**：`Tesseract.js v5`（CDN 动态注入，仅图片识别功能用到；默认不加载，不污染首屏）。
- **翻译/查词 API**：见 §5。
- **持久化**：`localStorage`（key 见 §4.4）。
- **状态管理**：模块内闭包变量（`sentences`, `isPlaying`, `currentRate`, `selectedVoiceName` 等），无外部状态库。

### 4.2 后端代理 `deepl_proxy.py`（纯标准库）
解决 **DeepL 不允许浏览器跨域直连** 的核心问题。部署在同源（或 Render）后，网页把翻译请求发给它，它代发 DeepL 返回结果。

**路由：**
| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/__deepl/health` | 永远开放 | 返回 `{ok, token_required, server_has_key, note}`，供前端探测 |
| POST | `/__deepl/translate` | 需 Token（若启用） | body `{text, target_lang, key?, token?}` → 转发 DeepL |
| GET | `/__deepl/usage` | 需 Token（若启用） | `?key=&token=` → 返 DeepL 额度 |
| 其它 | 静态文件 | — | 托管同目录 `index.html` 等 |

**环境变量：**
- `DEEPL_PROXY_HOST` 默认 `0.0.0.0`（对外）；
- `PORT` / `DEEPL_PROXY_PORT` 默认 `8000`；
- `DEEPL_PROXY_TOKEN`：设置后，translate/usage 必须携带 `X-Proxy-Token` 头或 `token` 参数，否则 401（防盗用额度）；
- `DEEPL_API_KEY`：服务器端托管密钥；设置后**网页无需填 DeepL key** 即可翻译（代理自动用），health 返回 `server_has_key:true`。
- **SSRF 防护**：仅转发到 `api-free.deepl.com` 或 `api.deepl.com`，不接受任意 URL。

### 4.3 部署形态
| 形态 | 适用 | DeepL 可用性 |
|---|---|---|
| 本地 `python3 deepl_proxy.py` | 仅自己电脑 | 走代理，可用 |
| GitHub Pages 纯静态 | 免费托管网页 | ❌ 跑不了代理 → 退回 MyMemory |
| Render（Blueprints, `render.yaml`） | 公网+代理 | ✅ 配 `DEEPL_PROXY_TOKEN` 后用代理 |
| 仅 `index.html` 双击打开 | 临时试用 | 直连 CORS 受限，仅 MyMemory |

- **GitHub vs Render 关系**：GitHub 只存代码；Render 监听仓库 push 自动重部署。改**环境变量**（如加 `DEEPL_API_KEY`）需 Render 后台 **Manual Deploy**，**GitHub push 不会触发**。

### 4.4 localStorage 数据字典
| Key | 内容 | 代码 |
|---|---|---|
| `elapp_vocab` | 生词本数组 | L388 |
| `elapp_history` | 历史记录数组（≤30） | L389 |
| `elapp_deepl_key` | DeepL 密钥（可选） | L396 |
| `elapp_proxy_token` | 代理 Token | L397 |
| `elapp_voice` | 选中的发音人名字 | L382 |

---

## 5. 外部 API 契约（供替换/升级参考）

| API | 端点 | 用途 | 鉴权 | 限制 |
|---|---|---|---|---|
| dictionaryapi.dev | `GET /api/v2/entries/en/{word}` | 音标/词性/英文释义 | 无 | 纯英文词条，部分短语无 |
| DeepL Free | `POST api-free.deepl.com/v2/translate`（`:fx` 密钥） | 高质量翻译 | `DeepL-Auth-Key` 头 | 50万字符/月；**禁止浏览器直连（CORS）** |
| DeepL Usage | `GET /v2/usage` | 额度查询 | 同上 | — |
| MyMemory | `GET api.mymemory.translated.net/get?q=&langpair=en|zh-CN` | 兜底翻译 | 无 | 每日有额度，超额返回 `MYMEMORY WARNING` |

> 替换翻译引擎（如接入 Google/有道/火山）时，只需在 `translateViaDeepl` 同层新增 `translateViaXxx` 并在 `doTranslate` 中编排优先级即可，UI 无需改动。

---

## 6. 已知限制与待完善项（Roadmap / Open Issues）

> 这是给「后续 AI 完善功能」最重要的指引——清楚标注了**什么能做、什么被平台卡死、建议怎么改**。

### 6.1 平台硬限制（非 bug，谨慎承诺）
- **iOS Safari 逐词高亮失效**：iOS 基本**不触发** `SpeechSynthesisUtterance.onboundary` 事件，故 `.speaking` 逐词高亮在 iPhone 上不工作。音色/选音已修，高亮属平台限制。
  - *建议方案*：改用「基于定时器 + 词长估算」的近似高亮（不可靠但可感知），或在 UI 注明该限制。
- **发音质量依赖设备**：音色由系统/浏览器提供。机械感可在 iOS **设置→辅助功能→语音内容→嗓音→英语** 下载增强嗓音（如 Samantha Enhanced）改善。
- **无账户/云端同步**：生词本与历史仅存本地浏览器，清缓存或换设备即丢失。
  - *建议方案*：导出/导入 JSON 已实现；可做「导出为 Anki/CSV」或接云存储。

### 6.2 功能缺口（值得补的）
1. **生词本复习模式**：目前仅收藏+朗读，缺「测验/闪卡/拼写练习」。
2. **整段/选中朗读**：当前只能逐句自动播放，建议支持「点哪句播哪句」「框选朗读」。
3. **翻译语言可切换**：目标语写死 `ZH`，建议支持日语/韩语等多目标。
4. **音色预览**：下拉选项旁无试听，建议 hover/点击可试听。
5. **空状态引导**：首次进入可加更友好的引导（如动图演示点词）。
6. **深色模式**：当前仅浅色主题。
7. **可访问性增强**：逐词高亮在 iOS 失效后，可考虑为视障用户增加 ARIA live 朗读进度。

### 6.3 工程待办
- [ ] 把 §6.1 的 iOS 近似高亮作为可选项实现。
- [ ] 生词本导入（当前只有导出）。
- [ ] 单元测试：分句/分词/短语标注的边界用例（缩写、引号、URL）。
- [ ] 把 `deepl_proxy.py` 的 SSRF 校验再加一层 host 白名单（当前仅路径白名单）。
- [ ] 代码拆分：当前单文件 1337 行，若继续膨胀建议拆分为 `app.js` + `styles.css` + `proxy/` 目录（注意保持「可双击打开 index.html」的零构建特性）。

---

## 7. 文件结构与接手指引

```
english-learning-app/
├── index.html          # ★核心：单文件应用（HTML+CSS+JS 内联，1337 行）
├── deepl_proxy.py      # 同源代理 + 静态服务器（Python 标准库，无依赖）
├── render.yaml         # Render Blueprints 部署配置（IaC）
├── Procfile            # Render/CloudStudio 启动命令
├── start.sh            # 通用启动脚本（取 PORT 环境变量）
├── requirements.txt    # 占位（声明无第三方依赖）
├── DEPLOY_RENDER.md    # Render 部署步骤说明
└── PRODUCT_SPEC.md     # 本文档
```

**接手第一步建议**：
1. 通读本文件 §2–§4，对照 `index.html` 行号快速建立心智模型。
2. 本地起服务验证：`python3 deepl_proxy.py` → 打开 `http://localhost:8000`。
3. 改前端直接编辑 `index.html`；改后端编辑 `deepl_proxy.py`。
4. 任何改动若影响功能/API 契约，请同步更新本文档并改 §0 时间戳。

---

*文档版本：v1.0 · 状态：对应代码提交 `fc67b1d`（2026-07-21）· 维护者：Judy-135*
