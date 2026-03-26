# 多组件二维稳态导热与可视化

## 1. 这个升级例子解决了什么问题

`examples/02_multicomponent_steady_heat.py` 把之前的单矩形例子升级成了一个简单的多组件装配体：

- `base_plate`：底板
- `chip`：芯片，内部有热源
- `heat_spreader`：扩展块，用来把热量摊开

这个例子不再只是“一个区域里的温度变化”，而是开始接近“组件热仿真”的基本思路：

- 不同组件可以有不同材料参数
- 某个组件内部可以发热
- 热量会在组件之间传递

## 2. 运行命令

在项目目录执行：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python examples/02_multicomponent_steady_heat.py
```

如果你只想快速试一下更粗或更细的网格，可以在项目目录执行：

```bash
cd ~/msfenicsx
conda activate msfenicsx
python - <<'PY'
from pathlib import Path
import importlib.util

example_path = Path("examples/02_multicomponent_steady_heat.py")
spec = importlib.util.spec_from_file_location("multicomponent_example", example_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

module.run_example(output_root="outputs/tmp_case", nx=24, ny=10)
PY
```

这里的 `nx`、`ny` 只是临时覆盖状态里的网格参数，适合做可视化和收敛直觉练习。

## 3. 输出文件怎么看

结果会写到：

```text
outputs/02_multicomponent_steady_heat/
```

重点看这几个文件：

- `figures/overview.html`
  - 推荐入口，一个页面里切换布局、网格、分区和温度场
- `figures/layout.png`
  - 只看初始几何布局
- `figures/mesh.png`
  - 只看有限元网格
- `figures/subdomains.png`
  - 看每个组件对应的分区编号
- `figures/temperature.png`
  - 看静态温度场
- `figures/temperature.html`
  - 看交互式温度场
- `data/summary.txt`
  - 看整体和各组件的温度统计

## 4. 如何理解每一张图

### 4.1 `layout.png`

这张图回答的是：

- 组件一开始是怎么摆放的
- 哪个块是底板
- 哪个块是芯片
- 哪个块是扩展块

这一步对应工程里“建模布局”的阶段，还没有开始求解。

### 4.2 `mesh.png`

这张图回答的是：

- 连续几何区域是怎么被切成小三角形的
- 内部接口附近网格是不是连通的

有限元不是直接在连续区域上算，而是在这些小单元上近似求解，所以网格是仿真的基础。

### 4.3 `subdomains.png`

这张图回答的是：

- 哪些单元属于 `base_plate`
- 哪些单元属于 `chip`
- 哪些单元属于 `heat_spreader`

这一步特别重要，因为后面的材料参数 `k` 和热源 `q` 都要依赖这个分区。

### 4.4 `temperature.png`

这张图是静态温度场。

你可以重点看：

- 芯片附近温度最高，因为芯片内部有热源
- 热量向下传到底板，向上传到扩展块
- 左右边界温度是 0，所以越靠近左右边缘，温度越低

## 5. `temperature.html` 怎么看

推荐先打开 `figures/overview.html`。如果你只想单独看交互式温度，再打开 `figures/temperature.html`。

直接在 VS Code 文件树里点开，或者在浏览器里打开这个文件。

它是交互式三角面图，你可以：

- 旋转
- 缩放
- 悬停查看点附近的温度

这比纯 PNG 更适合后续做多个例子时对比热点位置和温度扩散趋势。

## 6. 这个例子的物理设置

控制方程是：

```text
-div(k grad(T)) = q
```

含义：

- `T` 是温度
- `k` 是导热系数
- `q` 是体热源

在这个例子里：

- `base_plate`：中等导热
- `chip`：较高导热，并且 `q > 0`
- `heat_spreader`：更高导热

边界条件：

- 左边界 `T = 0`
- 右边界 `T = 0`
- 其他外边界绝热

## 7. 如何读 `summary.txt`

示例输出里会有类似内容：

```text
component_summary:
  - base_plate: ...
  - chip: ...
  - heat_spreader: ...
```

你可以把它理解成“每个组件的大致温度水平”：

- `min`：该组件内最低温度
- `max`：该组件内最高温度
- `mean`：该组件内平均温度

如果某个组件的 `mean` 很高，通常说明它更热，或者它离热源更近。

## 8. 你下一步最值得尝试的改动

建议按这个顺序做小实验：

1. 改芯片热源强度
2. 改扩展块导热系数
3. 改芯片尺寸
4. 改左右边界温度

每改一项，就重新看：

- `layout.png`
- `subdomains.png`
- `temperature.png`
- `summary.txt`

这样你会非常快地建立“几何、材料、边界、热源和温度场”之间的直觉联系。

## 9. 这个例子和后面的自动优化是什么关系

现在这个多组件例子已经不只是一个孤立脚本了，它同时也是后面自动优化系统的 baseline。

对应关系可以这样理解：

- `states/baseline_multicomponent.yaml`
  - 定义当前几何、材料、热源、边界和网格
- `src/compiler/`
  - 把这个状态编译成可求解问题
- `src/evaluator/`
  - 判断当前设计是否满足约束
- `src/orchestration/`
  - 负责一轮轮运行并保存记录

所以你现在看到的布局图、网格图、分区图和温度场图，后面不只是“看图”，而是会成为每轮决策都能复盘的证据。
