# Research Dream

面向科研场景的记忆巩固技能，适配任意挂载环境（OpenClaw、Codex、Claude Code、Cursor 等）。

`Research Dream` 用于 AI 助手长期陪伴科研用户时，把日常对话里的零散科研信号，逐步沉淀到记忆文件中，让记忆结构慢慢长成更稳定的科研数字分身。有原生分身工作区（如 OpenClaw）就用原生结构，没有就用自带的 `~/.research-dream/` 目录。

## 它做什么

- 在日常对话中做小步增量更新
- 在合适时机做一次更深的 consolidation
- 把信息分层写入 `USER.md`、`SOUL.md`、`MEMORY.md` 和 `memory/YYYY-MM-DD.md`
- 围绕“基础身份、能力、当前需求、认知风格、学术动机、人格特征、综合解读、审核记录”等维度持续沉淀

## 它不做什么

- 不额外引入新的 profile/schema/evidence 存储层
- 不把整份画像原样复制到单个文件
- 不伪造正式维度结果

## 工作方式

这个技能采用“双环机制”：

- 前台增量更新：对有价值的新信号做小步记录
- 后台周期性巩固：在时间与会话积累满足条件后，做一次更深的整理

深度整理的核心流程是：

```text
定向理解 -> 收集信号 -> 合并巩固 -> 修剪索引
```

## 文件分工

- `USER.md`：科研画像摘要
- `SOUL.md`：服务策略
- `MEMORY.md`：长期稳定模式
- `memory/YYYY-MM-DD.md`：短期动态与待观察项

## 适用场景

- 希望让 AI 助手（任意挂载环境）更持续地理解科研用户
- 希望把科研相关信息沉淀为更稳定的数字分身
- 希望沿用原版 dream-skill 的 consolidation 思路，但换成科研语义

## 入口

详细规则、触发逻辑和写入约束见 [SKILL.md](./SKILL.md)。

## 许可证

本项目采用 [MIT License](LICENSE)。
