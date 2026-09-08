[English](README.en.md) | **简体中文**

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/hero-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/hero-dark.svg">
  <img src="assets/presentation/hero-light.svg" width="960" alt="HarnessProbe — Make evaluation settings explicit before comparing.">
</picture>

**HarnessProbe 用类型化 profile 保存提示词和解码设置，将同一算术题子集交给兼容端点，并生成比较矩阵、HTML 与运行材料。**

`Python 3.12+` · [MIT](LICENSE) · [GitHub](https://github.com/SuperMarioYL/harnessprobe) · [网站](https://harnessprobe.lei6393.com)

## 为什么需要它

比较两次评测时，模型名之外还需要知道 system prompt、stop、温度及输出限制。把这些设置显式保存，才方便复查结果差异来自哪里。工具读取已有声明，不会自动发现厂商未公开的 harness，也不保证内置参考分数是当前官方结果。

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/process-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/process-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/process-dark.svg">
  <img src="assets/presentation/process-light.svg" width="960" alt="Validate before sending a request">
</picture>

## 架构

profile.py 解析受控 YAML 子集并用 Pydantic 验证。runner 将题目格式化后调用 OpenAICompatAdapter，评分并保存逐题结果；matrix 聚合得分与声明参考分的差距；report 生成 HTML 和 ZIP。缺少 key 或端点时 adapter 会走确定性 stub，必须与真实推理分开。

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/architecture-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/architecture-dark.svg">
  <img src="assets/presentation/architecture-light.svg" width="960" alt="Declared profiles to recorded evaluations">
</picture>

## 安装

需要 Python 3.12+。安装可能联网；先运行不发请求、不生成占位答案的配置示例。

```bash
git clone https://github.com/SuperMarioYL/harnessprobe.git
cd harnessprobe
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## 快速开始

```bash
python examples/presentation_demo.py
```

自带 YAML 声明 local-demo、64 token 上限、END stop 和空参考分数。真实 load_profile 成功解析；无 key 的 adapter 标为 stub；非法 reasoning_effort 被验证器拒绝。脚本没有调用 complete 或 run_match，因此没有模型分数。

## 用法

```bash
# 查看打包的 profile 元数据
harnessprobe profiles

# 配置好对应服务和凭据后，要求真实调用
harnessprobe match --models path/to/profile.yaml --bench aime --n 10 --require-live --html report.html --repro run.zip

# 从已有摘要状态重新渲染报告
harnessprobe report --state .harnessprobe-last.json --out report.html
```

自定义文件路径可作为 --models 的 profile key。只有 aime benchmark 路径被实现；这不等于完整官方 AIME 评测协议。--require-live 用于拒绝缺凭据情形，仍需核查每题请求是否成功。

## 能力与集成

| 组成 | 当前行为 |
|---|---|
| YAML profile | 加载、字段验证和元数据 |
| OpenAI 兼容 HTTP | system prompt、解码设置与题目请求 |
| 算术子集 | 格式化问题、提取整数答案、比较标准答案 |
| GapMatrix | 分数及与 profile 参考值之差 |
| HTML / ZIP | 汇总与当次逐题材料 |

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/integrations-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/integrations-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/integrations-dark.svg">
  <img src="assets/presentation/integrations-light.svg" width="960" alt="Configuration and result interfaces">
</picture>

## 配置与边界

请求中应用 model_name、system_prompt、temperature、max_tokens、stop_tokens、decoding 和 reasoning_effort。tool_call_template 与 provenance 可被保存，但当前 adapter 不根据它们构造 tools/function schema。

api_key_env 指定环境变量，base_url 可由 CLI --base-url 覆盖。缺 key 或端点时 stub 会生成基于标准答案的确定性测试输出；这些分数不能用于采购、模型排名或质量结论。published_score 只是输入参考值，gap 也不证明 harness 导致分差。

--save 的状态保存汇总，不含全部原始逐题响应。repro --state 会重新运行评测，可能重新请求服务，而不是恢复原始响应；要保存当次材料，在 match 时同时使用 --repro。

## 运行记录

v0.1.0 的真实离线配置预检，不是 benchmark。profile 中的 qwen 是 schema 允许的 vendor 标签，example-model 是构造模型标识，没有验证服务存在。

[输入、命令和完整输出](docs/demo-results.json)

[保留的历史终端录屏](assets/demo.gif) · [录制脚本](docs/demo.tape)。本轮示例以以上可重放记录为准。

## 路线图

- [x] 类型化 profile、兼容端点 runner 和比较矩阵。
- [x] HTML、当次结果 ZIP 和汇总状态。
- [ ] 交互 profile 编辑与更多评测任务。
- [ ] 更完整的服务兼容和协议验证。

不提供已经上线的企业授权套餐或经过认证的厂商私有 harness。

## 开发与许可证

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

请求字段实际应用见 harnessprobe/adapters/openai_compat.py。

[MIT](LICENSE) · [Issues](https://github.com/SuperMarioYL/harnessprobe/issues)
