1. 使用 runner 作为 case 执行中枢
2. 阶段 B-2 只模拟 tool_calls 和 streaming chunks，不做完整解析
3. RunResult 保留 raw response / chunks