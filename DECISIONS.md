1. 使用 runner 作为 case 执行中枢
2. 阶段 B-2 只模拟 tool_calls 和 streaming chunks，不做完整解析
3. RunResult 保留 raw response / chunks

# 阶段 C-2 设计决策记录

## Decision: streaming chunks 单独使用 stream_parser.py

日期：2026-07-10

决定：

新增 `src/infermatrix/parsers/stream_parser.py`，专门处理 OpenAI-compatible streaming chunks。

理由：

streaming response 不是一个完整 message，而是一组 chunk。它的核心逻辑是合并 `delta.content`、识别 `delta.role` 和 `finish_reason`，与普通 chat completion parser、tool call parser 的结构不同。

## Decision: 阶段 C-2 只合并文本，不解析 JSON

日期：2026-07-10

决定：

`parse_streaming_chunks()` 只负责输出 `merged_content`，不负责 `json.loads()` 或 JSON Schema 校验。

理由：

stream parser 的职责是把 chunks 合并成文本。structured output parser 和 schema checker 应该在后续阶段完成，避免职责混乱。

## Decision: 要求 streaming chunks 包含 assistant role 和 finish_reason

日期：2026-07-10

决定：

阶段 C-2 暂时要求 chunks 中必须出现 `delta.role == "assistant"`，并且必须出现非空 `finish_reason`。

理由：

这是当前 mock backend 的稳定格式，也有利于初期 parser 行为清晰。后续接真实 backend 时，如果发现兼容性差异，再根据真实样本调整。