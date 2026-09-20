# Email draft

**Subject:** Mini-Project Progress Update – Lightweight Data Selection Experiments

Dear Dr Wang and Dr Bao,

I would like to share a quick update on the mini-project. Over the past two days, I prepared a 1,000-example Spider candidate pool and used CodeT5-small's pretrained loss as an uncertainty score. I then selected 500 examples using three methods: random sampling, uncertainty sampling, and uncertainty sampling with a lightweight schema-diversity constraint.

For each method, I fine-tuned CodeT5-small for three epochs with five training seeds and evaluated the models on the full Spider development set of 1,034 examples. I also wrote a resumable script so the remaining runs and evaluation could continue while I was away for my examination.

The mean official Spider exact-match results were:

- Random: 15.36% ± 1.79 percentage points
- Uncertainty: 13.52% ± 1.10 percentage points
- Uncertainty + schema diversity: 17.00% ± 2.89 percentage points

The schema-diverse method had the best mean result and outperformed random sampling in four of five seeds. It also covered all 137 databases in the candidate pool, compared with 126.8 on average for random sampling and 114 for pure uncertainty sampling. My current understanding is that high-loss examples alone may be concentrated in a smaller group of difficult schemas, while the diversity constraint improves coverage.

My next goal is not only to improve accuracy, but to test whether diversity-aware selection can achieve better and more stable performance under the same data and computing budget. I will first separate database diversity from SQL-complexity balancing in an ablation and inspect the weaker seed.

If you think broader validation would be useful before Bunya access becomes available, I may be able to borrow a classmate's RTX 4070 to run additional seeds, selection budgets, or a larger model. Would you recommend doing this at this stage, or should I first focus on the ablation using the current setup?

I have attached a short stage report with the setup, results, limitations, and proposed next steps. Thank you for your guidance.

Best regards,
Zhanfei Zhang

---

# 中文翻译（供检查，不发送）

**主题：** 小型项目进展更新——轻量化数据选择实验

王博士、鲍博士，您好：

我想简要汇报一下小型项目的进展。在过去两天中，我准备了一个包含 1,000 条 Spider 样本的候选池，并使用 CodeT5-small 的预训练损失作为不确定性分数。然后，我在相同的 500 条数据预算下比较了三种方法：随机采样、不确定性采样，以及加入轻量化数据库结构多样性约束的不确定性采样。

对于每种方法，我都使用五个不同的训练种子对 CodeT5-small 进行了三轮微调，并在包含 1,034 条样本的完整 Spider 开发集上进行了评估。我还写了一个可恢复脚本，因此在我参加考试期间，剩余实验和评估可以继续运行。

官方 Spider 精确匹配率的平均结果为：

- 随机采样：15.36% ± 1.79 个百分点
- 不确定性采样：13.52% ± 1.10 个百分点
- 不确定性 + 数据库结构多样性：17.00% ± 2.89 个百分点

加入结构多样性的方法取得了最高的平均结果，并且在五个种子中的四个上优于随机采样。它还覆盖了候选池中的全部 137 个数据库，而随机采样平均覆盖 126.8 个，单纯不确定性采样覆盖 114 个。我目前的理解是，只选择高损失样本可能会集中于较少的困难数据库结构，而多样性约束改善了覆盖范围。

我下一阶段的目标不只是提高准确率，而是研究在相同数据量和计算预算下，考虑多样性的数据选择方法能否获得更好、更稳定的性能。我会先通过消融实验分开研究数据库多样性和 SQL 复杂度平衡的作用，并检查表现较弱的训练种子。

如果您认为在获得 Bunya 权限之前有必要做更广泛的验证，我可能可以借用同学的 RTX 4070，以运行更多训练种子、不同选样预算或更大的模型。请问您建议我现阶段这样扩展，还是先用当前配置专注完成消融实验？

我附上了一份简短的阶段报告，其中包含实验设置、结果、局限和下一步计划。感谢两位老师的指导。

此致
敬礼
Zhanfei Zhang
