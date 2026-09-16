# LEAD 代码小白导读

## 一句话理解

普通训练把全部题目都喂给模型；LEAD 会边训练边判断“哪些题目更值得学”，优先训练信息量大的少量样本，从而节省时间和算力。

## 官方代码的四步

1. `scripts/run_warmup_training.sh`
   - 先用一小部分数据训练一个“预热模型”。
   - 目的不是得到最终模型，而是帮助判断每条数据的难度。

2. `scripts/run_scoring.sh`
   - `difficulty_score.py`：估计样本难度。
   - `iu_score.py`：计算每条样本最初的训练价值。
   - `clustering.py`：把相似难度/特征的数据分组。

3. `scripts/run_lead.sh` -> `src/online/run_lead.py`
   - 粗选：`exp3.py` 把每个数据组当作一台老虎机，逐步偏向更有回报的组。
   - 细选：在选中的组里，优先取当前损失/价值较高的样本。
   - 模型训练后，代码继续更新样本价值，下一轮再重新选择。

4. `scripts/lora_merge.sh` 和 `scripts/eval.sh`
   - 合并 LoRA 权重并评估模型效果。

## 用人话看 `run_lead.py`

它反复执行下面这个循环：

```text
选择一个数据组
    -> 从组内挑最值得训练的样本
    -> 用这些样本训练一小轮
    -> 查看训练带来的变化
    -> 更新该组和样本的价值
    -> 进入下一轮
```

## BIRD 一条数据的结构

```json
{
  "db_id": "movie_platform",
  "question": "Who is the director of the movie Sex, Drink and Bloodshed?",
  "evidence": "Sex, Drink and Bloodshed refers to movie title = 'Sex, Drink and Bloodshed';",
  "SQL": "SELECT director_name FROM movies WHERE movie_title = 'Sex, Drink and Bloodshed'"
}
```

- `db_id`：应该查询哪一个数据库。
- `question`：用户的自然语言问题。
- `evidence`：额外提示，帮助理解题意或数据库中的值。
- `SQL`：标准答案。

数据库表结构不在这一行里，而是单独保存在 BIRD 的数据库/schema 文件中。真正训练时需要把“问题 + evidence + 对应数据库表结构”组成模型输入，把 SQL 作为模型输出。

## 不能直接照搬官方代码的地方

官方仓库使用的是通用指令数据和 Llama 路径示例，我们的项目至少要改四处：

1. 把 BIRD 的 question、evidence 和 schema 转成 Qwen3 的训练 prompt。
2. 把模型配置改为 Qwen3-1.7B，并使用 LoRA。
3. 加入 Full、Random、LEAD 三组公平对照。
4. 用 BIRD 的 execution accuracy (EX) 评估，而不是官方仓库现有的通用任务评估脚本。

## 现在已经完成与尚未完成

已完成：官方代码下载、代码结构确认、真实 BIRD 样例保存、改造点梳理。

待 Bunya 权限和完整数据可用后：创建 Python/PyTorch 环境、下载 Qwen3、准备完整 BIRD 数据与数据库、写转换脚本、先跑通 10-50 条 smoke test，再提交正式 GPU 任务。
